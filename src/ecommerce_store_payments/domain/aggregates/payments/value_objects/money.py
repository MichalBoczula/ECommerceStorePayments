from dataclasses import dataclass
from typing import final


@final
@dataclass(frozen=True, slots=True)
class Money:
    amount_minor: int
    currency: str

    def __post_init__(self) -> None:
        if self.amount_minor <= 0:
            raise ValueError("Money amount must be greater than zero.")

        normalized_currency = self.currency.strip().upper()
        if len(normalized_currency) != 3 or not normalized_currency.isalpha():
            raise ValueError("Currency must be a three-letter ISO 4217 code.")

        object.__setattr__(self, "currency", normalized_currency)
