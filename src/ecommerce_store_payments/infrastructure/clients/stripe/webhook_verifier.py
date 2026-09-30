import hashlib
import json
from collections.abc import Callable
from typing import Any, cast, final
from uuid import UUID

import stripe

from ecommerce_store_payments.application.payments.webhook import (
    CheckoutNotification,
    CheckoutOutcome,
    VerifiedWebhook,
    WebhookDisabledError,
    WebhookInvalidError,
)
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.config.settings import Settings

EVENT_OUTCOMES = {
    "checkout.session.completed": CheckoutOutcome.SUCCEEDED,
    "checkout.session.async_payment_succeeded": CheckoutOutcome.SUCCEEDED,
    "checkout.session.async_payment_failed": CheckoutOutcome.FAILED,
    "checkout.session.expired": CheckoutOutcome.EXPIRED,
}


@final
class StripeWebhookVerifier:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def verify(self, payload: bytes, signature: str) -> VerifiedWebhook:
        """Verify the Stripe timestamp/signature before parsing a test-mode own-account snapshot."""
        secret = self._settings.stripe_webhook_secret
        if secret is None:
            raise WebhookDisabledError()
        try:
            # An endpoint-specific secret binds delivery to our account. Connect/organization events are rejected.
            verify_signature = cast(
                Callable[[str, str, str, int], bool], cast(Any, stripe.WebhookSignature).verify_header
            )
            verify_signature(payload.decode("utf-8"), signature, secret.get_secret_value(), 300)
            decoded: object = json.loads(payload, object_pairs_hook=self._unique_object)
            if not isinstance(decoded, dict):
                raise WebhookInvalidError()
            event = cast(dict[str, Any], decoded)
            if event.get("object") != "event" or event.get("livemode") is not False:
                raise WebhookInvalidError()
            if event.get("account") is not None or event.get("context") is not None:
                raise WebhookInvalidError()
            event_id = self._identifier(event.get("id"), "evt_")
            event_type = self._identifier(event.get("type"))
            outcome = EVENT_OUTCOMES.get(event_type, CheckoutOutcome.UNKNOWN)
            checkout = None
            if outcome is not CheckoutOutcome.UNKNOWN:
                checkout, outcome = self._checkout(event["data"]["object"], outcome)
            return VerifiedWebhook(event_id, event_type, hashlib.sha256(payload).hexdigest(), outcome, checkout)
        except (
            stripe.SignatureVerificationError,
            UnicodeError,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
        ) as error:
            raise WebhookInvalidError() from error

    @staticmethod
    def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise WebhookInvalidError()
            result[key] = value
        return result

    @staticmethod
    def _identifier(value: object, prefix: str = "") -> str:
        if (
            not isinstance(value, str)
            or not value.startswith(prefix)
            or len(value) <= len(prefix)
            or len(value) > 255
            or not value.isascii()
            or not value.isprintable()
            or any(ch.isspace() for ch in value)
        ):
            raise WebhookInvalidError()
        return value

    @classmethod
    def _checkout(
        cls, session: dict[str, Any], outcome: CheckoutOutcome
    ) -> tuple[CheckoutNotification, CheckoutOutcome]:
        if session.get("object") != "checkout.session" or session.get("livemode") is not False:
            raise WebhookInvalidError()
        if session.get("mode") != "payment" or session.get("currency") != "pln":
            raise WebhookInvalidError()
        amount = session["amount_total"]
        if isinstance(amount, bool) or not isinstance(amount, int) or not 200 <= amount <= 99_999_999:
            raise WebhookInvalidError()
        metadata = session["metadata"]
        payment_id, order_id, attempt_id = (UUID(metadata[key]) for key in ("payment_id", "order_id", "attempt_id"))
        if any(value.int == 0 for value in (payment_id, order_id, attempt_id)):
            raise WebhookInvalidError()
        if session.get("client_reference_id") != str(payment_id):
            raise WebhookInvalidError()
        session_id = cls._identifier(session["id"], "cs_test_")
        provider_payment_id = session.get("payment_intent")
        if provider_payment_id is not None:
            provider_payment_id = cls._identifier(provider_payment_id, "pi_")
        status = session.get("status")
        payment_status = session.get("payment_status")
        if outcome is CheckoutOutcome.SUCCEEDED:
            if status != "complete" or payment_status not in ("paid", "unpaid"):
                raise WebhookInvalidError()
            if payment_status == "unpaid":
                outcome = CheckoutOutcome.WAITING
            elif provider_payment_id is None:
                raise WebhookInvalidError()
        elif outcome is CheckoutOutcome.EXPIRED:
            if status != "expired" or payment_status != "unpaid":
                raise WebhookInvalidError()
        elif status != "complete" or payment_status != "unpaid":
            raise WebhookInvalidError()
        return CheckoutNotification(
            payment_id, order_id, attempt_id, Money(amount, "PLN"), session_id, provider_payment_id
        ), outcome
