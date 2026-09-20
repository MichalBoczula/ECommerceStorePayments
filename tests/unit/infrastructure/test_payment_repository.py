from collections.abc import Mapping
from typing import cast
from uuid import UUID, uuid4

import pytest
from pymongo.asynchronous.collection import AsyncCollection

from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
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
        self.documents[document["_id"]] = document

    async def replace_one(
        self,
        query: Mapping[str, object],
        document: PaymentDocument,
    ) -> _UpdateResult:
        payment_id = cast(UUID, query["_id"])
        if payment_id not in self.documents:
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

    await repository.update(payment)
    restored_payment = await repository.get_by_id(payment.id)

    assert restored_payment is not None
    assert restored_payment.provider_session_id == "cs_test_123"


@pytest.mark.asyncio
async def test_update_raises_when_payment_does_not_exist() -> None:
    repository = _create_repository(_PaymentCollection())
    payment = Payment.create(uuid4(), Money(amount_minor=12999, currency="PLN"))

    with pytest.raises(LookupError, match=str(payment.id)):
        await repository.update(payment)
