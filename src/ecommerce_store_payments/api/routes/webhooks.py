import asyncio

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from ecommerce_store_payments.api.contracts.webhook_request import webhook_request
from ecommerce_store_payments.api.dependencies import WebhookServiceDependency
from ecommerce_store_payments.api.errors import UNSUPPORTED_MEDIA_TYPE, ApiRequestError, ErrorSpec, problem_responses
from ecommerce_store_payments.application.payments.webhook import WebhookInvalidError, WebhookRetryError

router = APIRouter(prefix="/payments/webhooks", tags=["Webhooks"])
PROCESSING_TIMEOUT_SECONDS = 10


class WebhookAcknowledgement(BaseModel):
    """Acknowledgement of accepted delivery, including ignored or semantically rejected events."""

    model_config = ConfigDict(
        json_schema_serialization_defaults_required=True,
        json_schema_extra={"additionalProperties": False, "examples": [{"received": True}]},
    )
    received: bool = Field(
        default=True,
        description=(
            "Delivery was accepted. True does not imply a payment transition or completed "
            "fulfillment; consult durable receipts."
        ),
        examples=[True],
        json_schema_extra={"const": True},
    )


@router.post(
    "/stripe",
    response_model=WebhookAcknowledgement,
    operation_id="receiveStripeWebhook",
    responses=problem_responses(400, 405, 413, 415, 500, 503),
    openapi_extra=webhook_request(),
)
async def receive_stripe_webhook(request: Request, webhook_service: WebhookServiceDependency) -> WebhookAcknowledgement:
    """Receive the original signed bytes without contacting Orders, invoices or Stripe."""
    if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
        raise ApiRequestError(UNSUPPORTED_MEDIA_TYPE)
    payload = bytearray()
    async for chunk in request.stream():
        if len(payload) + len(chunk) > 1024 * 1024:
            raise ApiRequestError(ErrorSpec(413, "webhook_too_large", "Webhook body exceeds the size limit."))
        payload.extend(chunk)
    signatures = request.headers.getlist("stripe-signature")
    if len(signatures) != 1 or not signatures[0]:
        raise WebhookInvalidError()
    try:
        async with asyncio.timeout(PROCESSING_TIMEOUT_SECONDS):
            await webhook_service.receive(bytes(payload), signatures[0])
    except TimeoutError as error:
        raise WebhookRetryError() from error
    return WebhookAcknowledgement()
