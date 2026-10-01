"""Signed webhook -> durable worker -> real Orders/PDF API, including lost HTTP replies."""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from time import monotonic, sleep
from typing import Any
from uuid import UUID, uuid4

import httpx
from bson.binary import Binary, UuidRepresentation
from bson.decimal128 import Decimal128
from fastapi.testclient import TestClient
from kiota_abstractions.authentication.anonymous_authentication_provider import AnonymousAuthenticationProvider
from pydantic import SecretStr
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.application.payments.fulfillment_service import FulfillmentService
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.clients.orders.generated.orders_client import OrdersClient
from ecommerce_store_payments.infrastructure.clients.orders.http_fulfillment import (
    HttpFulfillmentInvoices,
    HttpFulfillmentOrders,
)
from ecommerce_store_payments.infrastructure.clients.orders.precise_json import PreciseOrderJsonFactory
from ecommerce_store_payments.infrastructure.clients.orders.request_adapter import OrdersRequestAdapter
from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.fulfillment_repository import (
    MongoFulfillmentRepository,
)
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)
from tests.integration.infrastructure.test_invoice_image_client import InvoiceMongo, wait_for_invoice_api
from tests.webhook_fixtures import WEBHOOK_SECRET, encode, payload_for, signature

INVOICE_IMAGE = (
    "mb0101/ecommerce-store-invoice-api@sha256:09b24ae59f362ca73f6f7e0369a0e0b0814d78b17b7d86403c5b4a24612e4df4"
)

# Preserve the maximum supported downstream timeout through both HTTP clients.
REQUEST_TIMEOUT_SECONDS = 30


def guid(value: UUID) -> Binary:
    return Binary.from_uuid(value, uuid_representation=UuidRepresentation.STANDARD)


def test_verified_payments_complete_real_paid_orders_and_pdfs_with_ambiguous_replies(mongo_url: str) -> None:
    invoice_database = f"fulfillment_invoice_{uuid4().hex}"
    with Network() as network:
        with InvoiceMongo("mongo:8.0").with_network(network).with_network_aliases("invoice-mongo") as mongo:
            result = mongo.exec(
                [
                    "mongosh",
                    "--quiet",
                    "--eval",
                    "rs.initiate({_id:'rs0',members:[{_id:0,host:'invoice-mongo:27017'}]})",
                ]
            )
            assert result.exit_code == 0
            with MongoClient[dict[str, Any]](mongo.get_connection_url(), serverSelectionTimeoutMS=1000) as host_mongo:
                deadline = monotonic() + 30
                while monotonic() < deadline:
                    try:
                        if host_mongo.admin.command("hello").get("isWritablePrimary"):
                            break
                    except PyMongoError:
                        pass
                    sleep(0.25)
                else:
                    raise RuntimeError("Invoice replica set did not elect a primary")
                invoice_db = host_mongo[invoice_database]
                with (
                    DockerContainer(INVOICE_IMAGE)
                    .with_network(network)
                    .with_env(
                        "MongoDbSettings__ConnectionString", "mongodb://invoice-mongo:27017/?directConnection=true"
                    )
                    .with_env("MongoDbSettings__DatabaseName", invoice_database)
                    .with_env("Serilog__WriteTo__0__Name", "Console")
                    .with_exposed_ports(8080)
                ) as invoice:
                    url = f"http://{invoice.get_container_host_ip()}:{invoice.get_exposed_port(8080)}"
                    wait_for_invoice_api(url)
                    for mode in ("normal", "lost_paid", "lost_invoice", "pdf_retry"):
                        order_id, client_id, product_version, data_version = (uuid4() for _ in range(4))
                        now = datetime.now(UTC)
                        invoice_db["product-versions"].insert_one(
                            {
                                "_id": guid(product_version),
                                "IsActive": True,
                                "CreatedAt": now,
                                "DeactivatedAt": None,
                                "ProductId": guid(uuid4()),
                                "PriceAmount": Decimal128("12.99"),
                                "PriceCurrency": "PLN",
                                "Name": "Fulfillment product",
                                "Brand": "Test",
                            }
                        )
                        invoice_db["orders"].insert_one(
                            {
                                "_id": guid(order_id),
                                "ClientId": guid(client_id),
                                "Lines": [{"ProductVersionId": guid(product_version), "Quantity": 1}],
                                "CreatedAt": now,
                                "UpdatedAt": None,
                                "Status": 2,
                            }
                        )
                        invoice_db["client-data-versions"].insert_one(
                            {
                                "_id": guid(data_version),
                                "ClientId": guid(client_id),
                                "ClientName": "Fixture Client",
                                "PostalCode": "00-001",
                                "City": "Warsaw",
                                "Street": "Main",
                                "BuildingNumber": "1",
                                "ApartmentNumber": "",
                                "PhoneNumber": "123456789",
                                "PhonePrefix": "+48",
                                "AddressEmail": "fixture@example.test",
                                "CreatedAt": now,
                            }
                        )
                        settings = Settings(
                            environment="test",
                            mongodb_connection_string=mongo_url,
                            mongodb_database_name=f"fulfillment_payments_{uuid4().hex}",
                            orders_api_base_url=url,
                            orders_api_timeout_seconds=REQUEST_TIMEOUT_SECONDS,
                            stripe_webhook_secret=SecretStr(WEBHOOK_SECRET),
                        )

                        async def prepare(settings: Settings = settings, order_id: UUID = order_id) -> Payment:
                            database = MongoDatabase(settings)
                            try:
                                await database.ensure_indexes()
                                payment = Payment.create(order_id, Money(1299, "PLN"))
                                payment.begin_checkout()
                                payment.mark_as_pending("cs_test_fixture")
                                return await MongoPaymentRepository(database).create(payment)
                            finally:
                                await database.close()

                        payment = asyncio.run(prepare())
                        body = encode(payload_for(payment, event_id=f"evt_{mode}"))
                        try:
                            with TestClient(create_app(settings)) as api:
                                response = api.post(
                                    "/payments/webhooks/stripe",
                                    content=body,
                                    headers={"content-type": "application/json", "stripe-signature": signature(body)},
                                )
                                assert response.status_code == 200

                                async def fulfill(
                                    settings: Settings = settings, mode: str = mode, data_version: UUID = data_version
                                ) -> None:
                                    database = MongoDatabase(settings)
                                    try:
                                        async with httpx.AsyncClient(
                                            base_url=url, timeout=REQUEST_TIMEOUT_SECONDS, trust_env=False
                                        ) as actual:
                                            lost = False
                                            responses: list[str] = []

                                            async def forward(request: httpx.Request) -> httpx.Response:
                                                nonlocal lost
                                                if mode == "pdf_retry" and request.method == "POST" and not lost:
                                                    lost = True
                                                    return httpx.Response(500)
                                                response = await actual.send(request)
                                                responses.append(
                                                    f"{request.method} {request.url.path}: "
                                                    f"{response.status_code} {response.text}"
                                                )
                                                if not lost and (
                                                    (mode == "lost_paid" and request.method == "PATCH")
                                                    or (mode == "lost_invoice" and request.method == "POST")
                                                ):
                                                    lost = True
                                                    raise httpx.ReadTimeout(
                                                        "Fixture lost reply after commit", request=request
                                                    )
                                                return response

                                            async with httpx.AsyncClient(
                                                base_url=url,
                                                timeout=REQUEST_TIMEOUT_SECONDS,
                                                transport=httpx.MockTransport(forward),
                                            ) as transport:
                                                client = OrdersClient(
                                                    OrdersRequestAdapter(
                                                        AnonymousAuthenticationProvider(),
                                                        parse_node_factory=PreciseOrderJsonFactory(),
                                                        http_client=transport,
                                                        base_url=url,
                                                    )
                                                )
                                                orders, invoices = (
                                                    HttpFulfillmentOrders(client),
                                                    HttpFulfillmentInvoices(client),
                                                )
                                                service = FulfillmentService(
                                                    MongoFulfillmentRepository(database),
                                                    MongoPaymentRepository(database),
                                                    orders,
                                                    invoices,
                                                )
                                                assert await service.run_batch(100) == 1
                                                if mode == "pdf_retry":
                                                    work = await database.webhooks.find_one({"_id": f"evt_{mode}"})
                                                    assert work is not None and work["fulfillment_status"] == "retry"
                                                    service = FulfillmentService(
                                                        MongoFulfillmentRepository(database),
                                                        MongoPaymentRepository(database),
                                                        orders,
                                                        invoices,
                                                        lambda: datetime.now(UTC) + timedelta(seconds=61),
                                                    )
                                                    assert await service.run_batch(100) == 1
                                                work = await database.webhooks.find_one({"_id": f"evt_{mode}"})
                                                if work is None or work["fulfillment_status"] != "completed":
                                                    print("Fulfillment work:", json.dumps(work, default=str))
                                                    print("Invoice responses:", "\n".join(responses))
                                                    print("Invoice logs:", invoice.get_logs()[0].decode()[-20000:])
                                                assert work is not None and work["fulfillment_status"] == "completed"
                                                assert work.get("fulfillment_client_data_version_id") == data_version
                                                assert await service.run_batch(100) == 0
                                    finally:
                                        await database.close()

                                asyncio.run(fulfill())
                                assert api.get(f"/payments/order/{payment.order_id}").json()["status"] == "succeeded"
                                assert (
                                    api.post(
                                        "/payments/webhooks/stripe",
                                        content=body,
                                        headers={
                                            "content-type": "application/json",
                                            "stripe-signature": signature(body),
                                        },
                                    ).status_code
                                    == 200
                                )
                            documents = list(invoice_db["invoices"].find({"OrderId": guid(order_id)}))
                            assert len(documents) == 1 and documents[0]["GenerationStatus"] == "Completed"
                            stored_order = invoice_db["orders"].find_one({"_id": guid(order_id)})
                            assert stored_order is not None and stored_order["Status"] == 0
                            assert documents[0]["StorageUrl"].endswith(".pdf")
                        finally:
                            with MongoClient[dict[str, Any]](mongo_url) as cleanup:
                                cleanup.drop_database(settings.mongodb_database_name)
