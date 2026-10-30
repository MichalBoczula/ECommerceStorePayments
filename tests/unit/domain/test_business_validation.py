"""Standalone rule boundaries: no HTTP route accepts these internal typed arguments."""

from typing import cast
from uuid import UUID, uuid4

import pytest

from ecommerce_store_payments.domain.aggregates.payments.exceptions import (
    MoneyValidationError,
    PaymentErrorCode,
    PaymentValidationError,
)
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money


@pytest.mark.parametrize("value", [False, True, None, "1", 1.0, 0, -1])
def test_standalone_money_amount_rejects_one_typed_value(value: object) -> None:
    with pytest.raises(MoneyValidationError) as error:
        Money(cast(int, value), "PLN")
    assert error.value.code is PaymentErrorCode.INVALID_AMOUNT
    assert str(error.value) == "Money amount must be a positive integer."


@pytest.mark.parametrize("value", [None, True, 123, "", "PL", "PLNN", "PŁN", "P1N"])
def test_standalone_money_currency_rejects_one_typed_value(value: object) -> None:
    with pytest.raises(MoneyValidationError) as error:
        Money(1, cast(str, value))
    assert error.value.code is PaymentErrorCode.INVALID_CURRENCY
    assert str(error.value) == "Currency must contain three ASCII letters."


@pytest.mark.parametrize(("value", "normalized"), [(" pln ", "PLN"), ("usd", "USD"), ("ZZZ", "ZZZ")])
def test_domain_currency_normalization_is_distinct_from_the_orders_allowlist(value: str, normalized: str) -> None:
    money = Money(1, value)
    payment = Payment.create(uuid4(), money)
    assert money.amount_minor == 1 and money.currency == normalized
    restored = Payment.rehydrate(
        payment.id, payment.order_id, money, payment.status, None, None, None, payment.created_at, None, 0
    )
    assert all(getattr(restored, slot) == getattr(payment, slot) for slot in Payment.__slots__)


@pytest.mark.parametrize("value", ["", "cs bad", "cs\tbad", "cs\nbad", "cs_ł", "\x00", True, 1, None])
def test_invalid_standalone_provider_identifier_preserves_every_aggregate_field(value: object) -> None:
    payment = Payment.create(uuid4(), Money(1, "PLN"))
    before = {slot: getattr(payment, slot) for slot in Payment.__slots__}
    with pytest.raises(PaymentValidationError) as error:
        payment.mark_as_pending(cast(str, value))
    assert error.value.code is PaymentErrorCode.INVALID_PROVIDER_SESSION_ID
    assert str(error.value) == "Provider identifier must contain printable ASCII without whitespace."
    assert {slot: getattr(payment, slot) for slot in Payment.__slots__} == before


@pytest.mark.parametrize("value", [False, True, None, "1", 1.0, 0, -1])
def test_invalid_standalone_checkout_version_preserves_every_aggregate_field(value: object) -> None:
    payment = Payment.create(uuid4(), Money(1, "PLN"))
    before = {slot: getattr(payment, slot) for slot in Payment.__slots__}
    with pytest.raises(PaymentValidationError) as error:
        payment.begin_checkout(request_version=cast(int, value))
    assert error.value.code is PaymentErrorCode.INVALID_CHECKOUT_ATTEMPT
    assert str(error.value) == "Checkout request version is invalid."
    assert {slot: getattr(payment, slot) for slot in Payment.__slots__} == before


@pytest.mark.parametrize("value", [UUID(int=0), None, "11111111-1111-4111-8111-111111111111"])
def test_standalone_create_and_rehydrate_both_reject_the_same_invalid_order_identifier(value: object) -> None:
    payment = Payment.create(uuid4(), Money(1, "PLN"))
    for operation in (
        lambda: Payment.create(cast(UUID, value), payment.money),
        lambda: Payment.rehydrate(
            payment.id, cast(UUID, value), payment.money, payment.status, None, None, None, payment.created_at, None, 0
        ),
    ):
        with pytest.raises(PaymentValidationError) as error:
            operation()
        assert error.value.code is PaymentErrorCode.INVALID_ORDER_ID
        assert str(error.value) == "Payment and order identifiers must be nonzero UUIDs."
