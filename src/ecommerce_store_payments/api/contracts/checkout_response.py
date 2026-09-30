from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from ecommerce_store_payments.api.contracts.payment_response import PaymentResponse
from ecommerce_store_payments.application.payments.checkout_result import CheckoutResult


class CheckoutResponse(BaseModel):
    payment: PaymentResponse
    checkout_url: str | None
    checkout_status: Literal["open", "complete", "expired"]
    expires_at: datetime

    @classmethod
    def from_result(cls, result: CheckoutResult) -> CheckoutResponse:
        return cls(
            payment=PaymentResponse.from_domain(result.payment),
            checkout_url=result.session.url,
            checkout_status=result.session.status,
            expires_at=result.session.expires_at,
        )
