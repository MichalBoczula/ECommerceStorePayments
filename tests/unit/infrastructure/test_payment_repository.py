from collections.abc import Mapping
from typing import cast
from uuid import UUID, uuid4

import pytest
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError

from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import (
    PaymentConflictError,
    PaymentDuplicateError,
    PaymentMissingError,
)
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)


class _UpdateResult:
    def __init__(self, matched_count: int) -> None:
        self.matched_count = matched_count


class _PaymentCollection:
    def __init__(self) -> None:
        self.documents: dict[UUID, PaymentDocument] = {}

    async def insert_one(self, document: PaymentDocument) -> None:
        if any(existing["order_id"] == document["order_id"] for existing in self.documents.values()):
            raise DuplicateKeyError("duplicate order_id")
        self.documents[document["_id"]] = document

    async def replace_one(
        self,
        query: Mapping[str, object],
        document: PaymentDocument,
    ) -> _UpdateResult:
        payment_id = cast(UUID, query["_id"])
        if payment_id not in self.documents:
            return _UpdateResult(matched_count=0)

        stored_version = self.documents[payment_id].get("version", 0)
        expected_version = query.get("version", 0)
        if stored_version != expected_version:
            return _UpdateResult(matched_count=0)

        self.documents[payment_id] = document
        return _UpdateResult(matched_count=1)

    async def find_one(self, query: Mapping[str, object]) -> PaymentDocument | None:
        for document in self.documents.values():
            if all(document.get(key) == value for key, value in query.items()):
                return document
        return None


def _create_repository(collection: _PaymentCollection) -> MongoPaymentRepository:
    mongo_collection = cast(AsyncCollection[PaymentDocument], collection)
    return MongoPaymentRepository(mongo_collection)


@pytest.mark.asyncio
async def test_create_and_get_by_id_round_trip() -> None:
    collection = _PaymentCollection()
    repository = _create_repository(collection)
    payment = Payment.create(uuid4(), Money(amount_minor=12999, currency="PLN"))

    await repository.create(payment)
    restored_payment = await repository.get_by_id(payment.id)

    assert restored_payment is not None
    assert PaymentMapper.to_document(restored_payment) == PaymentMapper.to_document(payment)


@pytest.mark.asyncio
async def test_get_by_order_id_returns_payment() -> None:
    collection = _PaymentCollection()
    repository = _create_repository(collection)
    order_id = uuid4()
    payment = Payment.create(order_id, Money(amount_minor=12999, currency="PLN"))
    await repository.create(payment)

    restored_payment = await repository.get_by_order_id(order_id)

    assert restored_payment is not None
    assert restored_payment.id == payment.id


@pytest.mark.asyncio
async def test_update_replaces_existing_document() -> None:
    collection = _PaymentCollection()
    repository = _create_repository(collection)
    payment = Payment.create(uuid4(), Money(amount_minor=12999, currency="PLN"))
    await repository.create(payment)
    payment.mark_as_pending("cs_test_123")

    saved_payment = await repository.update(payment)
    restored_payment = await repository.get_by_id(payment.id)

    assert restored_payment is not None
    assert restored_payment.provider_session_id == "cs_test_123"
    assert saved_payment.version == restored_payment.version == 1
    assert payment.version == 0


@pytest.mark.asyncio
async def test_update_raises_when_payment_does_not_exist() -> None:
    repository = _create_repository(_PaymentCollection())
    payment = Payment.create(uuid4(), Money(amount_minor=12999, currency="PLN"))

    with pytest.raises(PaymentMissingError, match=str(payment.id)):
        await repository.update(payment)


@pytest.mark.asyncio
async def test_update_rejects_stale_payment() -> None:
    repository = _create_repository(_PaymentCollection())
    payment = Payment.create(uuid4(), Money(amount_minor=100, currency="PLN"))
    await repository.create(payment)
    stale = await repository.get_by_id(payment.id)
    assert stale is not None
    payment.mark_as_pending("cs_test_123")
    saved = await repository.update(payment)
    stale.cancel()

    with pytest.raises(PaymentConflictError) as error:
        await repository.update(stale)
    assert error.value.expected_version == 0
    assert saved.version == 1
    assert stale.version == 0


@pytest.mark.asyncio
async def test_create_maps_duplicate_order_to_typed_error() -> None:
    repository = _create_repository(_PaymentCollection())
    order_id = uuid4()
    await repository.create(Payment.create(order_id, Money(amount_minor=100, currency="PLN")))

    with pytest.raises(PaymentDuplicateError) as error:
        await repository.create(Payment.create(order_id, Money(amount_minor=200, currency="PLN")))
    assert error.value.order_id == order_id
