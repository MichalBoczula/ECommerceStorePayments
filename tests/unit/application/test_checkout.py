from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from ecommerce_store_payments.application.payments.checkout_provider import CheckoutRequest, CheckoutSession
from ecommerce_store_payments.application.payments.exceptions import (
    CheckoutDisabledError,
    CheckoutMoneyError,
    CheckoutRecoveryRequiredError,
    CheckoutTimeoutError,
    CheckoutUnavailableError,
    OrderNotPayableError,
    OrderTotalChangedError,
)
from ecommerce_store_payments.application.payments.order_details import OrderPaymentDetails
from ecommerce_store_payments.application.payments.payment_service import PaymentService
from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import PaymentConflictError
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from tests.unit.application.test_payment_service import MemoryPaymentRepository, OrderReaderStub


class CheckoutBoundary:
    def __init__(self) -> None:
        self.sessions: dict[UUID, CheckoutSession] = {}
        self.requests: list[CheckoutRequest] = []
        self.reads = 0
        self.timeout_once = False

    def require_available(self) -> None:
        pass

    def validate_money(self, money: Money) -> None:
        if money.currency != "PLN" or money.amount_minor < 200:
            raise CheckoutMoneyError()

    async def create(self, request: CheckoutRequest) -> CheckoutSession:
        self.requests.append(request)
        session = self.sessions.setdefault(
            request.attempt_id,
            CheckoutSession(
                f"cs_test_{request.attempt_id.hex}",
                "https://checkout.stripe.com/c/pay/demo",
                "open",
                datetime.now(UTC) + timedelta(hours=24),
            ),
        )
        if self.timeout_once:
            self.timeout_once = False
            raise CheckoutTimeoutError()
        return session

    async def get(self, session_id: str, request: CheckoutRequest) -> CheckoutSession:
        self.reads += 1
        session = self.sessions[request.attempt_id]
        assert session.session_id == session_id
        return session


def setup_checkout(
    repository: MemoryPaymentRepository | None = None,
) -> tuple[PaymentService, MemoryPaymentRepository, OrderReaderStub, CheckoutBoundary]:
    repository = repository or MemoryPaymentRepository()
    reader = OrderReaderStub(OrderPaymentDetails(uuid4(), Money(1299, "PLN"), "Created"))
    provider = CheckoutBoundary()
    return PaymentService(repository, reader, provider), repository, reader, provider


async def test_checkout_reserves_then_persists_pending_and_reuses_session() -> None:
    service, repository, reader, provider = setup_checkout()
    result = await service.checkout(reader.order.order_id)
    assert result.payment.status is PaymentStatus.PENDING
    assert result.payment.version == 2
    assert result.payment.checkout_attempt_id is not None
    assert result.payment.provider_session_id == result.session.session_id
    assert result.payment.provider_payment_id is None
    again = await service.checkout(reader.order.order_id)
    assert again.payment.id == result.payment.id
    assert again.payment.version == 2
    assert len(provider.sessions) == len(provider.requests) == 1
    assert provider.reads == 1
    assert (await repository.get_by_order_id(reader.order.order_id)) is not None


async def test_timeout_after_provider_acceptance_replays_same_durable_attempt() -> None:
    service, repository, reader, provider = setup_checkout()
    provider.timeout_once = True
    with pytest.raises(CheckoutTimeoutError):
        await service.checkout(reader.order.order_id)
    reserved = await repository.get_by_order_id(reader.order.order_id)
    assert reserved is not None and reserved.status is PaymentStatus.CREATED and reserved.version == 1
    restarted = PaymentService(repository, reader, provider)
    result = await restarted.checkout(reader.order.order_id)
    assert len(provider.sessions) == 1
    assert provider.requests[0] == provider.requests[1]
    assert result.payment.checkout_attempt_id == reserved.checkout_attempt_id


class FailingSaveRepository(MemoryPaymentRepository):
    async def update(self, payment: Payment) -> Payment:
        if payment.status is PaymentStatus.PENDING:
            raise RuntimeError("database failed before storing the session")
        return await super().update(payment)


async def test_database_failure_after_provider_success_can_be_recovered() -> None:
    service, repository, reader, provider = setup_checkout(FailingSaveRepository())
    with pytest.raises(RuntimeError):
        await service.checkout(reader.order.order_id)
    recovered = MemoryPaymentRepository()
    recovered.payments = repository.payments
    result = await PaymentService(recovered, reader, provider).checkout(reader.order.order_id)
    assert result.payment.status is PaymentStatus.PENDING
    assert provider.requests[0] == provider.requests[1]
    assert len(provider.sessions) == 1


class RacingCheckoutRepository(MemoryPaymentRepository):
    async def update(self, payment: Payment) -> Payment:
        await super().update(payment)
        raise PaymentConflictError(payment.id, payment.version)


async def test_checkout_returns_both_reservation_and_pending_concurrent_winners() -> None:
    service, _, reader, provider = setup_checkout(RacingCheckoutRepository())
    result = await service.checkout(reader.order.order_id)
    assert result.payment.status is PaymentStatus.PENDING and result.payment.version == 2
    assert len(provider.sessions) == 1


async def test_old_ambiguous_attempt_requires_reconciliation_without_provider_call() -> None:
    service, repository, reader, provider = setup_checkout()
    payment = Payment.create(reader.order.order_id, reader.order.money)
    old = datetime.now(UTC) - timedelta(hours=24)
    repository.payments[payment.order_id] = Payment.rehydrate(
        payment.id,
        payment.order_id,
        payment.money,
        PaymentStatus.CREATED,
        None,
        None,
        None,
        old,
        old,
        1,
        uuid4(),
        old,
    )
    with pytest.raises(CheckoutRecoveryRequiredError):
        await service.checkout(payment.order_id)
    assert not provider.requests


async def test_legacy_pending_cannot_create_another_checkout() -> None:
    service, repository, reader, provider = setup_checkout()
    payment = Payment.create(reader.order.order_id, reader.order.money)
    payment.mark_as_pending("cs_old")
    await repository.create(payment)
    with pytest.raises(CheckoutRecoveryRequiredError):
        await service.checkout(payment.order_id)
    assert not provider.requests


@pytest.mark.parametrize("order_status", ["Paid", "Cancelled"])
async def test_checkout_rechecks_order_before_any_provider_call(order_status: str) -> None:
    service, repository, reader, provider = setup_checkout()
    reader.order = OrderPaymentDetails(reader.order.order_id, reader.order.money, order_status)
    with pytest.raises(OrderNotPayableError):
        await service.checkout(reader.order.order_id)
    assert not provider.requests and not repository.payments


async def test_disabled_checkout_does_not_create_payment() -> None:
    _, repository, reader, _ = setup_checkout()
    with pytest.raises(CheckoutDisabledError):
        await PaymentService(repository, reader).checkout(reader.order.order_id)
    assert reader.calls == 0 and not repository.payments


async def test_unsupported_money_does_not_create_payment() -> None:
    service, repository, reader, provider = setup_checkout()
    reader.order = OrderPaymentDetails(reader.order.order_id, Money(1299, "EUR"), "Created")
    with pytest.raises(CheckoutMoneyError):
        await service.checkout(reader.order.order_id)
    assert not repository.payments and not provider.requests


async def test_checkout_cannot_use_changed_order_money_or_successful_payment() -> None:
    service, repository, reader, provider = setup_checkout()
    result = await service.checkout(reader.order.order_id)
    reader.order = OrderPaymentDetails(reader.order.order_id, Money(1599, "PLN"), "Created")
    with pytest.raises(OrderTotalChangedError):
        await service.checkout(reader.order.order_id)
    reader.order = OrderPaymentDetails(reader.order.order_id, result.payment.money, "Created")
    result.payment.mark_as_succeeded("pi_test_success")
    await repository.update(result.payment)
    with pytest.raises(CheckoutUnavailableError):
        await service.checkout(reader.order.order_id)
    assert len(provider.requests) == 1


async def test_terminal_retry_uses_new_attempt_on_same_payment() -> None:
    service, repository, reader, provider = setup_checkout()
    first = await service.checkout(reader.order.order_id)
    first.payment.mark_as_failed("declined")
    await repository.update(first.payment)
    second = await service.checkout(reader.order.order_id)
    assert second.payment.id == first.payment.id
    assert second.payment.checkout_attempt_id != first.payment.checkout_attempt_id
    assert len(provider.sessions) == 2
