import asyncio
from uuid import UUID, uuid4

import pytest

from ecommerce_store_payments.application.payments.order_details import OrderPaymentDetails
from ecommerce_store_payments.application.payments.payment_service import PaymentService
from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)


class _OrderReader:
    def __init__(self, order_id: UUID, money: Money, barrier: asyncio.Barrier | None = None) -> None:
        self._order_id = order_id
        self._money = money
        self._barrier = barrier

    async def get_by_id(self, order_id: UUID) -> OrderPaymentDetails:
        assert order_id == self._order_id
        if self._barrier is not None:
            await self._barrier.wait()
        return OrderPaymentDetails(order_id, self._money, "Created")


async def test_retry_preserves_payment_id_and_archives_previous_attempt(mongo_database: MongoDatabase) -> None:
    repository = MongoPaymentRepository(mongo_database)
    order_id = uuid4()
    money = Money(amount_minor=12999, currency="PLN")
    service = PaymentService(repository, _OrderReader(order_id, money))

    initial = await service.pay(order_id)
    assert initial.created and initial.payment.version == 0
    pending = await repository.get_by_order_id(order_id)
    assert pending is not None
    pending.mark_as_pending("cs_old")
    pending = await repository.update(pending)
    pending.mark_as_failed("declined")
    failed = await repository.update(pending)

    retried = await service.pay(order_id)
    repeated = await service.pay(order_id)
    current = await service.get_by_order_id(order_id)
    history = await repository.get_history(failed.id)

    assert not retried.created and not repeated.created
    assert current.id == retried.payment.id == initial.payment.id
    assert current.status is PaymentStatus.CREATED
    assert current.version == retried.payment.version == repeated.payment.version == 3
    assert current.provider_session_id is None and current.failure_code is None
    assert [state.status for state in history] == [
        PaymentStatus.CREATED,
        PaymentStatus.PENDING,
        PaymentStatus.FAILED,
    ]
    assert history[-1].failure_code == "declined"
    assert await mongo_database.payments.count_documents({"order_id": order_id}) == 1


async def test_parallel_first_pay_creates_one_payment(mongo_database: MongoDatabase) -> None:
    repository = MongoPaymentRepository(mongo_database)
    order_id = uuid4()
    reader = _OrderReader(order_id, Money(amount_minor=500, currency="PLN"), asyncio.Barrier(2))
    service = PaymentService(repository, reader)

    first, second = await asyncio.gather(service.pay(order_id), service.pay(order_id))

    assert first.payment.id == second.payment.id
    assert {first.created, second.created} == {True, False}
    assert await mongo_database.payments.count_documents({"order_id": order_id}) == 1


@pytest.mark.parametrize("terminal", [PaymentStatus.FAILED, PaymentStatus.CANCELED])
async def test_parallel_retry_has_one_version_winner(mongo_database: MongoDatabase, terminal: PaymentStatus) -> None:
    repository = MongoPaymentRepository(mongo_database)
    order_id = uuid4()
    money = Money(amount_minor=500, currency="PLN")
    payment = Payment.create(order_id, money)
    await repository.create(payment)
    if terminal is PaymentStatus.FAILED:
        payment.mark_as_pending("cs_old")
        payment = await repository.update(payment)
        payment.mark_as_failed("declined")
    else:
        payment.cancel()
    payment = await repository.update(payment)
    service = PaymentService(repository, _OrderReader(order_id, money, asyncio.Barrier(2)))

    first, second = await asyncio.gather(service.pay(order_id), service.pay(order_id))
    current = await repository.get_by_order_id(order_id)
    history = await repository.get_history(payment.id)

    assert current is not None
    assert first.payment.id == second.payment.id == current.id == payment.id
    assert not first.created and not second.created
    assert first.payment.version == second.payment.version == current.version == payment.version + 1
    assert current.status is PaymentStatus.CREATED
    assert history[-1].status is terminal
    assert len(history) == current.version
    assert await mongo_database.payments.count_documents({"order_id": order_id}) == 1
