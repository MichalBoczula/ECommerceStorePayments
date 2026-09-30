from datetime import UTC, datetime, timedelta
from typing import final
from uuid import UUID

from ecommerce_store_payments.application.payments.checkout_provider import CheckoutProvider, CheckoutRequest
from ecommerce_store_payments.application.payments.checkout_result import CheckoutResult
from ecommerce_store_payments.application.payments.exceptions import (
    CheckoutDisabledError,
    CheckoutRecoveryRequiredError,
    CheckoutUnavailableError,
    OrderNotPayableError,
    OrderTotalChangedError,
    PaymentNotFoundError,
)
from ecommerce_store_payments.application.payments.order_reader import OrderReader
from ecommerce_store_payments.application.payments.pay_result import PayResult
from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import (
    PaymentConflictError,
    PaymentDuplicateError,
)
from ecommerce_store_payments.domain.aggregates.payments.repositories.payment_repository import PaymentRepository


@final
class PaymentService:
    def __init__(
        self,
        payment_repository: PaymentRepository,
        order_reader: OrderReader,
        checkout_provider: CheckoutProvider | None = None,
    ) -> None:
        self._payment_repository = payment_repository
        self._order_reader = order_reader
        self._checkout_provider = checkout_provider

    async def checkout(self, order_id: UUID) -> CheckoutResult:
        """Reserve, create or recover one checkout without confirming payment."""
        provider = self._checkout_provider
        if provider is None:
            raise CheckoutDisabledError()
        provider.require_available()
        order = await self._order_reader.get_by_id(order_id)
        self._require_created_order(order_id, order.status)
        provider.validate_money(order.money)
        result = await self.pay(order_id)
        payment = result.payment
        if payment.money != order.money:
            raise OrderTotalChangedError(order_id)
        if payment.status not in (PaymentStatus.CREATED, PaymentStatus.PENDING):
            raise CheckoutUnavailableError()
        if payment.status is PaymentStatus.CREATED and payment.checkout_attempt_id is None:
            payment.begin_checkout(request_version=2)
            try:
                payment = await self._payment_repository.update(payment)
            except PaymentConflictError:
                current = await self._payment_repository.get_by_order_id(order_id)
                if current is None or current.checkout_attempt_id is None:
                    raise
                payment = current
        if payment.checkout_attempt_id is None or payment.checkout_started_at is None:
            # Legacy pending records have no durable provider attempt identity.
            raise CheckoutRecoveryRequiredError()
        request = CheckoutRequest(
            payment.id, payment.order_id, payment.checkout_attempt_id, payment.money, payment.checkout_request_version
        )
        if payment.status is PaymentStatus.PENDING:
            if payment.provider_session_id is None:
                raise CheckoutRecoveryRequiredError()
            return CheckoutResult(payment, await provider.get(payment.provider_session_id, request))
        if payment.status is not PaymentStatus.CREATED:
            raise CheckoutUnavailableError()
        # Stripe may prune keys after 24 hours. Never recreate an ambiguous old attempt.
        if datetime.now(UTC) - payment.checkout_started_at >= timedelta(hours=23):
            raise CheckoutRecoveryRequiredError()
        session = await provider.create(request)
        payment.mark_as_pending(session.session_id)
        try:
            payment = await self._payment_repository.update(payment)
        except PaymentConflictError:
            current = await self._payment_repository.get_by_order_id(order_id)
            if (
                current is None
                or current.checkout_attempt_id != request.attempt_id
                or current.provider_session_id != session.session_id
                or current.status is not PaymentStatus.PENDING
            ):
                raise
            payment = current
        return CheckoutResult(payment, session)

    async def pay(self, order_id: UUID) -> PayResult:
        """Return an existing payment or create/retry one after checking Orders."""
        existing_payment = await self._payment_repository.get_by_order_id(order_id)
        if existing_payment is not None:
            if existing_payment.status in (PaymentStatus.FAILED, PaymentStatus.CANCELED):
                return await self._retry(existing_payment)
            return PayResult(existing_payment, created=False)

        order = await self._order_reader.get_by_id(order_id)
        self._require_created_order(order_id, order.status)

        payment = Payment.create(order_id=order.order_id, money=order.money)
        try:
            return PayResult(await self._payment_repository.create(payment), created=True)
        except PaymentDuplicateError:
            existing_payment = await self._payment_repository.get_by_order_id(order_id)
            if existing_payment is None:
                raise
            if existing_payment.status in (PaymentStatus.FAILED, PaymentStatus.CANCELED):
                return await self._retry(existing_payment)
            return PayResult(existing_payment, created=False)

    async def _retry(self, payment: Payment) -> PayResult:
        """Start a fresh attempt on the same aggregate when Orders still matches."""
        order = await self._order_reader.get_by_id(payment.order_id)
        self._require_created_order(payment.order_id, order.status)
        if order.money != payment.money:
            raise OrderTotalChangedError(payment.order_id)

        payment.retry()
        try:
            return PayResult(await self._payment_repository.update(payment), created=False)
        except PaymentConflictError:
            current = await self._payment_repository.get_by_order_id(payment.order_id)
            if current is None or current.version <= payment.version:
                raise
            if current.status in (PaymentStatus.FAILED, PaymentStatus.CANCELED):
                raise
            return PayResult(current, created=False)

    @staticmethod
    def _require_created_order(order_id: UUID, status: str) -> None:
        """Require an order in Created state before creating or retrying payment."""
        if status.casefold() != "created":
            raise OrderNotPayableError(order_id, status)

    async def get_by_order_id(self, order_id: UUID) -> Payment:
        """Read the current payment by order ID or report that it is missing."""
        payment = await self._payment_repository.get_by_order_id(order_id)
        if payment is None:
            raise PaymentNotFoundError(order_id)

        return payment
