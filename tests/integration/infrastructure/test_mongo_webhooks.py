import asyncio
from dataclasses import replace
from uuid import uuid4

import pytest
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.errors import OperationFailure

from ecommerce_store_payments.application.payments.webhook import (
    CheckoutOutcome,
    WebhookCollisionError,
    WebhookRetryError,
    WebhookState,
)
from ecommerce_store_payments.application.payments.webhook_service import WebhookService
from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.replay_webhooks import replay
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.webhook_repository import (
    MongoWebhookRepository,
)
from tests.unit.application.test_webhook_service import VerifierStub
from tests.webhook_fixtures import notification


async def checkout(database: MongoDatabase, *, reserved_only: bool = False) -> Payment:
    repository = MongoPaymentRepository(database)
    payment = await repository.create(Payment.create(uuid4(), Money(1299, "PLN")))
    payment.begin_checkout()
    payment = await repository.update(payment)
    if not reserved_only:
        payment.mark_as_pending("cs_test_fixture")
        payment = await repository.update(payment)
    return payment


async def test_atomic_confirmation_receipt_history_and_durable_fulfillment_marker(
    mongo_database: MongoDatabase,
) -> None:
    payment = await checkout(mongo_database)
    event = notification(payment)
    repository = MongoPaymentRepository(mongo_database)
    webhooks = MongoWebhookRepository(mongo_database)
    service = WebhookService(VerifierStub(event), webhooks, repository)
    assert (await service.receive(b"body", "signature")).state is WebhookState.APPLIED
    assert (await service.receive(b"body", "signature")).state is WebhookState.APPLIED
    stored = await repository.get_by_id(payment.id)
    assert stored is not None and stored.status is PaymentStatus.SUCCEEDED and stored.version == 3
    assert [item.version for item in await repository.get_history(payment.id)] == [0, 1, 2]
    receipt = await mongo_database.webhooks.find_one({"_id": event.event_id})
    assert receipt is not None and receipt["state"] == "applied" and receipt["fulfillment_status"] == "pending"
    assert receipt["completed_at"] is not None
    assert "payload" not in receipt and "signature" not in receipt
    indexes = await mongo_database.webhooks.index_information()
    assert set(indexes) == {"_id_", "ix_webhooks_pending", "ix_webhooks_fulfillment"}


async def test_receipt_only_interruption_is_recovered_by_new_process_without_provider_credentials(
    mongo_database: MongoDatabase,
    mongo_url: str,
) -> None:
    payment = await checkout(mongo_database)
    await MongoWebhookRepository(mongo_database).receive(notification(payment))
    settings = Settings(
        environment="test",
        mongodb_connection_string=mongo_url,
        mongodb_database_name=mongo_database.payments.database.name,
    )
    assert settings.stripe_secret_key is None and settings.stripe_webhook_secret is None
    assert await replay(settings, 100) == 1
    assert await replay(settings, 100) == 0
    stored = await MongoPaymentRepository(mongo_database).get_by_id(payment.id)
    assert stored is not None and stored.status is PaymentStatus.SUCCEEDED


async def test_failure_after_payment_and_archive_rolls_back_and_redelivery_recovers(
    mongo_database: MongoDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payment = await checkout(mongo_database)
    repository = MongoPaymentRepository(mongo_database)
    webhooks = MongoWebhookRepository(mongo_database)
    event = notification(payment)
    service = WebhookService(VerifierStub(event), webhooks, repository)
    original = MongoPaymentRepository.update_in_session

    async def interrupted(self: MongoPaymentRepository, changed: Payment, session: AsyncClientSession) -> Payment:
        await original(self, changed, session)
        raise OperationFailure("fixture interruption before receipt completion")

    with monkeypatch.context() as patch:
        patch.setattr(MongoPaymentRepository, "update_in_session", interrupted)
        with pytest.raises(WebhookRetryError):
            await service.receive(b"body", "signature")
    stored = await repository.get_by_id(payment.id)
    assert stored is not None and stored.status is PaymentStatus.PENDING and stored.version == 2
    assert [item.version for item in await repository.get_history(payment.id)] == [0, 1]
    receipt = await webhooks.receive(event)
    assert receipt.state is WebhookState.PENDING
    assert (await service.receive(b"body", "signature")).state is WebhookState.APPLIED
    assert [item.version for item in await repository.get_history(payment.id)] == [0, 1, 2]


@pytest.mark.parametrize("same_event", [True, False])
async def test_concurrent_deliveries_confirm_logically_once(mongo_database: MongoDatabase, same_event: bool) -> None:
    payment = await checkout(mongo_database)
    repository = MongoPaymentRepository(mongo_database)
    webhooks = MongoWebhookRepository(mongo_database)
    events = [notification(payment, event_id="evt_fixture" if same_event else f"evt_{index}") for index in range(8)]
    results = await asyncio.gather(
        *[WebhookService(VerifierStub(event), webhooks, repository).receive(b"body", "signature") for event in events]
    )
    assert all(result.state is not WebhookState.PENDING for result in results)
    stored = await repository.get_by_id(payment.id)
    assert stored is not None and stored.status is PaymentStatus.SUCCEEDED and stored.version == 3
    assert await mongo_database.payment_history.count_documents({"payment_id": payment.id}) == 3
    assert await mongo_database.webhooks.count_documents({"fulfillment_status": "pending"}) == 1


async def test_webhook_can_recover_provider_success_before_session_is_saved(mongo_database: MongoDatabase) -> None:
    payment = await checkout(mongo_database, reserved_only=True)
    service = WebhookService(
        VerifierStub(notification(payment)),
        MongoWebhookRepository(mongo_database),
        MongoPaymentRepository(mongo_database),
    )
    assert (await service.receive(b"body", "signature")).state is WebhookState.APPLIED
    stored = await MongoPaymentRepository(mongo_database).get_by_id(payment.id)
    assert stored is not None and stored.version == 2 and stored.status is PaymentStatus.SUCCEEDED
    assert stored.provider_session_id == "cs_test_fixture"


async def test_duplicate_identity_with_different_payload_is_rejected(mongo_database: MongoDatabase) -> None:
    payment = await checkout(mongo_database)
    webhooks = MongoWebhookRepository(mongo_database)
    event = notification(payment)
    await webhooks.receive(event)
    with pytest.raises(WebhookCollisionError):
        await webhooks.receive(replace(event, payload_digest="different"))
    assert (await webhooks.receive(event)).state is WebhookState.PENDING


async def test_expiry_and_success_concurrently_converge_on_success(mongo_database: MongoDatabase) -> None:
    payment = await checkout(mongo_database)
    repository = MongoPaymentRepository(mongo_database)
    webhooks = MongoWebhookRepository(mongo_database)
    paid = notification(payment, CheckoutOutcome.SUCCEEDED, "evt_paid")
    expired = notification(payment, CheckoutOutcome.EXPIRED, "evt_expired")
    await asyncio.gather(
        *[
            WebhookService(VerifierStub(event), webhooks, repository).receive(b"body", "signature")
            for event in (paid, expired)
        ]
    )
    stored = await repository.get_by_id(payment.id)
    assert stored is not None and stored.status is PaymentStatus.SUCCEEDED
    assert await mongo_database.webhooks.count_documents({"fulfillment_status": "pending"}) == 1
