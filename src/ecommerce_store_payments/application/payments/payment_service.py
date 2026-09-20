from typing import final
from uuid import UUID

from ecommerce_store_payments.application.payments.exceptions import OrderNotPayableError, PaymentNotFoundError
from ecommerce_store_payments.application.payments.order_reader import OrderReader
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.repositories.payment_repository import PaymentRepository


@final
class PaymentService:
    def __init__(self, payment_repository: PaymentRepository, order_reader: OrderReader) -> None:
        self._payment_repository = payment_repository
        self._order_reader = order_reader

    async def pay(self, order_id: UUID) -> Payment:
        existing_payment = await self._payment_repository.get_by_order_id(order_id)
        if existing_payment is not None:
            return existing_payment

        order = await self._order_reader.get_by_id(order_id)
        if order.status.casefold() != "created":
            raise OrderNotPayableError(order_id, order.status)

        payment = Payment.create(order_id=order.order_id, money=order.money)
        return await self._payment_repository.create(payment)

    async def get_by_order_id(self, order_id: UUID) -> Payment:
        payment = await self._payment_repository.get_by_order_id(order_id)
        if payment is None:
            raise PaymentNotFoundError(order_id)

        return payment
