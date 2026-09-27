from typing import final
from uuid import UUID

from ecommerce_store_payments.application.payments.exceptions import (
    OrderNotPayableError,
    OrderTotalChangedError,
    PaymentNotFoundError,
)
from ecommerce_store_payments.application.payments.order_reader import OrderReader
from ecommerce_store_payments.application.payments.pay_result import PayResult
from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import (
    PaymentConflictError,
    PaymentDuplicateError,
)
from ecommerce_store_payments.domain.aggregates.payments.repositories.payment_repository import PaymentRepository


@final
class PaymentService:
    def __init__(self, payment_repository: PaymentRepository, order_reader: OrderReader) -> None:
        self._payment_repository = payment_repository
        self._order_reader = order_reader

    async def pay(self, order_id: UUID) -> PayResult:
        existing_payment = await self._payment_repository.get_by_order_id(order_id)
        if existing_payment is not None:
            if existing_payment.status in (PaymentStatus.FAILED, PaymentStatus.CANCELED):
                return await self._retry(existing_payment)
            return PayResult(existing_payment, created=False)

        order = await self._order_reader.get_by_id(order_id)
        self._require_created_order(order_id, order.status)

        payment = Payment.create(order_id=order.order_id, money=order.money)
        try:
            return PayResult(await self._payment_repository.create(payment), created=True)
        except PaymentDuplicateError:
            existing_payment = await self._payment_repository.get_by_order_id(order_id)
            if existing_payment is None:
                raise
            if existing_payment.status in (PaymentStatus.FAILED, PaymentStatus.CANCELED):
                return await self._retry(existing_payment)
            return PayResult(existing_payment, created=False)

    async def _retry(self, payment: Payment) -> PayResult:
        order = await self._order_reader.get_by_id(payment.order_id)
        self._require_created_order(payment.order_id, order.status)
        if order.money != payment.money:
            raise OrderTotalChangedError(payment.order_id)

        payment.retry()
        try:
            return PayResult(await self._payment_repository.update(payment), created=False)
        except PaymentConflictError:
            current = await self._payment_repository.get_by_order_id(payment.order_id)
            if current is None or current.version <= payment.version:
                raise
            if current.status in (PaymentStatus.FAILED, PaymentStatus.CANCELED):
                raise
            return PayResult(current, created=False)

    @staticmethod
    def _require_created_order(order_id: UUID, status: str) -> None:
        if status.casefold() != "created":
            raise OrderNotPayableError(order_id, status)

    async def get_by_order_id(self, order_id: UUID) -> Payment:
        payment = await self._payment_repository.get_by_order_id(order_id)
        if payment is None:
            raise PaymentNotFoundError(order_id)

        return payment
