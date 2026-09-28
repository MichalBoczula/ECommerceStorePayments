import csv
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx2 import Response
from pymongo.errors import ServerSelectionTimeoutError
from pytest_bdd import given, parsers, scenarios, then, when

from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from tests.acceptance.conftest import AcceptanceContext

scenarios("features/payments.feature", "features/health.feature")

MATRIX_PATH = Path(__file__).resolve().parents[2] / "docs" / "acceptance-matrix.tsv"
FEATURES_PATH = Path(__file__).resolve().parent / "features"
OPERATION_PAY = "POST /payments/{order_id}/pay"
OPERATION_GET = "GET /payments/order/{order_id}"


def _matrix() -> dict[str, dict[str, str]]:
    with MATRIX_PATH.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source, delimiter="\t"))
    assert all(row.keys() == {"id", "operation", "cause", "status", "code", "requirement"} for row in rows)
    assert len(rows) == len({row["id"] for row in rows})
    return {row["id"]: row for row in rows}


def test_every_matrix_case_has_one_source_scenario_and_expected_result_step() -> None:
    sources = "\n".join(path.read_text(encoding="utf-8") for path in FEATURES_PATH.glob("*.feature"))
    scenario_ids = re.findall(r"^\s*Scenario:\s+(PAY\d+-\d+)\b", sources, re.MULTILINE)
    step_ids = re.findall(r'^\s*Then the response matches case "(PAY\d+-\d+)"', sources, re.MULTILINE)
    assert len(scenario_ids) == len(set(scenario_ids))
    assert sorted(scenario_ids) == sorted(step_ids) == sorted(_matrix())


@given("a payable order")
def payable_order(acceptance: AcceptanceContext) -> None:
    assert acceptance.orders.status == "Created"


@given(parsers.parse('Orders returns "{mode}"'))
def orders_failure(acceptance: AcceptanceContext, mode: str) -> None:
    acceptance.orders.mode = mode


@given(parsers.parse('Orders reports status "{status}"'))
def orders_status(acceptance: AcceptanceContext, status: str) -> None:
    acceptance.orders.status = status


@given("a payment created through the API")
def existing_payment(acceptance: AcceptanceContext) -> None:
    acceptance.send("POST", f"/payments/{acceptance.orders.order_id}/pay")
    initial = acceptance.responses[0]
    assert initial.status_code == 201
    acceptance.initial_payment_id = UUID(initial.json()["id"])
    acceptance.initial_orders_calls = acceptance.orders.calls


@given(parsers.parse('a "{status}" payment created through the API'))
def terminal_payment(acceptance: AcceptanceContext, status: str) -> None:
    existing_payment(acceptance)
    acceptance.make_terminal(PaymentStatus(status.casefold()))


@given("Orders total has changed")
def changed_total(acceptance: AcceptanceContext) -> None:
    acceptance.orders.amount = 14.99


@given("the MongoDB readiness probe fails")
def readiness_unavailable(acceptance: AcceptanceContext, monkeypatch: pytest.MonkeyPatch) -> None:
    app = cast(FastAPI, acceptance.client.app)
    database = cast(MongoDatabase, app.state.database)

    async def unavailable() -> None:
        raise ServerSelectionTimeoutError("private MongoDB connection")

    monkeypatch.setattr(database, "probe", unavailable)


@when("I pay the order")
def pay(acceptance: AcceptanceContext) -> None:
    acceptance.send("POST", f"/payments/{acceptance.orders.order_id}/pay")


@when("I get the payment by order ID")
def get_by_order(acceptance: AcceptanceContext) -> None:
    acceptance.send("GET", f"/payments/order/{acceptance.orders.order_id}")


@when("I submit two Pay requests concurrently")
def concurrent_pay(acceptance: AcceptanceContext) -> None:
    path = f"/payments/{acceptance.orders.order_id}/pay"
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(acceptance.client.post, path)
        second = executor.submit(acceptance.client.post, path)
        acceptance.responses = [first.result(), second.result()]
    acceptance.last_operation = f"{OPERATION_PAY} x2"


@when("I pay with an invalid order ID")
def invalid_id(acceptance: AcceptanceContext) -> None:
    acceptance.send("POST", "/payments/invalid-uuid/pay")


@when("I pay with malformed JSON")
def malformed_json(acceptance: AcceptanceContext) -> None:
    acceptance.send(
        "POST", f"/payments/{acceptance.orders.order_id}/pay", content=b'{"private":', content_type="application/json"
    )


@when("I pay with plain text")
def unsupported_media(acceptance: AcceptanceContext) -> None:
    acceptance.send(
        "POST", f"/payments/{acceptance.orders.order_id}/pay", content=b"private", content_type="text/plain"
    )


@when("I request an unknown route")
def unknown_route(acceptance: AcceptanceContext) -> None:
    acceptance.send("GET", "/unknown-route")


@when("I post to a read-only health route")
def wrong_method(acceptance: AcceptanceContext) -> None:
    acceptance.send("POST", "/health/live")


@when(parsers.parse('I get "{path}"'))
def get_health(acceptance: AcceptanceContext, path: str) -> None:
    acceptance.send("GET", path)


@then(parsers.parse('the response matches case "{case_id}"'))
def matches_matrix(acceptance: AcceptanceContext, case_id: str) -> None:
    expected = _matrix()[case_id]
    assert acceptance.last_operation == expected["operation"]
    assert sorted(response.status_code for response in acceptance.responses) == sorted(
        int(code) for code in expected["status"].split(",")
    )
    for response in acceptance.responses:
        assert response.headers["x-trace-id"]
        if response.status_code < 400:
            assert expected["code"] == "-"
            assert response.headers["content-type"] == "application/json"
        else:
            assert response.headers["content-type"] == "application/problem+json"
            body = response.json()
            assert body["code"] == expected["code"]
            assert body["status"] == response.status_code
            assert body["instance"] == response.request.url.path
            assert body["traceId"] == response.headers["x-trace-id"]
            assert set(body) == {
                "type",
                "title",
                "status",
                "detail",
                "instance",
                "code",
                "traceId",
                "errors",
                "missingProperties",
            }
            assert "private" not in body["detail"]


@then(parsers.parse("the database has {current:d} current payment and {history:d} history snapshots"))
@then(parsers.parse("the database has {current:d} current payments and {history:d} history snapshots"))
def persisted_counts(acceptance: AcceptanceContext, current: int, history: int) -> None:
    assert acceptance.payments.count_documents({}) == current
    assert acceptance.history.count_documents({}) == history


@then(parsers.parse('the current payment is "{status}" at version {version:d}'))
def current_state(acceptance: AcceptanceContext, status: str, version: int) -> None:
    document = acceptance.payments.find_one({"order_id": acceptance.orders.order_id})
    assert document is not None
    assert document["status"] == status.casefold()
    assert document["version"] == version


@then("the response refers to the original payment")
def same_payment(acceptance: AcceptanceContext) -> None:
    assert acceptance.initial_payment_id is not None
    assert acceptance.responses[0].json()["id"] == str(acceptance.initial_payment_id)


@then("both responses refer to one payment")
def concurrent_identity(acceptance: AcceptanceContext) -> None:
    assert len({response.json()["id"] for response in acceptance.responses}) == 1


@then("Orders was not called again")
def no_new_orders_call(acceptance: AcceptanceContext) -> None:
    assert acceptance.orders.calls == acceptance.initial_orders_calls


@then(parsers.parse('the history statuses are "{statuses}"'))
def history_statuses(acceptance: AcceptanceContext, statuses: str) -> None:
    assert acceptance.initial_payment_id is not None
    snapshots = acceptance.history.find({"payment_id": acceptance.initial_payment_id}).sort("version", 1)
    assert [snapshot["status"] for snapshot in snapshots] == [status.casefold() for status in statuses.split(",")]


@then(parsers.parse('the Allow header is "{allowed}"'))
def allow_header(acceptance: AcceptanceContext, allowed: str) -> None:
    assert acceptance.responses[0].headers["allow"] == allowed


@then("the error hides the database failure")
def no_secret(acceptance: AcceptanceContext) -> None:
    assert "private MongoDB connection" not in acceptance.responses[0].text


@then("liveness is still healthy")
def liveness_after_failure(acceptance: AcceptanceContext) -> None:
    response: Response = acceptance.client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
