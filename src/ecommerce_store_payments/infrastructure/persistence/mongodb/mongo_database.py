import asyncio
from typing import cast, final

from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_history_document import (
    PaymentHistoryDocument,
)


@final
class MongoDatabase:
    def __init__(self, settings: Settings) -> None:
        self._client: AsyncMongoClient[PaymentDocument] = AsyncMongoClient(
            settings.mongodb_connection_string,
            uuidRepresentation="standard",
            tz_aware=True,
            serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
        )
        self._database: AsyncDatabase[PaymentDocument] = self._client[settings.mongodb_database_name]
        self._payments_collection_name = settings.mongodb_payments_collection_name
        self._history_collection_name = settings.mongodb_payment_history_collection_name
        self._probe_timeout_seconds = settings.mongodb_probe_timeout_seconds

    @property
    def payments(self) -> AsyncCollection[PaymentDocument]:
        return self._database[self._payments_collection_name]

    @property
    def payment_history(self) -> AsyncCollection[PaymentHistoryDocument]:
        return cast(AsyncCollection[PaymentHistoryDocument], self._database[self._history_collection_name])

    @property
    def client(self) -> AsyncMongoClient[PaymentDocument]:
        return self._client

    async def probe(self) -> None:
        await asyncio.wait_for(self._client.admin.command("ping"), timeout=self._probe_timeout_seconds)

    async def ensure_indexes(self) -> None:
        await self.payments.create_index("order_id", unique=True, name="ux_payments_order_id")
        await self.payment_history.create_index("payment_id", name="ix_payment_history_payment_id")

    async def close(self) -> None:
        await self._client.close()
