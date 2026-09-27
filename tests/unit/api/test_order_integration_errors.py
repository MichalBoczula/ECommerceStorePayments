from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ecommerce_store_payments.application.payments.exceptions import (
    OrderInvalidResponseError,
    OrderTimeoutError,
    OrderUnavailableError,
)
from ecommerce_store_payments.application.payments.payment_service import PaymentService


class _FailingOrdersService:
    def __init__(self, failure: type[Exception]) -> None:
        self._failure = failure

    async def pay(self, order_id: UUID) -> None:
        raise self._failure(order_id)


@pytest.mark.parametrize(
    ("failure", "expected_status"),
    [(OrderTimeoutError, 504), (OrderUnavailableError, 502), (OrderInvalidResponseError, 502)],
)
def test_pay_maps_orders_failures_to_gateway_errors(
    client: TestClient, failure: type[Exception], expected_status: int
) -> None:
    app = cast(FastAPI, client.app)
    app.state.payment_service = cast(PaymentService, _FailingOrdersService(failure))
    order_id = uuid4()

    response = client.post(f"/payments/{order_id}/pay")

    assert response.status_code == expected_status
    assert str(order_id) in response.json()["detail"]
    assert "private" not in response.text
    operation = app.openapi()["paths"]["/payments/{order_id}/pay"]["post"]
    assert str(expected_status) in operation["responses"]
