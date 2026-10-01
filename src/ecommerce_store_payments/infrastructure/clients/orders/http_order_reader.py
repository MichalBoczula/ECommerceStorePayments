"""Map the generated Invoice client onto the Application OrderReader port."""

from decimal import Decimal, DecimalException, localcontext
from typing import final
from uuid import UUID

from httpx import RequestError, TimeoutException
from kiota_abstractions.api_error import APIError

from ecommerce_store_payments.application.payments.exceptions import (
    OrderInvalidResponseError,
    OrderNotFoundError,
    OrderTimeoutError,
    OrderUnavailableError,
)
from ecommerce_store_payments.application.payments.order_details import OrderPaymentDetails
from ecommerce_store_payments.domain.aggregates.payments.exceptions import MoneyValidationError
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.clients.orders.currency_units import to_minor_units
from ecommerce_store_payments.infrastructure.clients.orders.generated.models.order_response_dto import OrderResponseDto
from ecommerce_store_payments.infrastructure.clients.orders.generated.orders_client import OrdersClient


def _exact_amount(value: object) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError("Orders amount is not an exact JSON number.")
    return value


@final
class HttpOrderReader:
    def __init__(self, client: OrdersClient) -> None:
        self._client = client

    async def get_by_id(self, order_id: UUID) -> OrderPaymentDetails:
        try:
            order = await self._client.orders.by_order_id(order_id).get()
        except APIError as error:
            if error.response_status_code == 404:
                raise OrderNotFoundError(order_id) from error
            raise OrderUnavailableError(order_id) from error
        except TimeoutException as error:
            raise OrderTimeoutError(order_id) from error
        except RequestError as error:
            raise OrderUnavailableError(order_id) from error
        except (ValueError, TypeError, UnicodeError, DecimalException) as error:
            raise OrderInvalidResponseError(order_id) from error

        return self.from_response(order_id, order)

    @staticmethod
    def from_response(order_id: UUID, order: OrderResponseDto | None) -> OrderPaymentDetails:
        try:
            if not isinstance(order, OrderResponseDto) or not order.lines:
                raise OrderInvalidResponseError(order_id)
            total = _exact_amount(order.total_amount)
            lines = [_exact_amount(line.line_total_amount) for line in order.lines]
            if any(line.adjusted() > 28 for line in lines):
                raise OrderInvalidResponseError(order_id)
            with localcontext() as context:
                context.prec = max(
                    context.prec,
                    max(len(line.as_tuple().digits) for line in lines) + len(str(len(lines))) + 1,
                )
                lines_total = sum(lines)
            if (
                order.id != order_id
                or not order.status
                or not order.status.strip()
                or not order.total_currency
                or any(
                    line.product_version is None or line.product_version.price_currency != order.total_currency
                    for line in order.lines
                )
                or lines_total != total
            ):
                raise OrderInvalidResponseError(order_id)

            money = Money(amount_minor=to_minor_units(total, order.total_currency), currency=order.total_currency)
        except (AttributeError, DecimalException, TypeError, ValueError, MoneyValidationError) as error:
            raise OrderInvalidResponseError(order_id) from error

        return OrderPaymentDetails(order_id=order_id, money=money, status=order.status)
