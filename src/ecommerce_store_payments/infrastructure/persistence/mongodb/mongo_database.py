from typing import final

from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument


@final
class MongoDatabase:
    def __init__(self, settings: Settings) -> None:
        self._client: AsyncMongoClient[PaymentDocument] = AsyncMongoClient(
            settings.mongodb_connection_string,
            uuidRepresentation="standard",
            tz_aware=True,
        )
        self._database: AsyncDatabase[PaymentDocument] = self._client[settings.mongodb_database_name]
        self._payments_collection_name = settings.mongodb_payments_collection_name

    @property
    def payments(self) -> AsyncCollection[PaymentDocument]:
        return self._database[self._payments_collection_name]

    async def ensure_indexes(self) -> None:
        await self.payments.create_index("order_id", unique=True, name="ux_payments_order_id")

    async def close(self) -> None:
        await self._client.close()
