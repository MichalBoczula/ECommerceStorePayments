import json
from decimal import Decimal, DecimalException, localcontext
from typing import final
from uuid import UUID

from httpx2 import AsyncClient, RequestError, TimeoutException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

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


class _ProductVersionResponse(BaseModel):
    price_currency: str = Field(alias="priceCurrency")


class _OrderLineResponse(BaseModel):
    line_total_amount: Decimal = Field(alias="lineTotalAmount", ge=0, allow_inf_nan=False, strict=True)
    product_version: _ProductVersionResponse = Field(alias="productVersion")


class _OrderResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    status: str = Field(min_length=1)
    total_amount: Decimal = Field(alias="totalAmount", gt=0, allow_inf_nan=False, strict=True)
    total_currency: str = Field(alias="totalCurrency")
    lines: list[_OrderLineResponse]


@final
class HttpOrderReader:
    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def get_by_id(self, order_id: UUID) -> OrderPaymentDetails:
        try:
            response = await self._client.get(f"/orders/{order_id}")
        except TimeoutException as error:
            raise OrderTimeoutError(order_id) from error
        except RequestError as error:
            raise OrderUnavailableError(order_id) from error

        if response.status_code == 404:
            raise OrderNotFoundError(order_id)
        if response.status_code != 200:
            raise OrderUnavailableError(order_id)

        try:
            payload = json.loads(response.text, parse_float=Decimal, parse_int=Decimal)
            order = _OrderResponse.model_validate(payload)
            if not order.lines:
                raise OrderInvalidResponseError(order_id)
            if any(line.line_total_amount.adjusted() > 28 for line in order.lines):
                raise OrderInvalidResponseError(order_id)
            with localcontext() as context:
                context.prec = max(
                    context.prec,
                    max(len(line.line_total_amount.as_tuple().digits) for line in order.lines)
                    + len(str(len(order.lines)))
                    + 1,
                )
                lines_total = sum(line.line_total_amount for line in order.lines)
            if (
                order.id != order_id
                or not order.status.strip()
                or any(line.product_version.price_currency != order.total_currency for line in order.lines)
                or lines_total != order.total_amount
            ):
                raise OrderInvalidResponseError(order_id)

            money = Money(
                amount_minor=to_minor_units(order.total_amount, order.total_currency),
                currency=order.total_currency,
            )
        except (json.JSONDecodeError, DecimalException, ValidationError, ValueError, MoneyValidationError) as error:
            raise OrderInvalidResponseError(order_id) from error

        return OrderPaymentDetails(
            order_id=order.id,
            money=money,
            status=order.status,
        )
