from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ecommerce_store_payments.application.payments.exceptions import OrderTotalChangedError, PaymentNotFoundError
from ecommerce_store_payments.application.payments.pay_result import PayResult
from ecommerce_store_payments.application.payments.payment_service import PaymentService
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import PaymentConflictError
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money


class _PayService:
    def __init__(self, result: PayResult) -> None:
        self.result = result

    async def pay(self, order_id: UUID) -> PayResult:
        assert order_id == self.result.payment.order_id
        return self.result

    async def get_by_order_id(self, order_id: UUID) -> Payment:
        assert order_id == self.result.payment.order_id
        return self.result.payment


@pytest.mark.parametrize(("created", "expected_status"), [(True, 201), (False, 200)])
def test_pay_returns_new_or_existing_status_and_get_reflects_payment(
    client: TestClient, created: bool, expected_status: int
) -> None:
    payment = Payment.create(uuid4(), Money(amount_minor=12999, currency="PLN"))
    app = cast(FastAPI, client.app)
    app.state.payment_service = cast(PaymentService, _PayService(PayResult(payment, created)))

    paid = client.post(f"/payments/{payment.order_id}/pay")
    read = client.get(f"/payments/order/{payment.order_id}")

    assert paid.status_code == expected_status
    assert read.status_code == 200
    assert paid.json() == read.json()
    assert paid.json()["id"] == str(payment.id)
    responses = app.openapi()["paths"]["/payments/{order_id}/pay"]["post"]["responses"]
    assert "201" in responses and "200" in responses and "409" in responses


class _FailingService:
    def __init__(self, failure: type[Exception]) -> None:
        self.failure = failure

    async def pay(self, order_id: UUID) -> PayResult:
        if self.failure is PaymentConflictError:
            raise PaymentConflictError(uuid4(), 0)
        raise OrderTotalChangedError(order_id)

    async def get_by_order_id(self, order_id: UUID) -> Payment:
        raise PaymentNotFoundError(order_id)


@pytest.mark.parametrize("failure", [PaymentConflictError, OrderTotalChangedError])
def test_pay_maps_retry_conflicts_to_409(client: TestClient, failure: type[Exception]) -> None:
    app = cast(FastAPI, client.app)
    app.state.payment_service = cast(PaymentService, _FailingService(failure))
    assert client.post(f"/payments/{uuid4()}/pay").status_code == 409


def test_get_missing_payment_returns_404(client: TestClient) -> None:
    app = cast(FastAPI, client.app)
    app.state.payment_service = cast(PaymentService, _FailingService(OrderTotalChangedError))
    assert client.get(f"/payments/order/{uuid4()}").status_code == 404
