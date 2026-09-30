import asyncio
from typing import cast
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from ecommerce_store_payments.api.dependencies import get_webhook_service
from ecommerce_store_payments.application.payments.webhook_service import WebhookService
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.clients.stripe.webhook_verifier import StripeWebhookVerifier
from ecommerce_store_payments.infrastructure.config.settings import Settings
from tests.unit.application.test_payment_service import MemoryPaymentRepository
from tests.unit.application.test_webhook_service import MemoryWebhookRepository
from tests.webhook_fixtures import WEBHOOK_SECRET, encode, payload_for, signature


def configure(client: TestClient) -> tuple[MemoryWebhookRepository, bytes]:
    payments = MemoryPaymentRepository()
    payment = Payment.create(uuid4(), Money(1299, "PLN"))
    payment.begin_checkout()
    payment.mark_as_pending("cs_test_fixture")
    payments.payments[payment.order_id] = payment
    webhooks = MemoryWebhookRepository(payments)
    service = WebhookService(
        StripeWebhookVerifier(Settings(stripe_webhook_secret=SecretStr(WEBHOOK_SECRET))), webhooks, payments
    )
    cast(FastAPI, client.app).dependency_overrides[get_webhook_service] = lambda: service
    return webhooks, encode(payload_for(payment))


def test_signed_webhook_uses_prepared_service_and_returns_minimal_ack(client: TestClient) -> None:
    webhooks, body = configure(client)
    response = client.post(
        "/payments/webhooks/stripe",
        content=body,
        headers={"content-type": "application/json", "stripe-signature": signature(body)},
    )
    assert response.status_code == 200 and response.json() == {"received": True}
    assert len(webhooks.receipts) == 1


@pytest.mark.parametrize(
    "cause, status, code",
    [
        ("missing", 400, "webhook_invalid"),
        ("tampered", 400, "webhook_invalid"),
        ("media", 415, "unsupported_media_type"),
        ("large", 413, "webhook_too_large"),
        ("retry", 503, "webhook_retry"),
        ("duplicate_header", 400, "webhook_invalid"),
    ],
)
def test_webhook_errors_have_safe_problem_bodies(client: TestClient, cause: str, status: int, code: str) -> None:
    webhooks, body = configure(client)
    headers = [("content-type", "application/json"), ("stripe-signature", signature(body))]
    if cause == "missing":
        headers.pop()
    elif cause == "tampered":
        body += b"private"
    elif cause == "media":
        headers[0] = ("content-type", "text/plain")
    elif cause == "large":
        body = b"x" * (1024 * 1024 + 1)
    elif cause == "retry":
        webhooks.interrupt_once = True
    else:
        headers.append(("stripe-signature", "private"))
    response = client.post("/payments/webhooks/stripe", content=body, headers=headers)
    assert response.status_code == status
    assert response.json()["code"] == code
    assert response.headers["content-type"] == "application/problem+json"
    assert "private" not in response.text and WEBHOOK_SECRET not in response.text


def test_unconfigured_webhook_returns_service_unavailable(client: TestClient) -> None:
    response = client.post(
        "/payments/webhooks/stripe",
        content=b"{}",
        headers={"content-type": "application/json", "stripe-signature": "invalid"},
    )
    assert response.status_code == 503 and response.json()["code"] == "webhook_disabled"


def test_processing_deadline_returns_retry_and_preserves_pending_work(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    webhooks, body = configure(client)
    monkeypatch.setattr("ecommerce_store_payments.api.routes.webhooks.PROCESSING_TIMEOUT_SECONDS", 0.01)

    async def blocked(*args: object, **kwargs: object) -> None:
        await asyncio.Event().wait()

    monkeypatch.setattr(webhooks, "complete", blocked)
    response = client.post(
        "/payments/webhooks/stripe",
        content=body,
        headers={"content-type": "application/json", "stripe-signature": signature(body)},
    )
    assert response.status_code == 503 and response.json()["code"] == "webhook_retry"
    assert len(webhooks.receipts) == 1
