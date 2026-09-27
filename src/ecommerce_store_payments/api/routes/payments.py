from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from ecommerce_store_payments.api.contracts.payment_response import PaymentResponse
from ecommerce_store_payments.api.dependencies import PaymentServiceDependency
from ecommerce_store_payments.application.payments.exceptions import (
    OrderInvalidResponseError,
    OrderNotFoundError,
    OrderNotPayableError,
    OrderTimeoutError,
    OrderTotalChangedError,
    OrderUnavailableError,
    PaymentNotFoundError,
)
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import (
    PaymentConflictError,
    PaymentDuplicateError,
    PaymentMissingError,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/{order_id}/pay",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="payOrder",
    responses={
        200: {"model": PaymentResponse, "description": "Existing payment or renewed attempt"},
        409: {"description": "Order or payment state conflict"},
        502: {"description": "Invalid response or failure from Orders"},
        504: {"description": "Orders timed out"},
    },
)
async def pay_order(order_id: UUID, payment_service: PaymentServiceDependency, response: Response) -> PaymentResponse:
    try:
        result = await payment_service.pay(order_id)
    except OrderNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except (OrderNotPayableError, OrderTotalChangedError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except OrderTimeoutError as error:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(error)) from error
    except (OrderUnavailableError, OrderInvalidResponseError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    except (PaymentDuplicateError, PaymentConflictError, PaymentMissingError) as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    response.status_code = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    return PaymentResponse.from_domain(result.payment)


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
