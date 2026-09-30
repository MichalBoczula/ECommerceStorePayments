import asyncio
from uuid import UUID

import pytest

from ecommerce_store_payments.application.payments.checkout_provider import CheckoutRequest, CheckoutSession
from ecommerce_store_payments.application.payments.exceptions import CheckoutTimeoutError
from ecommerce_store_payments.application.payments.payment_service import PaymentService
from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)
from tests.unit.application.test_checkout import CheckoutBoundary, setup_checkout


async def test_restart_recovers_provider_success_with_same_attempt_and_history(mongo_database: MongoDatabase) -> None:
    repository = MongoPaymentRepository(mongo_database)
    _, _, reader, provider = setup_checkout()
    provider.timeout_once = True
    service = PaymentService(repository, reader, provider)
    with pytest.raises(CheckoutTimeoutError):
        await service.checkout(reader.order.order_id)
    reserved = await repository.get_by_order_id(reader.order.order_id)
    assert reserved is not None and reserved.version == 1
    restarted = PaymentService(MongoPaymentRepository(mongo_database), reader, provider)
    result = await restarted.checkout(reader.order.order_id)
    stored = await repository.get_by_id(result.payment.id)
    history = await repository.get_history(result.payment.id)
    assert stored is not None and stored.status is PaymentStatus.PENDING and stored.version == 2
    assert stored.checkout_attempt_id == reserved.checkout_attempt_id == result.payment.checkout_attempt_id
    assert len(provider.sessions) == 1 and provider.requests[0] == provider.requests[1]
    assert len(history) == 2 and history[0].checkout_attempt_id is None
    assert history[1].checkout_attempt_id == stored.checkout_attempt_id
    assert await mongo_database.payments.count_documents({}) == 1


class ParallelCheckoutBoundary(CheckoutBoundary):
    def __init__(self) -> None:
        super().__init__()
        self.barrier = asyncio.Barrier(2)

    async def create(self, request: CheckoutRequest) -> CheckoutSession:
        session = await super().create(request)
        await self.barrier.wait()
        return session


async def test_parallel_checkout_creates_one_session_and_two_atomic_history_records(
    mongo_database: MongoDatabase,
) -> None:
    repository = MongoPaymentRepository(mongo_database)
    _, _, reader, _ = setup_checkout()
    provider = ParallelCheckoutBoundary()
    service = PaymentService(repository, reader, provider)
    first, second = await asyncio.wait_for(
        asyncio.gather(service.checkout(reader.order.order_id), service.checkout(reader.order.order_id)),
        timeout=20,
    )
    assert first.payment.id == second.payment.id
    assert first.payment.checkout_attempt_id == second.payment.checkout_attempt_id
    assert first.session.session_id == second.session.session_id
    assert first.payment.version == second.payment.version == 2
    assert len(provider.sessions) == 1
    assert len(await repository.get_history(first.payment.id)) == 2


class FailingSessionSaveRepository:
    def __init__(self, database: MongoDatabase) -> None:
        self.repository = MongoPaymentRepository(database)

    async def create(self, payment: Payment) -> Payment:
        return await self.repository.create(payment)

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        return await self.repository.get_by_id(payment_id)

    async def get_by_order_id(self, order_id: UUID) -> Payment | None:
        return await self.repository.get_by_order_id(order_id)

    async def get_history(self, payment_id: UUID) -> list[Payment]:
        return await self.repository.get_history(payment_id)

    async def update(self, payment: Payment) -> Payment:
        if payment.status is PaymentStatus.PENDING:
            raise RuntimeError("session persistence failed")
        return await self.repository.update(payment)


async def test_failed_session_save_leaves_recoverable_reservation(mongo_database: MongoDatabase) -> None:
    _, _, reader, provider = setup_checkout()
    with pytest.raises(RuntimeError):
        await PaymentService(FailingSessionSaveRepository(mongo_database), reader, provider).checkout(
            reader.order.order_id
        )
    repository = MongoPaymentRepository(mongo_database)
    reserved = await repository.get_by_order_id(reader.order.order_id)
    assert reserved is not None and reserved.status is PaymentStatus.CREATED and reserved.version == 1
    recovered = await PaymentService(repository, reader, provider).checkout(reader.order.order_id)
    assert recovered.payment.status is PaymentStatus.PENDING
    assert provider.requests[0].attempt_id == provider.requests[1].attempt_id
    assert len(provider.sessions) == 1 and len(await repository.get_history(reserved.id)) == 2
