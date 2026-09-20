from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from ecommerce_store_payments.api.contracts.payment_response import PaymentResponse
from ecommerce_store_payments.api.dependencies import PaymentServiceDependency
from ecommerce_store_payments.application.payments.exceptions import (
    OrderNotFoundError,
    OrderNotPayableError,
    PaymentNotFoundError,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/{order_id}/pay",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="payOrder",
)
async def pay_order(order_id: UUID, payment_service: PaymentServiceDependency) -> PaymentResponse:
    try:
        payment = await payment_service.pay(order_id)
    except OrderNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except OrderNotPayableError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    return PaymentResponse.from_domain(payment)


@router.get(
    "/order/{order_id}",
    response_model=PaymentResponse,
    operation_id="getPaymentByOrderId",
)
async def get_payment_by_order_id(order_id: UUID, payment_service: PaymentServiceDependency) -> PaymentResponse:
    try:
        payment = await payment_service.get_by_order_id(order_id)
    except PaymentNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return PaymentResponse.from_domain(payment)
