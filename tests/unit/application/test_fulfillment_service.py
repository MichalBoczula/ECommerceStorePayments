from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from ecommerce_store_payments.application.payments.fulfillment import (
    CompletedInvoice,
    FulfillmentBlockedError,
    FulfillmentLeaseLostError,
    FulfillmentOrder,
    FulfillmentRetryError,
    FulfillmentWork,
)
from ecommerce_store_payments.application.payments.fulfillment_service import FulfillmentService
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from tests.unit.application.test_payment_service import MemoryPaymentRepository

NOW = datetime(2026, 10, 1, tzinfo=UTC)


class WorkStub:
    def __init__(self, work: FulfillmentWork) -> None:
        self.work = work
        self.available = True
        self.paid = False
        self.completed: CompletedInvoice | None = None
        self.failure: tuple[str, datetime | None] | None = None
        self.lose_lease = False

    async def claim(self, now: datetime) -> FulfillmentWork | None:
        if not self.available:
            return None
        self.available = False
        return self.work

    async def save_order_paid(self, work: FulfillmentWork, client_id: UUID, now: datetime) -> None:
        if self.lose_lease:
            raise FulfillmentLeaseLostError()
        self.paid = True
        self.work = replace(work, client_id=client_id, order_paid=True)

    async def complete(self, work: FulfillmentWork, invoice: CompletedInvoice, now: datetime) -> None:
        self.completed = invoice

    async def fail(self, work: FulfillmentWork, code: str, next_attempt: datetime | None, now: datetime) -> None:
        if self.lose_lease:
            raise FulfillmentLeaseLostError()
        self.failure = code, next_attempt


class OrdersStub:
    def __init__(self, payment: Payment) -> None:
        self.order = FulfillmentOrder(payment.order_id, uuid4(), payment.money, "Created")
        self.reads = 0
        self.writes = 0
        self.read_error: Exception | None = None
        self.write_error: Exception | None = None
        self.commit_before_error = False
        self.wrong_success = False

    async def get(self, order_id: UUID) -> FulfillmentOrder:
        self.reads += 1
        if self.read_error:
            raise self.read_error
        return self.order

    async def mark_paid(self, order_id: UUID) -> None:
        self.writes += 1
        if self.commit_before_error or (self.write_error is None and not self.wrong_success):
            self.order = replace(self.order, status="Paid")
        if self.write_error:
            raise self.write_error


class InvoicesStub:
    def __init__(self, order_id: UUID) -> None:
        self.invoice = CompletedInvoice(uuid4(), order_id, uuid4())
        self.existing: CompletedInvoice | None = None
        self.creates = 0
        self.error: Exception | None = None
        self.commit_before_error = False

    async def get_by_order(self, order_id: UUID) -> CompletedInvoice | None:
        return self.existing

    async def create(self, client_id: UUID, order_id: UUID) -> CompletedInvoice:
        self.creates += 1
        if self.commit_before_error or self.error is None:
            self.existing = self.invoice
        if self.error:
            raise self.error
        return self.invoice


async def setup() -> tuple[FulfillmentService, WorkStub, OrdersStub, InvoicesStub, MemoryPaymentRepository, Payment]:
    payment = Payment.create(uuid4(), Money(1299, "PLN"))
    payment.begin_checkout()
    payment.confirm_checkout("cs_test_fixture", "pi_fixture")
    assert payment.checkout_attempt_id is not None
    work = WorkStub(
        FulfillmentWork(
            "evt_fixture", payment.id, payment.order_id, payment.checkout_attempt_id, payment.money, uuid4(), 1
        )
    )
    payments = MemoryPaymentRepository()
    await payments.create(payment)
    orders, invoices = OrdersStub(payment), InvoicesStub(payment.order_id)
    return FulfillmentService(work, payments, orders, invoices, lambda: NOW), work, orders, invoices, payments, payment


async def test_success_and_already_completed_batch() -> None:
    service, work, orders, invoices, _, _ = await setup()
    assert await service.run_batch(100) == 1
    assert work.paid and work.completed == invoices.invoice
    assert orders.writes == invoices.creates == 1
    assert await service.run_batch(100) == 0


@pytest.mark.parametrize("code", ["timeout", "400", "409", "500"])
async def test_reconciles_ambiguous_or_repeated_paid_only_after_authoritative_read(code: str) -> None:
    service, work, orders, invoices, _, _ = await setup()
    orders.write_error = FulfillmentRetryError(code)
    orders.commit_before_error = True
    assert await service.run_batch(1) == 1
    assert work.completed == invoices.invoice and orders.reads == 2


async def test_repeat_paid_error_without_paid_state_remains_retryable() -> None:
    service, work, orders, invoices, _, _ = await setup()
    orders.write_error = FulfillmentRetryError("order_update_unavailable")
    await service.run_batch(1)
    assert work.failure == ("order_update_unavailable", NOW + timedelta(seconds=60))
    assert invoices.creates == 0 and not work.paid


async def test_success_response_without_paid_readback_is_not_accepted() -> None:
    service, work, orders, invoices, _, _ = await setup()
    orders.wrong_success = True
    await service.run_batch(1)
    assert work.failure == ("order_not_confirmed", NOW + timedelta(seconds=60))
    assert invoices.creates == 0


async def test_invoice_response_loss_reconciles_completed_invoice() -> None:
    service, work, _, invoices, _, _ = await setup()
    invoices.error = FulfillmentRetryError("invoice_create_unavailable")
    invoices.commit_before_error = True
    await service.run_batch(1)
    assert work.completed == invoices.invoice


async def test_invoice_failure_saves_paid_progress_and_restart_does_not_repeat_paid() -> None:
    service, work, orders, invoices, payments, _ = await setup()
    invoices.error = FulfillmentRetryError("invoice_create_unavailable")
    await service.run_batch(1)
    assert work.paid and work.completed is None
    assert work.failure == ("invoice_create_unavailable", NOW + timedelta(seconds=60))
    work.available, invoices.error = True, None
    work.work = replace(work.work, attempts=2)
    await FulfillmentService(work, payments, orders, invoices, lambda: NOW + timedelta(seconds=60)).run_batch(1)
    assert work.completed == invoices.invoice and orders.writes == 1


async def test_existing_paid_order_and_invoice_require_no_writes() -> None:
    service, work, orders, invoices, _, _ = await setup()
    orders.order = replace(orders.order, status="Paid")
    invoices.existing = invoices.invoice
    await service.run_batch(1)
    assert work.completed == invoices.invoice and orders.writes == invoices.creates == 0


@pytest.mark.parametrize(
    "mismatch", ["amount", "owner", "cancelled", "unknown", "order", "payment", "attempt", "invoice", "regressed"]
)
async def test_invalid_association_or_state_requires_operator_repair(mismatch: str) -> None:
    service, work, orders, invoices, payments, payment = await setup()
    if mismatch == "amount":
        orders.order = replace(orders.order, money=Money(1300, "PLN"))
    if mismatch == "owner":
        work.work = replace(work.work, client_id=uuid4())
    if mismatch == "cancelled":
        orders.order = replace(orders.order, status="Cancelled")
    if mismatch == "unknown":
        orders.order = replace(orders.order, status="Unknown")
    if mismatch == "order":
        orders.order = replace(orders.order, order_id=uuid4())
    if mismatch == "payment":
        payments.payments.clear()
    if mismatch == "attempt":
        work.work = replace(work.work, attempt_id=uuid4())
    if mismatch == "invoice":
        invoices.invoice = replace(invoices.invoice, order_id=uuid4())
    if mismatch == "regressed":
        work.work = replace(work.work, order_paid=True)
    await service.run_batch(1)
    assert work.failure is not None and work.failure[1] is None and work.completed is None
    assert payment.provider_payment_id == "pi_fixture"


@pytest.mark.parametrize("attempts,delay", [(1, 60), (3, 240), (8, 3600), (10, None), (11, None)])
async def test_bounded_backoff_and_exhaustion(attempts: int, delay: int | None) -> None:
    service, work, orders, _, _, _ = await setup()
    work.work = replace(work.work, attempts=attempts)
    orders.read_error = FulfillmentRetryError("order_unavailable")
    await service.run_batch(1)
    assert work.failure == (
        "retry_exhausted" if attempts > 10 else "order_unavailable",
        NOW + timedelta(seconds=delay) if delay is not None else None,
    )


async def test_unknown_error_is_saved_without_private_detail() -> None:
    service, work, orders, _, _, _ = await setup()
    orders.read_error = RuntimeError("private secret")
    await service.run_batch(1)
    assert work.failure == ("fulfillment_unavailable", NOW + timedelta(seconds=60))


async def test_lost_lease_cannot_complete_or_overwrite_new_worker() -> None:
    service, work, _, invoices, _, _ = await setup()
    work.lose_lease = True
    await service.run_batch(1)
    assert invoices.creates == 0 and work.completed is None and work.failure is None


async def test_timeout_remains_recoverable(monkeypatch: pytest.MonkeyPatch) -> None:
    service, work, orders, _, _, _ = await setup()
    orders.read_error = TimeoutError()
    await service.run_batch(1)
    assert work.failure == ("attempt_timeout", NOW + timedelta(seconds=60))


async def test_configuration_error_requires_manual_resume() -> None:
    service, work, orders, _, _, _ = await setup()
    orders.read_error = FulfillmentBlockedError("order_unauthorized")
    await service.run_batch(1)
    assert work.failure == ("order_unauthorized", None)


@pytest.mark.parametrize("limit", [0, 1001])
async def test_batch_limit_is_bounded(limit: int) -> None:
    service, *_ = await setup()
    with pytest.raises(ValueError):
        await service.run_batch(limit)
