import json
from collections.abc import Callable
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient, ConnectError, MockTransport, ReadTimeout, Request, Response
from kiota_abstractions.authentication.anonymous_authentication_provider import AnonymousAuthenticationProvider

from ecommerce_store_payments.application.payments.exceptions import (
    OrderInvalidResponseError,
    OrderNotFoundError,
    OrderTimeoutError,
    OrderUnavailableError,
)
from ecommerce_store_payments.infrastructure.clients.orders.generated.orders_client import OrdersClient
from ecommerce_store_payments.infrastructure.clients.orders.http_order_reader import HttpOrderReader
from ecommerce_store_payments.infrastructure.clients.orders.precise_json import PreciseOrderJsonFactory
from ecommerce_store_payments.infrastructure.clients.orders.request_adapter import OrdersRequestAdapter


def _order(order_id: UUID, amount: float | int, currency: str = "PLN") -> dict[str, Any]:
    return {
        "id": str(order_id),
        "clientId": str(uuid4()),
        "createdAt": "2026-09-27T12:00:00Z",
        "status": "Created",
        "totalAmount": amount,
        "totalCurrency": currency,
        "lines": [
            {
                "productVersionId": str(uuid4()),
                "quantity": 1,
                "lineTotalAmount": amount,
                "productVersion": {
                    "id": str(uuid4()),
                    "productId": str(uuid4()),
                    "isActive": True,
                    "createdAt": "2026-09-27T12:00:00Z",
                    "name": "Product",
                    "brand": "Brand",
                    "priceAmount": amount,
                    "priceCurrency": currency,
                },
            }
        ],
    }


async def _get_order(order_id: UUID, handler: Callable[[Request], Response]) -> tuple[HttpOrderReader, AsyncClient]:
    client = AsyncClient(base_url="https://orders.example.test", transport=MockTransport(handler))
    adapter = OrdersRequestAdapter(
        AnonymousAuthenticationProvider(),
        parse_node_factory=PreciseOrderJsonFactory(),
        http_client=client,
        base_url="https://orders.example.test",
    )
    return HttpOrderReader(OrdersClient(adapter)), client


@pytest.mark.parametrize(
    ("amount", "currency", "expected_minor"),
    [(12.34, "PLN", 1234), (0.29, "USD", 29), (500, "JPY", 500), (1.234, "KWD", 1234)],
)
async def test_maps_actual_orders_response_with_currency_exponent(
    amount: float | int, currency: str, expected_minor: int
) -> None:
    order_id = uuid4()

    def handler(request: Request) -> Response:
        assert request.method == "GET"
        assert request.url.path == f"/orders/{order_id}"
        return Response(200, json=_order(order_id, amount, currency))

    reader, client = await _get_order(order_id, handler)
    async with client:
        result = await reader.get_by_id(order_id)

    assert result.order_id == order_id
    assert result.money.amount_minor == expected_minor
    assert result.money.currency == currency
    assert result.status == "Created"


async def test_maps_404_to_order_not_found() -> None:
    order_id = uuid4()
    reader, client = await _get_order(order_id, lambda _request: Response(404, json={"detail": "private"}))
    async with client:
        with pytest.raises(OrderNotFoundError):
            await reader.get_by_id(order_id)


@pytest.mark.parametrize("status_code", [204, 302, 429, 500, 503])
async def test_maps_unexpected_upstream_status_to_unavailable(status_code: int) -> None:
    order_id = uuid4()
    reader, client = await _get_order(order_id, lambda _request: Response(status_code))
    async with client:
        with pytest.raises(OrderUnavailableError) as error:
            await reader.get_by_id(order_id)
    assert str(error.value) == f"Cannot read order {order_id}: Orders service is unavailable."


@pytest.mark.parametrize("failure", [ReadTimeout, ConnectError])
async def test_maps_transport_failures(failure: type[ReadTimeout] | type[ConnectError]) -> None:
    order_id = uuid4()

    def handler(request: Request) -> Response:
        raise failure("private connection detail", request=request)

    reader, client = await _get_order(order_id, handler)
    expected = OrderTimeoutError if failure is ReadTimeout else OrderUnavailableError
    async with client:
        with pytest.raises(expected) as error:
            await reader.get_by_id(order_id)
    assert "private connection detail" not in str(error.value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "wrong-id"),
        ("status", "  "),
        ("totalCurrency", "ZZZ"),
        ("totalCurrency", "pln"),
        ("totalAmount", 0),
        ("totalAmount", -1),
        ("totalAmount", 1.234),
        ("totalAmount", "12.34"),
        ("lines", []),
    ],
)
async def test_rejects_invalid_order_response(field: str, value: object) -> None:
    order_id = uuid4()
    payload = _order(order_id, 12.34)
    payload[field] = value
    reader, client = await _get_order(order_id, lambda _request: Response(200, json=payload))
    async with client:
        with pytest.raises(OrderInvalidResponseError):
            await reader.get_by_id(order_id)


@pytest.mark.parametrize("mismatch", ["line_total", "line_currency"])
async def test_rejects_inconsistent_order_lines(mismatch: str) -> None:
    order_id = uuid4()
    payload = _order(order_id, 12.34)
    if mismatch == "line_total":
        payload["lines"][0]["lineTotalAmount"] = 10
    else:
        payload["lines"][0]["productVersion"]["priceCurrency"] = "USD"
    reader, client = await _get_order(order_id, lambda _request: Response(200, json=payload))
    async with client:
        with pytest.raises(OrderInvalidResponseError):
            await reader.get_by_id(order_id)


async def test_rejects_amount_that_cannot_be_represented_in_jpy() -> None:
    order_id = uuid4()
    reader, client = await _get_order(order_id, lambda _request: Response(200, json=_order(order_id, 1.5, "JPY")))
    async with client:
        with pytest.raises(OrderInvalidResponseError):
            await reader.get_by_id(order_id)


@pytest.mark.parametrize("body", ["{", "[]", '"not an order"', '{"totalAmount":"12.34"}'])
async def test_rejects_unparseable_or_incomplete_body(body: str) -> None:
    order_id = uuid4()
    reader, client = await _get_order(order_id, lambda _request: Response(200, text=body))
    async with client:
        with pytest.raises(OrderInvalidResponseError):
            await reader.get_by_id(order_id)


async def test_rejects_string_amount_even_when_other_fields_are_valid() -> None:
    order_id = uuid4()
    payload = _order(order_id, 12.34)
    payload["totalAmount"] = "12.34"
    reader, client = await _get_order(order_id, lambda _request: Response(200, text=json.dumps(payload)))
    async with client:
        with pytest.raises(OrderInvalidResponseError):
            await reader.get_by_id(order_id)


async def test_preserves_large_decimal_without_rounding() -> None:
    order_id = uuid4()
    amount = "1234567890123456789012345678.90"
    payload = _order(order_id, 1)
    payload["totalAmount"] = Decimal(amount)
    payload["lines"][0]["lineTotalAmount"] = Decimal(amount)
    body = json.dumps(payload, default=str).replace(f'"{amount}"', amount)
    reader, client = await _get_order(order_id, lambda _request: Response(200, text=body))
    async with client:
        result = await reader.get_by_id(order_id)
    assert result.money.amount_minor == 123456789012345678901234567890


async def test_rejects_unbounded_exponent() -> None:
    order_id = uuid4()
    payload = _order(order_id, 1)
    body = (
        json.dumps(payload)
        .replace('"totalAmount": 1', '"totalAmount": 1e1000000')
        .replace('"lineTotalAmount": 1', '"lineTotalAmount": 1e1000000')
    )
    reader, client = await _get_order(order_id, lambda _request: Response(200, text=body))
    async with client:
        with pytest.raises(OrderInvalidResponseError):
            await reader.get_by_id(order_id)
