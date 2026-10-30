from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment

PAYMENT_EXAMPLE: dict[str, JsonValue] = {
    "id": "33333333-3333-4333-8333-333333333333",
    "order_id": "11111111-1111-4111-8111-111111111111",
    "amount_minor": 1299,
    "currency": "PLN",
    "status": "created",
    "provider_session_id": None,
    "provider_payment_id": None,
    "failure_code": None,
    "created_at": "2026-10-01T12:00:00Z",
    "updated_at": None,
}


class PaymentResponse(BaseModel):
    """Complete current payment; nullable members are still present in every response."""

    model_config = ConfigDict(json_schema_extra={"additionalProperties": False, "examples": [PAYMENT_EXAMPLE]})

    id: UUID = Field(
        description="Stable nonzero payment identifier, retained across retries.", examples=[PAYMENT_EXAMPLE["id"]]
    )
    order_id: UUID = Field(
        description="Nonzero order identifier supplied in the route.", examples=[PAYMENT_EXAMPLE["order_id"]]
    )
    amount_minor: int = Field(
        description="Positive integer amount in the currency's minor units; 1299 PLN minor units means 12.99 PLN.",
        examples=[1299],
        json_schema_extra={"exclusiveMinimum": 0},
    )
    currency: str = Field(
        description=(
            "Normalized three-letter uppercase ASCII currency code. Pay supports the Orders "
            "currency; checkout currently supports PLN."
        ),
        examples=["PLN"],
        json_schema_extra={"pattern": "^[A-Z]{3}$"},
    )
    status: str = Field(
        description="Current domain payment state; a retry returns failed/canceled payments to created.",
        examples=["created", "succeeded"],
        json_schema_extra={"enum": [status.value for status in PaymentStatus]},
    )
    provider_session_id: str | None = Field(
        description="Checkout provider session identifier, or null before a session is recorded or after retry reset.",
        examples=[None, "cs_test_fixture"],
        json_schema_extra={"pattern": "^[!-~]+$"},
    )
    provider_payment_id: str | None = Field(
        description="Provider payment identifier after successful confirmation; otherwise null.",
        examples=[None, "pi_fixture"],
        json_schema_extra={"pattern": "^[!-~]+$"},
    )
    failure_code: str | None = Field(
        description="Recorded provider failure code when available; otherwise null. Retry clears this field.",
        examples=[None, "declined"],
        json_schema_extra={"pattern": "^[!-~]+$"},
    )
    created_at: datetime = Field(
        description="Timezone-aware creation timestamp, preserved across retries.",
        examples=[PAYMENT_EXAMPLE["created_at"]],
    )
    updated_at: datetime | None = Field(
        description=(
            "Timezone-aware last change timestamp, or null for the initial version; never earlier than created_at."
        ),
        examples=[None, "2026-10-01T12:01:00Z"],
    )

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
