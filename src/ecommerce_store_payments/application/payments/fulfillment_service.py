import asyncio
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta

from ecommerce_store_payments.application.payments.fulfillment import (
    CompletedInvoice,
    FulfillmentBlockedError,
    FulfillmentInvoices,
    FulfillmentLeaseLostError,
    FulfillmentOrder,
    FulfillmentOrders,
    FulfillmentRepository,
    FulfillmentRetryError,
    FulfillmentWork,
)
from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.repositories.payment_repository import PaymentRepository


def utc_now() -> datetime:
    return datetime.now(UTC)


class FulfillmentService:
    MAX_ATTEMPTS = 10
    ATTEMPT_TIMEOUT_SECONDS = 120

    def __init__(
        self,
        work: FulfillmentRepository,
        payments: PaymentRepository,
        orders: FulfillmentOrders,
        invoices: FulfillmentInvoices,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._work, self._payments = work, payments
        self._orders, self._invoices, self._clock = orders, invoices, clock

    async def run_batch(self, limit: int) -> int:
        if not 1 <= limit <= 1000:
            raise ValueError("Fulfillment batch limit must be between 1 and 1000.")
        processed = 0
        for _ in range(limit):
            work = await self._work.claim(self._clock())
            if work is None:
                break
            try:
                async with asyncio.timeout(self.ATTEMPT_TIMEOUT_SECONDS):
                    await self._process(work)
            except FulfillmentLeaseLostError:
                # Another worker owns recovery. The old worker must not overwrite its progress.
                pass
            except FulfillmentBlockedError as error:
                await self._record_failure(work, error.code, retry=False)
            except FulfillmentRetryError as error:
                await self._record_failure(work, error.code, retry=True)
            except TimeoutError:
                await self._record_failure(work, "attempt_timeout", retry=True)
            except Exception:
                # Unknown/ambiguous failure is recoverable; no private upstream detail is persisted.
                await self._record_failure(work, "fulfillment_unavailable", retry=True)
            processed += 1
        return processed

    async def _record_failure(self, work: FulfillmentWork, code: str, *, retry: bool) -> None:
        now = self._clock()
        next_attempt = (
            now + timedelta(seconds=min(60 * 2 ** min(work.attempts - 1, 6), 3600))
            if retry and work.attempts < self.MAX_ATTEMPTS
            else None
        )
        try:
            await self._work.fail(work, code, next_attempt, now)
        except FulfillmentLeaseLostError:
            pass

    def _validate_order(self, work: FulfillmentWork, order: FulfillmentOrder) -> None:
        if order.order_id != work.order_id or order.money != work.money or order.client_id.int == 0:
            raise FulfillmentBlockedError("order_mismatch")
        if work.client_id is not None and work.client_id != order.client_id:
            raise FulfillmentBlockedError("order_owner_changed")
        if order.status not in {"Created", "Paid"}:
            raise FulfillmentBlockedError("order_not_payable")

    @staticmethod
    def _validate_invoice(work: FulfillmentWork, invoice: CompletedInvoice) -> None:
        if invoice.order_id != work.order_id or invoice.invoice_id.int == 0 or invoice.client_data_version_id.int == 0:
            raise FulfillmentBlockedError("invoice_mismatch")

    async def _process(self, work: FulfillmentWork) -> None:
        if work.attempts > self.MAX_ATTEMPTS:
            raise FulfillmentBlockedError("retry_exhausted")
        payment = await self._payments.get_by_id(work.payment_id)
        if (
            payment is None
            or payment.status is not PaymentStatus.SUCCEEDED
            or payment.order_id != work.order_id
            or payment.money != work.money
            or payment.checkout_attempt_id != work.attempt_id
        ):
            raise FulfillmentBlockedError("payment_mismatch")
        order = await self._orders.get(work.order_id)
        self._validate_order(work, order)
        if order.status == "Created":
            if work.order_paid:
                raise FulfillmentBlockedError("order_state_regressed")
            try:
                await self._orders.mark_paid(work.order_id)
            except FulfillmentRetryError:
                # Repeat Paid is 400; timeouts/409/5xx can also conceal a committed write.
                order = await self._orders.get(work.order_id)
                self._validate_order(work, order)
                if order.status != "Paid":
                    raise
            else:
                order = await self._orders.get(work.order_id)
                self._validate_order(work, order)
                if order.status != "Paid":
                    raise FulfillmentRetryError("order_not_confirmed")
        await self._work.save_order_paid(work, order.client_id, self._clock())
        work = replace(work, client_id=order.client_id, order_paid=True)
        invoice = await self._invoices.get_by_order(work.order_id)
        if invoice is None:
            try:
                invoice = await self._invoices.create(order.client_id, work.order_id)
            except FulfillmentRetryError:
                invoice = await self._invoices.get_by_order(work.order_id)
                if invoice is None:
                    raise
        self._validate_invoice(work, invoice)
        await self._work.complete(work, invoice, self._clock())
