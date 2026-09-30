"""Resume verified pending receipts after interrupted delivery, without calling an external provider."""

import argparse
import asyncio

from ecommerce_store_payments.application.payments.webhook import WebhookState
from ecommerce_store_payments.application.payments.webhook_service import WebhookService
from ecommerce_store_payments.infrastructure.clients.stripe.webhook_verifier import StripeWebhookVerifier
from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.webhook_mapper import WebhookMapper
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.webhook_repository import (
    MongoWebhookRepository,
)


async def replay(settings: Settings, limit: int) -> int:
    database = MongoDatabase(settings)
    try:
        await database.probe()
        service = WebhookService(
            StripeWebhookVerifier(settings), MongoWebhookRepository(database), MongoPaymentRepository(database)
        )
        documents = [
            document
            async for document in database.webhooks.find({"state": WebhookState.PENDING.value})
            .sort("received_at", 1)
            .limit(limit)
        ]
        for document in documents:
            await service.process_received(WebhookMapper.to_receipt(document))
        return len(documents)
    finally:
        await database.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error("--limit must be between 1 and 1000")
    print(f"Processed {asyncio.run(replay(Settings(), args.limit))} pending webhook receipts.")


if __name__ == "__main__":
    main()
