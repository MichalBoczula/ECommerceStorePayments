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
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.webhook_document import WebhookDocument


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
        self._webhook_collection_name = settings.mongodb_webhook_collection_name
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

    @property
    def webhooks(self) -> AsyncCollection[WebhookDocument]:
        return cast(AsyncCollection[WebhookDocument], self._database[self._webhook_collection_name])

    async def probe(self) -> None:
        await asyncio.wait_for(self._client.admin.command("ping"), timeout=self._probe_timeout_seconds)

    async def ensure_indexes(self) -> None:
        await self.payments.create_index("order_id", unique=True, name="ux_payments_order_id")
        await self.payment_history.create_index("payment_id", name="ix_payment_history_payment_id")
        # Event identity is unique through MongoDB's implicit _id index.
        await self.webhooks.create_index([("state", 1), ("received_at", 1)], name="ix_webhooks_pending")
        await self.webhooks.create_index(
            [("fulfillment_status", 1), ("received_at", 1)], name="ix_webhooks_fulfillment"
        )

        await self.webhooks.create_index(
            [("fulfillment_status", 1), ("fulfillment_next_attempt", 1)], name="ix_webhooks_fulfillment_due"
        )
        await self.webhooks.create_index(
            [("fulfillment_status", 1), ("fulfillment_lease_until", 1)], name="ix_webhooks_fulfillment_lease"
        )

    async def close(self) -> None:
        await self._client.close()
