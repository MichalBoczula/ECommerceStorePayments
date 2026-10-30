"""Exact converter boundaries that can exceed the MongoDB-backed HTTP storage range."""

from decimal import Decimal, localcontext

import pytest

from ecommerce_store_payments.infrastructure.clients.orders.currency_units import to_minor_units


@pytest.mark.parametrize(
    ("currency", "major", "minor"),
    [
        ("PLN", "0.01", 1),
        ("EUR", "0.29", 29),
        ("USD", "90071992547409.91", 9007199254740991),
        ("GBP", "1.2300", 123),
        ("CHF", "1.23e1", 1230),
        ("JPY", "1", 1),
        ("KRW", "500", 500),
        ("BHD", "0.001", 1),
        ("JOD", "1.234", 1234),
        ("KWD", "1.234", 1234),
        ("OMR", "1.234", 1234),
        ("TND", "1.234", 1234),
        ("PLN", "1e28", 10**30),
    ],
)
def test_conversion_remains_exact_under_small_ambient_decimal_precision(currency: str, major: str, minor: int) -> None:
    with localcontext() as context:
        context.prec = 6
        assert to_minor_units(Decimal(major), currency) == minor
        assert context.prec == 6


@pytest.mark.parametrize(
    ("currency", "major", "message"),
    [
        ("PLN", "0", "Unsupported currency or invalid order amount."),
        ("PLN", "-0.01", "Unsupported currency or invalid order amount."),
        ("PLN", "NaN", "Unsupported currency or invalid order amount."),
        ("PLN", "Infinity", "Unsupported currency or invalid order amount."),
        ("PLN", "1e29", "Unsupported currency or invalid order amount."),
        ("ZZZ", "1", "Unsupported currency or invalid order amount."),
        ("pln", "1", "Unsupported currency or invalid order amount."),
        (" PLN ", "1", "Unsupported currency or invalid order amount."),
        ("PLN", "0.001", "Order amount cannot be represented in the currency's minor units."),
        ("JPY", "0.1", "Order amount cannot be represented in the currency's minor units."),
        ("KWD", "0.0001", "Order amount cannot be represented in the currency's minor units."),
    ],
)
def test_conversion_rejects_one_invalid_value_without_rounding(currency: str, major: str, message: str) -> None:
    with pytest.raises(ValueError) as error:
        to_minor_units(Decimal(major), currency)
    assert str(error.value) == message
