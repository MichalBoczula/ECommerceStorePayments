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
