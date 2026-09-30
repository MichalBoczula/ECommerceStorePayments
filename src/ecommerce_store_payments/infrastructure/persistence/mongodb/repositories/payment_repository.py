from typing import final
from uuid import UUID

from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.errors import DuplicateKeyError

from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import (
    PaymentConflictError,
    PaymentDuplicateError,
    PaymentMissingError,
)
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_history_mapper import (
    PaymentHistoryMapper,
)
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase


@final
class MongoPaymentRepository:
    def __init__(self, database: MongoDatabase) -> None:
        self._database = database

    async def create(self, payment: Payment) -> Payment:
        try:
            await self._database.payments.insert_one(PaymentMapper.to_document(payment))
        except DuplicateKeyError as error:
            raise PaymentDuplicateError(payment.id, payment.order_id) from error
        return payment

    async def update(self, payment: Payment) -> Payment:
        async def replace_and_archive(session: AsyncClientSession) -> Payment:
            return await self.update_in_session(payment, session)

        async with self._database.client.start_session() as session:
            return await session.with_transaction(replace_and_archive)

    async def update_in_session(self, payment: Payment, session: AsyncClientSession) -> Payment:
        """Compare and archive inside a caller-owned transaction, without nesting sessions."""
        document = PaymentMapper.to_document(payment)
        document["version"] = payment.version + 1
        version_filter: dict[str, object] = (
            {"$or": [{"version": 0}, {"version": {"$exists": False}}]}
            if payment.version == 0
            else {"version": payment.version}
        )
        query = {"_id": payment.id, "order_id": payment.order_id, **version_filter}

        previous = await self._database.payments.find_one(query, session=session)
        if previous is None:
            if await self._database.payments.find_one({"_id": payment.id}, session=session) is None:
                raise PaymentMissingError(payment.id)
            raise PaymentConflictError(payment.id, payment.version)

        result = await self._database.payments.replace_one(query, document, session=session)
        if result.matched_count == 0:
            raise PaymentConflictError(payment.id, payment.version)
        await self._database.payment_history.insert_one(PaymentHistoryMapper.from_payment(previous), session=session)
        return PaymentMapper.to_domain(document)

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        document = await self._database.payments.find_one({"_id": payment_id})
        return None if document is None else PaymentMapper.to_domain(document)

    async def get_by_order_id(self, order_id: UUID) -> Payment | None:
        document = await self._database.payments.find_one({"order_id": order_id})
        return None if document is None else PaymentMapper.to_domain(document)

    async def get_history(self, payment_id: UUID) -> list[Payment]:
        documents = [document async for document in self._database.payment_history.find({"payment_id": payment_id})]
        return [
            PaymentMapper.to_domain(PaymentHistoryMapper.to_payment(document))
            for document in sorted(documents, key=lambda item: item["version"])
        ]
