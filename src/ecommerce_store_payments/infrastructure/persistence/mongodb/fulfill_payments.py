"""Run a bounded recovery/fulfillment batch, or inspect/resume durable failed work."""

import argparse
import asyncio
import json
from datetime import UTC, datetime

from httpx import AsyncClient
from kiota_abstractions.authentication.anonymous_authentication_provider import AnonymousAuthenticationProvider

from ecommerce_store_payments.application.payments.fulfillment_service import FulfillmentService
from ecommerce_store_payments.application.payments.webhook_service import WebhookService
from ecommerce_store_payments.infrastructure.clients.orders.generated.orders_client import OrdersClient
from ecommerce_store_payments.infrastructure.clients.orders.http_fulfillment import (
    HttpFulfillmentInvoices,
    HttpFulfillmentOrders,
)
from ecommerce_store_payments.infrastructure.clients.orders.precise_json import PreciseOrderJsonFactory
from ecommerce_store_payments.infrastructure.clients.orders.request_adapter import OrdersRequestAdapter
from ecommerce_store_payments.infrastructure.clients.stripe.webhook_verifier import StripeWebhookVerifier
from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.webhook_mapper import WebhookMapper
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.fulfillment_repository import (
    MongoFulfillmentRepository,
)
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.webhook_repository import (
    MongoWebhookRepository,
)


async def run(settings: Settings, limit: int, *, inspect: bool = False, resume: str | None = None) -> int:
    if not 1 <= limit <= 1000:
        raise ValueError("Batch limit must be between 1 and 1000.")
    database = MongoDatabase(settings)
    try:
        await database.probe()
        await database.ensure_indexes()
        repository = MongoFulfillmentRepository(database)
        if resume is not None:
            if not await repository.resume(resume, datetime.now(UTC)):
                raise ValueError("Only failed fulfillment work can be resumed.")
            return 1
        if inspect:
            documents = [
                {
                    key: document.get(key)
                    for key in (
                        "_id",
                        "payment_id",
                        "order_id",
                        "fulfillment_status",
                        "fulfillment_attempts",
                        "fulfillment_next_attempt",
                        "fulfillment_lease_until",
                        "fulfillment_error",
                        "fulfillment_order_paid",
                        "fulfillment_invoice_id",
                    )
                }
                async for document in database.webhooks.find(
                    {"fulfillment_status": {"$in": ["pending", "processing", "retry", "failed"]}}
                )
                .sort("received_at", 1)
                .limit(limit)
            ]
            print(json.dumps(documents, default=str, indent=2))
            return len(documents)
        payments = MongoPaymentRepository(database)
        webhook_service = WebhookService(StripeWebhookVerifier(settings), MongoWebhookRepository(database), payments)
        pending = [
            document
            async for document in database.webhooks.find({"state": "pending"}).sort("received_at", 1).limit(limit)
        ]
        receipt_failures = 0
        for document in pending:
            try:
                await webhook_service.process_received(WebhookMapper.to_receipt(document))
            except Exception:
                receipt_failures += 1
        async with AsyncClient(
            base_url=settings.orders_api_base_url, timeout=settings.orders_api_timeout_seconds, trust_env=False
        ) as transport:
            client = OrdersClient(
                OrdersRequestAdapter(
                    AnonymousAuthenticationProvider(),
                    parse_node_factory=PreciseOrderJsonFactory(),
                    http_client=transport,
                    base_url=settings.orders_api_base_url,
                )
            )
            processed = await FulfillmentService(
                repository, payments, HttpFulfillmentOrders(client), HttpFulfillmentInvoices(client)
            ).run_batch(limit)
        if receipt_failures:
            raise RuntimeError(f"{receipt_failures} receipts remain pending; retry the job.")
        return processed
    finally:
        await database.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=100)
    commands = parser.add_mutually_exclusive_group()
    commands.add_argument("--inspect", action="store_true")
    commands.add_argument("--resume", metavar="EVENT_ID")
    args = parser.parse_args()
    if not 1 <= args.limit <= 1000:
        parser.error("--limit must be between 1 and 1000")
    count = asyncio.run(run(Settings(), args.limit, inspect=args.inspect, resume=args.resume))
    if not args.inspect:
        print(f"Processed {count} fulfillment records.")


if __name__ == "__main__":
    main()
