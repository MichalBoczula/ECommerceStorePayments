import json
import logging
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from http import HTTPStatus
from json import JSONDecodeError
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
from ecommerce_store_payments.domain.aggregates.payments.exceptions import (
    MoneyValidationError,
    PaymentTransitionError,
    PaymentValidationError,
)
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import (
    PaymentConflictError,
    PaymentDuplicateError,
    PaymentMissingError,
)

logger = logging.getLogger(__name__)
PROBLEM_MEDIA_TYPE = "application/problem+json"
TRACE_HEADER = "X-Trace-Id"


class ValidationEntry(BaseModel):
    message: str
    name: str
    entity: str


class ProblemDetails(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str
    code: str
    trace_id: str = Field(alias="traceId")
    errors: list[ValidationEntry]
    missing_properties: list[str] = Field(alias="missingProperties")


@dataclass(frozen=True, slots=True)
class ErrorSpec:
    status: int
    code: str
    detail: str


class ReadinessUnavailableError(Exception):
    """MongoDB is unavailable for a readiness probe."""


class ApiRequestError(Exception):
    def __init__(self, spec: ErrorSpec) -> None:
        self.spec = spec
        super().__init__(spec.code)


ERRORS: tuple[tuple[type[Exception], ErrorSpec], ...] = (
    (OrderNotFoundError, ErrorSpec(404, "order_not_found", "Order was not found.")),
    (PaymentNotFoundError, ErrorSpec(404, "payment_not_found", "Payment was not found.")),
    (OrderNotPayableError, ErrorSpec(409, "order_not_payable", "Order cannot be paid in its current state.")),
    (OrderTotalChangedError, ErrorSpec(409, "order_total_changed", "Order total has changed.")),
    (PaymentDuplicateError, ErrorSpec(409, "payment_duplicate", "A payment already exists for this order.")),
    (PaymentConflictError, ErrorSpec(409, "payment_conflict", "Payment has changed; retry the request.")),
    (PaymentMissingError, ErrorSpec(409, "payment_conflict", "Payment has changed; retry the request.")),
    (PaymentTransitionError, ErrorSpec(409, "invalid_payment_transition", "Payment transition is not allowed.")),
    (MoneyValidationError, ErrorSpec(400, "validation_failed", "One or more validation errors occurred.")),
    (PaymentValidationError, ErrorSpec(400, "validation_failed", "One or more validation errors occurred.")),
    (OrderTimeoutError, ErrorSpec(504, "order_timeout", "Orders service timed out.")),
    (OrderUnavailableError, ErrorSpec(502, "order_unavailable", "Orders service is unavailable.")),
    (
        OrderInvalidResponseError,
        ErrorSpec(502, "order_invalid_response", "Orders service returned an invalid response."),
    ),
    (ReadinessUnavailableError, ErrorSpec(503, "service_unavailable", "Payment service is not ready.")),
)

INTERNAL_ERROR = ErrorSpec(500, "internal_error", "An unexpected error occurred.")
INVALID_REQUEST = ErrorSpec(400, "invalid_request", "Request validation failed.")
INVALID_JSON = ErrorSpec(400, "invalid_json", "The request body is not valid JSON.")
UNSUPPORTED_MEDIA_TYPE = ErrorSpec(415, "unsupported_media_type", "The request content type is not supported.")


def problem_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    schema = ProblemDetails.model_json_schema(by_alias=True)
    return {
        status: {
            "description": f"{HTTPStatus(status).phrase}; see the stable code in the problem body.",
            "content": {PROBLEM_MEDIA_TYPE: {"schema": schema}},
        }
        for status in statuses
    }


def _problem(
    request: Request,
    spec: ErrorSpec,
    headers: Mapping[str, str] | None = None,
    missing_properties: list[str] | None = None,
) -> JSONResponse:
    trace_id: str = request.state.trace_id
    body = ProblemDetails(
        title=HTTPStatus(spec.status).phrase,
        status=spec.status,
        detail=spec.detail,
        instance=request.url.path,
        code=spec.code,
        traceId=trace_id,
        errors=[],
        missingProperties=missing_properties or [],
    )
    return JSONResponse(
        status_code=spec.status,
        content=body.model_dump(by_alias=True),
        media_type=PROBLEM_MEDIA_TYPE,
        headers={**(headers or {}), TRACE_HEADER: trace_id},
    )


def _known_error(error: Exception) -> ErrorSpec | None:
    if isinstance(error, ApiRequestError):
        return error.spec
    for error_type, spec in ERRORS:
        if isinstance(error, error_type):
            return spec
    return None


async def reject_pay_body(request: Request) -> None:
    """Pay takes its order ID from the path and has no JSON request contract."""
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 64 * 1024:
            raise ApiRequestError(INVALID_REQUEST)
        body.extend(chunk)
    if not body:
        return
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json" and not content_type.endswith("+json"):
        raise ApiRequestError(UNSUPPORTED_MEDIA_TYPE)
    try:
        json.loads(body)
    except (JSONDecodeError, UnicodeDecodeError) as error:
        raise ApiRequestError(INVALID_JSON) from error
    raise ApiRequestError(INVALID_REQUEST)


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
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        issues = error.errors()
        if any(issue["type"] == "json_invalid" for issue in issues):
            return _problem(request, INVALID_JSON)
        missing = [
            str(issue["loc"][-1])
            for issue in issues
            if issue["type"] == "missing"
            and len(issue["loc"]) > 1
            and issue["loc"][0] == "body"
            and isinstance(issue["loc"][-1], str)
        ]
        if missing:
            return _problem(request, INVALID_JSON, missing_properties=sorted(set(missing)))
        return _problem(request, INVALID_REQUEST)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, error: StarletteHTTPException) -> JSONResponse:
        if error.status_code == 404:
            spec = ErrorSpec(404, "route_not_found", "Route was not found.")
        elif error.status_code == 405:
            spec = ErrorSpec(405, "method_not_allowed", "Method is not allowed for this route.")
        elif error.status_code == 415:
            spec = UNSUPPORTED_MEDIA_TYPE
        else:
            spec = ErrorSpec(error.status_code, "http_error", "Request could not be processed.")
        return _problem(request, spec, headers=error.headers)
