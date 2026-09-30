import asyncio
from collections.abc import Generator, Mapping
from dataclasses import dataclass, field
from typing import Any, cast
from urllib.parse import parse_qs
from uuid import UUID, uuid4

import pytest
import stripe
from fastapi.testclient import TestClient
from httpx import AsyncClient, ConnectError, MockTransport, ReadTimeout, Request
from httpx import Response as OrdersResponse
from httpx2 import Response
from pydantic import SecretStr
from pymongo import MongoClient
from pymongo.collection import Collection

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.application.payments.checkout_provider import CheckoutRequest
from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.clients.stripe.checkout_provider import (
    STRIPE_API_VERSION,
    StripeCheckoutProvider,
)
from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_history_document import (
    PaymentHistoryDocument,
)
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)
from tests.unit.external_providers.test_stripe_checkout import StripeTransport


@dataclass
class OrdersBoundary:
    order_id: UUID = field(default_factory=uuid4)
    mode: str = "created"
    status: str = "Created"
    amount: float = 12.99
    calls: int = 0

    def handle(self, request: Request) -> OrdersResponse:
        assert request.method == "GET"
        assert request.url.path == f"/orders/{self.order_id}"
        self.calls += 1
        if self.mode == "missing":
            return OrdersResponse(404)
        if self.mode == "invalid":
            return OrdersResponse(200, json={"id": str(self.order_id), "status": "Created", "totalAmount": "private"})
        if self.mode == "timeout":
            raise ReadTimeout("private Orders timeout", request=request)
        if self.mode == "outage":
            raise ConnectError("private Orders connection", request=request)
        return OrdersResponse(
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
    stripe: AcceptanceStripeTransport
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


class AcceptanceStripeTransport(StripeTransport):
    def __init__(self) -> None:
        super().__init__(CheckoutRequest(uuid4(), uuid4(), uuid4(), Money(1299, "PLN")))
        self.sessions: dict[str, dict[str, object]] = {}
        self.mode = "ok"

    async def request_async(
        self, method: str, url: str, headers: Mapping[str, str], post_data: Any = None
    ) -> tuple[bytes, int, Mapping[str, str]]:
        if self.mode == "rejection":
            self.code = 400
            self.payload = {"error": {"type": "invalid_request_error", "message": "private Stripe detail"}}
        elif method == "post":
            body = parse_qs(str(post_data))
            key = headers["Idempotency-Key"]
            metadata = {name: body[f"metadata[{name}]"][0] for name in ("payment_id", "order_id", "attempt_id")}
            candidate = {
                **self.payload,
                "id": f"cs_test_{metadata['attempt_id']}",
                "amount_total": int(body["line_items[0][price_data][unit_amount]"][0]),
                "client_reference_id": body["client_reference_id"][0],
                "metadata": metadata,
            }
            self.payload = self.sessions.setdefault(key, candidate)
            if self.mode == "timeout_once":
                self.mode = "ok"
                error = stripe.APIConnectionError("private timeout")
                error.__cause__ = ReadTimeout("private timeout")
                self.error = error
        else:
            self.payload = next(payload for payload in self.sessions.values() if url.endswith(str(payload["id"])))
        try:
            return await super().request_async(method, url, headers, post_data)
        finally:
            self.error = None


@pytest.fixture
def acceptance(mongo_url: str, monkeypatch: pytest.MonkeyPatch) -> Generator[AcceptanceContext]:
    database_name = f"payments_acceptance_{uuid4().hex}"
    settings = Settings(
        environment="test",
        mongodb_connection_string=mongo_url,
        mongodb_database_name=database_name,
        orders_api_base_url="https://orders.example.test",
        stripe_enabled=True,
        stripe_secret_key=SecretStr("sk_test_fixture"),
    )
    orders = OrdersBoundary()
    stripe_boundary = AcceptanceStripeTransport()
    mongo: MongoClient[PaymentDocument] = MongoClient(mongo_url, uuidRepresentation="standard", tz_aware=True)

    def orders_client(*, base_url: str, timeout: float, trust_env: bool) -> AsyncClient:
        return AsyncClient(
            base_url=base_url, timeout=timeout, trust_env=trust_env, transport=MockTransport(orders.handle)
        )

    monkeypatch.setattr("ecommerce_store_payments.api.app.AsyncClient", orders_client)

    def checkout_provider(resolved: Settings) -> StripeCheckoutProvider:
        return StripeCheckoutProvider(
            resolved,
            stripe.StripeClient(
                "sk_test_fixture", stripe_version=STRIPE_API_VERSION, http_client=stripe_boundary, max_network_retries=0
            ),
        )

    monkeypatch.setattr("ecommerce_store_payments.api.app.StripeCheckoutProvider", checkout_provider)
    try:
        with TestClient(create_app(settings)) as client:
            yield AcceptanceContext(
                client=client, orders=orders, settings=settings, mongo=mongo, stripe=stripe_boundary
            )
    finally:
        try:
            mongo.drop_database(database_name)
        finally:
            mongo.close()
