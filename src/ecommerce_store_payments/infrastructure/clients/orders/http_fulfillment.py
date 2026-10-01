"""Generated Invoice/Orders operations behind the fulfillment application ports."""

from collections.abc import Awaitable, Callable
from decimal import DecimalException
from uuid import UUID

from httpx import RequestError
from kiota_abstractions.api_error import APIError

from ecommerce_store_payments.application.payments.exceptions import OrderInvalidResponseError
from ecommerce_store_payments.application.payments.fulfillment import (
    CompletedInvoice,
    FulfillmentBlockedError,
    FulfillmentOrder,
    FulfillmentRetryError,
)
from ecommerce_store_payments.infrastructure.clients.orders.generated.models.invoice_response_dto import (
    InvoiceResponseDto,
)
from ecommerce_store_payments.infrastructure.clients.orders.generated.models.update_order_status_request_dto import (
    UpdateOrderStatusRequestDto,
)
from ecommerce_store_payments.infrastructure.clients.orders.generated.orders_client import OrdersClient
from ecommerce_store_payments.infrastructure.clients.orders.http_order_reader import HttpOrderReader


async def _call[T](operation: Callable[[], Awaitable[T]], code: str) -> T:
    try:
        return await operation()
    except APIError as error:
        if error.response_status_code in {401, 403}:
            raise FulfillmentBlockedError(f"{code}_unauthorized") from error
        raise FulfillmentRetryError(f"{code}_unavailable") from error
    except RequestError as error:
        raise FulfillmentRetryError(f"{code}_unavailable") from error
    except (ValueError, TypeError, UnicodeError, DecimalException) as error:
        raise FulfillmentBlockedError(f"{code}_invalid_response") from error


class HttpFulfillmentOrders:
    def __init__(self, client: OrdersClient) -> None:
        self._client = client

    async def get(self, order_id: UUID) -> FulfillmentOrder:
        order = await _call(lambda: self._client.orders.by_order_id(order_id).get(), "order")
        try:
            details = HttpOrderReader.from_response(order_id, order)
            if order is None or order.client_id is None or order.client_id.int == 0:
                raise FulfillmentBlockedError("order_invalid_response")
        except OrderInvalidResponseError as error:
            raise FulfillmentBlockedError("order_invalid_response") from error
        return FulfillmentOrder(order_id, order.client_id, details.money, details.status)

    async def mark_paid(self, order_id: UUID) -> None:
        # Application always reads back the authoritative order, including on 400/409/timeout.
        await _call(
            lambda: self._client.orders.by_order_id(order_id).status.patch(UpdateOrderStatusRequestDto(status="Paid")),
            "order_update",
        )


class HttpFulfillmentInvoices:
    def __init__(self, client: OrdersClient) -> None:
        self._client = client

    @staticmethod
    def _map(order_id: UUID, invoice: InvoiceResponseDto | None) -> CompletedInvoice:
        if (
            invoice is None
            or invoice.id is None
            or invoice.id.int == 0
            or invoice.order_id != order_id
            or invoice.cliet_data_version_id is None
            or invoice.cliet_data_version_id.int == 0
            or not invoice.storage_url
            or not invoice.storage_url.strip()
            or invoice.created_at is None
        ):
            raise FulfillmentBlockedError("invoice_invalid_response")
        return CompletedInvoice(invoice.id, order_id, invoice.cliet_data_version_id)

    async def get_by_order(self, order_id: UUID) -> CompletedInvoice | None:
        async def read() -> CompletedInvoice | None:
            try:
                invoice = await self._client.invoices.by_order.by_order_id(order_id).get()
                return self._map(order_id, invoice)
            except APIError as error:
                if error.response_status_code == 404:
                    return None
                raise

        return await _call(read, "invoice_lookup")

    async def create(self, client_id: UUID, order_id: UUID) -> CompletedInvoice:
        invoice = await _call(
            lambda: self._client.invoices.by_client_id(client_id).by_order_id(order_id).post(), "invoice_create"
        )
        return self._map(order_id, invoice)
