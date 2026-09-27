from dataclasses import dataclass
from typing import final

from ecommerce_store_payments.domain.aggregates.payments.payment import Payment


@final
@dataclass(frozen=True, slots=True)
class PayResult:
    payment: Payment
    created: bool
