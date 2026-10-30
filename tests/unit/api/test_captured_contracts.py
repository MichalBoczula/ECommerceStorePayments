import asyncio
import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from jsonschema import ValidationError
from pydantic import SecretStr
from scripts.captured_contracts import CapturedContracts, check_captured_contracts
from scripts.contract_metadata import check_metadata
from scripts.openapi_contract import document

from ecommerce_store_payments.api.contracts.payment_response import PAYMENT_EXAMPLE
from ecommerce_store_payments.api.contracts.webhook_request import CHECKOUT_EVENTS, event_example
from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.infrastructure.clients.stripe.webhook_verifier import (
    EVENT_OUTCOMES,
    StripeWebhookVerifier,
)
from ecommerce_store_payments.infrastructure.config.settings import Settings
from tests.acceptance.evidence import EvidenceClient, ScenarioEvidence, content_evidence
from tests.unit.api.test_bdd_evidence import drain
from tests.webhook_fixtures import WEBHOOK_SECRET, encode, signature

TRACE = "0123456789abcdef0123456789abcdef"


@lru_cache
def spec() -> dict[str, Any]:
    return document()


def pair(
    body: Any = None,
    *,
    method: str = "POST",
    path: str = "/payments/11111111-1111-4111-8111-111111111111/pay",
    status: int = 201,
    media: str = "application/json",
    request_body: bytes = b"",
) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = json.dumps(PAYMENT_EXAMPLE if body is None else body).encode()
    return (
        {
            "kind": "request",
            "targetService": "payments",
            "method": method,
            "path": path,
            "headers": {},
            "headerItems": [],
            "content": content_evidence(request_body, None),
        },
        {
            "kind": "response",
            "status": status,
            "headers": {"content-type": media, "content-length": str(len(raw)), "x-trace-id": TRACE},
            "content": content_evidence(raw, media),
        },
    )


@pytest.mark.parametrize(
    "drift",
    [
        "description",
        "examples",
        "example-type",
        "format",
        "nullable",
        "required",
        "enum",
        "ack-required",
        "problem-required",
        "header",
        "header-example",
        "bodyless",
    ],
)
def test_generated_metadata_rejects_missing_prose_and_source_contract_drift(drift: str) -> None:
    source = deepcopy(spec())
    model = source["components"]["schemas"]["PaymentResponse"]
    pay = source["paths"]["/payments/{order_id}/pay"]["post"]
    if drift in {"description", "examples"}:
        del model["properties"]["currency"][drift]
    elif drift == "example-type":
        model["properties"]["amount_minor"]["examples"] = ["1299"]
    elif drift == "format":
        del model["properties"]["id"]["format"]
    elif drift == "nullable":
        model["properties"]["updated_at"]["anyOf"] = [{"type": "string", "format": "date-time"}]
    elif drift == "required":
        model["required"].remove("provider_session_id")
    elif drift == "enum":
        model["properties"]["status"]["enum"].remove("failed")
    elif drift == "ack-required":
        source["components"]["schemas"]["WebhookAcknowledgement"]["required"] = []
    elif drift == "problem-required":
        pay["responses"]["400"]["content"]["application/problem+json"]["schema"]["required"].remove("type")
    elif drift == "header":
        del pay["responses"]["405"]["headers"]["Allow"]
    elif drift == "header-example":
        del pay["responses"]["201"]["headers"]["X-Trace-Id"]["schema"]["examples"]
    else:
        pay["requestBody"] = {"content": {"application/json": {"schema": {"type": "object"}}}}
    with pytest.raises((ValueError, ValidationError)):
        check_metadata(source)


def test_complete_examples_preserve_nulls_and_domain_statuses_without_changing_binding() -> None:
    source = spec()
    payment = source["components"]["schemas"]["PaymentResponse"]
    assert payment["examples"][0] == PAYMENT_EXAMPLE
    assert payment["properties"]["status"]["enum"] == [status.value for status in PaymentStatus]
    assert payment["examples"][0]["provider_payment_id"] is None
    checkout = source["components"]["schemas"]["CheckoutResponse"]["examples"][0]
    assert checkout["payment"]["provider_payment_id"] is None and checkout["payment"]["failure_code"] is None
    assert "HTTPValidationError" not in source["components"]["schemas"]
    for command in ("pay", "checkout"):
        assert "requestBody" not in source["paths"][f"/payments/{{order_id}}/{command}"]["post"]


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-nullable",
        "null-id",
        "uuid",
        "date",
        "money-bool",
        "money-fraction",
        "status",
        "currency",
        "provider",
        "extra",
        "media",
        "length",
        "trace",
        "caller-trace",
        "body",
        "status-code",
    ],
)
def test_complete_payment_and_wire_protocol_reject_drift(mutation: str) -> None:
    request, response = pair()
    body = deepcopy(PAYMENT_EXAMPLE)
    if mutation == "missing-nullable":
        del body["provider_session_id"]
    elif mutation == "null-id":
        body["id"] = None
    elif mutation == "uuid":
        body["id"] = "not-a-uuid"
    elif mutation == "date":
        body["created_at"] = "2026-10-01T12:00:00"
    elif mutation == "money-bool":
        body["amount_minor"] = True
    elif mutation == "money-fraction":
        body["amount_minor"] = 12.99
    elif mutation == "status":
        body["status"] = "paid"
    elif mutation == "currency":
        body["currency"] = "pln"
    elif mutation == "provider":
        body["provider_session_id"] = "private identifier"
    elif mutation == "extra":
        body["internal_secret"] = "private"
    elif mutation == "media":
        response["headers"]["content-type"] = "text/plain"
    elif mutation == "length":
        response["headers"]["content-length"] = "0"
    elif mutation == "trace":
        response["headers"]["x-trace-id"] = "private"
    elif mutation == "caller-trace":
        request["headers"]["x-trace-id"] = TRACE
    elif mutation == "body":
        request["content"] = content_evidence(b"{}", "application/json")
    else:
        response["status"] = 202
    if body != PAYMENT_EXAMPLE:
        raw = json.dumps(body).encode()
        response["content"] = content_evidence(raw, "application/json")
        response["headers"]["content-length"] = str(len(raw))
    with pytest.raises((ValueError, ValidationError)):
        CapturedContracts(spec()).check(request, response)


@pytest.mark.parametrize("event_type", CHECKOUT_EVENTS)
@pytest.mark.parametrize("paid", [True, False])
def test_documented_webhook_variants_use_real_sdk_verification_and_leave_signed_bytes_intact(
    event_type: str, paid: bool
) -> None:
    payload = event_example(event_type, paid=paid)
    raw = encode(payload)
    verifier = StripeWebhookVerifier(Settings(stripe_webhook_secret=SecretStr(WEBHOOK_SECRET)))
    result = verifier.verify(raw, signature(raw))
    assert result.event_type == event_type
    assert set(CHECKOUT_EVENTS) == set(EVENT_OUTCOMES)
    request, response = pair({"received": True}, path="/payments/webhooks/stripe", status=200)
    request["content"] = content_evidence(raw, "application/json")
    request["headerItems"] = [["stripe-signature", signature(raw)]]
    assert CapturedContracts(spec()).check(request, response)["schemaValidated"] is True
    assert request["content"]["rawBody"].encode() == raw


@pytest.mark.parametrize(
    "mutation", ["live", "account", "context", "amount", "metadata", "paid-intent", "session-status", "signature"]
)
def test_accepted_webhook_contract_rejects_wrong_envelopes_and_missing_signed_evidence(mutation: str) -> None:
    payload = event_example(CHECKOUT_EVENTS[0])
    session = payload["data"]["object"]
    if mutation == "live":
        payload["livemode"] = True
    elif mutation == "account":
        payload["account"] = "acct_other"
    elif mutation == "context":
        payload["context"] = "organization"
    elif mutation == "amount":
        session["amount_total"] = 199
    elif mutation == "metadata":
        del session["metadata"]["attempt_id"]
    elif mutation == "paid-intent":
        session["payment_intent"] = None
    elif mutation == "session-status":
        session["status"] = "open"
    request, response = pair({"received": True}, path="/payments/webhooks/stripe", status=200)
    raw = encode(payload)
    request["content"] = content_evidence(raw, "application/json")
    request["headerItems"] = [] if mutation == "signature" else [["stripe-signature", signature(raw)]]
    with pytest.raises((ValueError, ValidationError)):
        CapturedContracts(spec()).check(request, response)


def test_ignored_event_envelope_allows_unknown_provider_fields() -> None:
    payload = {
        "id": "evt_other",
        "type": "payment_intent.created",
        "object": "event",
        "livemode": False,
        "future_provider_field": {"opaque": [1, None, True]},
    }
    schema = spec()["components"]["schemas"]["StripeWebhookEvent"]
    CapturedContracts(spec()).validate(schema, payload)
    assert (
        StripeWebhookVerifier(Settings(stripe_webhook_secret=SecretStr(WEBHOOK_SECRET)))
        .verify(encode(payload), signature(encode(payload)))
        .checkout
        is None
    )


@pytest.mark.parametrize(
    "path",
    [
        "/health",
        "/health/live",
        "/health/ready",
        "/swagger",
        "/redoc",
        "/docs/oauth2-redirect",
        "/openapi.json",
        "/unknown-route",
    ],
)
def test_actual_health_docs_and_global_problems_have_contract_observations(client: TestClient, path: str) -> None:
    evidence = ScenarioEvidence(
        "PAY99-02", "Contract probes", "PAY99-02 Actual HTTP", {}, contract_check=CapturedContracts(spec()).observe
    )
    response = EvidenceClient(client, evidence).get(path)
    assert response.status_code == (404 if path == "/unknown-route" else 200)
    records = drain(evidence)
    observed = records["HTTP 001 contract"]["value"]
    assert observed["valid"] is True
    assert records["HTTP 001 request"]["stepPhase"] == records["HTTP 001 contract"]["stepPhase"]


@pytest.mark.parametrize(
    "method,path", [("GET", "/payments/11111111-1111-4111-8111-111111111111/pay"), ("POST", "/health/ready")]
)
def test_actual_wrong_method_keeps_allow_header_and_original_operation(
    client: TestClient, method: str, path: str
) -> None:
    evidence = ScenarioEvidence(
        "PAY99-02", "Contract probes", "PAY99-02 Wrong method", {}, contract_check=CapturedContracts(spec()).observe
    )
    response = EvidenceClient(client, evidence).request(method, path)
    assert response.status_code == 405
    value = drain(evidence)["HTTP 001 contract"]["value"]
    assert value["valid"] and value["classification"] == "wrong-method" and "allow" in value["headersValidated"]


@pytest.mark.parametrize(
    ("path", "status", "classification"),
    [
        ("/żółw", 404, "unmatched-route"),
        ("/payments/zażółć/pay", 400, "operation"),
        ("/payments/a%2Fb/pay", 404, "unmatched-route"),
    ],
)
def test_encoded_paths_keep_wire_bytes_and_match_actual_decoded_routing(
    client: TestClient,
    path: str,
    status: int,
    classification: str,
) -> None:
    evidence = ScenarioEvidence(
        "PAY99-02", "Contract probes", "PAY99-02 Encoded routes", {}, contract_check=CapturedContracts(spec()).observe
    )
    response = EvidenceClient(client, evidence).request("POST" if path.startswith("/payments/") else "GET", path)
    records = drain(evidence)
    assert response.status_code == status
    assert "%" in records["HTTP 001 request"]["path"]
    observed = records["HTTP 001 contract"]["value"]
    assert observed["valid"] and observed["classification"] == classification


@pytest.mark.parametrize("mutation", ["status", "title", "instance", "trace", "extra", "missing"])
def test_problem_contract_requires_full_safe_shape_and_wire_correlations(client: TestClient, mutation: str) -> None:
    evidence = ScenarioEvidence("PAY99-02", "Contract probes", "PAY99-02 Safe problems", {})
    EvidenceClient(client, evidence).get("/unknown-route")
    records = drain(evidence)
    request, response = records["HTTP 001 request"], records["HTTP 001 response"]
    body = response["content"]["body"]
    if mutation == "status":
        body["status"] = 500
    elif mutation == "title":
        body["title"] = "Private exception"
    elif mutation == "instance":
        body["instance"] = "/different"
    elif mutation == "trace":
        body["traceId"] = TRACE
    elif mutation == "extra":
        body["stack"] = "private"
    else:
        del body["errors"]
    raw = json.dumps(body).encode()
    response["content"] = content_evidence(raw, "application/problem+json")
    response["headers"]["content-length"] = str(len(raw))
    with pytest.raises((ValueError, ValidationError)):
        CapturedContracts(spec()).check(request, response)


def saved_results(client: TestClient, folder: Path) -> tuple[Path, list[dict[str, Any]]]:
    evidence = ScenarioEvidence(
        "PAY99-02", "Contract probes", "PAY99-02 All phases", {}, contract_check=CapturedContracts(spec()).observe
    )
    wire = EvidenceClient(client, evidence)
    for phase in ("Given", "When", "Then"):
        evidence.phase = phase
        wire.get("/health/live")
    result: dict[str, Any] = {"name": "PAY99-02 All phases", "attachments": []}
    records: list[dict[str, Any]] = []

    def save(name: str, raw: str) -> None:
        filename = str(len(records)) + ".json"
        records.append(json.loads(raw))
        (folder / filename).write_text(raw)
        result["attachments"].append({"name": name, "type": "application/json", "source": filename})

    evidence.finish(save)
    path = folder / "probe-result.json"
    path.write_text(json.dumps(result))
    return path, records


def test_post_suite_gate_checks_setup_primary_and_supporting_responses(client: TestClient, tmp_path: Path) -> None:
    _, records = saved_results(client, tmp_path)
    assert check_captured_contracts(spec(), tmp_path) == {
        "exchanges": 3,
        "paymentsResponses": 3,
        "external": 0,
        "failures": 0,
    }
    assert {r["stepPhase"] for r in records if r.get("kind") == "contract"} == {"Given", "When", "Then"}


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "forged", "foreign", "support-body", "support-header"])
def test_post_suite_gate_rejects_missing_forged_and_invalid_supporting_contracts(
    client: TestClient, tmp_path: Path, mutation: str
) -> None:
    path, records = saved_results(client, tmp_path)
    result = json.loads(path.read_text())
    i = next(
        i
        for i, r in enumerate(records)
        if r.get("kind") == ("response" if mutation.startswith("support") else "contract") and r["stepPhase"] == "Then"
    )
    record = records[i]
    if mutation == "missing":
        result["attachments"].pop(i)
    elif mutation == "duplicate":
        result["attachments"].append(result["attachments"][i])
    elif mutation == "forged":
        record["value"]["valid"] = False
    elif mutation == "foreign":
        record["scenarioId"] = "PAY99-99"
    elif mutation == "support-body":
        record["content"]["body"] = {"wrong": "shape"}
    else:
        record["headers"]["x-trace-id"] = "private"
    (tmp_path / f"{i}.json").write_text(json.dumps(record))
    path.write_text(json.dumps(result))
    with pytest.raises((ValueError, ValidationError)):
        check_captured_contracts(spec(), tmp_path)


def test_contract_failure_keeps_the_real_response_and_never_fabricates_transport_failure() -> None:
    evidence = ScenarioEvidence(
        "PAY99-02", "Contract probes", "PAY99-02 Invalid schema", {}, contract_check=CapturedContracts(spec()).observe
    )
    exchange = evidence.begin("GET", "http://test/health", {}, b"", target="payments", role="api")
    evidence.response(exchange, 200, {"content-type": "application/json"}, b'{"wrong":true}')
    records = drain(evidence)
    assert records["HTTP 001 response"]["status"] == 200 and not any(
        r.get("kind") == "failure" for r in records.values()
    )
    assert records["HTTP 001 contract"]["value"]["valid"] is False


def test_external_boundaries_and_cancellation_are_classified_without_schema_or_http_fabrication() -> None:
    evidence = ScenarioEvidence(
        "PAY99-02",
        "Contract probes",
        "PAY99-02 Actual boundaries",
        {},
        contract_check=CapturedContracts(spec()).observe,
    )
    external = evidence.begin(
        "GET", "http://orders/orders/1", {}, b"", target="orders", role="orders-boundary", controlled=True
    )
    evidence.response(external, 200, {}, b"upstream body")
    cancelled = evidence.begin("GET", "http://test/health/ready", {}, b"", target="payments", role="api")
    evidence.failure(cancelled, asyncio.CancelledError("private"))
    records = drain(evidence)
    observations = [r["value"] for r in records.values() if r.get("kind") == "contract"]
    assert {v["classification"] for v in observations} == {"external-boundary", "transport-failure"}
    assert all(v["valid"] and not v["schemaValidated"] and "status" not in v for v in observations)
    assert "private" not in json.dumps(records)


@pytest.mark.parametrize("target", ["payments", "orders"])
def test_no_transport_failure_can_advertise_a_fabricated_status(target: str) -> None:
    request, _ = pair()
    request["targetService"] = target
    failure = {"kind": "failure", "exceptionType": "CancelledError", "cancelled": True, "status": 499}
    with pytest.raises(ValueError, match="cannot claim an HTTP response"):
        CapturedContracts(spec()).check(request, failure)
