"""Published Invoice HTTP/PDF boundary with isolated storage faults and lost acknowledgements."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import importlib
import json
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from time import monotonic, sleep
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import allure
import httpx
import pytest
from bson.decimal128 import Decimal128
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network

from tests.acceptance.conftest import AcceptanceContext
from tests.acceptance.fulfillment_boundary import DATA_VERSION, OLDER_VERSION, FulfillmentBoundary
from tests.acceptance.fulfillment_checks import FulfillmentChecks
from tests.acceptance.payment_checks import lossless
from tests.integration.infrastructure.test_invoice_image_client import InvoiceMongo, wait_for_invoice_api
from tests.integration.infrastructure.test_real_invoice_fulfillment import guid

# Scanned/published Invoice d28dd23c..., CI40908053521. Existing compatibility image pins remain.
INVOICE_PDF_IMAGE = (
    "mb0101/ecommerce-store-invoice-api@sha256:6e9244804a2645f8aecaff89f60cff03337a94b70ca877195e585c678f2d996a"
)


class RealInvoiceBoundary(FulfillmentBoundary):
    def __init__(self, context: AcceptanceContext, url: str, database: Any, container: DockerContainer) -> None:
        super().__init__(context.orders, "ok")
        self.context, self.url, self.database, self.container = context, url, database, container
        self.loss: str | None = None
        self.mappings: list[dict[str, Any]] = []

    def raw(self) -> dict[str, Any]:
        return {
            name: sorted((dict(d) for d in self.database[name].find({})), key=lambda d: str(d["_id"]))
            for name in ("orders", "product-versions", "client-data-versions", "invoices")
        }

    def snapshot(self) -> dict[str, Any]:
        data = self.raw()
        order = data["orders"][0]
        self.orders.status = "Paid" if order["Status"] == 0 else "Created"
        completed = [d for d in data["invoices"] if d["GenerationStatus"] == "Completed"]
        if completed:
            d = completed[0]
            self.orders.invoice_id = d["_id"]
            self.invoice = {
                "id": str(d["_id"]),
                "orderId": str(d["OrderId"]),
                "clietDataVersionId": str(d["ClientDataVersionId"]),
                "storageUrl": d["StorageUrl"],
                "createdAt": d["CreatedAt"].isoformat(),
            }
        else:
            self.invoice = None
        return {
            "orderId": str(self.orders.order_id),
            "clientId": str(self.orders.client_id),
            "status": self.orders.status,
            "invoice": self.invoice,
            "logicalPaidWrites": self.logical_paid,
            "logicalInvoices": self.logical_invoices,
            "publishedCollections": lossless(data),
        }

    async def forward(self, request: httpx.Request) -> httpx.Response:
        evidence = self.context.evidence
        body = request.read()
        target = "invoices" if request.url.path.startswith("/invoices/") else "orders"
        adapter = evidence.begin(
            request.method,
            str(request.url),
            request.headers,
            body,
            target=target,
            role="published-invoice-adapter",
            controlled=True,
            header_items=request.headers.multi_items(),
        )
        physical = evidence.begin(
            request.method,
            str(request.url),
            request.headers,
            body,
            target=target,
            role="published-invoice-http",
            controlled=False,
            header_items=request.headers.multi_items(),
        )
        prior = self.raw()
        try:
            async with httpx.AsyncClient(timeout=30, trust_env=False) as actual:
                response = await actual.send(request)
            evidence.response(
                physical,
                response.status_code,
                response.headers,
                response.content,
                header_items=response.headers.multi_items(),
            )
        except BaseException as error:
            evidence.failure(physical, error)
            evidence.failure(adapter, error)
            raise
        current = self.raw()
        if prior["orders"][0]["Status"] != 0 and current["orders"][0]["Status"] == 0:
            self.logical_paid += 1
        if not any(d["GenerationStatus"] == "Completed" for d in prior["invoices"]) and any(
            d["GenerationStatus"] == "Completed" for d in current["invoices"]
        ):
            self.logical_invoices += 1
        lost = (self.loss == "paid_ack_lost" and request.method == "PATCH") or (
            self.loss == "invoice_ack_lost" and request.method == "POST"
        )
        mapping = {
            "physicalExchangeId": json.loads(physical.metadata)["exchangeId"],
            "adapterExchangeId": json.loads(adapter.metadata)["exchangeId"],
            "remoteStatus": response.status_code,
            "acknowledgementLost": lost,
            "before": lossless(prior),
            "after": lossless(current),
        }
        self.mappings.append(mapping)
        evidence.observation(f"Published invoice exchange {len(self.mappings):03}", mapping)
        if lost:
            assert response.status_code == 200
            self.loss = None
            error = httpx.ReadTimeout("controlled loss after the published service committed", request=request)
            evidence.failure(adapter, error)
            self.trace.append({"method": request.method, "path": request.url.path, "result": "ReadTimeout"})
            raise error
        evidence.response(
            adapter,
            response.status_code,
            response.headers,
            response.content,
            header_items=response.headers.multi_items(),
        )
        self.trace.append({"method": request.method, "path": request.url.path, "result": response.status_code})
        return response

    def client(self, *, base_url: str, timeout: float, trust_env: bool) -> httpx.AsyncClient:
        assert base_url == self.url and timeout == 30 and trust_env is False
        return httpx.AsyncClient(
            base_url=base_url, timeout=30, trust_env=False, transport=httpx.MockTransport(self.forward)
        )

    def block_storage(self) -> None:
        with self.context.evidence.action(
            "Block only the disposable published Invoice PDF directory",
            {"path": "/app/Invoices", "image": INVOICE_PDF_IMAGE},
        ) as output:
            result = self.container.exec(
                ["sh", "-c", "mkdir -p /app/Invoices && rmdir /app/Invoices && touch /app/Invoices"]
            )
            assert result.exit_code == 0, result.output.decode()
            output["directoryReplacedByFile"] = True

    def repair_storage(self) -> None:
        data = self.raw()
        assert len(data["invoices"]) == 1
        invoice = data["invoices"][0]
        assert (
            invoice["GenerationStatus"] == "Failed" and invoice["StorageUrl"] == "" and data["orders"][0]["Status"] == 0
        )
        with self.context.evidence.action(
            "Repair the real failed PDF storage path", {"path": "/app/Invoices"}
        ) as output:
            result = self.container.exec(["rm", "/app/Invoices"])
            assert result.exit_code == 0
            output["failedInvoiceBeforeRetry"] = lossless(invoice)

    def pdf(self, values: dict[str, str]) -> None:
        assert values == {
            "ContentType": "application/pdf",
            "ContentDisposition": "attachment; invoice-{invoice.id}.pdf",
            "Magic": "%PDF-",
            "EOF": "%%EOF",
            "MinimumBytes": "1000",
            "StoredBytesMatch": "true",
            "CompletedInvoices": "1",
            "DataVersion": str(DATA_VERSION),
        }
        before = self.raw()
        self.snapshot()
        assert self.invoice is not None
        assert len(before["invoices"]) == 1 and before["invoices"][0]["GenerationStatus"] == "Completed"
        invoice = self.invoice
        path = f"/invoices/{invoice['id']}/pdf"

        async def download() -> httpx.Response:
            async with self.client(base_url=self.url, timeout=30, trust_env=False) as client:
                return await client.get(path)

        response = asyncio.run(download())
        body = response.content
        assert response.status_code == 200 and response.headers["content-type"] == "application/pdf"
        assert (
            response.headers["content-disposition"].startswith("attachment;")
            and f"invoice-{invoice['id']}.pdf" in response.headers["content-disposition"]
        )
        assert body.startswith(b"%PDF-") and body.rstrip().endswith(b"%%EOF") and len(body) >= 1000
        assert b"/Type /Page" in body
        storage_url = invoice["storageUrl"]
        assert isinstance(storage_url, str)
        stored_path = urlparse(storage_url).path
        assert (
            urlparse(storage_url).scheme == "file"
            and stored_path.startswith("/app/Invoices/")
            and stored_path.endswith(".pdf")
        )
        stored = self.container.exec(["base64", stored_path])
        assert stored.exit_code == 0
        assert base64.b64decode(stored.output) == body and self.raw() == before
        assert before["invoices"][0]["ClientDataVersionId"] == DATA_VERSION and DATA_VERSION != self.orders.client_id
        self.context.evidence.observation(
            "Real completed invoice PDF",
            {
                "expected": values,
                "invoice": invoice,
                "collections": lossless(before),
                "path": path,
                "byteLength": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "physicalExchangeId": self.mappings[-1]["physicalExchangeId"],
                "adapterExchangeId": self.mappings[-1]["adapterExchangeId"],
                "image": INVOICE_PDF_IMAGE,
            },
        )
        allure.attach(body, name="Generated invoice PDF", attachment_type=allure.attachment_type.PDF)


@pytest.fixture
def real_invoice_boundary(acceptance: AcceptanceContext) -> Generator[RealInvoiceBoundary]:
    context = acceptance
    database_name = "bdd_invoice_" + uuid4().hex
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
            with MongoClient[dict[str, Any]](
                mongo.get_connection_url(), uuidRepresentation="standard", tz_aware=True, serverSelectionTimeoutMS=1000
            ) as host:
                deadline = monotonic() + 30
                while monotonic() < deadline:
                    try:
                        if host.admin.command("hello").get("isWritablePrimary"):
                            break
                    except PyMongoError:
                        pass
                    sleep(0.25)
                else:
                    raise RuntimeError("Published Invoice replica set did not elect a primary")
                database = host[database_name]
                with (
                    DockerContainer(INVOICE_PDF_IMAGE)
                    .with_network(network)
                    .with_env("ASPNETCORE_ENVIRONMENT", "Testing")
                    .with_env("ExternalServices__ProductCatalog__BaseUrl", "http://unused-catalog.example.test")
                    .with_env(
                        "MongoDbSettings__ConnectionString", "mongodb://invoice-mongo:27017/?directConnection=true"
                    )
                    .with_env("MongoDbSettings__DatabaseName", database_name)
                    .with_env("Serilog__WriteTo__0__Name", "Console")
                    .with_exposed_ports(8080) as container
                ):
                    url = f"http://{container.get_container_host_ip()}:{container.get_exposed_port(8080)}"
                    try:
                        wait_for_invoice_api(url)
                    except RuntimeError:
                        logs = container.get_logs()
                        print("Published Invoice startup stdout:", logs[0].decode()[-16000:])
                        print("Published Invoice startup stderr:", logs[1].decode()[-16000:])
                        raise
                    boundary = RealInvoiceBoundary(context, url, database, container)
                    try:
                        yield boundary
                    finally:
                        host.drop_database(database_name)


def prepare_real(
    checks: FulfillmentChecks, boundary: RealInvoiceBoundary, values: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    assert values.keys() == {"Mode", "ImageDigest", "TimeoutSeconds", "Environment"}
    assert values["ImageDigest"] == INVOICE_PDF_IMAGE.split("@")[1] and values["TimeoutSeconds"] == "30"
    assert values["Environment"] == "Testing"
    mode = values["Mode"]
    assert mode in {"ok", "paid_ack_lost", "invoice_ack_lost", "pdf_storage_failure"}
    assert checks.boundary is not None
    context = checks.context
    database = boundary.database
    now = datetime.now(UTC)
    product = uuid4()
    with context.evidence.action(
        "Seed the isolated published Invoice service",
        {
            "image": INVOICE_PDF_IMAGE,
            "mode": mode,
            "orderId": str(context.orders.order_id),
            "clientId": str(context.orders.client_id),
            "latestDataVersion": str(DATA_VERSION),
            "olderDataVersion": str(OLDER_VERSION),
        },
    ) as output:
        database["product-versions"].insert_one(
            {
                "_id": guid(product),
                "IsActive": True,
                "CreatedAt": now,
                "DeactivatedAt": None,
                "ProductId": guid(uuid4()),
                "PriceAmount": Decimal128("12.99"),
                "PriceCurrency": "PLN",
                "Name": "BDD fulfillment product",
                "Brand": "Test",
            }
        )
        database["orders"].insert_one(
            {
                "_id": guid(context.orders.order_id),
                "ClientId": guid(context.orders.client_id),
                "Lines": [{"ProductVersionId": guid(product), "Quantity": 1}],
                "CreatedAt": now,
                "UpdatedAt": None,
                "Status": 2,
            }
        )
        for version, created in [(OLDER_VERSION, now - timedelta(days=1)), (DATA_VERSION, now)]:
            database["client-data-versions"].insert_one(
                {
                    "_id": guid(version),
                    "ClientId": guid(context.orders.client_id),
                    "ClientName": "BDD Client",
                    "PostalCode": "00-001",
                    "City": "Warsaw",
                    "Street": "Main",
                    "BuildingNumber": "1",
                    "ApartmentNumber": "",
                    "PhoneNumber": "123456789",
                    "PhonePrefix": "+48",
                    "AddressEmail": "fixture@example.test",
                    "CreatedAt": created,
                }
            )
        output["collections"] = lossless(boundary.raw())
    checks.boundary = boundary
    context.orders.fulfillment_handler = None
    context.settings.orders_api_base_url = boundary.url
    context.settings.orders_api_timeout_seconds = 30
    boundary.loss = mode if mode in {"paid_ack_lost", "invoice_ack_lost"} else None
    monkeypatch.setattr(
        importlib.import_module("ecommerce_store_payments.infrastructure.persistence.mongodb.fulfill_payments"),
        "AsyncClient",
        boundary.client,
    )
    if mode == "pdf_storage_failure":
        boundary.block_storage()
