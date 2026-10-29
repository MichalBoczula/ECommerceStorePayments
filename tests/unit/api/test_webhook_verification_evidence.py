import hashlib
import importlib
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import FastAPI
from fastapi import Request as ApiRequest
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from httpx2 import Request, Response
from pytest_bdd.parser import FeatureParser
from scripts.bdd_evidence import check_header_items, check_result_evidence
from scripts.generate_operation_links import FEATURES

from ecommerce_store_payments.application.payments.webhook import WebhookInvalidError
from tests.acceptance.evidence import EvidenceClient, ScenarioEvidence, table_values
from tests.acceptance.payment_checks import PaymentChecks
from tests.acceptance.webhook_verification_checks import (
    UNKNOWN_RECEIPT_FIELDS,
    WIRE_EXPECTED,
    WIRE_INPUTS,
    WebhookVerificationChecks,
    prepare_wire,
    wire_analysis,
)
from tests.unit.api.test_bdd_evidence import bundle
from tests.unit.api.test_checkout_evidence import ORDER, WINDOW, sample
from tests.unit.api.test_webhooks import configure
from tests.unit.external_providers.test_stripe_webhook import setup_payload
from tests.webhook_fixtures import signature

STAMP = 1_800_000_000


def inputs(**changes: str) -> dict[str, str]:
    return {
        "EventType": "payment_intent.payment_failed",
        "PayloadVariant": "normal",
        "MutationPath": "-",
        "MutationValue": "-",
        "SignatureMode": "correct",
        "TimestampOffsetSeconds": "0",
        "ContentType": "application/json",
        "BodyBytes": "natural",
        **changes,
    }


def capture() -> ScenarioEvidence:
    return ScenarioEvidence("PAY99-01", "Verification probe", "PAY99-01 Verification probe", {})


def drain(evidence: ScenarioEvidence) -> dict[str, Any]:
    result: dict[str, Any] = {}
    evidence.flush(lambda name, body: result.__setitem__(name, json.loads(body)))
    return result


@pytest.mark.parametrize(
    "mode,headers,matches,same",
    [
        ("correct", 1, 1, True),
        ("missing", 0, 0, True),
        ("empty", 1, 0, True),
        ("wrong_secret", 1, 0, True),
        ("no_v1", 1, 0, True),
        ("bad_v1", 1, 0, True),
        ("multiple_v1", 1, 1, True),
        ("duplicate_headers", 2, 2, True),
        ("tampered", 1, 0, False),
    ],
)
def test_signature_analysis_distinguishes_physical_headers_rotation_and_changed_bytes(
    mode: str, headers: int, matches: int, same: bool
) -> None:
    _, base = setup_payload()
    wire = prepare_wire(base, inputs(SignatureMode=mode), STAMP)
    observed = wire_analysis(wire.body, list(wire.headers), STAMP)
    assert observed["SignatureHeaders"] == headers and observed["MatchingV1Signatures"] == matches
    assert (wire.body == wire.signed_body) == same


@pytest.mark.parametrize(
    "variant",
    [
        "malformed_json",
        "duplicate_event_id",
        "duplicate_metadata",
        "invalid_utf8",
        "array",
        "null",
        "empty",
        "unicode",
        "reencoded",
    ],
)
def test_wire_variants_keep_raw_invalid_and_multibyte_payloads_lossless(variant: str) -> None:
    _, base = setup_payload()
    wire = prepare_wire(base, inputs(PayloadVariant=variant), STAMP)
    if variant == "invalid_utf8":
        with pytest.raises(UnicodeDecodeError):
            wire.body.decode()
    elif variant == "malformed_json":
        with pytest.raises(ValueError):
            json.loads(wire.body)
    elif variant in {"duplicate_event_id", "duplicate_metadata"}:

        def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
            assert len(pairs) == len(dict(pairs))
            return dict(pairs)

        with pytest.raises(AssertionError):
            json.loads(wire.body, object_pairs_hook=reject_duplicates)
    elif variant == "empty":
        assert wire.body == b""
    elif variant == "null":
        assert json.loads(wire.body) is None
    elif variant == "array":
        assert type(json.loads(wire.body)) is list
    elif variant == "unicode":
        assert "Zażółć".encode() in wire.body and b"\\u017c" not in wire.body
    else:
        assert wire.body != wire.signed_body and json.loads(wire.body) == json.loads(wire.signed_body)
    assert wire_analysis(wire.body, list(wire.headers), STAMP)["MatchingV1Signatures"] == (
        0 if variant == "reencoded" else 1
    )


@pytest.mark.parametrize(
    "mutation",
    ["body", "collapsed_headers", "removed_header", "matching_count", "header_count", "offset", "length", "same"],
)
def test_wire_evidence_rejects_changed_bytes_lost_headers_and_false_expectations(mutation: str) -> None:
    _, base = setup_payload()
    wire = prepare_wire(base, inputs(SignatureMode="duplicate_headers"), STAMP)
    expected = {
        "SignatureHeaders": "2",
        "MatchingV1Signatures": "2",
        "BodyBytes": "natural",
        "SignedBytesEqual": "true",
        "TimestampOffsetSeconds": "0",
    }
    headers = list(wire.headers)
    body = wire.body
    if mutation == "body":
        body += b" "
    elif mutation == "collapsed_headers":
        headers = [
            ("content-type", "application/json"),
            ("stripe-signature", ", ".join(v for k, v in headers if k == "stripe-signature")),
        ]
    elif mutation == "removed_header":
        headers.pop()
    elif mutation == "matching_count":
        expected["MatchingV1Signatures"] = "1"
    elif mutation == "header_count":
        expected["SignatureHeaders"] = "1"
    elif mutation == "offset":
        expected["TimestampOffsetSeconds"] = "-1"
    elif mutation == "length":
        expected["BodyBytes"] = "0"
    else:
        expected["SignedBytesEqual"] = "false"
    response = Response(
        400,
        json={},
        request=Request("POST", "http://testserver/payments/webhooks/stripe", content=body, headers=headers),
    )
    response.extensions["payments.bdd.exchangeId"] = "probe/1"
    checks = WebhookVerificationChecks(
        PaymentChecks(cast(Any, SimpleNamespace(responses=[response], evidence=capture())))
    )
    checks.wire = wire
    with pytest.raises(AssertionError):
        checks.wire_evidence(expected)


@pytest.mark.parametrize(
    "mutation", ["missing", "shape", "value_type", "uppercase", "mapping", "lost_duplicate", "secret", "extra"]
)
def test_header_inventory_guard_rejects_missing_coalesced_corrupt_and_unredacted_items(mutation: str) -> None:
    record: dict[str, Any] = {
        "headers": {"stripe-signature": "one, two", "authorization": "[redacted]"},
        "headerItems": [["stripe-signature", "one"], ["stripe-signature", "two"], ["authorization", "[redacted]"]],
    }
    check_header_items(record)
    if mutation == "missing":
        del record["headerItems"]
    elif mutation == "shape":
        record["headerItems"][0] = ["stripe-signature"]
    elif mutation == "value_type":
        record["headerItems"][0][1] = 1
    elif mutation == "uppercase":
        record["headerItems"][0][0] = "Stripe-Signature"
    elif mutation == "mapping":
        record["headers"]["stripe-signature"] = "other"
    elif mutation == "lost_duplicate":
        record["headerItems"].pop(0)
    elif mutation == "secret":
        record["headerItems"][-1][1] = "private-token"
    else:
        record["headerItems"].append(["other", "invisible"])
    with pytest.raises(ValueError):
        check_header_items(record)


def test_actual_capture_preserves_header_multiplicity_and_redacts_each_sensitive_value() -> None:
    app = FastAPI()

    @app.post("/echo")
    async def echo(request: ApiRequest) -> JSONResponse:
        response = JSONResponse({"signatureHeaders": len(request.headers.getlist("stripe-signature"))})
        response.raw_headers.extend(
            [(b"set-cookie", b"private-cookie-one=1"), (b"set-cookie", b"private-cookie-two=2")]
        )
        return response

    evidence = capture()
    with TestClient(app) as raw:
        response = EvidenceClient(raw, evidence).post(
            "/echo",
            content=b"{}",
            headers=[
                ("stripe-signature", "one"),
                ("stripe-signature", "two"),
                ("authorization", "private-one"),
                ("authorization", "private-two"),
            ],
        )
    assert response.json() == {"signatureHeaders": 2}
    records = drain(evidence)
    for record in records.values():
        check_header_items(record)
    assert [v for k, v in records["HTTP 001 request"]["headerItems"] if k == "stripe-signature"] == ["one", "two"]
    assert [v for k, v in records["HTTP 001 request"]["headerItems"] if k == "authorization"] == [
        "[redacted]",
        "[redacted]",
    ]
    assert [v for k, v in records["HTTP 001 response"]["headerItems"] if k == "set-cookie"] == [
        "[redacted]",
        "[redacted]",
    ]
    assert "private" not in json.dumps(records)


def test_two_valid_physical_signatures_reach_the_real_route_and_are_rejected_without_a_receipt(
    client: TestClient,
) -> None:
    webhooks, body = configure(client)
    value = signature(body)
    evidence = capture()
    response = EvidenceClient(client, evidence).post(
        "/payments/webhooks/stripe",
        content=body,
        headers=[("content-type", "application/json"), ("stripe-signature", value), ("stripe-signature", value)],
    )
    assert response.status_code == 400 and response.json()["code"] == "webhook_invalid" and not webhooks.receipts
    request = drain(evidence)["HTTP 001 request"]
    assert [v for k, v in request["headerItems"] if k == "stripe-signature"] == [value, value]


@pytest.mark.parametrize("mutation", ["missing", "mapping", "redaction"])
def test_result_publication_rejects_bad_header_items(mutation: str, tmp_path: Path) -> None:
    result, profile = bundle(tmp_path)
    attachment = next(a for a in result["attachments"] if a["name"] == "HTTP 001 request")
    path = tmp_path / attachment["source"]
    record = json.loads(path.read_text())
    if mutation == "missing":
        del record["headerItems"]
    elif mutation == "mapping":
        record["headerItems"] = [["stripe-signature", "changed"]]
    else:
        record["headers"] = {"authorization": "[redacted]"}
        record["headerItems"] = [["authorization", "private-token"]]
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        check_result_evidence(result, profile, tmp_path)


@pytest.mark.parametrize("collection", ["payments", "payment_history", "stripe_webhooks"])
def test_rejected_verification_checks_every_field_in_every_populated_collection(
    collection: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, before = sample()
    after = deepcopy(before)
    after[collection][0]["changed"] = "same-count-write"
    payments = PaymentChecks(cast(Any, SimpleNamespace()))
    payments.before = before
    monkeypatch.setattr(payments, "snapshot", lambda: after)
    with pytest.raises(AssertionError):
        WebhookVerificationChecks(payments).rejected(
            {"CurrentStatus": "pending", "CurrentVersion": "2", "NewReceipts": "0", "NewExternalCalls": "0"}
        )


def ignored_receipt_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[WebhookVerificationChecks, dict[str, str], dict[str, Any]]:
    _, before = sample()
    after = deepcopy(before)
    _, base = setup_payload()
    wire = prepare_wire(base, inputs(), STAMP)
    expected = {
        "_id": "{event.id}",
        "event_type": '"payment_intent.payment_failed"',
        "payload_digest": "{request.sha256}",
        "outcome": '"unknown"',
        **{
            k: "null"
            for k in (
                "payment_id",
                "order_id",
                "attempt_id",
                "amount_minor",
                "currency",
                "session_id",
                "provider_payment_id",
            )
        },
        "state": '"ignored"',
        "reason": '"unsupported_event"',
        "received_at": "{request.window}",
        "completed_at": "{request.window}",
        "fulfillment_status": "null",
    }
    new = {
        "_id": wire.event["id"],
        "event_type": "payment_intent.payment_failed",
        "payload_digest": hashlib.sha256(wire.body).hexdigest(),
        "outcome": "unknown",
        **{
            k: None
            for k in (
                "payment_id",
                "order_id",
                "attempt_id",
                "amount_minor",
                "currency",
                "session_id",
                "provider_payment_id",
            )
        },
        "state": "ignored",
        "reason": "unsupported_event",
        "received_at": WINDOW[0],
        "completed_at": WINDOW[0],
        "fulfillment_status": None,
    }
    after["stripe_webhooks"].insert(0, new)
    response = Response(
        200,
        json={"received": True},
        headers={"content-type": "application/json", "x-trace-id": "a" * 32},
        request=Request("POST", "http://testserver/payments/webhooks/stripe"),
    )
    response.extensions["payments.bdd.exchangeId"] = "probe/1"
    context = SimpleNamespace(
        orders=SimpleNamespace(order_id=ORDER, http_calls=[]),
        stripe=SimpleNamespace(calls=[], sessions={}),
        responses=[response],
        request_window=WINDOW,
        evidence=capture(),
    )
    payments = PaymentChecks(cast(Any, context))
    payments.before = before
    payments.external_calls = (0, 0)
    monkeypatch.setattr(payments, "snapshot", lambda: after)
    checks = WebhookVerificationChecks(payments)
    checks.wire = wire
    checks.before_sessions = {}
    return checks, expected, after


def test_accepted_boundary_requires_the_complete_ignored_receipt_and_original_byte_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checks, expected, _ = ignored_receipt_probe(monkeypatch)
    checks.unknown_receipt(expected)


@pytest.mark.parametrize(
    "mutation", ["missing", "digest", "metadata", "old_receipt", "extra_receipt", "timestamp", "payment", "reason"]
)
def test_accepted_verification_rejects_partial_receipts_normalized_digests_and_unrelated_changes(
    mutation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    checks, expected, after = ignored_receipt_probe(monkeypatch)
    receipt = after["stripe_webhooks"][0]
    if mutation == "missing":
        del receipt["fulfillment_status"]
    elif mutation == "digest":
        receipt["payload_digest"] = "0" * 64
    elif mutation == "metadata":
        receipt["payment_id"] = ORDER
    elif mutation == "old_receipt":
        after["stripe_webhooks"][-1]["value"] = "changed"
    elif mutation == "extra_receipt":
        after["stripe_webhooks"].append(deepcopy(receipt))
    elif mutation == "timestamp":
        receipt["completed_at"] = WINDOW[0].replace(tzinfo=None)
    elif mutation == "payment":
        after["payments"][0]["value"] = "changed"
    else:
        receipt["reason"] = "not-verified"
    with pytest.raises(AssertionError):
        checks.unknown_receipt(expected)


@pytest.mark.parametrize("offset,accepted", [(-300, True), (-301, False), (3600, True)])
def test_actual_sdk_old_timestamp_boundary_and_future_behavior(
    offset: int, accepted: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    verifier, base = setup_payload()
    wire = prepare_wire(base, inputs(TimestampOffsetSeconds=str(offset)), STAMP)
    monkeypatch.setattr(importlib.import_module("stripe._webhook"), "time", SimpleNamespace(time=lambda: STAMP))
    if accepted:
        verified = verifier.verify(wire.body, dict(wire.headers)["stripe-signature"])
        assert (
            verified.outcome.value == "unknown"
            and verified.checkout is None
            and verified.payload_digest == hashlib.sha256(wire.body).hexdigest()
        )
    else:
        with pytest.raises(WebhookInvalidError):
            verifier.verify(wire.body, dict(wire.headers)["stripe-signature"])


def test_verification_sources_require_authored_wire_full_problems_and_populated_state_checks() -> None:
    feature = FeatureParser(str(FEATURES), "webhook_verification.feature").parse()
    assert len(feature.scenarios) == 45
    accepted = 0
    for scenario in feature.scenarios.values():
        steps = {step.name: step for step in scenario.steps}
        assert (
            "an unrelated succeeded payment fills all collections" in steps
            and "I remember webhook verification state" in steps
        )
        for name, fields in [
            ("the webhook verification request is prepared", WIRE_INPUTS),
            ("the webhook delivery matches this verification evidence", WIRE_EXPECTED),
        ]:
            table = steps[name].datatable
            assert table is not None
            assert table_values([[c.value for c in r.cells] for r in table.rows]).keys() == fields
        outcome = next(step for step in scenario.steps if step.name.startswith("the response matches case"))
        assert outcome.datatable is not None
        expected = table_values([[c.value for c in r.cells] for r in outcome.datatable.rows])
        if expected["HTTPStatuses"] == "200":
            accepted += 1
            table = steps["the accepted verification stores this exact ignored receipt"].datatable
            assert table is not None
            assert table_values([[c.value for c in r.cells] for r in table.rows]).keys() == UNKNOWN_RECEIPT_FIELDS
        else:
            assert "verification rejection preserves this complete state" in steps
            assert {
                "JSON.type",
                "JSON.title",
                "JSON.status",
                "JSON.detail",
                "JSON.instance",
                "JSON.errors",
                "JSON.missingProperties",
            } <= expected.keys()
    assert accepted == 7
