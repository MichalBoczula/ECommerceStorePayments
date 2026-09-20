from dataclasses import dataclass
from typing import final
from uuid import UUID

from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money


@final
@dataclass(frozen=True, slots=True)
class OrderPaymentDetails:
    order_id: UUID
    money: Money
    status: str
