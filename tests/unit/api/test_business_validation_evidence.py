"""Challenge business evidence with changed problems, wire tokens and populated state."""

import json
from copy import deepcopy
from decimal import Decimal
from functools import lru_cache
from types import SimpleNamespace
from typing import Any, cast

import pytest
from httpx import Request, Response
from pytest_bdd.parser import FeatureParser
from scripts.bdd_evidence import source_evidence
from scripts.generate_operation_links import FEATURES

from tests.acceptance.business_validation_checks import BusinessValidationChecks, contract_body, safe_problem
from tests.acceptance.evidence import ScenarioEvidence, content_evidence, table_values
from tests.acceptance.payment_checks import PaymentChecks

ORDER = "11111111-1111-4111-8111-111111111111"
PATH = f"/payments/{ORDER}/pay"


def contract() -> dict[str, str]:
    return dict(
        TotalAmountToken="90071992547409.91",
        CurrencyToken='"USD"',
        LineAmountTokens='["90071992547409.91"]',
        LineCurrencyToken='"USD"',
        StatusToken='"Created"',
        OrderIdToken=json.dumps(ORDER),
    )


@lru_cache(maxsize=1)
def expected_problem() -> dict[str, str]:
    return source_evidence(FEATURES)["PAY10-16"]["expected"]


def problem() -> tuple[dict[str, Any], dict[str, str]]:
    authored = expected_problem()
    body = {k.removeprefix("JSON."): json.loads(v) for k, v in authored.items() if k.startswith("JSON.")}
    body.update(code=authored["Code"], traceId="a" * 32)
    return body, authored


def response(body: dict[str, Any], trace: str | None = None) -> Response:
    return Response(
        502,
        json=body,
        headers={"content-type": "application/problem+json", "x-trace-id": trace or body["traceId"]},
        request=Request("POST", PATH),
        extensions={"payments.bdd.exchangeId": "fixture/1"},
    )


@pytest.mark.parametrize(
    "field", ["type", "title", "status", "detail", "instance", "code", "traceId", "errors", "missingProperties"]
)
def test_safe_problem_requires_every_authored_field(field: str) -> None:
    body, authored = problem()
    safe_problem(response(body), authored)
    body[field] = "corrupt"
    with pytest.raises(AssertionError):
        safe_problem(response(body), authored)


@pytest.mark.parametrize(
    "mutation", ["missing", "extra", "trace_header", "empty_trace", "trace_not_hex", "wrong_media", "wrong_status"]
)
def test_safe_problem_rejects_presence_trace_and_transport_drift(mutation: str) -> None:
    body, authored = problem()
    reply = response(body)
    if mutation == "missing":
        del body["errors"]
        reply = response(body)
    elif mutation == "extra":
        body["debug"] = "private"
        reply = response(body)
    elif mutation == "trace_header":
        reply = response(body, "b" * 32)
    elif mutation == "empty_trace":
        body["traceId"] = ""
        reply = response(body)
    elif mutation == "trace_not_hex":
        body["traceId"] = "x" * 32
        reply = response(body)
    elif mutation == "wrong_media":
        reply.headers["content-type"] = "application/json"
    else:
        reply.status_code = 400
    with pytest.raises(AssertionError):
        safe_problem(reply, authored)


def test_authored_decimal_tokens_reach_the_wire_without_float_rounding() -> None:
    values = contract()
    wire = contract_body(values)
    parsed = json.loads(wire, parse_float=Decimal)
    assert b"90071992547409.91" in wire and b'"totalAmount":90071992547409.91' in wire
    assert parsed["totalAmount"] == parsed["lines"][0]["lineTotalAmount"] == Decimal("90071992547409.91")
    values["TotalAmountToken"] = "1.23e1"
    assert b'"totalAmount":1.23e1' in contract_body(values)
    values["TotalAmountToken"] = "<absent>"
    assert "totalAmount" not in json.loads(contract_body(values))


@pytest.mark.parametrize(
    "mutation", ["missing", "extra", "array_not_list", "numeric_token_not_string", "invalid_total_token"]
)
def test_authored_contract_rejects_ambiguous_or_incomplete_fixture_inputs(mutation: str) -> None:
    values = contract()
    if mutation == "missing":
        del values["CurrencyToken"]
    elif mutation == "extra":
        values["debug"] = "hidden"
    elif mutation == "array_not_list":
        values["LineAmountTokens"] = "null"
    elif mutation == "numeric_token_not_string":
        values["LineAmountTokens"] = "[12.99]"
    else:
        values["TotalAmountToken"] = "bad"
    with pytest.raises((AssertionError, ValueError)):
        contract_body(values)


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_non_json_numeric_constants_are_captured_as_invalid_json_with_exact_bytes(token: str) -> None:
    wire = ('{"totalAmount":' + token + "}").encode()
    captured = content_evidence(wire, "application/json")
    assert captured["bodyFormat"] == "invalid-json" and captured["body"] == captured["rawBody"] == wire.decode()
    json.dumps(captured, allow_nan=False)


@pytest.mark.parametrize(
    "mutation",
    [
        "current_changed",
        "history_changed",
        "receipt_changed",
        "added",
        "removed",
        "orders_extra",
        "stripe_extra",
        "session_changed",
        "repeat_changes_state",
        "none",
    ],
)
def test_business_rejection_detects_changes_in_every_populated_collection_and_dependency(mutation: str) -> None:
    body, authored = problem()
    before = {name: [{"_id": name, "value": 1}] for name in ["payments", "payment_history", "stripe_webhooks"]}
    current = deepcopy(before)
    ops = [("GET", f"/orders/{ORDER}")]
    stripe_calls: list[object] = []
    sessions = {"prior": {"id": "cs_prior"}}
    if mutation.endswith("_changed") and mutation != "session_changed":
        current[
            {"current_changed": "payments", "history_changed": "payment_history", "receipt_changed": "stripe_webhooks"}[
                mutation
            ]
        ][0]["value"] = 2
    elif mutation == "added":
        current["payments"].append({"_id": "extra", "value": 1})
    elif mutation == "removed":
        current["payment_history"] = []
    elif mutation == "orders_extra":
        ops.append(("GET", f"/orders/{ORDER}"))
    elif mutation == "stripe_extra":
        stripe_calls.append(object())
    elif mutation == "session_changed":
        sessions["prior"]["id"] = "cs_replaced"

    def post(path: str) -> Response:
        assert path == PATH
        ops.append(("GET", f"/orders/{ORDER}"))
        if mutation == "repeat_changes_state":
            current["payments"][0]["value"] = 2
        return response({**body, "traceId": "b" * 32})

    context = SimpleNamespace(
        responses=[response(body)],
        orders=SimpleNamespace(order_id=ORDER, http_calls=ops),
        stripe=SimpleNamespace(calls=stripe_calls, sessions=sessions),
        client=SimpleNamespace(post=post),
        evidence=ScenarioEvidence("PAY10-16", "Guard", "PAY10-16 Guard", {}),
    )

    def missing_target(_: object) -> None:
        return None

    checks = cast(
        PaymentChecks, SimpleNamespace(context=context, snapshot=lambda: deepcopy(current), target=missing_target)
    )
    guard = BusinessValidationChecks(checks)
    guard.before = before
    guard.sessions = {"prior": {"id": "cs_prior"}}
    values = dict(OrdersReads="1", StripeCalls="0", TargetPayment="absent", Collections="unchanged", Repeat="true")
    if mutation == "none":
        guard.rejection(values, authored)
        return
    with pytest.raises(AssertionError):
        guard.rejection(
            values,
            authored,
        )


def test_every_business_case_has_executed_contract_complete_outcome_and_isolation_tables() -> None:
    feature = FeatureParser(str(FEATURES), "business_validation.feature").parse()
    profiles = source_evidence(FEATURES)
    assert len(feature.scenarios) == 56
    for scenario in feature.scenarios.values():
        cid = scenario.name.split()[0]
        steps = {s.name: s for s in scenario.steps}
        assert "an unrelated succeeded payment fills all collections" in steps
        assert "I remember complete business validation state" in steps
        assert "Orders exposes this business contract" in steps
        expected = profiles[cid]["expected"]
        if expected["Code"] == "-":
            assert "the accepted business boundary remains stable" in steps
            full_step = (
                "the complete checkout response is"
                if "I create checkout for the order" in steps
                else "the complete payment response is"
            )
            assert full_step in steps and steps[full_step].type == "then"
        else:
            step = steps["business rejection preserves populated state on both requests"]
            assert step.type == "then" and step.datatable is not None
            assert table_values([[c.value for c in row.cells] for row in step.datatable.rows]) == dict(
                OrdersReads="1", StripeCalls="0", TargetPayment="absent", Collections="unchanged", Repeat="true"
            )
            assert {
                f"JSON.{key}"
                for key in ["type", "title", "status", "detail", "instance", "errors", "missingProperties"]
            } <= expected.keys()
