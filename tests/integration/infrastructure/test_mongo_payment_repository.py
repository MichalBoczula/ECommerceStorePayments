import asyncio
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest
from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError

from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import (
    PaymentConflictError,
    PaymentDuplicateError,
    PaymentMissingError,
)
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)


def _mongo_datetime(value: datetime) -> datetime:
    return value.replace(microsecond=value.microsecond // 1000 * 1000)


async def test_create_reads_back_domain_and_bson_values(mongo_database: MongoDatabase) -> None:
    repository = MongoPaymentRepository(mongo_database)
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
    assert restored.version == document["version"] == 0
    assert await repository.get_history(payment.id) == []


async def test_update_round_trip_and_missing_payment(mongo_database: MongoDatabase) -> None:
    repository = MongoPaymentRepository(mongo_database)
    payment = Payment.create(uuid4(), Money(amount_minor=500, currency="EUR"))
    await repository.create(payment)

    payment.mark_as_pending("cs_test_123")
    pending_payment = await repository.update(payment)
    pending = await repository.get_by_order_id(payment.order_id)
    assert pending is not None
    assert pending.status is PaymentStatus.PENDING
    assert pending.provider_session_id == "cs_test_123"
    assert pending_payment.version == pending.version == 1
    assert payment.version == 0

    pending_payment.mark_as_succeeded("pi_test_456")
    succeeded_payment = await repository.update(pending_payment)
    restored = await repository.get_by_id(payment.id)
    document = await mongo_database.payments.find_one({"_id": payment.id})
    assert restored is not None
    assert document is not None
    assert restored.status is PaymentStatus.SUCCEEDED
    assert restored.provider_session_id == "cs_test_123"
    assert restored.provider_payment_id == "pi_test_456"
    assert restored.money == payment.money
    assert restored.version == succeeded_payment.version == document["version"] == 2
    assert restored.created_at == _mongo_datetime(payment.created_at)
    assert pending_payment.updated_at is not None
    assert restored.updated_at == document["updated_at"] == _mongo_datetime(pending_payment.updated_at)
    assert restored.updated_at is not None and restored.updated_at.utcoffset() == UTC.utcoffset(restored.updated_at)
    assert await mongo_database.payments.count_documents({}) == 1
    history = await repository.get_history(payment.id)
    assert [snapshot.version for snapshot in history] == [0, 1]
    assert [snapshot.status for snapshot in history] == [PaymentStatus.CREATED, PaymentStatus.PENDING]
    assert history[0].provider_session_id is None
    assert history[1].provider_session_id == "cs_test_123"
    assert [snapshot.order_id for snapshot in history] == [payment.order_id, payment.order_id]
    assert [snapshot.money for snapshot in history] == [payment.money, payment.money]
    documents = [item async for item in mongo_database.payment_history.find({"payment_id": payment.id})]
    assert {item["_id"] for item in documents} == {f"{payment.id}:0", f"{payment.id}:1"}
    assert all(item["recorded_at"].tzinfo is not None for item in documents)
    assert all(item["payment_id"] == payment.id for item in documents)
    assert await mongo_database.payment_history.count_documents({}) == 2


async def test_missing_reads_and_update(mongo_database: MongoDatabase) -> None:
    repository = MongoPaymentRepository(mongo_database)
    payment = Payment.create(uuid4(), Money(amount_minor=500, currency="PLN"))

    assert await repository.get_by_id(payment.id) is None
    assert await repository.get_by_order_id(payment.order_id) is None
    with pytest.raises(PaymentMissingError, match=str(payment.id)):
        await repository.update(payment)
    assert await mongo_database.payments.count_documents({}) == 0
    assert await mongo_database.payment_history.count_documents({}) == 0


async def test_unique_order_index_rejects_second_payment(mongo_database: MongoDatabase) -> None:
    repository = MongoPaymentRepository(mongo_database)
    indexes = await mongo_database.payments.index_information()
    assert indexes["ux_payments_order_id"]["key"] == [("order_id", 1)]
    assert indexes["ux_payments_order_id"]["unique"] is True
    history_indexes = await mongo_database.payment_history.index_information()
    assert set(history_indexes) == {"_id_", "ix_payment_history_payment_id"}
    assert history_indexes["ix_payment_history_payment_id"]["key"] == [("payment_id", 1)]
    order_id = uuid4()
    first = Payment.create(order_id, Money(amount_minor=500, currency="PLN"))
    second = Payment.create(order_id, Money(amount_minor=600, currency="PLN"))

    await repository.create(first)
    with pytest.raises(PaymentDuplicateError) as error:
        await repository.create(second)
    assert error.value.order_id == order_id

    stored = await repository.get_by_order_id(order_id)
    assert stored is not None and stored.id == first.id
    assert await mongo_database.payments.count_documents({}) == 1
    assert await mongo_database.payment_history.count_documents({}) == 0


async def test_competing_updates_leave_one_winner(mongo_database: MongoDatabase) -> None:
    repository = MongoPaymentRepository(mongo_database)
    initial = Payment.create(uuid4(), Money(amount_minor=500, currency="PLN"))
    await repository.create(initial)
    pending = await repository.get_by_id(initial.id)
    canceled = await repository.get_by_id(initial.id)
    assert pending is not None and canceled is not None
    pending.mark_as_pending("cs_test_123")
    canceled.cancel()

    results = await asyncio.gather(repository.update(pending), repository.update(canceled), return_exceptions=True)

    successes = [result for result in results if isinstance(result, Payment)]
    conflicts = [result for result in results if isinstance(result, PaymentConflictError)]
    assert len(successes) == len(conflicts) == 1
    assert conflicts[0].expected_version == 0
    assert pending.version == canceled.version == 0
    stored = await repository.get_by_id(initial.id)
    assert stored is not None
    assert stored.status is successes[0].status
    assert stored.version == successes[0].version == 1
    assert await mongo_database.payments.count_documents({}) == 1
    assert [snapshot.version for snapshot in await repository.get_history(initial.id)] == [0]


async def test_competing_creates_for_order_leave_one_payment(mongo_database: MongoDatabase) -> None:
    repository = MongoPaymentRepository(mongo_database)
    order_id = uuid4()
    first = Payment.create(order_id, Money(amount_minor=500, currency="PLN"))
    second = Payment.create(order_id, Money(amount_minor=600, currency="PLN"))

    results = await asyncio.gather(repository.create(first), repository.create(second), return_exceptions=True)

    winners = [result for result in results if isinstance(result, Payment)]
    duplicates = [result for result in results if isinstance(result, PaymentDuplicateError)]
    assert len(winners) == len(duplicates) == 1
    assert await mongo_database.payments.count_documents({}) == 1
    stored = await repository.get_by_order_id(order_id)
    assert stored is not None
    assert stored.id == winners[0].id
    assert stored.version == 0


async def test_first_update_of_versionless_document_migrates_it_atomically(mongo_database: MongoDatabase) -> None:
    repository = MongoPaymentRepository(mongo_database)
    payment = Payment.create(uuid4(), Money(amount_minor=500, currency="PLN"))
    legacy_document = cast(
        PaymentDocument, {key: value for key, value in PaymentMapper.to_document(payment).items() if key != "version"}
    )
    await mongo_database.payments.insert_one(legacy_document)
    first = await repository.get_by_id(payment.id)
    second = await repository.get_by_id(payment.id)
    assert first is not None and second is not None
    assert first.version == second.version == 0

    first.mark_as_pending("cs_test_123")
    migrated = await repository.update(first)
    second.cancel()
    with pytest.raises(PaymentConflictError):
        await repository.update(second)

    stored = await mongo_database.payments.find_one({"_id": payment.id})
    assert stored is not None
    assert stored["version"] == migrated.version == 1
    assert stored["status"] == PaymentStatus.PENDING.value
    assert [snapshot.version for snapshot in await repository.get_history(payment.id)] == [0]
    archived = await mongo_database.payment_history.find_one({"payment_id": payment.id})
    assert archived is not None and archived["status"] == PaymentStatus.CREATED.value


async def test_update_cannot_reassign_payment_to_another_order(mongo_database: MongoDatabase) -> None:
    repository = MongoPaymentRepository(mongo_database)
    original = Payment.create(uuid4(), Money(amount_minor=500, currency="PLN"))
    await repository.create(original)
    reassigned = Payment.rehydrate(
        payment_id=original.id,
        order_id=uuid4(),
        money=original.money,
        status=original.status,
        provider_session_id=None,
        provider_payment_id=None,
        failure_code=None,
        created_at=original.created_at,
        updated_at=None,
        version=0,
    )
    reassigned.cancel()

    with pytest.raises(PaymentConflictError):
        await repository.update(reassigned)

    stored = await repository.get_by_id(original.id)
    assert stored is not None
    assert stored.order_id == original.order_id
    assert stored.status is PaymentStatus.CREATED
    assert stored.version == 0
    assert await repository.get_history(original.id) == []


async def test_failed_archive_rolls_back_current_update(mongo_database: MongoDatabase) -> None:
    repository = MongoPaymentRepository(mongo_database)
    payment = Payment.create(uuid4(), Money(amount_minor=500, currency="PLN"))
    await repository.create(payment)
    payment.mark_as_pending("cs_test_123")
    await mongo_database.payment_history.insert_one(
        {
            "_id": f"{payment.id}:0",
            "payment_id": payment.id,
            "order_id": payment.order_id,
            "amount_minor": 500,
            "currency": "PLN",
            "status": PaymentStatus.CREATED.value,
            "provider_session_id": None,
            "provider_payment_id": None,
            "failure_code": None,
            "created_at": payment.created_at,
            "updated_at": None,
            "version": 0,
            "recorded_at": datetime.now(UTC),
        }
    )

    with pytest.raises(DuplicateKeyError):
        await repository.update(payment)

    stored = await repository.get_by_id(payment.id)
    assert stored is not None and stored.status is PaymentStatus.CREATED and stored.version == 0
    assert await mongo_database.payment_history.count_documents({"payment_id": payment.id}) == 1


async def test_database_names_isolate_documents(mongo_database: MongoDatabase, mongo_url: str) -> None:
    repository = MongoPaymentRepository(mongo_database)
    payment = Payment.create(uuid4(), Money(amount_minor=500, currency="PLN"))
    await repository.create(payment)

    other_name = f"payments_isolation_{uuid4().hex}"
    other_database = MongoDatabase(
        Settings(
            environment="test",
            mongodb_connection_string=mongo_url,
            mongodb_database_name=other_name,
        )
    )
    cleanup_client: AsyncMongoClient[PaymentDocument] = AsyncMongoClient(mongo_url)
    try:
        other_repository = MongoPaymentRepository(other_database)
        other_payment = Payment.create(uuid4(), Money(amount_minor=600, currency="EUR"))
        await other_repository.create(other_payment)
        assert await other_repository.get_by_id(payment.id) is None
        assert await other_repository.get_by_order_id(payment.order_id) is None
        assert await repository.get_by_id(other_payment.id) is None
        assert await repository.get_by_order_id(other_payment.order_id) is None
        assert await repository.get_by_id(payment.id) is not None
        assert await other_repository.get_by_id(other_payment.id) is not None
    finally:
        try:
            await cleanup_client.drop_database(other_name)
        finally:
            await other_database.close()
            await cleanup_client.close()
