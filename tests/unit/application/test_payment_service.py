from typing import cast
from uuid import UUID, uuid4

import pytest

from ecommerce_store_payments.application.payments.exceptions import (
    OrderNotPayableError,
    OrderTotalChangedError,
    PaymentNotFoundError,
)
from ecommerce_store_payments.application.payments.order_details import OrderPaymentDetails
from ecommerce_store_payments.application.payments.order_reader import OrderReader
from ecommerce_store_payments.application.payments.payment_service import PaymentService
from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import (
    PaymentConflictError,
    PaymentDuplicateError,
)
from ecommerce_store_payments.domain.aggregates.payments.repositories.payment_repository import PaymentRepository
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money


class MemoryPaymentRepository:
    def __init__(self) -> None:
        self.payments: dict[UUID, Payment] = {}

    async def create(self, payment: Payment) -> Payment:
        self.payments[payment.order_id] = self._copy(payment)
        return self._copy(payment)

    async def update(self, payment: Payment) -> Payment:
        current = self.payments.get(payment.order_id)
        if current is None or current.version != payment.version:
            raise PaymentConflictError(payment.id, payment.version)
        updated = self._copy(payment, version=payment.version + 1)
        self.payments[payment.order_id] = self._copy(updated)
        return updated

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        payment = next((payment for payment in self.payments.values() if payment.id == payment_id), None)
        return None if payment is None else self._copy(payment)

    async def get_by_order_id(self, order_id: UUID) -> Payment | None:
        payment = self.payments.get(order_id)
        return None if payment is None else self._copy(payment)

    @staticmethod
    def _copy(payment: Payment, *, version: int | None = None) -> Payment:
        return Payment.rehydrate(
            payment_id=payment.id,
            order_id=payment.order_id,
            money=payment.money,
            status=payment.status,
            provider_session_id=payment.provider_session_id,
            provider_payment_id=payment.provider_payment_id,
            failure_code=payment.failure_code,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
            version=payment.version if version is None else version,
            checkout_attempt_id=payment.checkout_attempt_id,
            checkout_started_at=payment.checkout_started_at,
            checkout_request_version=payment.checkout_request_version,
        )


class _RacingPaymentRepository(MemoryPaymentRepository):
    async def create(self, payment: Payment) -> Payment:
        await super().create(Payment.create(payment.order_id, payment.money))
        raise PaymentDuplicateError(payment.id, payment.order_id)


class _RacingTerminalRepository(MemoryPaymentRepository):
    async def create(self, payment: Payment) -> Payment:
        winner = Payment.create(payment.order_id, payment.money)
        winner.cancel()
        await super().create(winner)
        raise PaymentDuplicateError(payment.id, payment.order_id)


class _UnrelatedDuplicateRepository(MemoryPaymentRepository):
    async def create(self, payment: Payment) -> Payment:
        raise PaymentDuplicateError(payment.id, payment.order_id)


class _RacingRetryRepository(MemoryPaymentRepository):
    async def update(self, payment: Payment) -> Payment:
        winner = await super().update(payment)
        raise PaymentConflictError(winner.id, payment.version)


class _UnresolvedRetryRepository(MemoryPaymentRepository):
    async def update(self, payment: Payment) -> Payment:
        raise PaymentConflictError(payment.id, payment.version)


class OrderReaderStub:
    def __init__(self, order: OrderPaymentDetails) -> None:
        self.order = order
        self.calls = 0

    async def get_by_id(self, order_id: UUID) -> OrderPaymentDetails:
        self.calls += 1
        assert order_id == self.order.order_id
        return self.order


def _create_service(
    repository: MemoryPaymentRepository,
    order_reader: OrderReaderStub,
) -> PaymentService:
    return PaymentService(
        payment_repository=cast(PaymentRepository, repository),
        order_reader=cast(OrderReader, order_reader),
    )


@pytest.mark.asyncio
async def test_pay_creates_payment_from_order_details() -> None:
    order_id = uuid4()
    repository = MemoryPaymentRepository()
    order_reader = OrderReaderStub(
        OrderPaymentDetails(
            order_id=order_id,
            money=Money(amount_minor=12999, currency="PLN"),
            status="Created",
        )
    )
    service = _create_service(repository, order_reader)

    result = await service.pay(order_id)
    payment = result.payment

    assert result.created
    assert payment.order_id == order_id
    assert payment.money == Money(amount_minor=12999, currency="PLN")
    stored = await repository.get_by_order_id(order_id)
    assert stored is not None and stored.id == payment.id


@pytest.mark.parametrize("status", [PaymentStatus.CREATED, PaymentStatus.PENDING, PaymentStatus.SUCCEEDED])
async def test_pay_returns_existing_payment_without_loading_order(status: PaymentStatus) -> None:
    order_id = uuid4()
    repository = MemoryPaymentRepository()
    existing_payment = Payment.create(order_id, Money(amount_minor=12999, currency="PLN"))
    if status in (PaymentStatus.PENDING, PaymentStatus.SUCCEEDED):
        existing_payment.mark_as_pending("cs_123")
    if status is PaymentStatus.SUCCEEDED:
        existing_payment.mark_as_succeeded("pi_123")
    await repository.create(existing_payment)
    order_reader = OrderReaderStub(
        OrderPaymentDetails(
            order_id=order_id,
            money=Money(amount_minor=50000, currency="PLN"),
            status="Created",
        )
    )
    service = _create_service(repository, order_reader)

    result = await service.pay(order_id)

    assert result.payment.id == existing_payment.id
    assert result.payment.status is status
    assert not result.created
    assert order_reader.calls == 0


@pytest.mark.asyncio
async def test_pay_rejects_order_that_is_not_created() -> None:
    order_id = uuid4()
    repository = MemoryPaymentRepository()
    order_reader = OrderReaderStub(
        OrderPaymentDetails(
            order_id=order_id,
            money=Money(amount_minor=12999, currency="PLN"),
            status="Paid",
        )
    )
    service = _create_service(repository, order_reader)

    with pytest.raises(OrderNotPayableError, match="cannot be paid"):
        await service.pay(order_id)


@pytest.mark.asyncio
async def test_get_by_order_id_raises_when_payment_is_missing() -> None:
    order_id = uuid4()
    repository = MemoryPaymentRepository()
    order_reader = OrderReaderStub(
        OrderPaymentDetails(
            order_id=order_id,
            money=Money(amount_minor=12999, currency="PLN"),
            status="Created",
        )
    )
    service = _create_service(repository, order_reader)

    with pytest.raises(PaymentNotFoundError, match=str(order_id)):
        await service.get_by_order_id(order_id)


@pytest.mark.asyncio
async def test_pay_returns_winner_when_another_request_creates_payment_first() -> None:
    order_id = uuid4()
    repository = _RacingPaymentRepository()
    order_reader = OrderReaderStub(OrderPaymentDetails(order_id, Money(amount_minor=100, currency="PLN"), "Created"))
    service = _create_service(repository, order_reader)

    result = await service.pay(order_id)

    stored = await repository.get_by_order_id(order_id)
    assert stored is not None and result.payment.id == stored.id
    assert not result.created
    assert order_reader.calls == 1


async def test_pay_retries_concurrent_create_winner_if_already_canceled() -> None:
    order_id = uuid4()
    repository = _RacingTerminalRepository()
    reader = OrderReaderStub(OrderPaymentDetails(order_id, Money(amount_minor=100, currency="PLN"), "Created"))
    service = _create_service(repository, reader)

    result = await service.pay(order_id)

    assert result.payment.status is PaymentStatus.CREATED
    assert result.payment.version == 1
    assert not result.created
    assert reader.calls == 2


@pytest.mark.asyncio
async def test_pay_propagates_duplicate_when_no_payment_exists_for_order() -> None:
    order_id = uuid4()
    repository = _UnrelatedDuplicateRepository()
    order_reader = OrderReaderStub(OrderPaymentDetails(order_id, Money(amount_minor=100, currency="PLN"), "Created"))
    service = _create_service(repository, order_reader)

    with pytest.raises(PaymentDuplicateError):
        await service.pay(order_id)


@pytest.mark.parametrize("terminal", [PaymentStatus.FAILED, PaymentStatus.CANCELED])
async def test_pay_retries_terminal_payment_in_place(terminal: PaymentStatus) -> None:
    order_id = uuid4()
    repository = MemoryPaymentRepository()
    payment = Payment.create(order_id, Money(amount_minor=12999, currency="PLN"))
    if terminal is PaymentStatus.FAILED:
        payment.mark_as_pending("cs_old")
        payment.mark_as_failed("declined")
    else:
        payment.cancel()
    await repository.create(payment)
    reader = OrderReaderStub(OrderPaymentDetails(order_id, payment.money, "Created"))
    service = _create_service(repository, reader)

    result = await service.pay(order_id)
    stored = await service.get_by_order_id(order_id)

    assert not result.created
    assert result.payment.id == stored.id == payment.id
    assert result.payment.status is stored.status is PaymentStatus.CREATED
    assert result.payment.version == stored.version == 1
    assert result.payment.updated_at is not None
    assert result.payment.provider_session_id is None
    assert result.payment.failure_code is None
    assert reader.calls == 1
    repeated = await service.pay(order_id)
    assert repeated.payment.version == 1 and not repeated.created
    assert reader.calls == 1


@pytest.mark.parametrize("order_status", ["Paid", "Canceled"])
async def test_pay_cannot_retry_when_order_is_not_created(order_status: str) -> None:
    order_id = uuid4()
    repository = MemoryPaymentRepository()
    payment = Payment.create(order_id, Money(amount_minor=12999, currency="PLN"))
    payment.cancel()
    await repository.create(payment)
    service = _create_service(repository, OrderReaderStub(OrderPaymentDetails(order_id, payment.money, order_status)))

    with pytest.raises(OrderNotPayableError):
        await service.pay(order_id)
    stored = await service.get_by_order_id(order_id)
    assert stored.status is PaymentStatus.CANCELED and stored.version == 0


async def test_pay_cannot_retry_if_order_total_changed() -> None:
    order_id = uuid4()
    repository = MemoryPaymentRepository()
    payment = Payment.create(order_id, Money(amount_minor=12999, currency="PLN"))
    payment.cancel()
    await repository.create(payment)
    service = _create_service(
        repository,
        OrderReaderStub(OrderPaymentDetails(order_id, Money(amount_minor=500, currency="EUR"), "Created")),
    )

    with pytest.raises(OrderTotalChangedError):
        await service.pay(order_id)
    stored = await service.get_by_order_id(order_id)
    assert stored.status is PaymentStatus.CANCELED and stored.money == payment.money


async def test_pay_returns_concurrent_retry_winner() -> None:
    order_id = uuid4()
    repository = _RacingRetryRepository()
    payment = Payment.create(order_id, Money(amount_minor=100, currency="PLN"))
    payment.cancel()
    await repository.create(payment)
    service = _create_service(repository, OrderReaderStub(OrderPaymentDetails(order_id, payment.money, "Created")))

    result = await service.pay(order_id)

    assert result.payment.id == payment.id
    assert result.payment.status is PaymentStatus.CREATED
    assert result.payment.version == 1
    assert not result.created


async def test_pay_propagates_unresolved_retry_conflict() -> None:
    order_id = uuid4()
    repository = _UnresolvedRetryRepository()
    payment = Payment.create(order_id, Money(amount_minor=100, currency="PLN"))
    payment.cancel()
    await repository.create(payment)
    service = _create_service(repository, OrderReaderStub(OrderPaymentDetails(order_id, payment.money, "Created")))

    with pytest.raises(PaymentConflictError):
        await service.pay(order_id)
