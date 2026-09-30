import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs
from uuid import uuid4

import httpx
import pytest
import stripe
from pydantic import SecretStr

from ecommerce_store_payments.application.payments.checkout_provider import CheckoutRequest
from ecommerce_store_payments.application.payments.exceptions import (
    CheckoutDisabledError,
    CheckoutMoneyError,
    CheckoutProviderError,
    CheckoutTimeoutError,
)
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.clients.stripe.checkout_provider import (
    STRIPE_API_VERSION,
    StripeCheckoutProvider,
)
from ecommerce_store_payments.infrastructure.config.settings import Settings


class StripeTransport(stripe.HTTPClient):
    name = "test-boundary"

    def __init__(self, request: CheckoutRequest) -> None:
        # The SDK constructor exposes an untyped optional transport hook.
        super().__init__()  # pyright: ignore[reportUnknownMemberType]
        self.calls: list[tuple[str, str, Mapping[str, str], Any]] = []
        self.code = 200
        self.error: Exception | None = None
        self.payload: dict[str, object] = {
            "id": "cs_test_demo",
            "object": "checkout.session",
            "livemode": False,
            "mode": "payment",
            "amount_total": request.money.amount_minor,
            "currency": "pln",
            "client_reference_id": str(request.payment_id),
            "metadata": {
                "payment_id": str(request.payment_id),
                "order_id": str(request.order_id),
                "attempt_id": str(request.attempt_id),
            },
            "status": "open",
            "url": "https://checkout.stripe.com/c/pay/cs_test_demo",
            "expires_at": int((datetime.now(UTC) + timedelta(hours=24)).timestamp()),
        }

    async def request_async(
        self, method: str, url: str, headers: Mapping[str, str], post_data: Any = None
    ) -> tuple[bytes, int, Mapping[str, str]]:
        self.calls.append((method, url, headers, post_data))
        if self.error is not None:
            raise self.error
        return json.dumps(self.payload).encode(), self.code, {"request-id": "req_boundary_test"}


def make_provider() -> tuple[StripeCheckoutProvider, StripeTransport, CheckoutRequest]:
    request = CheckoutRequest(uuid4(), uuid4(), uuid4(), Money(1299, "PLN"))
    transport = StripeTransport(request)
    settings = Settings(stripe_enabled=True, stripe_secret_key=SecretStr("sk_test_fixture"))
    client = stripe.StripeClient(
        settings.stripe_secret_key.get_secret_value() if settings.stripe_secret_key else "",
        stripe_version=STRIPE_API_VERSION,
        http_client=transport,
        max_network_retries=0,
    )
    return StripeCheckoutProvider(settings, client), transport, request


async def test_sdk_encodes_server_money_metadata_return_urls_and_stable_key() -> None:
    provider, transport, request = make_provider()
    session = await provider.create(request)
    assert session.session_id == "cs_test_demo" and session.status == "open"
    method, url, headers, data = transport.calls[0]
    assert method == "post" and url == "https://api.stripe.com/v1/checkout/sessions"
    assert headers["Stripe-Version"] == STRIPE_API_VERSION
    assert headers["Idempotency-Key"] == f"checkout:{request.payment_id}:{request.attempt_id}"
    body = parse_qs(str(data))
    assert body["line_items[0][price_data][unit_amount]"] == ["1299"]
    assert body["line_items[0][price_data][currency]"] == ["pln"]
    assert body["payment_method_types[0]"] == ["card"]
    assert body["metadata[attempt_id]"] == [str(request.attempt_id)]
    assert body["payment_intent_data[metadata][order_id]"] == [str(request.order_id)]
    assert body["success_url"] == ["http://localhost:4200/orders?checkout=success"]
    assert "automatic_tax[enabled]" not in body and "allow_promotion_codes" not in body
    await provider.create(request)
    assert transport.calls[1][2]["Idempotency-Key"] == headers["Idempotency-Key"]


@pytest.mark.parametrize("state", ["open", "complete", "expired"])
async def test_retrieve_never_creates_or_confirms_payment(state: str) -> None:
    provider, transport, request = make_provider()
    transport.payload["status"] = state
    session = await provider.get("cs_test_demo", request)
    assert transport.calls[0][0] == "get"
    assert session.status == state
    assert session.url is None if state != "open" else session.url is not None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("livemode", True),
        ("id", "cs_live_wrong"),
        ("mode", "subscription"),
        ("amount_total", 1),
        ("currency", "eur"),
        ("client_reference_id", "wrong"),
        ("metadata", {}),
        ("status", "unknown"),
        ("expires_at", True),
        ("url", "https://attacker.example/c/pay/demo"),
        ("url", None),
        ("url", "https://checkout.stripe.com@attacker.example/c/pay/demo"),
    ],
)
async def test_rejects_invalid_or_unrelated_provider_response(field: str, value: object) -> None:
    provider, transport, request = make_provider()
    transport.payload[field] = value
    with pytest.raises(CheckoutProviderError):
        await provider.create(request)


@pytest.mark.parametrize("code", [400, 401, 409, 429, 500])
async def test_provider_rejection_is_typed_and_does_not_leak_details(code: int) -> None:
    provider, transport, request = make_provider()
    transport.code = code
    transport.payload = {"error": {"type": "invalid_request_error", "message": "private provider detail"}}
    with pytest.raises(CheckoutProviderError) as caught:
        await provider.create(request)
    assert "private" not in str(caught.value)


async def test_timeout_is_distinguished_from_transport_failure() -> None:
    provider, transport, request = make_provider()
    timeout = stripe.APIConnectionError("private")
    timeout.__cause__ = httpx.ReadTimeout("private")
    transport.error = timeout
    with pytest.raises(CheckoutTimeoutError):
        await provider.create(request)
    transport.error = stripe.APIConnectionError("private")
    with pytest.raises(CheckoutProviderError):
        await provider.get("cs_test_demo", request)


@pytest.mark.parametrize("money", [Money(199, "PLN"), Money(100_000_000, "PLN"), Money(1299, "EUR")])
async def test_provider_currency_policy_prevents_requests(money: Money) -> None:
    provider, transport, request = make_provider()
    with pytest.raises(CheckoutMoneyError):
        await provider.create(CheckoutRequest(request.payment_id, request.order_id, request.attempt_id, money))
    assert not transport.calls


async def test_disabled_provider_is_unavailable_without_a_client() -> None:
    provider = StripeCheckoutProvider(Settings())
    with pytest.raises(CheckoutDisabledError):
        provider.require_available()
    await provider.close()


async def test_configured_provider_closes_owned_async_client(monkeypatch: pytest.MonkeyPatch) -> None:
    for variable in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.delenv(variable, raising=False)
    provider = StripeCheckoutProvider(Settings(stripe_enabled=True, stripe_secret_key=SecretStr("sk_test_fixture")))
    provider.require_available()
    await provider.close()
