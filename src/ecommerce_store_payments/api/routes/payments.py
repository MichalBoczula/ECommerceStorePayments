from uuid import UUID

from fastapi import APIRouter, Response, status

from ecommerce_store_payments.api.contracts.payment_response import PaymentResponse
from ecommerce_store_payments.api.dependencies import PaymentServiceDependency
from ecommerce_store_payments.api.errors import problem_responses

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/{order_id}/pay",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="payOrder",
    responses={
        200: {"model": PaymentResponse, "description": "Existing payment or renewed attempt"},
        **problem_responses(404, 405, 409, 422, 500, 502, 504),
    },
)
async def pay_order(order_id: UUID, payment_service: PaymentServiceDependency, response: Response) -> PaymentResponse:
    result = await payment_service.pay(order_id)

    response.status_code = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    return PaymentResponse.from_domain(result.payment)


@router.get(
    "/order/{order_id}",
    response_model=PaymentResponse,
    operation_id="getPaymentByOrderId",
    responses=problem_responses(404, 405, 422, 500),
)
async def get_payment_by_order_id(order_id: UUID, payment_service: PaymentServiceDependency) -> PaymentResponse:
    payment = await payment_service.get_by_order_id(order_id)
    return PaymentResponse.from_domain(payment)
