from uuid import UUID

from fastapi import APIRouter, Request, Response, status

from ecommerce_store_payments.api.contracts.checkout_response import CheckoutResponse
from ecommerce_store_payments.api.contracts.payment_response import PaymentResponse
from ecommerce_store_payments.api.dependencies import PaymentServiceDependency
from ecommerce_store_payments.api.errors import problem_responses, reject_pay_body

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/{order_id}/checkout",
    response_model=CheckoutResponse,
    operation_id="createOrderCheckout",
    responses=problem_responses(400, 404, 405, 409, 415, 500, 502, 503, 504),
)
async def create_order_checkout(
    order_id: UUID, payment_service: PaymentServiceDependency, request: Request
) -> CheckoutResponse:
    await reject_pay_body(request)
    result = await payment_service.checkout(order_id)
    return CheckoutResponse.from_result(result)


@router.post(
    "/{order_id}/pay",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="payOrder",
    responses={
        200: {"model": PaymentResponse, "description": "Existing payment or renewed attempt"},
        **problem_responses(400, 404, 405, 409, 415, 500, 502, 504),
    },
)
async def pay_order(
    order_id: UUID, payment_service: PaymentServiceDependency, response: Response, request: Request
) -> PaymentResponse:
    await reject_pay_body(request)
    result = await payment_service.pay(order_id)

    response.status_code = status.HTTP_201_CREATED if result.created else status.HTTP_200_OK
    return PaymentResponse.from_domain(result.payment)


@router.get(
    "/order/{order_id}",
    response_model=PaymentResponse,
    operation_id="getPaymentByOrderId",
    responses=problem_responses(400, 404, 405, 500),
)
async def get_payment_by_order_id(order_id: UUID, payment_service: PaymentServiceDependency) -> PaymentResponse:
    payment = await payment_service.get_by_order_id(order_id)
    return PaymentResponse.from_domain(payment)
