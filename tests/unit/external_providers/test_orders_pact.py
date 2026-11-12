"""Consumer-owned examples exercise Orders and fulfillment over Pact HTTP."""

import asyncio
import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from uuid import UUID

import pytest
from httpx import AsyncClient
from kiota_abstractions.authentication.anonymous_authentication_provider import AnonymousAuthenticationProvider
from pact import Pact, match

from ecommerce_store_payments.application.payments.exceptions import OrderNotFoundError
from ecommerce_store_payments.application.payments.fulfillment import CompletedInvoice, FulfillmentOrder
from ecommerce_store_payments.application.payments.order_details import OrderPaymentDetails
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.clients.orders.generated.orders_client import OrdersClient
from ecommerce_store_payments.infrastructure.clients.orders.http_fulfillment import (
    HttpFulfillmentInvoices,
    HttpFulfillmentOrders,
)
from ecommerce_store_payments.infrastructure.clients.orders.http_order_reader import HttpOrderReader
from ecommerce_store_payments.infrastructure.clients.orders.precise_json import PreciseOrderJsonFactory
from ecommerce_store_payments.infrastructure.clients.orders.request_adapter import OrdersRequestAdapter


@dataclass(frozen=True)
class OrderExample:
    order_id: UUID
    currency: str
    total: int | float
    lines: tuple[int | float, ...]
    expected_minor: int


# Independent consumer fixtures: no provider OpenAPI, provider DTOs or generated test data.
EXAMPLES = (
    OrderExample(UUID("10000000-0000-4000-8000-000000000001"), "PLN", 0.29, (0.10, 0.19), 29),
    OrderExample(UUID("10000000-0000-4000-8000-000000000002"), "JPY", 500, (200, 300), 500),
    OrderExample(UUID("10000000-0000-4000-8000-000000000003"), "KWD", 1.234, (1, 0.234), 1234),
    OrderExample(UUID("10000000-0000-4000-8000-000000000004"), "USD", 12345.67, (12300, 45.67), 1234567),
)
MISSING_ID = UUID("10000000-0000-4000-8000-000000000099")
FULFILLMENT_ORDER = OrderExample(UUID("10000000-0000-4000-8000-000000000010"), "PLN", 12.99, (7.50, 5.49), 1299)
ORDER_TO_INVOICE = OrderExample(UUID("10000000-0000-4000-8000-000000000011"), "PLN", 12.99, (7.50, 5.49), 1299)
CLIENT_ID = UUID("10000000-0000-4000-8000-000000000012")
INVOICE_ID = UUID("10000000-0000-4000-8000-000000000013")
CLIENT_DATA_VERSION_ID = UUID("10000000-0000-4000-8000-000000000014")
NEW_INVOICE_ID = UUID("10000000-0000-4000-8000-000000000015")
INTERACTION_COUNT = 10
PACT_NAME = "payments-invoice.json"


def _order_body(example: OrderExample, status: str = "Created") -> dict[str, object]:
    return {
        "id": str(example.order_id),
        "status": status,
        "totalAmount": example.total,
        "totalCurrency": example.currency,
        "lines": [
            {"lineTotalAmount": amount, "productVersion": {"priceCurrency": example.currency}}
            for amount in example.lines
        ],
    }


def _order_state(example: OrderExample) -> dict[str, str | list[str]]:
    return {
        "orderId": str(example.order_id),
        "currency": example.currency,
        "totalAmount": str(example.total),
        "lineAmounts": [str(amount) for amount in example.lines],
    }


def _invoice_body(order_id: UUID, *, generated_id: bool = False) -> dict[str, object]:
    return {
        "id": match.uuid(str(NEW_INVOICE_ID)) if generated_id else str(INVOICE_ID),
        "orderId": str(order_id),
        "clietDataVersionId": str(CLIENT_DATA_VERSION_ID),
        "storageUrl": match.regex("file:///invoice.pdf", regex=r"^\s*\S.*$"),
        "createdAt": match.regex(
            "2026-10-01T00:00:00Z",
            regex=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,7})?(Z|[+-]\d{2}:\d{2})$",
        ),
    }


def _add_fulfillment_interactions(pact: Pact) -> None:
    order_id = FULFILLMENT_ORDER.order_id
    order_state = {**_order_state(FULFILLMENT_ORDER), "clientId": str(CLIENT_ID)}
    (
        pact.upon_receiving("read the Paid order and its owner for fulfillment")
        .given("a Paid order exists for fulfillment", **order_state)
        .with_request("GET", f"/orders/{order_id}")
        .with_header("Accept", "application/json")
        .will_respond_with(200)
        .with_body(
            {**_order_body(FULFILLMENT_ORDER, "Paid"), "clientId": str(CLIENT_ID)}, content_type="application/json"
        )
    )
    (
        pact.upon_receiving("mark a Created order Paid")
        .given("a Created order exists for fulfillment", **order_state)
        .with_request("PATCH", f"/orders/{order_id}/status")
        .with_header("Accept", "application/json")
        .with_body({"status": "Paid"}, content_type="application/json")
        .will_respond_with(200)
    )
    (
        pact.upon_receiving("read the completed invoice for an order")
        .given(
            "a completed invoice exists for the order",
            orderId=str(order_id),
            invoiceId=str(INVOICE_ID),
            clientDataVersionId=str(CLIENT_DATA_VERSION_ID),
        )
        .with_request("GET", f"/invoices/by-order/{order_id}")
        .with_header("Accept", "application/json")
        .will_respond_with(200)
        .with_body(_invoice_body(order_id), content_type="application/json")
    )
    order_to_invoice = ORDER_TO_INVOICE.order_id
    (
        pact.upon_receiving("find no completed invoice for an order")
        .given("the order has no completed invoice", orderId=str(order_to_invoice))
        .with_request("GET", f"/invoices/by-order/{order_to_invoice}")
        .with_header("Accept", "application/json")
        .will_respond_with(404)
        .with_body({"status": 404}, content_type="application/problem+json")
    )
    (
        pact.upon_receiving("create an invoice for a Paid order")
        .given(
            "a Paid order and client data exist without an invoice",
            **_order_state(ORDER_TO_INVOICE),
            clientId=str(CLIENT_ID),
            clientDataVersionId=str(CLIENT_DATA_VERSION_ID),
        )
        .with_request("POST", f"/invoices/{CLIENT_ID}/{order_to_invoice}")
        .with_header("Accept", "application/json")
        .will_respond_with(200)
        .with_body(_invoice_body(order_to_invoice, generated_id=True), content_type="application/json")
    )


async def _exercise_fulfillment(client: OrdersClient) -> None:
    orders = HttpFulfillmentOrders(client)
    invoices = HttpFulfillmentInvoices(client)
    order_id = FULFILLMENT_ORDER.order_id
    await orders.mark_paid(order_id)
    assert await orders.get(order_id) == FulfillmentOrder(
        order_id=order_id,
        client_id=CLIENT_ID,
        money=Money(amount_minor=FULFILLMENT_ORDER.expected_minor, currency=FULFILLMENT_ORDER.currency),
        status="Paid",
    )
    assert await invoices.get_by_order(order_id) == CompletedInvoice(INVOICE_ID, order_id, CLIENT_DATA_VERSION_ID)
    assert await invoices.get_by_order(ORDER_TO_INVOICE.order_id) is None
    assert await invoices.create(CLIENT_ID, ORDER_TO_INVOICE.order_id) == CompletedInvoice(
        NEW_INVOICE_ID, ORDER_TO_INVOICE.order_id, CLIENT_DATA_VERSION_ID
    )


async def _exercise_consumer(directory: Path) -> Path:
    pact = Pact("payments", "invoice").with_specification("V4")
    for example in EXAMPLES:
        (
            pact.upon_receiving(f"read a Created order in {example.currency}")
            .given("a Created order exists for payment", **_order_state(example))
            .with_request("GET", f"/orders/{example.order_id}")
            .with_header("Accept", "application/json")
            .will_respond_with(200)
            .with_body(_order_body(example), content_type="application/json")
        )
    (
        pact.upon_receiving("read an order that does not exist")
        .given("the order does not exist", orderId=str(MISSING_ID))
        .with_request("GET", f"/orders/{MISSING_ID}")
        .with_header("Accept", "application/json")
        .will_respond_with(404)
        .with_body({"status": 404}, content_type="application/problem+json")
    )
    _add_fulfillment_interactions(pact)

    # No MockTransport, replacement parser or direct DTO construction: the real
    # generated GET and response deserialization use the production HTTP stack.
    with pact.serve(addr="127.0.0.1") as server:
        base_url = str(server.url)
        async with AsyncClient(base_url=base_url, timeout=5, trust_env=False) as client:
            orders_client = OrdersClient(
                OrdersRequestAdapter(
                    AnonymousAuthenticationProvider(),
                    parse_node_factory=PreciseOrderJsonFactory(),
                    http_client=client,
                    base_url=base_url,
                )
            )
            reader = HttpOrderReader(orders_client)
            for example in EXAMPLES:
                result = await reader.get_by_id(example.order_id)
                assert result == OrderPaymentDetails(
                    order_id=example.order_id,
                    money=Money(amount_minor=example.expected_minor, currency=example.currency),
                    status="Created",
                )
            with pytest.raises(OrderNotFoundError) as error:
                await reader.get_by_id(MISSING_ID)
            assert str(MISSING_ID) in str(error.value)
            await _exercise_fulfillment(orders_client)
    # The default server context rejects unmatched/missing requests. Write only
    # after that verification and every application-model assertion succeeds.
    pact.write_file(directory, overwrite=True)
    return directory / PACT_NAME


async def test_orders_consumer_pact_is_reproducible_and_maps_application_results(tmp_path: Path) -> None:
    first = await _exercise_consumer(tmp_path / "first")
    second = await _exercise_consumer(tmp_path / "second")
    content = first.read_bytes()
    assert content == second.read_bytes(), "Identical source/toolchain must produce identical Pact bytes."
    document = json.loads(content)
    assert document["consumer"]["name"] == "payments"
    assert document["provider"]["name"] == "invoice"
    assert document["metadata"]["pactSpecification"]["version"] == "4.0"
    assert len(document["interactions"]) == INTERACTION_COUNT

    await asyncio.to_thread(_publish_contract, first, content)


def _publish_contract(first: Path, content: bytes) -> None:
    output = Path(os.environ.get("PAYMENTS_PACT_DIR", "artifacts/verification/pact/pacts"))
    output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(first, output / PACT_NAME)  # preserve the official writer's exact bytes
    (output / "manifest.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "consumer": "payments",
                "provider": "invoice",
                "pactSpecification": "4.0",
                "pactPython": version("pact-python"),
                "pactPythonFfi": version("pact-python-ffi"),
                "file": PACT_NAME,
                "sha256": hashlib.sha256(content).hexdigest(),
                "interactionCount": INTERACTION_COUNT,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
