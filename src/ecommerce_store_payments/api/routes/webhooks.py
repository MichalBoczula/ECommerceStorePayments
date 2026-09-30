import asyncio

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ecommerce_store_payments.api.dependencies import WebhookServiceDependency
from ecommerce_store_payments.api.errors import UNSUPPORTED_MEDIA_TYPE, ApiRequestError, ErrorSpec, problem_responses
from ecommerce_store_payments.application.payments.webhook import WebhookInvalidError, WebhookRetryError

router = APIRouter(prefix="/payments/webhooks", tags=["Webhooks"])
PROCESSING_TIMEOUT_SECONDS = 10


class WebhookAcknowledgement(BaseModel):
    received: bool = True


@router.post(
    "/stripe",
    response_model=WebhookAcknowledgement,
    operation_id="receiveStripeWebhook",
    responses=problem_responses(400, 405, 413, 415, 500, 503),
    openapi_extra={
        "parameters": [
            {
                "name": "Stripe-Signature",
                "in": "header",
                "required": True,
                "schema": {"type": "string"},
                "description": "Stripe timestamp and v1 signature.",
            }
        ],
        "requestBody": {
            "required": True,
            "description": "Original Stripe snapshot event bytes; signature verified before parsing.",
            "content": {
                "application/json": {
                    "schema": {"type": "object", "additionalProperties": True},
                }
            },
        },
    },
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
