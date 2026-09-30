import time
from typing import Any
from uuid import uuid4

import pytest
from pydantic import SecretStr

from ecommerce_store_payments.application.payments.webhook import (
    CheckoutOutcome,
    WebhookDisabledError,
    WebhookInvalidError,
)
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.clients.stripe.webhook_verifier import StripeWebhookVerifier
from ecommerce_store_payments.infrastructure.config.settings import Settings
from tests.webhook_fixtures import WEBHOOK_SECRET, encode, payload_for, signature


def setup_payload() -> tuple[StripeWebhookVerifier, dict[str, Any]]:
    payment = Payment.create(uuid4(), Money(1299, "PLN"))
    payment.begin_checkout()
    payment.mark_as_pending("cs_test_fixture")
    return StripeWebhookVerifier(Settings(stripe_webhook_secret=SecretStr(WEBHOOK_SECRET))), payload_for(payment)


def test_actual_sdk_signature_verification_maps_normalized_success_without_api_key() -> None:
    verifier, payload = setup_payload()
    body = encode(payload)
    result = verifier.verify(body, signature(body))
    assert result.outcome is CheckoutOutcome.SUCCEEDED
    assert result.checkout is not None and result.checkout.money == Money(1299, "PLN")
    assert result.checkout.provider_payment_id == "pi_fixture"


@pytest.mark.parametrize("invalid", ["missing", "tampered", "wrong_secret", "old", "malformed", "duplicate_json"])
def test_rejects_missing_invalid_stale_or_tampered_signature_and_payload(invalid: str) -> None:
    verifier, payload = setup_payload()
    body = encode(payload)
    header = signature(body)
    if invalid == "missing":
        header = ""
    elif invalid == "tampered":
        body += b" "
    elif invalid == "wrong_secret":
        header = signature(body, "whsec_other")
    elif invalid == "old":
        header = signature(body, timestamp=int(time.time()) - 301)
    else:
        body = b'{"private":' if invalid == "malformed" else b'{"id":"evt_a","id":"evt_b"}'
        header = signature(body)
    with pytest.raises(WebhookInvalidError):
        verifier.verify(body, header)


@pytest.mark.parametrize(
    "invalid",
    [
        "live",
        "connect",
        "organization",
        "session_live",
        "currency",
        "bool_amount",
        "float_amount",
        "missing_metadata",
        "invalid_uuid",
        "zero_uuid",
        "reference",
        "session_id",
        "payment_id",
        "missing_payment_id",
        "wrong_object",
        "wrong_status",
        "no_payment_required",
        "mode",
        "event_id",
    ],
)
def test_rejects_wrong_account_mode_and_inconsistent_checkout_contract(invalid: str) -> None:
    verifier, payload = setup_payload()
    session = payload["data"]["object"]
    if invalid == "live":
        payload["livemode"] = True
    elif invalid == "connect":
        payload["account"] = "acct_other"
    elif invalid == "organization":
        payload["context"] = "organization_other"
    elif invalid == "session_live":
        session["livemode"] = True
    elif invalid == "currency":
        session["currency"] = "eur"
    elif invalid == "bool_amount":
        session["amount_total"] = True
    elif invalid == "float_amount":
        session["amount_total"] = 1299.0
    elif invalid == "missing_metadata":
        del session["metadata"]
    elif invalid == "invalid_uuid":
        session["metadata"]["attempt_id"] = "invalid"
    elif invalid == "zero_uuid":
        session["metadata"]["attempt_id"] = "00000000-0000-0000-0000-000000000000"
    elif invalid == "reference":
        session["client_reference_id"] = str(uuid4())
    elif invalid == "session_id":
        session["id"] = "cs_live_other"
    elif invalid == "payment_id":
        session["payment_intent"] = "pi_space here"
    elif invalid == "missing_payment_id":
        session["payment_intent"] = None
    elif invalid == "wrong_object":
        session["object"] = "payment_intent"
    elif invalid == "wrong_status":
        session["status"] = "open"
    elif invalid == "no_payment_required":
        session["payment_status"] = "no_payment_required"
    elif invalid == "mode":
        session["mode"] = "subscription"
    else:
        payload["id"] = "evt_"
    body = encode(payload)
    with pytest.raises(WebhookInvalidError):
        verifier.verify(body, signature(body))


@pytest.mark.parametrize(
    "kind, status, paid, expected",
    [
        ("checkout.session.completed", "complete", "unpaid", CheckoutOutcome.WAITING),
        ("checkout.session.async_payment_succeeded", "complete", "paid", CheckoutOutcome.SUCCEEDED),
        ("checkout.session.async_payment_failed", "complete", "unpaid", CheckoutOutcome.FAILED),
        ("checkout.session.expired", "expired", "unpaid", CheckoutOutcome.EXPIRED),
        ("payment_intent.payment_failed", "complete", "paid", CheckoutOutcome.UNKNOWN),
    ],
)
def test_supported_event_policy_and_unknown_events(
    kind: str, status: str, paid: str, expected: CheckoutOutcome
) -> None:
    verifier, payload = setup_payload()
    payload["type"] = kind
    payload["data"]["object"]["status"] = status
    payload["data"]["object"]["payment_status"] = paid
    body = encode(payload)
    result = verifier.verify(body, signature(body))
    assert result.outcome is expected
    assert (result.checkout is None) == (expected is CheckoutOutcome.UNKNOWN)


def test_unconfigured_webhooks_are_disabled_independently_of_checkout_creation() -> None:
    verifier = StripeWebhookVerifier(Settings())
    with pytest.raises(WebhookDisabledError):
        verifier.verify(b"body", "header")
