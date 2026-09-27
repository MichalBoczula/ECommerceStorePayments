from typing import final
from uuid import UUID

from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import DuplicateKeyError

from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import (
    PaymentConflictError,
    PaymentDuplicateError,
    PaymentMissingError,
)
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper


@final
class MongoPaymentRepository:
    def __init__(self, collection: AsyncCollection[PaymentDocument]) -> None:
        self._collection = collection

    async def create(self, payment: Payment) -> Payment:
        try:
            await self._collection.insert_one(PaymentMapper.to_document(payment))
        except DuplicateKeyError as error:
            raise PaymentDuplicateError(payment.id, payment.order_id) from error
        return payment

    async def update(self, payment: Payment) -> Payment:
        document = PaymentMapper.to_document(payment)
        document["version"] = payment.version + 1
        version_filter: dict[str, object] = (
            {"$or": [{"version": 0}, {"version": {"$exists": False}}]}
            if payment.version == 0
            else {"version": payment.version}
        )
        result = await self._collection.replace_one(
            {"_id": payment.id, "order_id": payment.order_id, **version_filter},
            document,
        )
        if result.matched_count == 0:
            if await self._collection.find_one({"_id": payment.id}) is None:
                raise PaymentMissingError(payment.id)
            raise PaymentConflictError(payment.id, payment.version)

        return PaymentMapper.to_domain(document)

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        document = await self._collection.find_one({"_id": payment_id})
        return None if document is None else PaymentMapper.to_domain(document)

    async def get_by_order_id(self, order_id: UUID) -> Payment | None:
        document = await self._collection.find_one({"order_id": order_id})
        return None if document is None else PaymentMapper.to_domain(document)
