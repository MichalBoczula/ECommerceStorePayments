"""Exercise the generated client against the pinned, published Invoice image."""

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic, sleep
from uuid import UUID, uuid4

import httpx
import pytest
from bson.binary import Binary, UuidRepresentation
from bson.decimal128 import Decimal128
from kiota_abstractions.authentication.anonymous_authentication_provider import AnonymousAuthenticationProvider
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from testcontainers.community.mongodb import MongoDbContainer
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network

from ecommerce_store_payments.application.payments.exceptions import OrderNotFoundError
from ecommerce_store_payments.infrastructure.clients.orders.generated.orders_client import OrdersClient
from ecommerce_store_payments.infrastructure.clients.orders.http_order_reader import HttpOrderReader
from ecommerce_store_payments.infrastructure.clients.orders.precise_json import PreciseOrderJsonFactory
from ecommerce_store_payments.infrastructure.clients.orders.request_adapter import OrdersRequestAdapter

INVOICE_IMAGE = (
    "mb0101/ecommerce-store-invoice-api@sha256:35059e4b5e3af8e3a89d61dd34d1453f9096c3892b026004d0b904b58f8be598"
)


class _InvoiceMongo(MongoDbContainer):
    def _configure(self) -> None:
        self.with_command(["mongod", "--replSet", "rs0", "--bind_ip_all"])

    def get_connection_url(self) -> str:
        return f"mongodb://{self.get_container_host_ip()}:{self.get_exposed_port(27017)}/?directConnection=true"


def _wait_for_api(base_url: str) -> None:
    deadline = monotonic() + 90
    while monotonic() < deadline:
        try:
            if httpx.get(f"{base_url}/health/live", timeout=2).status_code == 200:
                return
        except httpx.RequestError:
            pass
        sleep(0.5)
    raise RuntimeError("Invoice image did not start; inspect its container logs.")


def test_published_invoice_order_contract_and_kiota_client() -> None:
    order_id, client_id, version_id, product_id = (uuid4() for _ in range(4))
    database_name = f"payments_invoice_contract_{uuid4().hex}"
    with Network() as network:
        with _InvoiceMongo("mongo:8.0").with_network(network).with_network_aliases("invoice-mongo") as mongo:
            result = mongo.exec(
                [
                    "mongosh",
                    "--quiet",
                    "--eval",
                    "rs.initiate({_id:'rs0',members:[{_id:0,host:'invoice-mongo:27017'}]})",
                ]
            )
            assert result.exit_code == 0, result.output.decode()
            host_mongo: MongoClient[dict[str, object]] = MongoClient(
                mongo.get_connection_url(), serverSelectionTimeoutMS=1000
            )
            try:
                deadline = monotonic() + 30
                while monotonic() < deadline:
                    try:
                        if host_mongo.admin.command("hello").get("isWritablePrimary"):
                            break
                    except PyMongoError:  # replica-set election has not finished
                        pass
                    sleep(0.25)
                else:
                    raise RuntimeError("Invoice MongoDB replica set did not elect a primary")
                database = host_mongo[database_name]

                def guid(value: UUID) -> Binary:
                    return Binary.from_uuid(value, uuid_representation=UuidRepresentation.STANDARD)

                database["product-versions"].insert_one(
                    {
                        "_id": guid(version_id),
                        "IsActive": True,
                        "CreatedAt": datetime.now(UTC),
                        "DeactivatedAt": None,
                        "ProductId": guid(product_id),
                        "PriceAmount": Decimal128("12.99"),
                        "PriceCurrency": "PLN",
                        "Name": "Contract product",
                        "Brand": "Contract brand",
                    }
                )
                database["orders"].insert_one(
                    {
                        "_id": guid(order_id),
                        "ClientId": guid(client_id),
                        "Lines": [{"ProductVersionId": guid(version_id), "Quantity": 1}],
                        "CreatedAt": datetime.now(UTC),
                        "UpdatedAt": None,
                        "Status": 2,
                    }
                )
                with (
                    DockerContainer(INVOICE_IMAGE)
                    .with_network(network)
                    .with_env(
                        "MongoDbSettings__ConnectionString", "mongodb://invoice-mongo:27017/?directConnection=true"
                    )
                    .with_env("MongoDbSettings__DatabaseName", database_name)
                    .with_exposed_ports(8080)
                ) as invoice:
                    base_url = f"http://{invoice.get_container_host_ip()}:{invoice.get_exposed_port(8080)}"
                    _wait_for_api(base_url)
                    published = httpx.get(f"{base_url}/swagger/v1/swagger.json", timeout=10).json()
                    pinned = json.loads(
                        (Path(__file__).resolve().parents[3] / "contracts/invoice/openapi.json").read_text()
                    )
                    assert published["paths"]["/orders/{orderId}"]["get"] == pinned["paths"]["/orders/{orderId}"]["get"]
                    for name in ("OrderResponseDto", "OrderLineResponseDto", "ProductVersionResponseDto"):
                        assert published["components"]["schemas"][name] == pinned["components"]["schemas"][name]

                    async def verify() -> None:
                        async with httpx.AsyncClient(base_url=base_url, timeout=10, trust_env=False) as transport:
                            adapter = OrdersRequestAdapter(
                                AnonymousAuthenticationProvider(),
                                parse_node_factory=PreciseOrderJsonFactory(),
                                http_client=transport,
                                base_url=base_url,
                            )
                            reader = HttpOrderReader(OrdersClient(adapter))
                            order = await reader.get_by_id(order_id)
                            assert order.order_id == order_id
                            assert order.status == "Created"
                            assert order.money.amount_minor == 1299
                            assert order.money.currency == "PLN"
                            with pytest.raises(OrderNotFoundError):
                                await reader.get_by_id(uuid4())

                    asyncio.run(verify())
            finally:
                try:
                    host_mongo.drop_database(database_name)
                finally:
                    host_mongo.close()
