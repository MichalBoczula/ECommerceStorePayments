from typing import Protocol
from uuid import UUID

from ecommerce_store_payments.domain.aggregates.payments.payment import Payment


class PaymentRepository(Protocol):
    async def create(self, payment: Payment) -> Payment: ...

    async def update(self, payment: Payment) -> Payment: ...

    async def get_by_id(self, payment_id: UUID) -> Payment | None: ...

    async def get_by_order_id(self, order_id: UUID) -> Payment | None: ...
