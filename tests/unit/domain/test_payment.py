from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import pytest

from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.exceptions import (
    PaymentErrorCode,
    PaymentTransitionError,
    PaymentValidationError,
)
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money


def test_create_initializes_new_payment() -> None:
    order_id = uuid4()
    money = Money(amount_minor=12999, currency="PLN")

    payment = Payment.create(order_id, money)

    assert payment.id
    assert payment.order_id == order_id
    assert payment.money == money
    assert payment.status is PaymentStatus.CREATED
    assert payment.provider_session_id is None
    assert payment.provider_payment_id is None
    assert payment.failure_code is None
    assert payment.created_at.tzinfo is UTC
    assert payment.updated_at is None


def test_payment_can_transition_from_created_to_succeeded() -> None:
    payment = Payment.create(uuid4(), Money(amount_minor=12999, currency="PLN"))

    payment.mark_as_pending("cs_test_123")
    payment.mark_as_succeeded("pi_test_123")

    assert payment.status is PaymentStatus.SUCCEEDED
    assert payment.provider_session_id == "cs_test_123"
    assert payment.provider_payment_id == "pi_test_123"
    assert payment.updated_at is not None


def test_payment_rejects_invalid_transition() -> None:
    payment = Payment.create(uuid4(), Money(amount_minor=12999, currency="PLN"))

    with pytest.raises(PaymentTransitionError) as error:
        payment.mark_as_succeeded("pi_test_123")

    assert error.value.code is PaymentErrorCode.INVALID_PAYMENT_TRANSITION
    assert error.value.current == "created"
    assert error.value.target == "succeeded"
    assert payment.status is PaymentStatus.CREATED
    assert payment.updated_at is None


def test_rehydrate_restores_persisted_state() -> None:
    payment_id = uuid4()
    order_id = uuid4()
    money = Money(amount_minor=12999, currency="PLN")
    created_at = datetime(2026, 9, 20, tzinfo=UTC)
    updated_at = datetime(2026, 9, 21, tzinfo=UTC)

    payment = Payment.rehydrate(
        payment_id=payment_id,
        order_id=order_id,
        money=money,
        status=PaymentStatus.SUCCEEDED,
        provider_session_id="cs_test_123",
        provider_payment_id="pi_test_123",
        failure_code=None,
        created_at=created_at,
        updated_at=updated_at,
    )

    assert payment.id == payment_id
    assert payment.order_id == order_id
    assert payment.money == money
    assert payment.status is PaymentStatus.SUCCEEDED
    assert payment.created_at == created_at
    assert payment.updated_at == updated_at


@pytest.mark.parametrize("order_id", [UUID(int=0)])
def test_create_rejects_invalid_order_id(order_id: UUID) -> None:
    with pytest.raises(PaymentValidationError) as error:
        Payment.create(order_id, Money(amount_minor=100, currency="PLN"))
    assert error.value.code is PaymentErrorCode.INVALID_ORDER_ID


def test_rehydrate_rejects_invalid_payment_id() -> None:
    with pytest.raises(PaymentValidationError) as error:
        Payment.rehydrate(
            payment_id=UUID(int=0),
            order_id=uuid4(),
            money=Money(amount_minor=100, currency="PLN"),
            status=PaymentStatus.CREATED,
            provider_session_id=None,
            provider_payment_id=None,
            failure_code=None,
            created_at=datetime.now(UTC),
            updated_at=None,
        )
    assert error.value.code is PaymentErrorCode.INVALID_PAYMENT_ID


@pytest.mark.parametrize(
    "status",
    [
        PaymentStatus.CREATED,
        PaymentStatus.PENDING,
        PaymentStatus.SUCCEEDED,
        PaymentStatus.FAILED,
        PaymentStatus.CANCELED,
    ],
)
def test_rehydrate_accepts_each_consistent_state(status: PaymentStatus) -> None:
    payment = _payment_in(status)

    restored = Payment.rehydrate(
        payment_id=payment.id,
        order_id=payment.order_id,
        money=payment.money,
        status=payment.status,
        provider_session_id=payment.provider_session_id,
        provider_payment_id=payment.provider_payment_id,
        failure_code=payment.failure_code,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )

    assert restored.status is status
    assert restored.provider_session_id == payment.provider_session_id
    assert restored.provider_payment_id == payment.provider_payment_id
    assert restored.failure_code == payment.failure_code


def test_rehydrate_rejects_unknown_status() -> None:
    with pytest.raises(PaymentValidationError) as error:
        Payment.rehydrate(
            payment_id=uuid4(),
            order_id=uuid4(),
            money=Money(amount_minor=100, currency="PLN"),
            status=cast(PaymentStatus, "unknown"),
            provider_session_id=None,
            provider_payment_id=None,
            failure_code=None,
            created_at=datetime.now(UTC),
            updated_at=None,
        )
    assert error.value.code is PaymentErrorCode.INVALID_PAYMENT_STATE


@pytest.mark.parametrize(
    ("status", "session", "provider_payment", "failure", "has_updated_at"),
    [
        (PaymentStatus.CREATED, "cs_1", None, None, False),
        (PaymentStatus.CREATED, None, None, None, True),
        (PaymentStatus.PENDING, None, None, None, True),
        (PaymentStatus.PENDING, "cs_1", "pi_1", None, True),
        (PaymentStatus.SUCCEEDED, "cs_1", None, None, True),
        (PaymentStatus.SUCCEEDED, "cs_1", "pi_1", "failure", True),
        (PaymentStatus.FAILED, "cs_1", "pi_1", "failure", True),
        (PaymentStatus.CANCELED, None, None, "failure", True),
        (PaymentStatus.PENDING, "cs_1", None, None, False),
    ],
)
def test_rehydrate_rejects_inconsistent_state(
    status: PaymentStatus,
    session: str | None,
    provider_payment: str | None,
    failure: str | None,
    has_updated_at: bool,
) -> None:
    created_at = datetime(2026, 9, 20, tzinfo=UTC)
    with pytest.raises(PaymentValidationError) as error:
        Payment.rehydrate(
            payment_id=uuid4(),
            order_id=uuid4(),
            money=Money(amount_minor=100, currency="PLN"),
            status=status,
            provider_session_id=session,
            provider_payment_id=provider_payment,
            failure_code=failure,
            created_at=created_at,
            updated_at=datetime(2026, 9, 21, tzinfo=UTC) if has_updated_at else None,
        )
    assert error.value.code is PaymentErrorCode.INVALID_PAYMENT_STATE


@pytest.mark.parametrize(
    ("created_at", "updated_at"),
    [
        (datetime(2026, 9, 20), None),
        (datetime(2026, 9, 20, tzinfo=UTC), datetime(2026, 9, 21)),
        (datetime(2026, 9, 20, tzinfo=UTC), datetime(2026, 9, 19, tzinfo=UTC)),
    ],
)
def test_rehydrate_rejects_invalid_timestamps(created_at: datetime, updated_at: datetime | None) -> None:
    with pytest.raises(PaymentValidationError) as error:
        Payment.rehydrate(
            payment_id=uuid4(),
            order_id=uuid4(),
            money=Money(amount_minor=100, currency="PLN"),
            status=PaymentStatus.CREATED,
            provider_session_id=None,
            provider_payment_id=None,
            failure_code=None,
            created_at=created_at,
            updated_at=updated_at,
        )
    assert error.value.code is PaymentErrorCode.INVALID_PAYMENT_TIMESTAMP


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("session", " ", PaymentErrorCode.INVALID_PROVIDER_SESSION_ID),
        ("session", " cs_1", PaymentErrorCode.INVALID_PROVIDER_SESSION_ID),
        ("session", "cs 1", PaymentErrorCode.INVALID_PROVIDER_SESSION_ID),
        ("payment", "", PaymentErrorCode.INVALID_PROVIDER_PAYMENT_ID),
        ("payment", "pi_1 ", PaymentErrorCode.INVALID_PROVIDER_PAYMENT_ID),
        ("payment", "pi_é", PaymentErrorCode.INVALID_PROVIDER_PAYMENT_ID),
        ("failure", " ", PaymentErrorCode.INVALID_FAILURE_CODE),
    ],
)
def test_invalid_provider_data_does_not_change_payment(field: str, value: str, code: PaymentErrorCode) -> None:
    payment = Payment.create(uuid4(), Money(amount_minor=100, currency="PLN"))
    if field == "failure":
        payment.mark_as_pending("cs_1")
    previous_updated_at = payment.updated_at

    with pytest.raises(PaymentValidationError) as error:
        if field == "session":
            payment.mark_as_pending(value)
        elif field == "payment":
            payment.mark_as_succeeded(value)
        else:
            payment.mark_as_failed(value)

    assert error.value.code is code
    assert payment.updated_at == previous_updated_at


def test_rehydrate_rejects_invalid_provider_session() -> None:
    with pytest.raises(PaymentValidationError) as error:
        Payment.rehydrate(
            payment_id=uuid4(),
            order_id=uuid4(),
            money=Money(amount_minor=100, currency="PLN"),
            status=PaymentStatus.PENDING,
            provider_session_id="cs 1",
            provider_payment_id=None,
            failure_code=None,
            created_at=datetime(2026, 9, 20, tzinfo=UTC),
            updated_at=datetime(2026, 9, 21, tzinfo=UTC),
        )
    assert error.value.code is PaymentErrorCode.INVALID_PROVIDER_SESSION_ID


def test_failure_without_code_and_cancellation_after_pending_round_trip() -> None:
    failed = Payment.create(uuid4(), Money(amount_minor=100, currency="PLN"))
    failed.mark_as_pending("cs_1")
    failed.mark_as_failed()
    updated_at = failed.updated_at
    failed.mark_as_failed()

    canceled = Payment.create(uuid4(), Money(amount_minor=100, currency="PLN"))
    canceled.mark_as_pending("cs_2")
    canceled.cancel()

    assert failed.failure_code is None
    assert failed.updated_at == updated_at
    assert canceled.status is PaymentStatus.CANCELED
    assert canceled.provider_session_id == "cs_2"


def _payment_in(status: PaymentStatus) -> Payment:
    payment = Payment.create(uuid4(), Money(amount_minor=100, currency="PLN"))
    if status in (PaymentStatus.PENDING, PaymentStatus.SUCCEEDED, PaymentStatus.FAILED):
        payment.mark_as_pending("cs_1")
    if status is PaymentStatus.SUCCEEDED:
        payment.mark_as_succeeded("pi_1")
    elif status is PaymentStatus.FAILED:
        payment.mark_as_failed("failed")
    elif status is PaymentStatus.CANCELED:
        payment.cancel()
    return payment


def _apply(payment: Payment, operation: str, identifier: str) -> None:
    if operation == "pending":
        payment.mark_as_pending(identifier)
    elif operation == "succeeded":
        payment.mark_as_succeeded(identifier)
    elif operation == "failed":
        payment.mark_as_failed(identifier)
    else:
        payment.cancel()


@pytest.mark.parametrize(
    ("initial", "operation", "identifier", "expected"),
    [
        (PaymentStatus.CREATED, "pending", "cs_1", PaymentStatus.PENDING),
        (PaymentStatus.CREATED, "cancel", "", PaymentStatus.CANCELED),
        (PaymentStatus.PENDING, "succeeded", "pi_1", PaymentStatus.SUCCEEDED),
        (PaymentStatus.PENDING, "failed", "failed", PaymentStatus.FAILED),
        (PaymentStatus.PENDING, "cancel", "", PaymentStatus.CANCELED),
        (PaymentStatus.PENDING, "pending", "cs_1", PaymentStatus.PENDING),
        (PaymentStatus.SUCCEEDED, "succeeded", "pi_1", PaymentStatus.SUCCEEDED),
        (PaymentStatus.FAILED, "failed", "failed", PaymentStatus.FAILED),
        (PaymentStatus.CANCELED, "cancel", "", PaymentStatus.CANCELED),
    ],
)
def test_allowed_transition_or_exact_repeat(
    initial: PaymentStatus, operation: str, identifier: str, expected: PaymentStatus
) -> None:
    payment = _payment_in(initial)
    old_updated_at = payment.updated_at

    _apply(payment, operation, identifier)

    assert payment.status is expected
    assert payment.updated_at is not None
    if initial is expected:
        assert payment.updated_at == old_updated_at


@pytest.mark.parametrize(
    ("initial", "operation", "identifier"),
    [
        (PaymentStatus.CREATED, "succeeded", "pi_1"),
        (PaymentStatus.CREATED, "failed", "failed"),
        (PaymentStatus.PENDING, "pending", "cs_2"),
        (PaymentStatus.SUCCEEDED, "succeeded", "pi_2"),
        (PaymentStatus.SUCCEEDED, "failed", "failed"),
        (PaymentStatus.SUCCEEDED, "cancel", ""),
        (PaymentStatus.FAILED, "pending", "cs_1"),
        (PaymentStatus.FAILED, "failed", "other"),
        (PaymentStatus.FAILED, "succeeded", "pi_1"),
        (PaymentStatus.CANCELED, "pending", "cs_1"),
        (PaymentStatus.CANCELED, "succeeded", "pi_1"),
    ],
)
def test_disallowed_transition_preserves_state(initial: PaymentStatus, operation: str, identifier: str) -> None:
    payment = _payment_in(initial)
    previous_updated_at = payment.updated_at
    previous_session = payment.provider_session_id
    previous_payment = payment.provider_payment_id
    previous_failure = payment.failure_code

    with pytest.raises(PaymentTransitionError) as error:
        _apply(payment, operation, identifier)

    assert error.value.code is PaymentErrorCode.INVALID_PAYMENT_TRANSITION
    assert payment.status is initial
    assert payment.updated_at == previous_updated_at
    assert payment.provider_session_id == previous_session
    assert payment.provider_payment_id == previous_payment
    assert payment.failure_code == previous_failure
