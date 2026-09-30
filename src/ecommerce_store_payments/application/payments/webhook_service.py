from typing import final

from ecommerce_store_payments.application.payments.webhook import (
    CheckoutOutcome,
    WebhookReceipt,
    WebhookRepository,
    WebhookRetryError,
    WebhookState,
    WebhookVerifier,
)
from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import PaymentConflictError
from ecommerce_store_payments.domain.aggregates.payments.repositories.payment_repository import PaymentRepository


@final
class WebhookService:
    def __init__(self, verifier: WebhookVerifier, webhooks: WebhookRepository, payments: PaymentRepository) -> None:
        self._verifier = verifier
        self._webhooks = webhooks
        self._payments = payments

    async def receive(self, payload: bytes, signature: str) -> WebhookReceipt:
        """Verify original bytes, durably receive and atomically apply a checkout notification."""
        event = self._verifier.verify(payload, signature)
        return await self.process_received(await self._webhooks.receive(event))

    async def process_received(self, receipt: WebhookReceipt) -> WebhookReceipt:
        """Resume normalized work already persisted after signature verification; never accept browser input here."""
        event = receipt.event
        for _ in range(4):
            if receipt.state is not WebhookState.PENDING:
                return receipt
            payment = await self._payments.get_by_id(event.checkout.payment_id) if event.checkout else None
            state, reason, changed = self._apply(receipt, payment)
            try:
                return await self._webhooks.complete(receipt, payment, state, reason, changed=changed)
            except PaymentConflictError:
                receipt = await self._webhooks.receive(event)
                continue
        raise WebhookRetryError()

    @staticmethod
    def _apply(receipt: WebhookReceipt, payment: Payment | None) -> tuple[WebhookState, str, bool]:
        """Confirm only matching attempts; success wins over older failure or expiry notifications."""
        event = receipt.event
        checkout = event.checkout
        if checkout is None:
            return WebhookState.IGNORED, "unsupported_event", False
        if payment is None:
            return WebhookState.REJECTED, "payment_not_found", False
        if payment.order_id != checkout.order_id or payment.money != checkout.money:
            return WebhookState.REJECTED, "payment_mismatch", False
        if payment.checkout_attempt_id != checkout.attempt_id:
            return WebhookState.IGNORED, "stale_attempt", False
        if payment.provider_session_id not in (None, checkout.session_id):
            return WebhookState.REJECTED, "session_mismatch", False
        if event.outcome is CheckoutOutcome.SUCCEEDED:
            assert checkout.provider_payment_id is not None
            if payment.status is PaymentStatus.SUCCEEDED:
                if payment.provider_payment_id != checkout.provider_payment_id:
                    return WebhookState.REJECTED, "provider_payment_mismatch", False
                return WebhookState.IGNORED, "already_succeeded", False
            payment.confirm_checkout(checkout.session_id, checkout.provider_payment_id)
            return WebhookState.APPLIED, "payment_succeeded", True
        if payment.status is PaymentStatus.SUCCEEDED:
            return WebhookState.IGNORED, "already_succeeded", False
        if event.outcome is CheckoutOutcome.WAITING:
            return WebhookState.IGNORED, "awaiting_payment", False
        if payment.status in (PaymentStatus.FAILED, PaymentStatus.CANCELED):
            return WebhookState.IGNORED, "already_terminal", False
        if payment.status is PaymentStatus.CREATED:
            payment.mark_as_pending(checkout.session_id)
        payment.mark_as_failed("checkout_expired" if event.outcome is CheckoutOutcome.EXPIRED else "checkout_failed")
        return WebhookState.APPLIED, "payment_failed", True
