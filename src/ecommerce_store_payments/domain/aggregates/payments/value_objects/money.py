from dataclasses import dataclass
from typing import final

from ecommerce_store_payments.domain.aggregates.payments.exceptions import MoneyValidationError, PaymentErrorCode


@final
@dataclass(frozen=True, slots=True)
class Money:
    amount_minor: int
    currency: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "currency", self._validate(self.amount_minor, self.currency))

    @staticmethod
    def _validate(amount_minor: object, currency: object) -> str:
        """Require a positive minor-unit integer and normalize an ASCII currency code."""
        if isinstance(amount_minor, bool) or not isinstance(amount_minor, int) or amount_minor <= 0:
            raise MoneyValidationError(PaymentErrorCode.INVALID_AMOUNT, "Money amount must be a positive integer.")

        if not isinstance(currency, str):
            raise MoneyValidationError(PaymentErrorCode.INVALID_CURRENCY, "Currency must contain three ASCII letters.")

        raw_currency = currency.strip()
        if len(raw_currency) != 3 or not raw_currency.isascii() or not raw_currency.isalpha():
            raise MoneyValidationError(PaymentErrorCode.INVALID_CURRENCY, "Currency must contain three ASCII letters.")

        return raw_currency.upper()
