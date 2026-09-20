from typing import final
from uuid import UUID

from pymongo.asynchronous.collection import AsyncCollection

from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper


@final
class MongoPaymentRepository:
    def __init__(self, collection: AsyncCollection[PaymentDocument]) -> None:
        self._collection = collection

    async def create(self, payment: Payment) -> Payment:
        await self._collection.insert_one(PaymentMapper.to_document(payment))
        return payment

    async def update(self, payment: Payment) -> Payment:
        result = await self._collection.replace_one(
            {"_id": payment.id},
            PaymentMapper.to_document(payment),
        )
        if result.matched_count == 0:
            raise LookupError(f"Payment {payment.id} does not exist.")

        return payment

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        document = await self._collection.find_one({"_id": payment_id})
        return None if document is None else PaymentMapper.to_domain(document)

    async def get_by_order_id(self, order_id: UUID) -> Payment | None:
        document = await self._collection.find_one({"order_id": order_id})
        return None if document is None else PaymentMapper.to_domain(document)
