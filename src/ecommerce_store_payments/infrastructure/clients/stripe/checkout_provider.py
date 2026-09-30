from datetime import UTC, datetime
from typing import Never, final
from urllib.parse import urlsplit

import httpx
import stripe

from ecommerce_store_payments.application.payments.checkout_provider import CheckoutRequest, CheckoutSession
from ecommerce_store_payments.application.payments.exceptions import (
    CheckoutDisabledError,
    CheckoutMoneyError,
    CheckoutProviderError,
    CheckoutTimeoutError,
)
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.config.settings import Settings

STRIPE_API_VERSION = "2026-08-26.dahlia"


@final
class StripeCheckoutProvider:
    def __init__(self, settings: Settings, client: stripe.StripeClient | None = None) -> None:
        self._settings = settings
        self._http: stripe.HTTPXClient | None = None
        self._client = client
        if client is None and settings.stripe_enabled and settings.stripe_secret_key is not None:
            self._http = stripe.HTTPXClient(timeout=settings.stripe_timeout_seconds)
            self._client = stripe.StripeClient(
                settings.stripe_secret_key.get_secret_value(),
                stripe_version=STRIPE_API_VERSION,
                http_client=self._http,
                max_network_retries=1,
            )

    def require_available(self) -> None:
        """Require explicitly configured test-mode checkout before any payment write."""
        if not self._settings.stripe_enabled or self._client is None:
            raise CheckoutDisabledError()

    def validate_money(self, money: Money) -> None:
        """The initial hosted card checkout supports PLN amounts with a PLN 2 minimum and conservative demo maximum."""
        if money.currency != "PLN" or not 200 <= money.amount_minor <= 99_999_999:
            raise CheckoutMoneyError()

    async def close(self) -> None:
        if self._http is not None:
            await self._http.close_async()

    @staticmethod
    def _metadata(request: CheckoutRequest) -> dict[str, str]:
        return {
            "payment_id": str(request.payment_id),
            "order_id": str(request.order_id),
            "attempt_id": str(request.attempt_id),
        }

    async def create(self, request: CheckoutRequest) -> CheckoutSession:
        """Create/replay a hosted session using the durably reserved attempt key."""
        self.require_available()
        self.validate_money(request.money)
        assert self._client is not None
        try:
            session = await self._client.v1.checkout.sessions.create_async(
                {
                    "mode": "payment",
                    "payment_method_types": ["card"],
                    "client_reference_id": str(request.payment_id),
                    "metadata": self._metadata(request),
                    "payment_intent_data": {"metadata": self._metadata(request)},
                    "success_url": self._settings.stripe_success_url,
                    "cancel_url": self._settings.stripe_cancel_url,
                    "line_items": [
                        {
                            "quantity": 1,
                            "price_data": {
                                "currency": "pln",
                                "unit_amount": request.money.amount_minor,
                                "product_data": {"name": f"Order {request.order_id}"},
                            },
                        }
                    ],
                },
                {"idempotency_key": f"checkout:{request.payment_id}:{request.attempt_id}"},
            )
            return self._map(session, request)
        except stripe.StripeError as error:
            self._raise_provider_error(error)
        except (AttributeError, KeyError, TypeError, ValueError, OverflowError) as error:
            raise CheckoutProviderError() from error

    async def get(self, session_id: str, request: CheckoutRequest) -> CheckoutSession:
        """Read the same provider session without creating a replacement."""
        self.require_available()
        assert self._client is not None
        try:
            session = await self._client.v1.checkout.sessions.retrieve_async(session_id)
            if session.id != session_id:
                raise CheckoutProviderError()
            return self._map(session, request)
        except stripe.StripeError as error:
            self._raise_provider_error(error)
        except (AttributeError, KeyError, TypeError, ValueError, OverflowError) as error:
            raise CheckoutProviderError() from error

    @staticmethod
    def _raise_provider_error(error: stripe.StripeError) -> Never:
        if isinstance(error, stripe.APIConnectionError) and isinstance(error.__cause__, httpx.TimeoutException):
            raise CheckoutTimeoutError() from error
        raise CheckoutProviderError() from error

    @classmethod
    def _map(cls, session: stripe.checkout.Session, request: CheckoutRequest) -> CheckoutSession:
        if (
            not session.id.startswith("cs_test_")
            or not session.id.isascii()
            or not session.id.isprintable()
            or any(character.isspace() for character in session.id)
            or session.livemode is not False
            or session.mode != "payment"
            or session.amount_total != request.money.amount_minor
            or session.currency != request.money.currency.lower()
            or session.client_reference_id != str(request.payment_id)
            or session.metadata is None
            or any(session.metadata[key] != value for key, value in cls._metadata(request).items())
            or session.status not in ("open", "complete", "expired")
        ):
            raise CheckoutProviderError()
        url = session.url if session.status == "open" else None
        if session.status == "open":
            parts = urlsplit(url or "")
            if parts.scheme != "https" or parts.netloc != "checkout.stripe.com" or not parts.path.startswith("/c/pay/"):
                raise CheckoutProviderError()
        return CheckoutSession(session.id, url, session.status, cls._expiration(session.expires_at))

    @staticmethod
    def _expiration(value: object) -> datetime:
        if isinstance(value, bool) or not isinstance(value, int):
            raise CheckoutProviderError()
        return datetime.fromtimestamp(value, UTC)
