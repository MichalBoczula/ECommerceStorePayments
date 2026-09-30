from dataclasses import dataclass

from ecommerce_store_payments.application.payments.checkout_provider import CheckoutSession
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment


@dataclass(frozen=True, slots=True)
class CheckoutResult:
    payment: Payment
    session: CheckoutSession
