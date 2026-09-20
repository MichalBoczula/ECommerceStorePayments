from decimal import Decimal
from typing import final
from uuid import UUID

from httpx2 import AsyncClient
from pydantic import BaseModel, ConfigDict, Field

from ecommerce_store_payments.application.payments.exceptions import OrderNotFoundError
from ecommerce_store_payments.application.payments.order_details import OrderPaymentDetails
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money


class _OrderResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    status: str
    total_amount: Decimal = Field(alias="totalAmount")
    total_currency: str = Field(alias="totalCurrency")


@final
class HttpOrderReader:
    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    async def get_by_id(self, order_id: UUID) -> OrderPaymentDetails:
        response = await self._client.get(f"/orders/{order_id}")
        if response.status_code == 404:
            raise OrderNotFoundError(order_id)

        response.raise_for_status()
        order = _OrderResponse.model_validate(response.json())

        amount_minor = order.total_amount * 100
        if amount_minor != amount_minor.to_integral_value():
            raise ValueError(f"Order {order_id} amount has more than two decimal places.")

        return OrderPaymentDetails(
            order_id=order.id,
            money=Money(
                amount_minor=int(amount_minor),
                currency=order.total_currency,
            ),
            status=order.status,
        )
