"""Negative guards for framework wire evidence, protocol and complete populated state."""

import json
from copy import deepcopy
from functools import lru_cache
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest
from httpx2 import Request, Response
from pytest_bdd.parser import FeatureParser
from scripts.bdd_evidence import source_evidence
from scripts.generate_operation_links import FEATURES

from tests.acceptance.evidence import ScenarioEvidence, content_evidence, table_values
from tests.acceptance.framework_checks import FrameworkChecks, framework_protocol, request_body
from tests.acceptance.payment_checks import PaymentChecks
from tests.webhook_fixtures import signature

ORDER = UUID("11111111-1111-4111-8111-111111111111")


def inputs() -> dict[str, str]:
    return dict(
        Method="POST",
        Path="/health",
        BodyKind="none",
        BodyValue="<empty>",
        ContentType="<absent>",
        TraceHeader="1" * 32,
        Signature="absent",
    )


@lru_cache(maxsize=1)
def expectation() -> dict[str, str]:
    return source_evidence(FEATURES)["PAY11-23"]["expected"]


def problem(trace: str = "a" * 32) -> dict[str, Any]:
    result = {k.removeprefix("JSON."): json.loads(v) for k, v in expectation().items() if k.startswith("JSON.")}
    return {**result, "code": "method_not_allowed", "traceId": trace}


def response(trace: str = "a" * 32, *, request: Request | None = None) -> Response:
    return Response(
        405,
        json=problem(trace),
        headers={"content-type": "application/problem+json", "allow": "GET", "x-trace-id": trace},
        request=request or Request("POST", "http://testserver/health", headers={"x-trace-id": "1" * 32}),
        extensions={"payments.bdd.exchangeId": trace},
    )


@pytest.mark.parametrize("field", sorted(inputs()))
def test_missing_authored_request_fields_are_rejected(field: str) -> None:
    values = inputs()
    del values[field]
    with pytest.raises(AssertionError):
        request_body(values)


@pytest.mark.parametrize(
    "mutation",
    [
        "extra",
        "method",
        "absolute",
        "network_path",
        "none_value",
        "hex",
        "repeat_boolean",
        "repeat_too_large",
        "repeat_multibyte",
        "padding_below",
        "padding_above",
        "unknown_kind",
    ],
)
def test_malformed_or_unbounded_authored_wire_inputs_are_rejected(mutation: str) -> None:
    values = inputs()
    if mutation == "extra":
        values["Debug"] = "hidden"
    elif mutation == "method":
        values["Method"] = "TRACE"
    elif mutation == "absolute":
        values["Path"] = "https://foreign.example/"
    elif mutation == "network_path":
        values["Path"] = "//foreign.example/"
    elif mutation == "none_value":
        values["BodyValue"] = "not-empty"
    elif mutation == "hex":
        values.update(BodyKind="hex", BodyValue="xyz")
    elif mutation.startswith("repeat_"):
        values.update(
            BodyKind="repeat",
            BodyValue=json.dumps(
                {
                    "Token": "ł" if mutation == "repeat_multibyte" else "{",
                    "Count": True if mutation == "repeat_boolean" else 65538 if mutation == "repeat_too_large" else 1,
                }
            ),
        )
    elif mutation.startswith("padding_"):
        values.update(BodyKind="json-padding", BodyValue="1" if mutation == "padding_below" else "65538")
    else:
        values["BodyKind"] = "guess"
    with pytest.raises((AssertionError, ValueError)):
        request_body(values)


@pytest.mark.parametrize(
    ("kind", "value", "size"),
    [
        ("none", "<empty>", 0),
        ("empty", "<empty>", 0),
        ("hex", "ff", 1),
        ("text", '"żółć"', 10),
        ("repeat", '{"Token":"{","Count":65537}', 65537),
        ("json-padding", "65536", 65536),
    ],
)
def test_authored_request_bytes_preserve_encoding_presence_and_limits(kind: str, value: str, size: int) -> None:
    values = {**inputs(), "BodyKind": kind, "BodyValue": value}
    body = request_body(values)
    assert len(body or b"") == size
    if kind == "none":
        assert body is None
    if kind == "empty":
        assert body == b""
    if kind == "json-padding":
        assert body is not None
        assert len(json.loads(body)) == 65534


@pytest.mark.parametrize("body", [b"1e999", b"-1e999", b'{"value":1e999}', b"[1e999]"])
def test_valid_overflowing_json_numbers_keep_valid_text_and_an_encodable_evidence_envelope(body: bytes) -> None:
    record = content_evidence(body, "application/json")
    assert record["bodyFormat"] == "json-number-text" and record["body"] == record["rawBody"] == body.decode()
    json.dumps(record, allow_nan=False)


def test_overflow_does_not_hide_malformed_json_or_non_json_constants() -> None:
    for body in [b"1e999 trailing", b'{"value":NaN}', b"Infinity"]:
        record = content_evidence(body, "application/json")
        assert record["bodyFormat"] == "invalid-json"
        json.dumps(record, allow_nan=False)


@pytest.mark.parametrize(
    "mutation", ["missing_allow", "wrong_allow", "unexpected_allow", "reflected_trace", "content_length"]
)
def test_protocol_guard_rejects_header_and_trace_drift(mutation: str) -> None:
    reply = response()
    framework_protocol(reply, expectation(), "GET")
    allow = "GET"
    if mutation == "missing_allow":
        del reply.headers["allow"]
    elif mutation == "wrong_allow":
        reply.headers["allow"] = "POST"
    elif mutation == "unexpected_allow":
        allow = "<absent>"
    elif mutation == "reflected_trace":
        reply = response("1" * 32)
    else:
        reply.headers["content-length"] = "1"
    with pytest.raises(AssertionError):
        framework_protocol(reply, expectation(), allow)


@pytest.mark.parametrize(
    "mutation", ["method", "path", "query", "body", "media", "trace", "missing_signature", "forged_signature"]
)
def test_wire_guard_requires_every_authored_request_input_and_real_signature(mutation: str) -> None:
    context = SimpleNamespace(orders=SimpleNamespace(order_id=ORDER))
    checks = FrameworkChecks(cast(PaymentChecks, SimpleNamespace(context=context)))
    values = inputs()
    checks.inputs = values
    checks.body = None
    if mutation in {"missing_signature", "forged_signature"}:
        values["Signature"] = "valid"
    method = "GET" if mutation == "method" else "POST"
    path = "/wrong" if mutation == "path" else "/health"
    if mutation == "query":
        path += "?private=unexpected"
    headers = {"x-trace-id": "2" * 32 if mutation == "trace" else "1" * 32}
    if mutation == "media":
        headers["content-type"] = "application/json"
    if mutation == "forged_signature":
        headers["stripe-signature"] = "t=1,v1=bad"
    reply = response(
        request=Request(
            method, "http://testserver" + path, headers=headers, content=b"{}" if mutation == "body" else None
        )
    )
    with pytest.raises(AssertionError):
        checks.wire(cast(Any, reply))


def test_wire_guard_accepts_exact_signed_bytes() -> None:
    context = SimpleNamespace(orders=SimpleNamespace(order_id=ORDER))
    checks = FrameworkChecks(cast(PaymentChecks, SimpleNamespace(context=context)))
    checks.inputs = {
        **inputs(),
        "Signature": "valid",
        "BodyKind": "text",
        "BodyValue": "null",
        "ContentType": "application/json",
    }
    checks.body = b"null"
    reply = response(
        request=Request(
            "POST",
            "http://testserver/health",
            headers={
                "stripe-signature": signature(b"null"),
                "x-trace-id": "1" * 32,
                "content-type": "application/json",
            },
            content=b"null",
        )
    )
    checks.wire(cast(Any, reply))


@pytest.mark.parametrize(
    "mutation",
    [
        "current",
        "history",
        "receipt",
        "added",
        "removed",
        "orders",
        "stripe",
        "sessions",
        "repeat_changes_state",
        "none",
    ],
)
def test_repeated_framework_guard_rejects_changes_to_all_populated_collections_and_dependencies(mutation: str) -> None:
    before = {
        "payments": [
            {"_id": "main", "order_id": ORDER, "status": "pending", "version": 2},
            {"_id": "other", "status": "succeeded"},
        ],
        "payment_history": [{"_id": str(i), "value": i} for i in range(5)],
        "stripe_webhooks": [{"_id": "prior", "value": 1}],
    }
    after = deepcopy(before)
    ops: list[object] = []
    calls: list[object] = []
    sessions = {"prior": {"id": "cs_prior"}}
    if mutation in {"current", "history", "receipt"}:
        after[{"current": "payments", "history": "payment_history", "receipt": "stripe_webhooks"}[mutation]][0][
            "extra"
        ] = "corrupt"
    elif mutation == "added":
        after["payments"].append({"_id": "extra"})
    elif mutation == "removed":
        after["payment_history"] = []
    elif mutation == "orders":
        ops.append("unexpected")
    elif mutation == "stripe":
        calls.append("unexpected")
    elif mutation == "sessions":
        sessions["prior"]["id"] = "replacement"

    def snapshot() -> Any:
        return deepcopy(after)

    def target(_: object) -> dict[str, Any]:
        return before["payments"][0]

    def request(*_: Any, **__: Any) -> Any:
        if mutation == "repeat_changes_state":
            after["payments"][0]["extra"] = "corrupt"
        return response("b" * 32)

    evidence = ScenarioEvidence("PAY11-23", "Guard", "PAY11-23 Guard", {})
    context = SimpleNamespace(
        orders=SimpleNamespace(order_id=ORDER, http_calls=ops),
        stripe=SimpleNamespace(calls=calls, sessions=sessions),
        client=SimpleNamespace(request=request),
        responses=[response()],
        evidence=evidence,
    )
    checks = FrameworkChecks(cast(PaymentChecks, SimpleNamespace(context=context, snapshot=snapshot, target=target)))
    checks.inputs = inputs()
    checks.before = before
    checks.calls = (0, 0)
    checks.sessions = {"prior": {"id": "cs_prior"}}
    effects = dict(
        Payments="2",
        History="5",
        Receipts="1",
        TargetStatus="pending",
        OrdersCalls="0",
        StripeCalls="0",
        ProviderSessions="unchanged",
        Repeat="true",
        Allow="GET",
        FaultHits="0",
    )
    if mutation == "none":
        checks.rejected(expectation(), effects)
    else:
        with pytest.raises(AssertionError):
            checks.rejected(expectation(), effects)


def test_every_new_framework_case_has_complete_executable_tables_and_explicit_fault_boundaries() -> None:
    feature = FeatureParser(str(FEATURES), "framework_failures.feature").parse()
    assert len(feature.scenarios) == 71
    profiles = source_evidence(FEATURES)
    faults = 0
    accepted = 0
    for scenario in feature.scenarios.values():
        cid = scenario.name.split()[0]
        steps = {s.name: s for s in scenario.steps}
        assert "the framework request contains" in steps
        assert (
            "an unrelated succeeded payment fills all collections" in steps
            and "I remember populated framework state" in steps
        )
        expected = profiles[cid]["expected"]
        if expected["Code"] == "-":
            accepted += 1
            assert steps["the accepted framework input has these effects"].type == "then"
        else:
            assert 'a stored payment is prepared in state "pending"' in steps
            assert {
                f"JSON.{key}"
                for key in ["type", "title", "status", "detail", "instance", "errors", "missingProperties"]
            } <= expected.keys()
            step = steps["framework rejection keeps this populated state and protocol"]
            assert step.type == "then" and step.datatable is not None
            effects = table_values([[c.value for c in row.cells] for row in step.datatable.rows])
            assert effects["Payments"] == "2" and effects["History"] == "5" and effects["Receipts"] == "1"
            if expected["HTTPStatuses"] == "500":
                faults += 1
                assert "this framework failure is installed" in steps and effects["FaultHits"] == "2"
    assert faults == 7 and accepted == 3
