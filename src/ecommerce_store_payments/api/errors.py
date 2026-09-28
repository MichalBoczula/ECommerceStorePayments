import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from ecommerce_store_payments.application.payments.exceptions import (
    OrderInvalidResponseError,
    OrderNotFoundError,
    OrderNotPayableError,
    OrderTimeoutError,
    OrderTotalChangedError,
    OrderUnavailableError,
    PaymentNotFoundError,
)
from ecommerce_store_payments.domain.aggregates.payments.exceptions import PaymentTransitionError
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import (
    PaymentConflictError,
    PaymentDuplicateError,
    PaymentMissingError,
)

logger = logging.getLogger(__name__)
PROBLEM_MEDIA_TYPE = "application/problem+json"
TRACE_HEADER = "X-Trace-Id"


class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    code: str
    trace_id: str = Field(alias="traceId")


@dataclass(frozen=True, slots=True)
class ErrorSpec:
    status: int
    code: str
    detail: str


class ReadinessUnavailableError(Exception):
    """MongoDB is unavailable for a readiness probe."""


ERRORS: tuple[tuple[type[Exception], ErrorSpec], ...] = (
    (OrderNotFoundError, ErrorSpec(404, "order_not_found", "Order was not found.")),
    (PaymentNotFoundError, ErrorSpec(404, "payment_not_found", "Payment was not found.")),
    (OrderNotPayableError, ErrorSpec(409, "order_not_payable", "Order cannot be paid in its current state.")),
    (OrderTotalChangedError, ErrorSpec(409, "order_total_changed", "Order total has changed.")),
    (PaymentDuplicateError, ErrorSpec(409, "payment_duplicate", "A payment already exists for this order.")),
    (PaymentConflictError, ErrorSpec(409, "payment_conflict", "Payment has changed; retry the request.")),
    (PaymentMissingError, ErrorSpec(409, "payment_conflict", "Payment has changed; retry the request.")),
    (PaymentTransitionError, ErrorSpec(409, "invalid_payment_transition", "Payment transition is not allowed.")),
    (OrderTimeoutError, ErrorSpec(504, "order_timeout", "Orders service timed out.")),
    (OrderUnavailableError, ErrorSpec(502, "order_unavailable", "Orders service is unavailable.")),
    (
        OrderInvalidResponseError,
        ErrorSpec(502, "order_invalid_response", "Orders service returned an invalid response."),
    ),
    (ReadinessUnavailableError, ErrorSpec(503, "service_unavailable", "Payment service is not ready.")),
)

INTERNAL_ERROR = ErrorSpec(500, "internal_error", "An unexpected error occurred.")
INVALID_REQUEST = ErrorSpec(422, "invalid_request", "Request validation failed.")


def problem_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    schema = ProblemDetails.model_json_schema(by_alias=True)
    return {
        status: {
            "description": f"{HTTPStatus(status).phrase}; see the stable code in the problem body.",
            "content": {PROBLEM_MEDIA_TYPE: {"schema": schema}},
        }
        for status in statuses
    }


def _problem(request: Request, spec: ErrorSpec, headers: Mapping[str, str] | None = None) -> JSONResponse:
    trace_id: str = request.state.trace_id
    body = ProblemDetails(
        title=HTTPStatus(spec.status).phrase,
        status=spec.status,
        detail=spec.detail,
        code=spec.code,
        traceId=trace_id,
    )
    return JSONResponse(
        status_code=spec.status,
        content=body.model_dump(by_alias=True),
        media_type=PROBLEM_MEDIA_TYPE,
        headers={**(headers or {}), TRACE_HEADER: trace_id},
    )


def _known_error(error: Exception) -> ErrorSpec | None:
    for error_type, spec in ERRORS:
        if isinstance(error, error_type):
            return spec
    return None


def install_error_handlers(app: FastAPI) -> None:
    @app.middleware("http")
    async def trace_and_catch(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request.state.trace_id = uuid4().hex
        try:
            response = await call_next(request)
        except Exception as error:
            spec = _known_error(error)
            if spec is None:
                logger.exception("Unhandled request failure trace_id=%s", request.state.trace_id)
                spec = INTERNAL_ERROR
            return _problem(request, spec)
        response.headers[TRACE_HEADER] = request.state.trace_id
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, _error: RequestValidationError) -> JSONResponse:
        return _problem(request, INVALID_REQUEST)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, error: StarletteHTTPException) -> JSONResponse:
        if error.status_code == 404:
            spec = ErrorSpec(404, "route_not_found", "Route was not found.")
        elif error.status_code == 405:
            spec = ErrorSpec(405, "method_not_allowed", "Method is not allowed for this route.")
        else:
            spec = ErrorSpec(error.status_code, "http_error", "Request could not be processed.")
        return _problem(request, spec, headers=error.headers)
