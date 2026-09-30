from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.exceptions import PaymentErrorCode, PaymentValidationError
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money


def test_attempt_reservation_is_idempotent_and_retry_clears_it() -> None:
    payment = Payment.create(uuid4(), Money(1299, "PLN"))
    payment.begin_checkout()
    attempt_id = payment.checkout_attempt_id
    started_at = payment.checkout_started_at
    assert attempt_id is not None and started_at is not None
    payment.begin_checkout()
    assert (payment.checkout_attempt_id, payment.checkout_started_at) == (attempt_id, started_at)
    payment.mark_as_pending("cs_test_one")
    with pytest.raises(PaymentValidationError):
        payment.begin_checkout()
    payment.mark_as_failed("declined")
    payment.retry()
    assert payment.checkout_attempt_id is None and payment.checkout_started_at is None


@pytest.mark.parametrize("invalid", ["missing_id", "missing_time", "zero_id", "naive_time", "before", "after"])
def test_invalid_attempt_snapshots_are_rejected(invalid: str) -> None:
    now = datetime.now(UTC)
    attempt_id = uuid4() if invalid != "missing_id" else None
    started_at = now if invalid != "missing_time" else None
    if invalid == "zero_id":
        attempt_id = type(uuid4())(int=0)
    elif invalid == "naive_time":
        started_at = now.replace(tzinfo=None)
    elif invalid == "before":
        started_at = now - timedelta(seconds=1)
    elif invalid == "after":
        started_at = now + timedelta(seconds=1)
    with pytest.raises(PaymentValidationError) as error:
        Payment.rehydrate(
            uuid4(),
            uuid4(),
            Money(1299, "PLN"),
            PaymentStatus.CREATED,
            None,
            None,
            None,
            now,
            now,
            1,
            attempt_id,
            started_at,
        )
    assert error.value.code is PaymentErrorCode.INVALID_CHECKOUT_ATTEMPT


@pytest.mark.parametrize("state", ["created", "pending", "failed", "canceled"])
def test_verified_confirmation_recovers_same_attempt_and_round_trips(state: str) -> None:
    payment = Payment.create(uuid4(), Money(1299, "PLN"))
    payment.begin_checkout()
    if state != "created":
        payment.mark_as_pending("cs_test_one")
    if state == "failed":
        payment.mark_as_failed("checkout_expired")
    elif state == "canceled":
        payment.cancel()
    payment.confirm_checkout("cs_test_one", "pi_one")
    assert payment.status is PaymentStatus.SUCCEEDED
    assert payment.failure_code is None
    updated = payment.updated_at
    payment.confirm_checkout("cs_test_one", "pi_one")
    assert payment.updated_at == updated
    restored = Payment.rehydrate(
        payment.id,
        payment.order_id,
        payment.money,
        payment.status,
        payment.provider_session_id,
        payment.provider_payment_id,
        payment.failure_code,
        payment.created_at,
        payment.updated_at,
        1,
        payment.checkout_attempt_id,
        payment.checkout_started_at,
    )
    assert restored.status is PaymentStatus.SUCCEEDED


@pytest.mark.parametrize("invalid", ["unreserved", "session", "payment", "blank_session", "blank_payment"])
def test_verified_confirmation_rejects_unreserved_or_conflicting_provider_data(invalid: str) -> None:
    payment = Payment.create(uuid4(), Money(1299, "PLN"))
    if invalid != "unreserved":
        payment.begin_checkout()
        payment.mark_as_pending("cs_test_one")
    if invalid == "payment":
        payment.confirm_checkout("cs_test_one", "pi_one")
    session = "cs_test_other" if invalid == "session" else "cs_test_one"
    session = "" if invalid == "blank_session" else session
    provider_payment = "" if invalid == "blank_payment" else "pi_other"
    with pytest.raises(PaymentValidationError):
        payment.confirm_checkout(session, provider_payment)


def test_reserved_request_version_stays_stable_and_resets_on_retry() -> None:
    payment = Payment.create(uuid4(), Money(1299, "PLN"))
    payment.begin_checkout(request_version=2)
    payment.begin_checkout(request_version=1)
    assert payment.checkout_request_version == 2
    payment.mark_as_pending("cs_test_one")
    payment.mark_as_failed("declined")
    payment.retry()
    assert payment.checkout_request_version == 1


@pytest.mark.parametrize("version", [True, 0, -1, "2"])
def test_invalid_reserved_request_version_is_rejected(version: object) -> None:
    from ecommerce_store_payments.domain.aggregates.payments.payment_policy import PaymentPolicy

    with pytest.raises(PaymentValidationError):
        PaymentPolicy.require_checkout_request_version(version)
