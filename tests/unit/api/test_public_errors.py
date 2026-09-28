from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ecommerce_store_payments.application.payments.exceptions import (
    OrderNotFoundError,
    OrderNotPayableError,
    OrderTotalChangedError,
    PaymentNotFoundError,
)
from ecommerce_store_payments.application.payments.payment_service import PaymentService
from ecommerce_store_payments.domain.aggregates.payments.exceptions import PaymentTransitionError
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import (
    PaymentConflictError,
    PaymentMissingError,
)


class _BrokenService:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def pay(self, _order_id: UUID) -> None:
        raise self.error

    async def get_by_order_id(self, _order_id: UUID) -> None:
        raise self.error


def _check_problem(client: TestClient, path: str, status: int, code: str, method: str = "get") -> None:
    response = client.request(method, path)
    body = response.json()
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    assert body == {
        "type": "about:blank",
        "title": body["title"],
        "status": status,
        "detail": body["detail"],
        "code": code,
        "traceId": response.headers["x-trace-id"],
    }
    assert len(body["traceId"]) == 32
    assert "private" not in response.text


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (OrderNotFoundError(uuid4()), 404, "order_not_found"),
        (OrderNotPayableError(uuid4(), "private"), 409, "order_not_payable"),
        (OrderTotalChangedError(uuid4()), 409, "order_total_changed"),
        (PaymentConflictError(uuid4(), 1), 409, "payment_conflict"),
        (PaymentMissingError(uuid4()), 409, "payment_conflict"),
        (PaymentTransitionError("private", "Created"), 409, "invalid_payment_transition"),
        (RuntimeError("private database credentials"), 500, "internal_error"),
    ],
)
def test_pay_errors_have_safe_stable_contract(client: TestClient, error: Exception, status: int, code: str) -> None:
    app = cast(FastAPI, client.app)
    app.state.payment_service = cast(PaymentService, _BrokenService(error))
    _check_problem(client, f"/payments/{uuid4()}/pay", status, code, "post")


def test_get_missing_payment_has_distinct_code(client: TestClient) -> None:
    app = cast(FastAPI, client.app)
    app.state.payment_service = cast(PaymentService, _BrokenService(PaymentNotFoundError(uuid4())))
    _check_problem(client, f"/payments/order/{uuid4()}", 404, "payment_not_found")


def test_framework_and_validation_errors_are_sanitized(client: TestClient) -> None:
    _check_problem(client, "/not-a-route", 404, "route_not_found")
    _check_problem(client, "/health", 405, "method_not_allowed", "post")
    assert client.post("/health").headers["allow"] == "GET"
    _check_problem(client, "/payments/invalid-uuid/pay", 422, "invalid_request", "post")
    _check_problem(client, "/payments/order/invalid-uuid", 422, "invalid_request")


def test_problem_openapi_media_and_schema_match_http_contract(client: TestClient) -> None:
    app = cast(FastAPI, client.app)
    paths = app.openapi()["paths"]
    for path, method, statuses in (
        ("/payments/{order_id}/pay", "post", (404, 405, 409, 422, 500, 502, 504)),
        ("/payments/order/{order_id}", "get", (404, 405, 422, 500)),
        ("/health/ready", "get", (405, 500, 503)),
    ):
        responses = paths[path][method]["responses"]
        for status in statuses:
            media = responses[str(status)]["content"]
            assert set(media) == {"application/problem+json"}
            schema = media["application/problem+json"]["schema"]
            assert "traceId" in schema["properties"]
            assert {"title", "status", "detail", "code", "traceId"} <= set(schema["required"])


def test_success_response_receives_distinct_trace_ids(client: TestClient) -> None:
    first = client.get("/health")
    second = client.get("/health")
    assert first.headers["x-trace-id"] != second.headers["x-trace-id"]
    assert first.json() == {"status": "healthy"}
