from dataclasses import replace
from uuid import uuid4

import pytest

from ecommerce_store_payments.application.payments.webhook import (
    CheckoutOutcome,
    VerifiedWebhook,
    WebhookCollisionError,
    WebhookReceipt,
    WebhookRetryError,
    WebhookState,
)
from ecommerce_store_payments.application.payments.webhook_service import WebhookService
from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import PaymentConflictError
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from tests.unit.application.test_payment_service import MemoryPaymentRepository
from tests.webhook_fixtures import notification


class VerifierStub:
    def __init__(self, event: VerifiedWebhook) -> None:
        self.event = event
        self.last_input: tuple[bytes, str] | None = None

    def verify(self, payload: bytes, signature: str) -> VerifiedWebhook:
        self.last_input = payload, signature
        return self.event


class MemoryWebhookRepository:
    def __init__(self, payments: MemoryPaymentRepository) -> None:
        self.payments = payments
        self.receipts: dict[str, WebhookReceipt] = {}
        self.interrupt_once = False
        self.conflicts = 0

    async def receive(self, event: VerifiedWebhook) -> WebhookReceipt:
        current = self.receipts.setdefault(event.event_id, WebhookReceipt(event))
        if current.event != event:
            raise WebhookCollisionError()
        return current

    async def complete(
        self, receipt: WebhookReceipt, payment: Payment | None, state: WebhookState, reason: str, *, changed: bool
    ) -> WebhookReceipt:
        if self.interrupt_once:
            self.interrupt_once = False
            raise WebhookRetryError()
        if self.conflicts:
            self.conflicts -= 1
            assert payment is not None
            raise PaymentConflictError(payment.id, payment.version)
        if changed:
            assert payment is not None
            await self.payments.update(payment)
        result = replace(receipt, state=state, reason=reason)
        self.receipts[receipt.event.event_id] = result
        return result


async def setup_webhook() -> tuple[
    WebhookService, MemoryPaymentRepository, MemoryWebhookRepository, VerifierStub, Payment
]:
    payments = MemoryPaymentRepository()
    payment = Payment.create(uuid4(), Money(1299, "PLN"))
    payment.begin_checkout()
    payment.mark_as_pending("cs_test_fixture")
    payment = await payments.create(payment)
    verifier = VerifierStub(notification(payment))
    webhooks = MemoryWebhookRepository(payments)
    return WebhookService(verifier, webhooks, payments), payments, webhooks, verifier, payment


async def test_confirm_once_and_pass_original_bytes_to_verifier() -> None:
    service, payments, _, verifier, payment = await setup_webhook()
    first = await service.receive(b"original bytes", "header")
    assert first.state is WebhookState.APPLIED
    assert verifier.last_input == (b"original bytes", "header")
    assert await service.receive(b"original bytes", "header") == first
    current = await payments.get_by_id(payment.id)
    assert current is not None and current.status is PaymentStatus.SUCCEEDED and current.version == 1


async def test_receipt_survives_interruption_and_restart_can_finish_it() -> None:
    service, payments, webhooks, verifier, payment = await setup_webhook()
    webhooks.interrupt_once = True
    with pytest.raises(WebhookRetryError):
        await service.receive(b"body", "header")
    assert webhooks.receipts[verifier.event.event_id].state is WebhookState.PENDING
    current = await payments.get_by_id(payment.id)
    assert current is not None and current.status is PaymentStatus.PENDING
    restarted = WebhookService(verifier, webhooks, payments)
    assert (await restarted.receive(b"body", "header")).state is WebhookState.APPLIED


@pytest.mark.parametrize("conflicts", [1, 4])
async def test_conflicts_reload_or_leave_retryable_work(conflicts: int) -> None:
    service, _, webhooks, _, _ = await setup_webhook()
    webhooks.conflicts = conflicts
    if conflicts == 4:
        with pytest.raises(WebhookRetryError):
            await service.receive(b"body", "header")
    else:
        assert (await service.receive(b"body", "header")).state is WebhookState.APPLIED


@pytest.mark.parametrize("mismatch", ["money", "order", "attempt", "session", "missing", "unknown"])
async def test_mismatched_and_unrelated_notifications_cannot_confirm_payment(mismatch: str) -> None:
    service, payments, _, verifier, payment = await setup_webhook()
    checkout = verifier.event.checkout
    assert checkout is not None
    if mismatch == "money":
        checkout = replace(checkout, money=Money(1300, "PLN"))
    elif mismatch == "order":
        checkout = replace(checkout, order_id=uuid4())
    elif mismatch == "attempt":
        checkout = replace(checkout, attempt_id=uuid4())
    elif mismatch == "session":
        checkout = replace(checkout, session_id="cs_test_other")
    elif mismatch == "missing":
        checkout = replace(checkout, payment_id=uuid4())
    else:
        checkout = None
    verifier.event = replace(verifier.event, checkout=checkout)
    result = await service.receive(b"body", "header")
    assert result.state in (WebhookState.REJECTED, WebhookState.IGNORED)
    current = await payments.get_by_id(payment.id)
    assert current is not None and current.status is PaymentStatus.PENDING and current.version == 0


async def test_success_wins_over_expiry_in_either_order_without_extra_success_write() -> None:
    service, payments, _, verifier, payment = await setup_webhook()
    verifier.event = notification(payment, CheckoutOutcome.EXPIRED, "evt_expired")
    assert (await service.receive(b"expired", "header")).state is WebhookState.APPLIED
    verifier.event = notification(payment, CheckoutOutcome.SUCCEEDED, "evt_paid")
    assert (await service.receive(b"paid", "header")).state is WebhookState.APPLIED
    verifier.event = notification(payment, CheckoutOutcome.EXPIRED, "evt_late_expired")
    assert (await service.receive(b"expired", "header")).state is WebhookState.IGNORED
    verifier.event = notification(payment, CheckoutOutcome.SUCCEEDED, "evt_second_paid")
    assert (await service.receive(b"paid", "header")).state is WebhookState.IGNORED
    current = await payments.get_by_id(payment.id)
    assert current is not None and current.status is PaymentStatus.SUCCEEDED and current.version == 2


@pytest.mark.parametrize("outcome", [CheckoutOutcome.WAITING, CheckoutOutcome.FAILED, CheckoutOutcome.EXPIRED])
async def test_waiting_and_terminal_notifications_have_explicit_policy(outcome: CheckoutOutcome) -> None:
    service, payments, _, verifier, payment = await setup_webhook()
    verifier.event = notification(payment, outcome)
    result = await service.receive(b"body", "header")
    current = await payments.get_by_id(payment.id)
    assert current is not None
    if outcome is CheckoutOutcome.WAITING:
        assert result.state is WebhookState.IGNORED and current.status is PaymentStatus.PENDING
    else:
        assert result.state is WebhookState.APPLIED and current.status is PaymentStatus.FAILED


async def test_new_attempt_cannot_be_completed_by_old_success() -> None:
    service, payments, _, _, payment = await setup_webhook()
    payment.mark_as_failed("declined")
    payment.retry()
    payment.begin_checkout()
    payment.mark_as_pending("cs_test_new")
    await payments.update(payment)
    assert (await service.receive(b"old event", "header")).reason == "stale_attempt"


async def test_successful_attempt_cannot_change_its_provider_payment_id() -> None:
    service, _, _, verifier, _ = await setup_webhook()
    await service.receive(b"body", "header")
    assert verifier.event.checkout is not None
    verifier.event = replace(
        verifier.event, event_id="evt_other", checkout=replace(verifier.event.checkout, provider_payment_id="pi_other")
    )
    assert (await service.receive(b"body", "header")).reason == "provider_payment_mismatch"
