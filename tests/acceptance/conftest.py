import asyncio
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from httpx2 import AsyncClient, ConnectError, MockTransport, ReadTimeout, Request, Response
from pymongo import MongoClient
from pymongo.collection import Collection

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_history_document import (
    PaymentHistoryDocument,
)
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)


@dataclass
class OrdersBoundary:
    order_id: UUID = field(default_factory=uuid4)
    mode: str = "created"
    status: str = "Created"
    amount: float = 12.99
    calls: int = 0

    def handle(self, request: Request) -> Response:
        assert request.method == "GET"
        assert request.url.path == f"/orders/{self.order_id}"
        self.calls += 1
        if self.mode == "missing":
            return Response(404)
        if self.mode == "invalid":
            return Response(200, json={"id": str(self.order_id), "status": "Created", "totalAmount": "private"})
        if self.mode == "timeout":
            raise ReadTimeout("private Orders timeout", request=request)
        if self.mode == "outage":
            raise ConnectError("private Orders connection", request=request)
        return Response(
            200,
            json={
                "id": str(self.order_id),
                "status": self.status,
                "totalAmount": self.amount,
                "totalCurrency": "PLN",
                "lines": [{"lineTotalAmount": self.amount, "productVersion": {"priceCurrency": "PLN"}}],
            },
        )


@dataclass
class AcceptanceContext:
    client: TestClient
    orders: OrdersBoundary
    settings: Settings
    mongo: MongoClient[PaymentDocument]
    last_operation: str = ""
    responses: list[Response] = field(default_factory=list[Response])
    initial_payment_id: UUID | None = None
    initial_orders_calls: int = 0

    @property
    def payments(self) -> Collection[PaymentDocument]:
        return self.mongo[self.settings.mongodb_database_name]["payments"]

    @property
    def history(self) -> Collection[PaymentHistoryDocument]:
        return cast(
            Collection[PaymentHistoryDocument], self.mongo[self.settings.mongodb_database_name]["payment_history"]
        )

    def send(self, method: str, path: str, *, content: bytes | None = None, content_type: str | None = None) -> None:
        headers = {"content-type": content_type} if content_type else None
        self.last_operation = f"{method} {path.replace(str(self.orders.order_id), '{order_id}')}"
        self.responses = [self.client.request(method, path, content=content, headers=headers)]

    def make_terminal(self, status: PaymentStatus) -> None:
        async def update() -> None:
            database = MongoDatabase(self.settings)
            try:
                repository = MongoPaymentRepository(database)
                payment = await repository.get_by_order_id(self.orders.order_id)
                assert payment is not None
                if status is PaymentStatus.FAILED:
                    payment.mark_as_pending("cs_acceptance")
                    payment = await repository.update(payment)
                    payment.mark_as_failed("declined")
                else:
                    payment.cancel()
                await repository.update(payment)
            finally:
                await database.close()

        asyncio.run(update())


@pytest.fixture
def acceptance(mongo_url: str, monkeypatch: pytest.MonkeyPatch) -> Generator[AcceptanceContext]:
    database_name = f"payments_acceptance_{uuid4().hex}"
    settings = Settings(
        environment="test",
        mongodb_connection_string=mongo_url,
        mongodb_database_name=database_name,
        orders_api_base_url="https://orders.example.test",
    )
    orders = OrdersBoundary()
    mongo: MongoClient[PaymentDocument] = MongoClient(mongo_url, uuidRepresentation="standard", tz_aware=True)

    def orders_client(*, base_url: str, timeout: float, trust_env: bool) -> AsyncClient:
        return AsyncClient(
            base_url=base_url, timeout=timeout, trust_env=trust_env, transport=MockTransport(orders.handle)
        )

    monkeypatch.setattr("ecommerce_store_payments.api.app.AsyncClient", orders_client)
    try:
        with TestClient(create_app(settings)) as client:
            yield AcceptanceContext(client=client, orders=orders, settings=settings, mongo=mongo)
    finally:
        try:
            mongo.drop_database(database_name)
        finally:
            mongo.close()
