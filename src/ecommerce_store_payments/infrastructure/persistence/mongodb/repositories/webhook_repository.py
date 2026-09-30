from datetime import UTC, datetime
from typing import final

from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.errors import DuplicateKeyError, PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

from ecommerce_store_payments.application.payments.webhook import (
    CheckoutOutcome,
    VerifiedWebhook,
    WebhookCollisionError,
    WebhookReceipt,
    WebhookRetryError,
    WebhookState,
)
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import PaymentConflictError
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.webhook_mapper import WebhookMapper
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)


@final
class MongoWebhookRepository:
    def __init__(self, database: MongoDatabase) -> None:
        self._database = database

    async def receive(self, event: VerifiedWebhook) -> WebhookReceipt:
        """Persist normalized work with majority acknowledgement; duplicate pending work remains processable."""
        collection = self._database.webhooks.with_options(write_concern=WriteConcern("majority"))
        try:
            await collection.insert_one(WebhookMapper.to_document(event))
            return WebhookReceipt(event)
        except DuplicateKeyError:
            document = await collection.find_one({"_id": event.event_id})
            if document is None:
                raise WebhookRetryError() from None
            if document["payload_digest"] != event.payload_digest:
                raise WebhookCollisionError() from None
            return WebhookMapper.to_receipt(document)
        except PyMongoError as error:
            raise WebhookRetryError() from error

    async def complete(
        self, receipt: WebhookReceipt, payment: Payment | None, state: WebhookState, reason: str, *, changed: bool
    ) -> WebhookReceipt:
        """Commit the payment/history and receipt/work marker together, or leave the receipt pending."""

        async def commit(session: AsyncClientSession) -> WebhookReceipt:
            document = await self._database.webhooks.find_one({"_id": receipt.event.event_id}, session=session)
            if document is None:
                raise WebhookRetryError()
            current = WebhookMapper.to_receipt(document)
            if current.state is not WebhookState.PENDING:
                return current
            if payment is not None:
                stored = await self._database.payments.find_one({"_id": payment.id}, session=session)
                if stored is None or stored.get("version", 0) != payment.version:
                    raise PaymentConflictError(payment.id, payment.version)
                if changed:
                    await MongoPaymentRepository(self._database).update_in_session(payment, session)
            document["state"] = state.value
            document["reason"] = reason
            document["completed_at"] = datetime.now(UTC)
            if changed and receipt.event.outcome is CheckoutOutcome.SUCCEEDED:
                # Durable handoff for STRIPE/3; no downstream requests happen in this transaction.
                document["fulfillment_status"] = "pending"
            await self._database.webhooks.replace_one({"_id": document["_id"]}, document, session=session)
            return WebhookMapper.to_receipt(document)

        try:
            async with self._database.client.start_session() as session:
                return await session.with_transaction(
                    commit,
                    read_concern=ReadConcern("snapshot"),
                    write_concern=WriteConcern("majority"),
                    max_commit_time_ms=5000,
                )
        except PyMongoError as error:
            raise WebhookRetryError() from error
