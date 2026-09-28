from typing import cast
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ecommerce_store_payments.application.payments.payment_service import PaymentService
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import PaymentDuplicateError


class _DuplicateService:
    async def pay(self, order_id: UUID) -> None:
        raise PaymentDuplicateError(uuid4(), order_id)


def test_pay_maps_unresolved_duplicate_to_conflict(client: TestClient) -> None:
    app = cast(FastAPI, client.app)
    app.state.payment_service = cast(PaymentService, _DuplicateService())
    order_id = uuid4()

    response = client.post(f"/payments/{order_id}/pay")

    assert response.status_code == 409
    assert response.json()["code"] == "payment_duplicate"
    assert str(order_id) not in response.text
