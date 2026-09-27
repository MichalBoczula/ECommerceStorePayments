from decimal import Decimal, localcontext

# Deliberately explicit: unknown codes must not silently be treated as two-decimal currencies.
# ISO 4217 minor units for the currencies currently accepted at the Orders boundary.
_MINOR_UNIT_EXPONENTS = {
    "PLN": 2,
    "EUR": 2,
    "USD": 2,
    "GBP": 2,
    "CHF": 2,
    "JPY": 0,
    "KRW": 0,
    "BHD": 3,
    "JOD": 3,
    "KWD": 3,
    "OMR": 3,
    "TND": 3,
}


def to_minor_units(amount: Decimal, currency: str) -> int:
    exponent = _MINOR_UNIT_EXPONENTS.get(currency)
    if exponent is None or not amount.is_finite() or amount <= 0 or amount.adjusted() > 28:
        raise ValueError("Unsupported currency or invalid order amount.")

    with localcontext() as context:
        context.prec = max(context.prec, len(amount.as_tuple().digits) + exponent)
        minor_units = amount * (10**exponent)
        if minor_units != minor_units.to_integral_value():
            raise ValueError("Order amount cannot be represented in the currency's minor units.")
        return int(minor_units)
