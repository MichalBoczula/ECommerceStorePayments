from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from ecommerce_store_payments.domain.aggregates.payments.exceptions import MoneyValidationError, PaymentErrorCode
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money


def test_money_normalizes_currency() -> None:
    money = Money(amount_minor=12999, currency=" pln ")

    assert money.amount_minor == 12999
    assert money.currency == "PLN"


@pytest.mark.parametrize(("subtotal", "gross"), [(150, 184), (250, 308)])
def test_checkout_vat_rounds_half_to_even(subtotal: int, gross: int) -> None:
    assert Money(subtotal, "PLN").for_checkout(4) == Money(gross, "PLN")


@pytest.mark.parametrize("amount_minor", [0, -1, True, cast(int, 1.5)])
def test_money_rejects_non_positive_amount(amount_minor: int) -> None:
    with pytest.raises(MoneyValidationError) as error:
        Money(amount_minor=amount_minor, currency="PLN")
    assert error.value.code is PaymentErrorCode.INVALID_AMOUNT


@pytest.mark.parametrize("currency", ["", "PL", "PLN1", "€UR", "PŁN", "ßD", cast(str, None)])
def test_money_rejects_invalid_currency(currency: str) -> None:
    with pytest.raises(MoneyValidationError) as error:
        Money(amount_minor=100, currency=currency)
    assert error.value.code is PaymentErrorCode.INVALID_CURRENCY


def test_money_is_immutable() -> None:
    money = Money(amount_minor=100, currency="PLN")

    with pytest.raises(FrozenInstanceError):
        money.amount_minor = 200  # pyright: ignore[reportAttributeAccessIssue]
