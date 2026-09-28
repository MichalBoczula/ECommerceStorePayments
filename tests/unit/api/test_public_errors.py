from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from ecommerce_store_payments.application.payments.exceptions import (
    OrderNotFoundError,
    OrderNotPayableError,
    OrderTotalChangedError,
    PaymentNotFoundError,
)
from ecommerce_store_payments.application.payments.payment_service import PaymentService
from ecommerce_store_payments.domain.aggregates.payments.exceptions import (
    PaymentErrorCode,
    PaymentTransitionError,
    PaymentValidationError,
)
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
        "instance": path.split("?", 1)[0],
        "code": code,
        "traceId": response.headers["x-trace-id"],
        "errors": [],
        "missingProperties": [],
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
        (PaymentValidationError(PaymentErrorCode.INVALID_ORDER_ID, "private"), 400, "validation_failed"),
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
    _check_problem(client, "/payments/invalid-uuid/pay", 400, "invalid_request", "post")
    _check_problem(client, "/payments/order/invalid-uuid", 400, "invalid_request")


def test_pay_rejects_invalid_json_unsupported_media_type_and_unexpected_body(client: TestClient) -> None:
    path = f"/payments/{uuid4()}/pay"
    for content, content_type, status, code in (
        (b'{"secret":', "application/json", 400, "invalid_json"),
        (b"secret", "text/plain", 415, "unsupported_media_type"),
        (b'{"secret":"private"}', "application/json", 400, "invalid_request"),
    ):
        response = client.post(path, content=content, headers={"content-type": content_type})
        assert response.status_code == status
        assert response.headers["content-type"] == "application/problem+json"
        assert response.json()["code"] == code
        assert response.json()["instance"] == path
        assert "private" not in response.text
        assert "secret" not in response.text


def test_instance_omits_query_and_trace_header_is_not_reflected(client: TestClient) -> None:
    response = client.get("/not-a-route?secret=private", headers={"X-Trace-Id": "private"})
    assert response.json()["instance"] == "/not-a-route"
    assert response.json()["traceId"] == response.headers["x-trace-id"]
    assert "private" not in response.text
    assert response.headers["x-trace-id"] != "private"


def test_framework_json_validation_reports_only_required_contract_names(client: TestClient) -> None:
    class RequiredBody(BaseModel):
        order_id: UUID

    app = cast(FastAPI, client.app)

    @app.post("/test-required")
    async def required_body(_body: RequiredBody) -> None:
        pass

    response = client.post("/test-required", json={})
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_json"
    assert response.json()["missingProperties"] == ["order_id"]
    assert response.json()["errors"] == []


def test_problem_openapi_media_and_schema_match_http_contract(client: TestClient) -> None:
    app = cast(FastAPI, client.app)
    paths = app.openapi()["paths"]
    for path, method, statuses in (
        ("/payments/{order_id}/pay", "post", (400, 404, 405, 409, 415, 500, 502, 504)),
        ("/payments/order/{order_id}", "get", (400, 404, 405, 500)),
        ("/health/ready", "get", (405, 500, 503)),
    ):
        responses = paths[path][method]["responses"]
        for status in statuses:
            media = responses[str(status)]["content"]
            assert set(media) == {"application/problem+json"}
            schema = media["application/problem+json"]["schema"]
            assert "traceId" in schema["properties"]
            assert {"title", "status", "detail", "instance", "code", "traceId", "errors", "missingProperties"} <= set(
                schema["required"]
            )
            assert {"message", "name", "entity"} == set(schema["properties"]["errors"]["items"]["required"])
            assert "$defs" not in schema


def test_success_response_receives_distinct_trace_ids(client: TestClient) -> None:
    first = client.get("/health")
    second = client.get("/health")
    assert first.headers["x-trace-id"] != second.headers["x-trace-id"]
    assert first.json() == {"status": "healthy"}
