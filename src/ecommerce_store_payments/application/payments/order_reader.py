from typing import Protocol
from uuid import UUID

from ecommerce_store_payments.application.payments.order_details import OrderPaymentDetails


class OrderReader(Protocol):
    async def get_by_id(self, order_id: UUID) -> OrderPaymentDetails: ...
