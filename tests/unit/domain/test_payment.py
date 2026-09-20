from datetime import UTC, datetime
from uuid import uuid4

import pytest

from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
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

    with pytest.raises(ValueError, match="must be pending"):
        payment.mark_as_succeeded("pi_test_123")


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
