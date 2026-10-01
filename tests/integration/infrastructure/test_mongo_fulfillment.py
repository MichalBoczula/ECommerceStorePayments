import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from ecommerce_store_payments.application.payments.fulfillment import CompletedInvoice, FulfillmentLeaseLostError
from ecommerce_store_payments.application.payments.fulfillment_service import FulfillmentService
from ecommerce_store_payments.application.payments.webhook_service import WebhookService
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
from tests.integration.infrastructure.test_mongo_webhooks import checkout
from tests.unit.application.test_fulfillment_service import InvoicesStub, OrdersStub
from tests.unit.application.test_webhook_service import VerifierStub
from tests.webhook_fixtures import notification


async def seed(database: MongoDatabase) -> str:
    payment = await checkout(database)
    event = notification(payment)
    await WebhookService(
        VerifierStub(event), MongoWebhookRepository(database), MongoPaymentRepository(database)
    ).receive(b"body", "header")
    return event.event_id


async def test_atomic_claim_concurrent_workers_and_fenced_expired_lease(mongo_database: MongoDatabase) -> None:
    event_id = await seed(mongo_database)
    repository = MongoFulfillmentRepository(mongo_database)
    now = datetime.now(UTC)
    claims = await asyncio.gather(*(repository.claim(now) for _ in range(8)))
    active = [work for work in claims if work is not None]
    assert len(active) == 1
    first = active[0]
    assert first.attempts == 1
    later = now + timedelta(seconds=301)
    second = await repository.claim(later)
    assert second is not None and second.lease_id != first.lease_id and second.attempts == 2
    with pytest.raises(FulfillmentLeaseLostError):
        await repository.save_order_paid(first, uuid4(), later)
    with pytest.raises(FulfillmentLeaseLostError):
        await repository.fail(first, "stale", None, later)
    with pytest.raises(FulfillmentLeaseLostError):
        await repository.complete(first, CompletedInvoice(uuid4(), first.order_id, uuid4()), later)
    await repository.save_order_paid(second, uuid4(), later)
    invoice = CompletedInvoice(uuid4(), second.order_id, uuid4())
    await repository.complete(second, invoice, later)
    assert await repository.claim(later) is None
    document = await mongo_database.webhooks.find_one({"_id": event_id})
    assert document is not None and document.get("fulfillment_invoice_id") == invoice.invoice_id
    assert document["fulfillment_status"] == "completed" and document.get("fulfillment_error") is None
    assert not await repository.resume(event_id, later)


async def test_retry_due_progress_and_manual_resume_survive_new_repository(mongo_database: MongoDatabase) -> None:
    event_id = await seed(mongo_database)
    now = datetime.now(UTC)
    repository = MongoFulfillmentRepository(mongo_database)
    first = await repository.claim(now)
    assert first is not None
    client_id = uuid4()
    await repository.save_order_paid(first, client_id, now)
    await repository.fail(first, "invoice_unavailable", now + timedelta(seconds=60), now)
    restarted = MongoFulfillmentRepository(mongo_database)
    assert await restarted.claim(now) is None
    second = await restarted.claim(now + timedelta(seconds=60))
    assert second is not None and second.client_id == client_id and second.order_paid and second.attempts == 2
    await restarted.fail(second, "repair_needed", None, now + timedelta(seconds=60))
    assert await restarted.claim(now + timedelta(days=1)) is None
    assert await restarted.resume(event_id, now + timedelta(seconds=61))
    third = await restarted.claim(now + timedelta(seconds=61))
    assert third is not None and third.attempts == 1 and third.order_paid
    assert not await restarted.resume(event_id, now + timedelta(seconds=61))


async def test_crash_after_invoice_commit_recovers_with_one_logical_invoice(mongo_database: MongoDatabase) -> None:
    await seed(mongo_database)
    repository = MongoFulfillmentRepository(mongo_database)
    now = datetime.now(UTC)
    abandoned = await repository.claim(now)
    assert abandoned is not None
    payment = await MongoPaymentRepository(mongo_database).get_by_id(abandoned.payment_id)
    assert payment is not None
    orders, invoices = OrdersStub(payment), InvoicesStub(payment.order_id)
    orders.order = replace(orders.order, status="Paid")
    await repository.save_order_paid(abandoned, orders.order.client_id, now)
    # Downstream completed, process died before local completion acknowledgement.
    await invoices.create(orders.order.client_id, payment.order_id)
    service = FulfillmentService(
        MongoFulfillmentRepository(mongo_database),
        MongoPaymentRepository(mongo_database),
        orders,
        invoices,
        lambda: now + timedelta(seconds=301),
    )
    assert await service.run_batch(10) == 1
    assert orders.writes == 0 and invoices.creates == 1
    assert await service.run_batch(10) == 0


async def test_many_workers_and_webhook_replay_produce_one_completed_work(mongo_database: MongoDatabase) -> None:
    payment = await checkout(mongo_database)
    event = notification(payment)
    webhook = WebhookService(
        VerifierStub(event), MongoWebhookRepository(mongo_database), MongoPaymentRepository(mongo_database)
    )
    await webhook.receive(b"body", "header")
    orders, invoices = OrdersStub(payment), InvoicesStub(payment.order_id)
    await asyncio.gather(
        *(
            FulfillmentService(
                MongoFulfillmentRepository(mongo_database), MongoPaymentRepository(mongo_database), orders, invoices
            ).run_batch(10)
            for _ in range(8)
        )
    )
    await webhook.receive(b"body", "header")
    assert orders.writes == invoices.creates == 1
    assert await mongo_database.webhooks.count_documents({"fulfillment_status": "completed"}) == 1
    assert await mongo_database.webhooks.count_documents({"fulfillment_status": "pending"}) == 0
