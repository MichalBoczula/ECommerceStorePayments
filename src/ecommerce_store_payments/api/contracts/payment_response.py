from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ecommerce_store_payments.domain.aggregates.payments.payment import Payment


class PaymentResponse(BaseModel):
    id: UUID
    order_id: UUID
    amount_minor: int
    currency: str
    status: str
    provider_session_id: str | None
    provider_payment_id: str | None
    failure_code: str | None
    created_at: datetime
    updated_at: datetime | None

    @classmethod
    def from_domain(cls, payment: Payment) -> PaymentResponse:
        return cls(
            id=payment.id,
            order_id=payment.order_id,
            amount_minor=payment.money.amount_minor,
            currency=payment.money.currency,
            status=payment.status.value,
            provider_session_id=payment.provider_session_id,
            provider_payment_id=payment.provider_payment_id,
            failure_code=payment.failure_code,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
        )
