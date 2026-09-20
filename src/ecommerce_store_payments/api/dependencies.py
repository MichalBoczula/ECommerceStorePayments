from typing import Annotated, cast

from fastapi import Depends, Request

from ecommerce_store_payments.application.payments.payment_service import PaymentService


def get_payment_service(request: Request) -> PaymentService:
    return cast(PaymentService, request.app.state.payment_service)


PaymentServiceDependency = Annotated[PaymentService, Depends(get_payment_service)]
