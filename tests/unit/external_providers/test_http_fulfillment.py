import json
from collections.abc import AsyncGenerator, Callable
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient, MockTransport, ReadTimeout, Request, Response
from kiota_abstractions.authentication.anonymous_authentication_provider import AnonymousAuthenticationProvider

from ecommerce_store_payments.application.payments.fulfillment import FulfillmentBlockedError, FulfillmentRetryError
from ecommerce_store_payments.infrastructure.clients.orders.generated.orders_client import OrdersClient
from ecommerce_store_payments.infrastructure.clients.orders.http_fulfillment import (
    HttpFulfillmentInvoices,
    HttpFulfillmentOrders,
)
from ecommerce_store_payments.infrastructure.clients.orders.precise_json import PreciseOrderJsonFactory
from ecommerce_store_payments.infrastructure.clients.orders.request_adapter import OrdersRequestAdapter
from tests.unit.external_providers.test_http_order_reader import order_payload

ORDER_ID, CLIENT_ID, INVOICE_ID, VERSION_ID = (uuid4() for _ in range(4))


def invoice_payload() -> dict[str, Any]:
    return {
        "id": str(INVOICE_ID),
        "orderId": str(ORDER_ID),
        "clietDataVersionId": str(VERSION_ID),
        "storageUrl": "file:///invoice.pdf",
        "createdAt": "2026-10-01T00:00:00Z",
    }


@pytest.fixture
async def adapters() -> AsyncGenerator[
    tuple[HttpFulfillmentOrders, HttpFulfillmentInvoices, list[Callable[[Request], Response]]]
]:
    handlers: list[Callable[[Request], Response]] = []
    async with AsyncClient(
        base_url="https://orders.example.test", transport=MockTransport(lambda request: handlers[0](request))
    ) as transport:
        client = OrdersClient(
            OrdersRequestAdapter(
                AnonymousAuthenticationProvider(),
                parse_node_factory=PreciseOrderJsonFactory(),
                http_client=transport,
                base_url="https://orders.example.test",
            )
        )
        yield HttpFulfillmentOrders(client), HttpFulfillmentInvoices(client), handlers


async def test_reads_valid_owner_and_exact_money(
    adapters: tuple[HttpFulfillmentOrders, HttpFulfillmentInvoices, list[Callable[[Request], Response]]],
) -> None:
    orders, _, handlers = adapters
    body = order_payload(ORDER_ID, 12.99)
    body["clientId"] = str(CLIENT_ID)
    handlers.append(lambda request: Response(200, json=body))
    result = await orders.get(ORDER_ID)
    assert result.client_id == CLIENT_ID and result.money.amount_minor == 1299


async def test_serializes_paid_patch(
    adapters: tuple[HttpFulfillmentOrders, HttpFulfillmentInvoices, list[Callable[[Request], Response]]],
) -> None:
    orders, _, handlers = adapters

    def handler(request: Request) -> Response:
        assert request.method == "PATCH" and request.url.path == f"/orders/{ORDER_ID}/status"
        assert json.loads(request.content) == {"status": "Paid"}
        return Response(200, json=order_payload(ORDER_ID, 12.99))

    handlers.append(handler)
    await orders.mark_paid(ORDER_ID)


@pytest.mark.parametrize("code", [400, 404, 409, 429, 500, 503, 204, 302])
async def test_downstream_error_is_safe_and_reconcilable(
    adapters: tuple[HttpFulfillmentOrders, HttpFulfillmentInvoices, list[Callable[[Request], Response]]], code: int
) -> None:
    orders, _, handlers = adapters
    handlers.append(lambda request: Response(code, json={"detail": "private secret"}))
    with pytest.raises(FulfillmentRetryError) as error:
        await orders.mark_paid(ORDER_ID)
    assert str(error.value) == "order_update_unavailable"


@pytest.mark.parametrize("owner", [None, "00000000-0000-0000-0000-000000000000", "wrong-id"])
async def test_invalid_owner_is_blocked(
    adapters: tuple[HttpFulfillmentOrders, HttpFulfillmentInvoices, list[Callable[[Request], Response]]],
    owner: str | None,
) -> None:
    orders, _, handlers = adapters
    body = order_payload(ORDER_ID, 12.99)
    body["clientId"] = owner
    handlers.append(lambda request: Response(200, json=body))
    with pytest.raises(FulfillmentBlockedError):
        await orders.get(ORDER_ID)


async def test_invoice_lookup_and_create_use_generated_routes(
    adapters: tuple[HttpFulfillmentOrders, HttpFulfillmentInvoices, list[Callable[[Request], Response]]],
) -> None:
    _, invoices, handlers = adapters
    paths: list[tuple[str, str]] = []

    def handler(request: Request) -> Response:
        paths.append((request.method, request.url.path))
        return Response(200, json=invoice_payload())

    handlers.append(handler)
    result = await invoices.get_by_order(ORDER_ID)
    assert result is not None and result.invoice_id == INVOICE_ID and result.client_data_version_id == VERSION_ID
    assert await invoices.create(CLIENT_ID, ORDER_ID) == result
    assert paths == [("GET", f"/invoices/by-order/{ORDER_ID}"), ("POST", f"/invoices/{CLIENT_ID}/{ORDER_ID}")]


async def test_only_lookup_404_means_not_completed(
    adapters: tuple[HttpFulfillmentOrders, HttpFulfillmentInvoices, list[Callable[[Request], Response]]],
) -> None:
    _, invoices, handlers = adapters
    handlers.append(lambda request: Response(404, json={"detail": "private"}))
    assert await invoices.get_by_order(ORDER_ID) is None
    with pytest.raises(FulfillmentRetryError):
        await invoices.create(CLIENT_ID, ORDER_ID)


@pytest.mark.parametrize(
    "field,value",
    [("id", None), ("orderId", str(uuid4())), ("clietDataVersionId", None), ("storageUrl", ""), ("createdAt", None)],
)
async def test_incomplete_or_wrong_invoice_is_blocked(
    adapters: tuple[HttpFulfillmentOrders, HttpFulfillmentInvoices, list[Callable[[Request], Response]]],
    field: str,
    value: object,
) -> None:
    _, invoices, handlers = adapters
    body = invoice_payload()
    body[field] = value
    handlers.append(lambda request: Response(200, json=body))
    with pytest.raises(FulfillmentBlockedError):
        await invoices.get_by_order(ORDER_ID)


@pytest.mark.parametrize("code", [401, 403])
async def test_auth_failure_requires_configuration_repair(
    adapters: tuple[HttpFulfillmentOrders, HttpFulfillmentInvoices, list[Callable[[Request], Response]]], code: int
) -> None:
    orders, _, handlers = adapters
    handlers.append(lambda request: Response(code))
    with pytest.raises(FulfillmentBlockedError):
        await orders.get(ORDER_ID)


async def test_transport_timeout_is_recoverable(
    adapters: tuple[HttpFulfillmentOrders, HttpFulfillmentInvoices, list[Callable[[Request], Response]]],
) -> None:
    orders, _, handlers = adapters

    def handler(request: Request) -> Response:
        raise ReadTimeout("private", request=request)

    handlers.append(handler)
    with pytest.raises(FulfillmentRetryError):
        await orders.get(ORDER_ID)
