import asyncio
import csv
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from scripts.bdd_evidence import source_evidence
from scripts.generate_operation_links import FEATURES, MATRIX, generate
from scripts.technical_scenarios import (
    TECHNICAL,
    check_technical_result,
    check_technical_source,
    technical_links,
    technical_rows,
)

from tests.acceptance.evidence import AsyncEvidenceClient
from tests.unit.api.test_bdd_evidence import capture, drain


@pytest.mark.parametrize(
    ("index", "key", "value"),
    [
        (0, "kind", "invented"),
        (0, "operation", "GET /invented-docs"),
        (0, "operation", "POST /swagger"),
        (0, "requirement", "PAY/999"),
        (0, "status", "499"),
        (0, "status", "503"),
        (0, "media", "application/json"),
        (0, "code", "service_unavailable"),
        (0, "exception", "CancelledError"),
        (6, "status", "499"),
        (6, "media", "application/json"),
        (6, "code", "cancelled"),
        (6, "exception", "TimeoutError"),
        (6, "operation", "GET /swagger"),
        (9, "operation", "COMMAND invented"),
        (9, "operation", "GET /health/ready"),
        (9, "status", "200"),
        (9, "media", "application/json"),
        (9, "code", "internal_error"),
        (9, "kind", "response"),
        (9, "kind", "cancelled"),
    ],
)
def test_source_projection_rejects_invented_routes_statuses_and_cancellation(index: int, key: str, value: str) -> None:
    rows = technical_rows()
    rows[index][key] = value
    with pytest.raises(ValueError):
        technical_links(rows, {"PAY/22"})


@pytest.mark.parametrize("mutation", ["duplicate", "missing-column", "empty", "extra-column"])
def test_technical_matrix_requires_complete_unique_rows(mutation: str, tmp_path: Path) -> None:
    rows = technical_rows()
    fields = list(rows[0])
    if mutation == "duplicate":
        rows.append(rows[0])
    elif mutation == "missing-column":
        fields.remove("exception")
        rows = [{k: v for k, v in row.items() if k in fields} for row in rows]
    elif mutation == "empty":
        rows[0]["cause"] = ""
    else:
        fields.append("invented")
        rows = [{**row, "invented": "wrong"} for row in rows]
    path = tmp_path / "technical.tsv"
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError):
        technical_rows(path)


def test_technical_cases_preserve_named_api_coverage_and_join_real_sources() -> None:
    links = generate()
    assert links["coverage"]["expandedBddCases"] == 391
    assert links["coverage"]["technicalCases"] == 21
    assert links["coverage"]["guaranteedScenarioStatusPairs"] == 42
    assert links["coverage"]["matchedRouteCases"] == 367
    assert len(links["operations"]) == 7
    rows = links["technicalScenarios"]
    assert len(rows) == 21 and {r["kind"] for r in rows} == {"response", "cancelled", "action"}
    assert all(r["source"] and r["requirement"] == "PAY/22" for r in rows)
    assert all(not r["id"].startswith("PAY13-") for op in links["operations"] for r in op["scenarios"])
    profiles = source_evidence(FEATURES)
    for row in technical_rows():
        check_technical_source(profiles[row["id"]], row)
    assert TECHNICAL != MATRIX


@pytest.mark.parametrize("field", ["Outcome", "HTTPStatuses", "ContentType", "Code", "ExceptionType", "Result"])
def test_native_technical_table_must_match_projection(field: str) -> None:
    row = technical_rows()[6]
    profile: dict[str, Any] = {
        "technical": True,
        "expected": dict(
            Outcome="cancelled",
            HTTPStatuses="<none>",
            ContentType="<none>",
            Code="-",
            ExceptionType="CancelledError",
            Result="cancelled",
        ),
    }
    check_technical_source(profile, row)
    profile["expected"][field] = "wrong"
    with pytest.raises(ValueError):
        check_technical_source(profile, row)


def outcome(kind: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    expected = dict(
        Outcome=kind,
        HTTPStatuses="200" if kind == "response" else "<none>",
        ContentType="application/json" if kind == "response" else "<none>",
        Code="-",
        ExceptionType="CancelledError" if kind == "cancelled" else "<none>",
        Result=kind,
    )
    expectation = {
        "exchangeIds": [] if kind == "action" else ["exchange"],
        "actionIds": [] if kind == "response" else ["action"],
    }
    records = {
        "start": {"kind": "action-start", "actionId": "action"},
        "end": {
            "kind": "action-result",
            "actionId": "action",
            "output": {"result": kind, "exceptionType": expected["ExceptionType"]},
        },
    }
    pair: list[dict[str, Any]] = [{"kind": "request", "actionId": "action"}]
    pair.append(
        {"kind": "failure", "cancelled": True, "exceptionType": "CancelledError"}
        if kind == "cancelled"
        else {
            "kind": "response",
            "status": 200,
            "targetService": "payments",
            "content": {"contentType": "application/json", "body": {"ok": True}},
        }
    )
    return expectation, expected, {"exchange": pair}, records


@pytest.mark.parametrize("kind", ["response", "cancelled", "action"])
def test_real_outcome_kinds_have_separate_witness_requirements(kind: str) -> None:
    check_technical_result(*outcome(kind))


@pytest.mark.parametrize(
    "mutation",
    [
        "no-exchange",
        "duplicate-exchange",
        "response-after-cancel",
        "not-cancelled",
        "wrong-exception",
        "no-action",
        "duplicate-action",
        "wrong-owner",
        "no-start",
        "no-end",
        "wrong-result",
        "wrong-action-exception",
        "invented-499",
    ],
)
def test_cancelled_outcomes_cannot_replace_real_failure_and_action_witnesses(mutation: str) -> None:
    expectation, expected, pairs, records = outcome("cancelled")
    if mutation == "no-exchange":
        expectation["exchangeIds"] = []
    elif mutation == "duplicate-exchange":
        expectation["exchangeIds"] *= 2
    elif mutation == "response-after-cancel":
        pairs["exchange"].append({"kind": "response"})
    elif mutation == "not-cancelled":
        pairs["exchange"][1]["cancelled"] = False
    elif mutation == "wrong-exception":
        pairs["exchange"][1]["exceptionType"] = "TimeoutError"
    elif mutation == "no-action":
        expectation["actionIds"] = []
    elif mutation == "duplicate-action":
        expectation["actionIds"] *= 2
    elif mutation == "wrong-owner":
        pairs["exchange"][0]["actionId"] = "foreign"
    elif mutation == "no-start":
        del records["start"]
    elif mutation == "no-end":
        del records["end"]
    elif mutation == "wrong-result":
        records["end"]["output"]["result"] = "wrong"
    elif mutation == "wrong-action-exception":
        records["end"]["output"]["exceptionType"] = "TimeoutError"
    else:
        expected["HTTPStatuses"] = "499"
    with pytest.raises(ValueError):
        check_technical_result(expectation, expected, pairs, records)


@pytest.mark.parametrize(
    "mutation",
    [
        "no-response",
        "wrong-service",
        "wrong-status",
        "wrong-media",
        "wrong-code",
        "json-type",
        "invented-action",
        "action-http",
    ],
)
def test_technical_responses_and_actions_cannot_claim_different_outcomes(mutation: str) -> None:
    expectation, expected, pairs, records = outcome("action" if mutation == "action-http" else "response")
    if mutation == "no-response":
        pairs["exchange"] = pairs["exchange"][:1]
    elif mutation == "wrong-service":
        pairs["exchange"][1]["targetService"] = "orders"
    elif mutation == "wrong-status":
        pairs["exchange"][1]["status"] = 503
    elif mutation == "wrong-media":
        pairs["exchange"][1]["content"]["contentType"] = "text/html"
    elif mutation == "wrong-code":
        expected["Code"] = "different"
    elif mutation == "json-type":
        expected["JSON.ok"] = "1"
    elif mutation == "invented-action":
        expectation["actionIds"] = ["action"]
    else:
        expectation["exchangeIds"] = ["exchange"]
    with pytest.raises(ValueError):
        check_technical_result(expectation, expected, pairs, records)


async def test_actual_asgi_cancellation_records_failure_without_response_and_restores_owner() -> None:
    app = FastAPI()
    entered = asyncio.Event()

    @app.get("/probe")
    async def probe() -> None:
        entered.set()
        await asyncio.Event().wait()

    evidence = capture()
    async with AsyncClient(transport=ASGITransport(app), base_url="http://cancel.test") as raw:
        client = AsyncEvidenceClient(raw, evidence)
        with evidence.action("Actual cancellation", {}):
            owner = evidence.active_action_id
            task = asyncio.create_task(client.request("GET", "/probe"))
            await asyncio.wait_for(entered.wait(), 2)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        assert evidence.active_action_id is None
    records = drain(evidence)
    assert raw.is_closed and not any(v.get("kind") == "response" for v in records.values())
    requests = [v for v in records.values() if v.get("kind") == "request"]
    assert len(requests) == 1 and requests[0]["actionId"] == owner
    failures = [v for v in records.values() if v.get("kind") == "failure"]
    assert len(failures) == 1
    failure = failures[0]
    assert failure["exceptionType"] == "CancelledError" and failure["cancelled"] is True
    assert "status" not in failure
    assert client.cancelled_exchange_id == failure["exchangeId"]
