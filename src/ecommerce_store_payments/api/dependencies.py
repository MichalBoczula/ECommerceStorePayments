from typing import Annotated, cast

from fastapi import Depends, Request

from ecommerce_store_payments.application.payments.payment_service import PaymentService
from ecommerce_store_payments.application.payments.webhook_service import WebhookService


def get_payment_service(request: Request) -> PaymentService:
    return cast(PaymentService, request.app.state.payment_service)


PaymentServiceDependency = Annotated[PaymentService, Depends(get_payment_service)]


def get_webhook_service(request: Request) -> WebhookService:
    return cast(WebhookService, request.app.state.webhook_service)


WebhookServiceDependency = Annotated[WebhookService, Depends(get_webhook_service)]
