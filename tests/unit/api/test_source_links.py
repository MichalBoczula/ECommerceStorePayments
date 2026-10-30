import asyncio
import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from scripts.generate_operation_links import FEATURES
from scripts.openapi_contract import document
from scripts.source_links import ATTACHMENT, SourceLinks, check_source_links, receipt_facts

from ecommerce_store_payments.api.contracts.webhook_request import event_example
from tests.acceptance.evidence import EvidenceClient, ScenarioEvidence
from tests.unit.api.test_bdd_evidence import drain
from tests.unit.api.test_source_knowledge import knowledge
from tests.webhook_fixtures import signature


@lru_cache
def checks() -> SourceLinks:
    return SourceLinks(knowledge(), document(), FEATURES)


def evidence(case: str = "PAY11-22", *, checked: bool = False) -> ScenarioEvidence:
    profile = checks().profiles[case]
    return ScenarioEvidence(
        case,
        profile["feature"],
        profile["scenario"],
        profile["parameters"],
        source_check=checks().observe if checked else None,
    )


def expected(e: ScenarioEvidence, exchange_id: str) -> None:
    e.record(
        "Expected response",
        {
            **e.identity,
            "stepPhase": "Then",
            "step": "assert response",
            "value": checks().profiles[str(e.identity["scenarioId"])]["expected"],
            "exchangeIds": [exchange_id],
        },
    )


def health(client: TestClient, *, checked: bool = False) -> tuple[ScenarioEvidence, dict[str, Any]]:
    e = evidence(checked=checked)
    e.record("Scenario identity", e.identity)
    e.phase, e.step = "When", "I request the health probe"
    r = EvidenceClient(client, e).get("/health")
    expected(e, r.extensions["payments.bdd.exchangeId"])
    return e, drain(e)


def worker(
    *, source: str | None = "payments.command.fulfill", phase: str = "When"
) -> tuple[ScenarioEvidence, dict[str, Any]]:
    # Synthetic recorder fixture for link validation, not a claim of command execution.
    e = evidence("PAY23-01")
    e.phase = "Given"
    payload = json.dumps(event_example("checkout.session.completed")).encode()
    ex = e.begin(
        "POST",
        "http://payments/payments/webhooks/stripe",
        {"content-type": "application/json", "stripe-signature": signature(payload)},
        payload,
        target="payments",
        role="api",
    )
    raw = b'{"received":true}'
    e.response(
        ex, 200, {"content-type": "application/json", "content-length": str(len(raw)), "x-trace-id": "1" * 32}, raw
    )
    e.phase = phase
    e.step = "the durable fulfillment command runs"
    with e.action("Synthetic explicit command", {"limit": 100}, source_id=source) as out:
        out["processed"] = 1
    expected(e, json.loads(ex.metadata)["exchangeId"])
    return e, drain(e)


def test_actual_http_has_source_context_exact_attachment_refs_and_no_branch_execution_claim(client: TestClient) -> None:
    e, records = health(client)
    value = checks().check(e.identity, records)
    row = value["exchanges"][0]
    assert row["flowId"] == "payments.flow.health-alias"
    assert row["outcomeId"] == "payments.outcome.health-alias.http-200"
    assert row["requestAttachment"] in records and row["outcomeAttachment"] in records
    assert row["declaredStepIds"] and row["executedStepIds"] == row["executedRuleIds"] == []
    assert value["primaryWitnesses"][0]["kind"] == "primary-http"


def test_collector_keeps_frozen_records_across_flushes_and_attaches_one_recomputed_group(client: TestClient) -> None:
    e, records = health(client, checked=True)
    # health() already flushed; finish still sees the immutable request and outcome.
    e.finish(lambda name, body: records.__setitem__(name, json.loads(body)))
    assert records[ATTACHMENT]["value"] == {"valid": True, **checks().check(e.identity, records)}
    assert records[ATTACHMENT]["value"]["exchanges"][0]["phase"] == "When"
    assert drain(e) == {}


def test_worker_primary_action_keeps_given_webhook_as_setup_and_has_no_invented_http() -> None:
    e, records = worker()
    value = checks().check(e.identity, records)
    assert [r["kind"] for r in value["primaryWitnesses"]] == ["setup-http", "primary-action"]
    action = value["actions"][0]
    assert action["flowId"] == "payments.flow.fulfill" and action["outcomeId"] == "payments.outcome.command.fulfill"
    assert "status" not in action and action["startAttachment"] in records and action["outcomeAttachment"] in records


@pytest.mark.parametrize(
    "source,phase", [(None, "When"), ("payments.command.replay", "When"), ("payments.command.fulfill", "Given")]
)
def test_setup_response_or_wrong_command_cannot_replace_worker_when(source: str | None, phase: str) -> None:
    e, records = worker(source=source, phase=phase)
    with pytest.raises(ValueError, match="Primary worker"):
        checks().check(e.identity, records)


@pytest.mark.parametrize(
    "drift",
    [
        "foreign",
        "missing-pair",
        "foreign-selected",
        "duplicate-selected",
        "setup",
        "supporting",
        "unrelated",
        "status",
        "expectation",
    ],
)
def test_false_http_witnesses_are_rejected(client: TestClient, drift: str) -> None:
    e, records = health(client)
    req, res = records["HTTP 001 request"], records["HTTP 001 response"]
    if drift == "foreign":
        req["scenarioId"] = "PAY99-99"
    elif drift == "missing-pair":
        del records["HTTP 001 response"]
    elif drift == "foreign-selected":
        records["Expected response"]["exchangeIds"] = ["foreign/1"]
    elif drift == "duplicate-selected":
        records["Expected response"]["exchangeIds"] *= 2
    elif drift in {"setup", "supporting"}:
        req["stepPhase"] = res["stepPhase"] = "Given" if drift == "setup" else "Then"
    elif drift == "unrelated":
        req["path"] = res["path"] = "/health/live"
    elif drift == "status":
        res["status"] = 499
    else:
        records["Expected response"]["value"]["HTTPStatuses"] = "201"
    with pytest.raises(ValueError):
        checks().check(e.identity, records)


def test_external_failure_and_cancellation_remain_non_http_and_join_their_explicit_owner(client: TestClient) -> None:
    e, records = health(client)
    with e.action("Synthetic command cancellation", {}, source_id="payments.command.fulfill"):
        ex = e.begin("GET", "http://orders/orders/1", {}, b"", target="orders", role="fulfillment", controlled=True)
        e.failure(ex, asyncio.CancelledError())
    records.update(drain(e))
    value = checks().check(e.identity, records)
    row = next(r for r in value["exchanges"] if r["targetService"] == "orders")
    assert row["classification"] == "external-boundary"
    assert row["status"] is None and row["operationId"] is None and row["declaredStepIds"] == []
    assert row["outcomeId"] == "payments.outcome.transport.cancelled"
    assert row["ownerSourceId"] == "payments.command.fulfill"
    assert records[row["outcomeAttachment"]]["kind"] == "failure"


def test_receipt_facts_exclude_expected_tokens_preserve_phase_and_do_not_claim_causality(client: TestClient) -> None:
    e, records = health(client)
    receipt = {
        "_id": "evt_actual",
        "event_type": "checkout.session.completed",
        "payload_digest": "a" * 64,
        "received_at": {"$date": "2026-10-30T00:00:00Z"},
        "state": "applied",
        "reason": "payment_succeeded",
        "fulfillment_status": "retry",
        "fulfillment_error": "invoice_create_unavailable",
    }
    e.phase = "Given"
    e.observation("Actual snapshot", {"receipts": [receipt]})
    e.observation("Authored expectation", {**receipt, "state": '"applied"', "received_at": "{before}"})
    records.update(drain(e))
    facts = checks().check(e.identity, records)["receiptFacts"]
    assert len(facts) == 1 and facts[0]["jsonPointer"] == "/value/receipts/0"
    assert facts[0]["phase"] == "Given" and facts[0]["reasonId"] == "payments.receipt.payment_succeeded"
    assert facts[0]["matchingExchangeIds"] == [] and "do not establish causality" in facts[0]["causalityClaim"]
    assert facts[0]["fulfillmentError"] == "invoice_create_unavailable"
    records["Actual snapshot"]["value"]["receipts"][0]["reason"] = "stale_attempt"
    with pytest.raises(ValueError, match="state/reason"):
        checks().check(e.identity, records)
    assert receipt_facts({"state": {"nested": True}}) == []


def test_failed_join_remains_an_observation_without_replacing_any_actual_pair(client: TestClient) -> None:
    e, records = health(client, checked=True)
    # A missing selected witness is recorded as a failed join; the actual response survives.
    e.record("Unexpected observation", {"foreign": "identity"})
    e.finish(lambda name, body: records.__setitem__(name, json.loads(body)))
    assert records[ATTACHMENT]["value"] == {"valid": False, "errorType": "ValueError"}
    assert records["HTTP 001 response"]["status"] == 200


@pytest.mark.parametrize("mutation", ["missing", "forged", "duplicate", "foreign", "absent-case"])
def test_post_suite_gate_recomputes_every_group_and_rejects_missing_cases(
    client: TestClient, tmp_path: Path, mutation: str
) -> None:
    e, records = health(client, checked=True)
    e.finish(lambda name, body: records.__setitem__(name, json.loads(body)))
    if mutation == "missing":
        del records[ATTACHMENT]
    elif mutation == "forged":
        records[ATTACHMENT]["value"]["exchanges"][0]["executedRuleIds"] = ["pretend"]
    elif mutation == "foreign":
        records["HTTP 001 request"]["instanceId"] = "foreign"
    items: list[dict[str, Any]] = []
    for n, (name, record) in enumerate(records.items()):
        source = f"{n}-attachment.json"
        (tmp_path / source).write_text(json.dumps(record))
        items.append(dict(name=name, type="application/json", source=source))
    if mutation == "duplicate":
        items.append(deepcopy(items[-1]))
    (tmp_path / "case-result.json").write_text(json.dumps(dict(attachments=items)))
    with pytest.raises(ValueError):
        check_source_links(knowledge(), document(), FEATURES, tmp_path)
