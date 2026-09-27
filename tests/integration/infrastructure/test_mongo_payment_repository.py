from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pymongo.errors import DuplicateKeyError

from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)


def _mongo_datetime(value: datetime) -> datetime:
    return value.replace(microsecond=value.microsecond // 1000 * 1000)


async def test_create_reads_back_domain_and_bson_values(mongo_database: MongoDatabase) -> None:
    repository = MongoPaymentRepository(mongo_database.payments)
    payment = Payment.create(uuid4(), Money(amount_minor=12999, currency="PLN"))

    await repository.create(payment)

    restored = await repository.get_by_id(payment.id)
    by_order = await repository.get_by_order_id(payment.order_id)
    document = await mongo_database.payments.find_one({"_id": payment.id})
    assert restored is not None
    assert by_order is not None
    assert document is not None
    assert restored.id == by_order.id == document["_id"] == payment.id
    assert restored.order_id == document["order_id"] == payment.order_id
    assert restored.money == payment.money
    assert restored.status is PaymentStatus.CREATED
    assert restored.provider_session_id is None
    assert restored.provider_payment_id is None
    assert restored.failure_code is None
    assert restored.created_at == document["created_at"] == _mongo_datetime(payment.created_at)
    assert restored.created_at.utcoffset() == UTC.utcoffset(restored.created_at)
    assert restored.updated_at is None


async def test_update_round_trip_and_missing_payment(mongo_database: MongoDatabase) -> None:
    repository = MongoPaymentRepository(mongo_database.payments)
    payment = Payment.create(uuid4(), Money(amount_minor=500, currency="EUR"))
    await repository.create(payment)

    payment.mark_as_pending("cs_test_123")
    await repository.update(payment)
    pending = await repository.get_by_order_id(payment.order_id)
    assert pending is not None
    assert pending.status is PaymentStatus.PENDING
    assert pending.provider_session_id == "cs_test_123"

    payment.mark_as_succeeded("pi_test_456")
    await repository.update(payment)
    restored = await repository.get_by_id(payment.id)
    document = await mongo_database.payments.find_one({"_id": payment.id})
    assert restored is not None
    assert document is not None
    assert restored.status is PaymentStatus.SUCCEEDED
    assert restored.provider_session_id == "cs_test_123"
    assert restored.provider_payment_id == "pi_test_456"
    assert restored.money == payment.money
    assert restored.created_at == _mongo_datetime(payment.created_at)
    assert payment.updated_at is not None
    assert restored.updated_at == document["updated_at"] == _mongo_datetime(payment.updated_at)
    assert restored.updated_at is not None and restored.updated_at.utcoffset() == UTC.utcoffset(restored.updated_at)
    assert await mongo_database.payments.count_documents({}) == 1


async def test_missing_reads_and_update(mongo_database: MongoDatabase) -> None:
    repository = MongoPaymentRepository(mongo_database.payments)
    payment = Payment.create(uuid4(), Money(amount_minor=500, currency="PLN"))

    assert await repository.get_by_id(payment.id) is None
    assert await repository.get_by_order_id(payment.order_id) is None
    with pytest.raises(LookupError, match=str(payment.id)):
        await repository.update(payment)
    assert await mongo_database.payments.count_documents({}) == 0


async def test_unique_order_index_rejects_second_payment(mongo_database: MongoDatabase) -> None:
    repository = MongoPaymentRepository(mongo_database.payments)
    indexes = await mongo_database.payments.index_information()
    assert indexes["ux_payments_order_id"]["key"] == [("order_id", 1)]
    assert indexes["ux_payments_order_id"]["unique"] is True
    order_id = uuid4()
    first = Payment.create(order_id, Money(amount_minor=500, currency="PLN"))
    second = Payment.create(order_id, Money(amount_minor=600, currency="PLN"))

    await repository.create(first)
    with pytest.raises(DuplicateKeyError):
        await repository.create(second)

    stored = await repository.get_by_order_id(order_id)
    assert stored is not None and stored.id == first.id
    assert await mongo_database.payments.count_documents({}) == 1


async def test_database_names_isolate_documents(mongo_database: MongoDatabase, mongo_url: str) -> None:
    repository = MongoPaymentRepository(mongo_database.payments)
    payment = Payment.create(uuid4(), Money(amount_minor=500, currency="PLN"))
    await repository.create(payment)

    other_database = MongoDatabase(
        Settings(
            environment="test",
            mongodb_connection_string=mongo_url,
            mongodb_database_name=f"payments_isolation_{uuid4().hex}",
        )
    )
    try:
        other_repository = MongoPaymentRepository(other_database.payments)
        assert await other_repository.get_by_id(payment.id) is None
        assert await other_repository.get_by_order_id(payment.order_id) is None
        assert await repository.get_by_id(payment.id) is not None
    finally:
        await other_database.close()
