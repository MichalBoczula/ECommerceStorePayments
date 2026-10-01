from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from pymongo import ReturnDocument
from pymongo.write_concern import WriteConcern

from ecommerce_store_payments.application.payments.fulfillment import (
    CompletedInvoice,
    FulfillmentLeaseLostError,
    FulfillmentStatus,
    FulfillmentWork,
)
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.webhook_document import WebhookDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase


class MongoFulfillmentRepository:
    LEASE_SECONDS = 300

    def __init__(self, database: MongoDatabase) -> None:
        self._collection = database.webhooks.with_options(write_concern=WriteConcern("majority"))

    async def claim(self, now: datetime) -> FulfillmentWork | None:
        document = await self._collection.find_one_and_update(
            {
                "state": "applied",
                "outcome": "succeeded",
                "$or": [
                    {
                        "fulfillment_status": {"$in": ["pending", "retry"]},
                        "$or": [{"fulfillment_next_attempt": None}, {"fulfillment_next_attempt": {"$lte": now}}],
                    },
                    {"fulfillment_status": "processing", "fulfillment_lease_until": {"$lte": now}},
                ],
            },
            {
                "$set": {
                    "fulfillment_status": "processing",
                    "fulfillment_lease_id": uuid4(),
                    "fulfillment_lease_until": now + timedelta(seconds=self.LEASE_SECONDS),
                },
                "$inc": {"fulfillment_attempts": 1},
            },
            sort=[("received_at", 1)],
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return None
        return self.to_work(document)

    @staticmethod
    def to_work(document: WebhookDocument) -> FulfillmentWork:
        payment_id, order_id, attempt_id = document["payment_id"], document["order_id"], document["attempt_id"]
        amount, currency = document["amount_minor"], document["currency"]
        lease_id = document.get("fulfillment_lease_id")
        assert payment_id is not None and order_id is not None and attempt_id is not None
        assert amount is not None and currency is not None and lease_id is not None
        return FulfillmentWork(
            document["_id"],
            payment_id,
            order_id,
            attempt_id,
            Money(amount, currency),
            lease_id,
            document.get("fulfillment_attempts", 0),
            document.get("fulfillment_client_id"),
            document.get("fulfillment_order_paid", False),
        )

    async def _save(self, work: FulfillmentWork, now: datetime, changes: dict[str, Any]) -> None:
        result = await self._collection.update_one(
            {
                "_id": work.event_id,
                "fulfillment_status": "processing",
                "fulfillment_lease_id": work.lease_id,
                "fulfillment_lease_until": {"$gt": now},
            },
            {"$set": changes},
        )
        if result.matched_count != 1:
            raise FulfillmentLeaseLostError()

    async def save_order_paid(self, work: FulfillmentWork, client_id: UUID, now: datetime) -> None:
        await self._save(work, now, {"fulfillment_order_paid": True, "fulfillment_client_id": client_id})

    async def complete(self, work: FulfillmentWork, invoice: CompletedInvoice, now: datetime) -> None:
        await self._save(
            work,
            now,
            {
                "fulfillment_status": "completed",
                "fulfillment_invoice_id": invoice.invoice_id,
                "fulfillment_client_data_version_id": invoice.client_data_version_id,
                "fulfillment_completed_at": now,
                "fulfillment_error": None,
                "fulfillment_next_attempt": None,
                "fulfillment_lease_id": None,
                "fulfillment_lease_until": None,
            },
        )

    async def fail(self, work: FulfillmentWork, code: str, next_attempt: datetime | None, now: datetime) -> None:
        await self._save(
            work,
            now,
            {
                "fulfillment_status": "retry" if next_attempt else "failed",
                "fulfillment_error": code,
                "fulfillment_next_attempt": next_attempt,
                "fulfillment_lease_id": None,
                "fulfillment_lease_until": None,
            },
        )

    async def resume(self, event_id: str, now: datetime) -> bool:
        """Explicitly resume exhausted/blocked work; never steal an active lease or reopen completion."""
        result = await self._collection.update_one(
            {"_id": event_id, "state": "applied", "outcome": "succeeded", "fulfillment_status": "failed"},
            {
                "$set": {
                    "fulfillment_status": FulfillmentStatus.PENDING.value,
                    "fulfillment_attempts": 0,
                    "fulfillment_next_attempt": now,
                    "fulfillment_error": None,
                }
            },
        )
        return result.matched_count == 1
