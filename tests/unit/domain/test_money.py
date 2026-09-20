from dataclasses import FrozenInstanceError

import pytest

from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money


def test_money_normalizes_currency() -> None:
    money = Money(amount_minor=12999, currency=" pln ")

    assert money.amount_minor == 12999
    assert money.currency == "PLN"


@pytest.mark.parametrize("amount_minor", [0, -1])
def test_money_rejects_non_positive_amount(amount_minor: int) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        Money(amount_minor=amount_minor, currency="PLN")


@pytest.mark.parametrize("currency", ["", "PL", "PLN1"])
def test_money_rejects_invalid_currency(currency: str) -> None:
    with pytest.raises(ValueError, match="three-letter ISO 4217"):
        Money(amount_minor=100, currency=currency)


def test_money_is_immutable() -> None:
    money = Money(amount_minor=100, currency="PLN")

    with pytest.raises(FrozenInstanceError):
        setattr(money, "amount_minor", 200)
