from collections.abc import Callable
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ecommerce_store_payments.api.dependencies import get_payment_service
from ecommerce_store_payments.application.payments.checkout_provider import CheckoutRequest, CheckoutSession
from ecommerce_store_payments.application.payments.exceptions import (
    CheckoutProviderError,
    CheckoutTimeoutError,
)
from ecommerce_store_payments.application.payments.payment_service import PaymentService
from tests.unit.application.test_checkout import CheckoutBoundary, setup_checkout


def test_checkout_response_and_existing_pay_contract(client: TestClient) -> None:
    service, _, reader, _ = setup_checkout()
    app = cast(FastAPI, client.app)
    app.dependency_overrides[get_payment_service] = lambda: service
    path = f"/payments/{reader.order.order_id}"
    response = client.post(f"{path}/checkout")
    assert response.status_code == 200
    body = response.json()
    assert body["checkout_status"] == "open" and body["checkout_url"].startswith("https://checkout.stripe.com/")
    assert body["payment"]["status"] == "pending"
    assert body["payment"]["provider_payment_id"] is None
    assert "checkout_attempt_id" not in body["payment"]
    repeated = client.post(f"{path}/checkout")
    assert repeated.json() == body
    pay = client.post(f"{path}/pay")
    assert pay.status_code == 200 and pay.json() == body["payment"]


@pytest.mark.parametrize("suffix", ["checkout", "pay"])
def test_body_rejection_applies_to_both_commands(client: TestClient, suffix: str) -> None:
    service, _, reader, _ = setup_checkout()
    cast(FastAPI, client.app).dependency_overrides[get_payment_service] = lambda: service
    response = client.post(f"/payments/{reader.order.order_id}/{suffix}", json={"amount_minor": 1})
    assert response.status_code == 400


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [(CheckoutTimeoutError, 504, "checkout_timeout"), (CheckoutProviderError, 502, "checkout_provider_error")],
)
def test_provider_errors_are_safe_http_problems(
    client: TestClient, error: Callable[[], Exception], status: int, code: str
) -> None:
    _, repository, reader, _ = setup_checkout()

    class FailingProvider(CheckoutBoundary):
        async def create(self, request: CheckoutRequest) -> CheckoutSession:
            raise error()

    service = PaymentService(repository, reader, FailingProvider())
    cast(FastAPI, client.app).dependency_overrides[get_payment_service] = lambda: service
    response = client.post(f"/payments/{reader.order.order_id}/checkout")
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == code
    assert response.json()["traceId"] == response.headers["x-trace-id"]


def test_disabled_checkout_is_documented_and_returns_503(client: TestClient) -> None:
    response = client.post("/payments/00000000-0000-0000-0000-000000000001/checkout")
    assert response.status_code == 503 and response.json()["code"] == "checkout_disabled"
    schema = cast(FastAPI, client.app).openapi()
    operation = schema["paths"]["/payments/{order_id}/checkout"]["post"]
    assert operation["operationId"] == "createOrderCheckout"
    assert "422" not in operation["responses"] and "503" in operation["responses"]
