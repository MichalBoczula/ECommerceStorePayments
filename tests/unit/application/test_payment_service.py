from typing import cast
from uuid import UUID, uuid4

import pytest

from ecommerce_store_payments.application.payments.exceptions import OrderNotPayableError, PaymentNotFoundError
from ecommerce_store_payments.application.payments.order_details import OrderPaymentDetails
from ecommerce_store_payments.application.payments.order_reader import OrderReader
from ecommerce_store_payments.application.payments.payment_service import PaymentService
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.repositories.payment_repository import PaymentRepository
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money


class _PaymentRepository:
    def __init__(self) -> None:
        self.payments: dict[UUID, Payment] = {}

    async def create(self, payment: Payment) -> Payment:
        self.payments[payment.order_id] = payment
        return payment

    async def update(self, payment: Payment) -> Payment:
        self.payments[payment.order_id] = payment
        return payment

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        return next((payment for payment in self.payments.values() if payment.id == payment_id), None)

    async def get_by_order_id(self, order_id: UUID) -> Payment | None:
        return self.payments.get(order_id)


class _OrderReader:
    def __init__(self, order: OrderPaymentDetails) -> None:
        self.order = order
        self.calls = 0

    async def get_by_id(self, order_id: UUID) -> OrderPaymentDetails:
        self.calls += 1
        assert order_id == self.order.order_id
        return self.order


def _create_service(
    repository: _PaymentRepository,
    order_reader: _OrderReader,
) -> PaymentService:
    return PaymentService(
        payment_repository=cast(PaymentRepository, repository),
        order_reader=cast(OrderReader, order_reader),
    )


@pytest.mark.asyncio
async def test_pay_creates_payment_from_order_details() -> None:
    order_id = uuid4()
    repository = _PaymentRepository()
    order_reader = _OrderReader(
        OrderPaymentDetails(
            order_id=order_id,
            money=Money(amount_minor=12999, currency="PLN"),
            status="Created",
        )
    )
    service = _create_service(repository, order_reader)

    payment = await service.pay(order_id)

    assert payment.order_id == order_id
    assert payment.money == Money(amount_minor=12999, currency="PLN")
    assert await repository.get_by_order_id(order_id) is payment


@pytest.mark.asyncio
async def test_pay_returns_existing_payment_without_loading_order() -> None:
    order_id = uuid4()
    repository = _PaymentRepository()
    existing_payment = Payment.create(order_id, Money(amount_minor=12999, currency="PLN"))
    await repository.create(existing_payment)
    order_reader = _OrderReader(
        OrderPaymentDetails(
            order_id=order_id,
            money=Money(amount_minor=50000, currency="PLN"),
            status="Created",
        )
    )
    service = _create_service(repository, order_reader)

    payment = await service.pay(order_id)

    assert payment is existing_payment
    assert order_reader.calls == 0


@pytest.mark.asyncio
async def test_pay_rejects_order_that_is_not_created() -> None:
    order_id = uuid4()
    repository = _PaymentRepository()
    order_reader = _OrderReader(
        OrderPaymentDetails(
            order_id=order_id,
            money=Money(amount_minor=12999, currency="PLN"),
            status="Paid",
        )
    )
    service = _create_service(repository, order_reader)

    with pytest.raises(OrderNotPayableError, match="cannot be paid"):
        await service.pay(order_id)


@pytest.mark.asyncio
async def test_get_by_order_id_raises_when_payment_is_missing() -> None:
    order_id = uuid4()
    repository = _PaymentRepository()
    order_reader = _OrderReader(
        OrderPaymentDetails(
            order_id=order_id,
            money=Money(amount_minor=12999, currency="PLN"),
            status="Created",
        )
    )
    service = _create_service(repository, order_reader)

    with pytest.raises(PaymentNotFoundError, match=str(order_id)):
        await service.get_by_order_id(order_id)
