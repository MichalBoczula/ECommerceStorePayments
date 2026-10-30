from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ecommerce_store_payments.api.contracts.payment_response import PAYMENT_EXAMPLE, PaymentResponse
from ecommerce_store_payments.application.payments.checkout_result import CheckoutResult


class CheckoutResponse(BaseModel):
    """Current payment and the provider session selected for the existing checkout attempt."""

    model_config = ConfigDict(
        json_schema_extra={
            "additionalProperties": False,
            "examples": [
                {
                    "payment": {
                        **PAYMENT_EXAMPLE,
                        "status": "pending",
                        "provider_session_id": "cs_test_fixture",
                        "updated_at": "2026-10-01T12:01:00Z",
                    },
                    "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_fixture",
                    "checkout_status": "open",
                    "expires_at": "2026-10-02T12:01:00Z",
                }
            ],
        }
    )

    payment: PaymentResponse = Field(
        description="Complete current payment associated with this session.",
        examples=[
            {
                **PAYMENT_EXAMPLE,
                "status": "pending",
                "provider_session_id": "cs_test_fixture",
                "updated_at": "2026-10-01T12:01:00Z",
            }
        ],
    )
    checkout_url: str | None = Field(
        description="Provider-hosted HTTPS checkout URL; may be null for a complete or expired session.",
        examples=["https://checkout.stripe.com/c/pay/cs_test_fixture", None],
        json_schema_extra={"format": "uri"},
    )
    checkout_status: Literal["open", "complete", "expired"] = Field(
        description="Provider session lifecycle status, distinct from the nested payment's domain status.",
        examples=["open", "complete", "expired"],
    )
    expires_at: datetime = Field(
        description="Timezone-aware provider session expiry timestamp.", examples=["2026-10-02T12:01:00Z"]
    )

    @classmethod
    def from_result(cls, result: CheckoutResult) -> CheckoutResponse:
        return cls(
            payment=PaymentResponse.from_domain(result.payment),
            checkout_url=result.session.url,
            checkout_status=result.session.status,
            expires_at=result.session.expires_at,
        )
