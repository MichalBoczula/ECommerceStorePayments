import asyncio
import base64
import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, get_ident
from typing import Any
from uuid import uuid4

import pytest
import stripe
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from scripts.bdd_evidence import check_evidence_results, check_result_evidence, check_source_evidence, source_evidence
from scripts.generate_operation_links import FEATURES, MATRIX, ROOT

from ecommerce_store_payments.application.payments.checkout_provider import CheckoutRequest
from ecommerce_store_payments.application.payments.exceptions import CheckoutProviderError, CheckoutTimeoutError
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.clients.stripe.checkout_provider import (
    STRIPE_API_VERSION,
    StripeCheckoutProvider,
)
from ecommerce_store_payments.infrastructure.config.settings import Settings
from tests.acceptance.conftest import AcceptanceStripeTransport
from tests.acceptance.evidence import EvidenceClient, ScenarioEvidence, content_evidence, table_values


def capture() -> ScenarioEvidence:
    return ScenarioEvidence("PAY99-01", "Evidence probe", "PAY99-01 Probe actual capture", {"money": "12.99"})


def drain(evidence: ScenarioEvidence) -> dict[str, Any]:
    records: dict[str, Any] = {}
    evidence.flush(lambda name, body: records.__setitem__(name, json.loads(body)))
    return records


def test_instance_identity_is_canonical_and_separates_scenarios_and_examples() -> None:
    first = ScenarioEvidence("PAY99-01", "A", "First title", {"b": "2", "a": "1"})
    same = ScenarioEvidence("PAY99-01", "B", "Changed display title", {"a": "1", "b": "2"})
    other = ScenarioEvidence("PAY99-01", "A", "First title", {"a": "1", "b": "3"})
    assert first.identity["instanceId"] == same.identity["instanceId"] != other.identity["instanceId"]
    assert first.identity["instanceId"] != capture().identity["instanceId"]
    with pytest.raises(ValueError, match="stable"):
        ScenarioEvidence("random", "A", "Title", {})


@pytest.mark.parametrize(
    ("body", "media", "format_name", "parsed"),
    [
        (b'{"ok":true}', "application/json", "json", {"ok": True}),
        (b'{"broken":', "application/json", "invalid-json", '{"broken":'),
        (b"plain", "text/plain", "text", "plain"),
        (b"\xff", "text/plain", "invalid-text", None),
        (b"%PDF-\x00\xff", "application/pdf", "binary", None),
        (b"", None, "empty", None),
    ],
)
def test_exact_content_preserves_json_malformed_text_binary_and_empty(
    body: bytes,
    media: str | None,
    format_name: str,
    parsed: object,
) -> None:
    record = content_evidence(body, media)
    assert base64.b64decode(record["bodyBytesBase64"]) == body
    assert record["byteLength"] == len(body) and record["bodyFormat"] == format_name and record["body"] == parsed


def test_request_metadata_observations_and_actions_are_immutable_and_do_not_repeat_on_flush() -> None:
    evidence = capture()
    values = {"lines": [1, 2]}
    headers = {"content-type": "application/json", "Authorization": "private-token"}
    evidence.observation("Before", values)
    exchange = evidence.begin("POST", "https://example.test/pay?kind=a", headers, b"{}", target="payments", role="api")
    evidence.phase = "Then"
    values["lines"].append(3)
    headers["content-type"] = "text/plain"
    evidence.response(exchange, 200, {"content-type": "application/json"}, b"{}")
    with evidence.action("Repository preparation", values) as output:
        output["saved"] = [1]
    output["saved"].append(2)
    records = drain(evidence)
    assert records["Before"]["value"] == {"lines": [1, 2]}
    assert records["HTTP 001 request"]["headers"]["authorization"] == "[redacted]"
    assert records["HTTP 001 request"]["headers"]["content-type"] == "application/json"
    assert records["HTTP 001 response"]["stepPhase"] == "Setup"
    assert records["HTTP 001 request"]["query"] == "kind=a"
    assert records["Action 002 result"]["output"] == {"saved": [1]}
    assert drain(evidence) == {}


def test_actual_api_capture_retains_setup_concurrent_and_supporting_exchanges_on_main_thread() -> None:
    app = FastAPI()
    barrier = Barrier(2)

    @app.post("/work")
    def work() -> dict[str, str]:
        barrier.wait(timeout=10)
        return {"status": "done"}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "healthy"}

    evidence = capture()
    with TestClient(app) as raw:
        client = EvidenceClient(raw, evidence)
        evidence.phase = "Given"
        assert client.get("/health").json() == {"status": "healthy"}
        evidence.phase = "When"
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(client.post, "/work", attempt=f"request-{n}") for n in (1, 2)]
            assert all(future.result().json() == {"status": "done"} for future in futures)
        evidence.phase = "Then"
        assert client.get("/health").status_code == 200
    attached: list[tuple[int, dict[str, Any]]] = []
    evidence.finish(lambda _name, body: attached.append((get_ident(), json.loads(body))))
    assert all(thread == get_ident() for thread, _ in attached)
    requests = [record for _, record in attached if record.get("kind") == "request"]
    assert len(requests) == 4 and len({r["exchangeId"] for r in requests}) == 4
    assert [r["stepPhase"] for r in requests] == ["Given", "When", "When", "Then"]
    assert {r["requestAttempt"] for r in requests if r["exchangeRole"] == "api-concurrent"} == {
        "request-1",
        "request-2",
    }
    assert {r["exchangeId"] for r in requests} == {
        record["exchangeId"] for _, record in attached if record.get("kind") == "response"
    }


def test_transport_failure_keeps_request_and_safe_exception_without_a_response() -> None:
    app = FastAPI()

    @app.get("/failure")
    def failure() -> None:
        raise RuntimeError("private-database-password")

    evidence = capture()
    with TestClient(app) as raw, pytest.raises(RuntimeError, match="private"):
        EvidenceClient(raw, evidence).get("/failure")
    records = drain(evidence)
    assert set(records) == {"HTTP 001 request", "HTTP 001 failure"}
    assert records["HTTP 001 failure"]["exceptionType"] == "RuntimeError"
    assert "private-database-password" not in json.dumps(records)


async def test_actual_stripe_sdk_edges_capture_rejection_and_lost_response_and_redact_authorization() -> None:
    evidence = capture()
    boundary = AcceptanceStripeTransport(evidence)
    settings = Settings(stripe_enabled=True, stripe_secret_key=SecretStr("sk_test_fixture"))
    sdk = stripe.StripeClient(
        "sk_test_fixture", stripe_version=STRIPE_API_VERSION, http_client=boundary, max_network_retries=0
    )
    provider = StripeCheckoutProvider(settings, sdk)
    request = CheckoutRequest(uuid4(), uuid4(), uuid4(), Money(1299, "PLN"))
    await provider.create(request)
    records = drain(evidence)
    assert records["HTTP 001 request"]["targetService"] == "stripe"
    assert "sk_test_fixture" not in json.dumps(records)
    assert records["HTTP 001 response"]["status"] == 200
    boundary.mode = "rejection"
    with pytest.raises(CheckoutProviderError):
        await provider.create(request)
    assert drain(evidence)["HTTP 002 response"]["status"] == 400
    boundary.mode = "timeout_once"
    with pytest.raises(CheckoutTimeoutError):
        await provider.create(request)
    records = drain(evidence)
    assert records["HTTP 003 failure"]["exceptionType"] == "APIConnectionError"
    assert "private timeout" not in json.dumps(records)


def test_failed_and_cancelled_actions_keep_start_and_safe_outcome_and_restore_owner() -> None:
    evidence = capture()
    for error in (ValueError("private"), asyncio.CancelledError("private")):
        with pytest.raises(type(error)), evidence.action("Command", {"limit": 100}):
            raise error
    records = drain(evidence)
    assert len(records) == 4 and all("private" not in json.dumps(record) for record in records.values())
    exchange = evidence.begin("GET", "/health", {}, b"", target="payments", role="api")
    assert json.loads(exchange.metadata)["actionId"] is None


@pytest.mark.parametrize("table", [[], [["Wrong", "Value"], ["A", "1"]], [["Field", "Value"], ["A", "1"], ["A", "2"]]])
def test_invalid_gherkin_tables_cannot_silently_override_inputs(table: list[list[str]]) -> None:
    with pytest.raises(ValueError):
        table_values(table)


def bundle(tmp_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    profile = source_evidence(FEATURES)["PAY11-19"]
    evidence = ScenarioEvidence("PAY11-19", profile["feature"], profile["scenario"], {})
    evidence.record("Scenario identity", evidence.identity)
    evidence.observation("Scenario inputs", profile["inputs"])
    evidence.phase = "When"
    exchange = evidence.begin("GET", "http://testserver/health/live", {}, b"", target="payments", role="api")
    evidence.response(exchange, 200, {"content-type": "application/json"}, b'{"status":"healthy"}')
    evidence.record(
        "Expected response",
        {
            **evidence.identity,
            "value": profile["expected"],
            "exchangeIds": [json.loads(exchange.metadata)["exchangeId"]],
        },
    )
    result: dict[str, Any] = {
        "name": profile["scenario"],
        "description": profile["description"],
        "labels": [{"name": key, "value": evidence.identity[key]} for key in ("service", "scenarioId", "instanceId")],
        "attachments": [],
    }

    def save(name: str, body: str, media: str = "application/json") -> None:
        path = f"{len(result['attachments'])}.{'json' if media == 'application/json' else 'csv'}"
        (tmp_path / path).write_text(body)
        result["attachments"].append({"name": name, "source": path, "type": media})

    evidence.finish(save)
    for key in ("inputs", "expected"):
        buffer = io.StringIO()
        csv.writer(buffer).writerows([["Field", "Value"], *profile[key].items()])
        save("Data table", buffer.getvalue(), "text/csv")
    return result, profile


def test_current_source_and_complete_captured_evidence_are_publishable(tmp_path: Path) -> None:
    check_source_evidence(FEATURES, MATRIX)
    assert len(source_evidence(FEATURES)) == 99
    result, profile = bundle(tmp_path)
    check_result_evidence(result, profile, tmp_path)


@pytest.mark.parametrize(
    "mutation",
    [
        "description",
        "label",
        "file",
        "unsafe",
        "foreign",
        "request",
        "bytes",
        "index",
        "witness",
        "table",
        "expectation",
        "json",
        "association",
    ],
)
def test_corrupt_or_incomplete_attachments_fail_publication(mutation: str, tmp_path: Path) -> None:
    result, profile = bundle(tmp_path)
    if mutation == "description":
        result["description"] = ""
    elif mutation == "label":
        result["labels"].append(result["labels"][0])
    elif mutation == "file":
        (tmp_path / result["attachments"][0]["source"]).unlink()
    elif mutation == "unsafe":
        result["attachments"][0]["source"] = "../other.json"
    elif mutation in {"request", "table"}:
        result["attachments"] = [
            a
            for a in result["attachments"]
            if not (a["name"] == "HTTP 001 request" if mutation == "request" else a["type"] == "text/csv")
        ]
    else:
        name = {
            "foreign": "HTTP 001 request",
            "bytes": "HTTP 001 response",
            "index": "Scenario evidence index",
            "witness": "Expected response",
            "expectation": "Expected response",
            "json": "HTTP 001 response",
            "association": "HTTP 001 response",
        }[mutation]
        attachment = next(a for a in result["attachments"] if a["name"] == name)
        path = tmp_path / attachment["source"]
        record = json.loads(path.read_text())
        if mutation == "foreign":
            record["instanceId"] = "foreign"
        elif mutation == "bytes":
            record["content"]["sha256"] = "0" * 64
        elif mutation == "index":
            record["exchanges"] = []
        elif mutation == "witness":
            record["exchangeIds"] = []
        elif mutation == "expectation":
            record["value"] = {}
        elif mutation == "association":
            record["stepPhase"] = "Then"
        elif mutation == "json":
            record["content"] = content_evidence(b'{"status":"wrong"}', "application/json")
        path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        check_result_evidence(result, profile, tmp_path)


@pytest.mark.parametrize("mutation", ["description", "inputs", "expected", "status"])
def test_missing_or_stale_source_documentation_fails_before_execution(mutation: str, tmp_path: Path) -> None:
    shutil.copytree(FEATURES, tmp_path / "features")
    path = tmp_path / "features/health.feature"
    text = path.read_text()
    if mutation == "description":
        text = text.replace(source_evidence(FEATURES)["PAY11-19"]["description"], "")
    elif mutation == "inputs":
        text = text.replace("Given the health request uses", "Given another setup", 1)
    elif mutation == "expected":
        text = text.replace("HTTPStatuses", "OtherStatus", 1)
    else:
        text = re.sub(r"(\|\s*HTTPStatuses\s*\|\s*)200(\s*\|)", r"\g<1>201\2", text, count=1)
    path.write_text(text)
    with pytest.raises(ValueError):
        check_source_evidence(tmp_path / "features", MATRIX)


@pytest.mark.parametrize("fail_after_supporting", [False, True])
def test_actual_allure_hooks_render_health_descriptions_tables_and_supporting_calls(
    tmp_path: Path,
    fail_after_supporting: bool,
) -> None:
    features = tmp_path / "features"
    features.mkdir()
    shutil.copyfile(FEATURES / "health.feature", features / "health.feature")
    probe = tmp_path / "test_probe.py"
    probe.write_text("""from typing import cast
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo import MongoClient
from pytest_bdd import scenarios, given, then, parsers
from tests.acceptance.conftest import AcceptanceContext, AcceptanceStripeTransport, OrdersBoundary
from tests.acceptance.evidence import EvidenceClient, ScenarioEvidence
from tests.acceptance.test_api import matches_matrix, readiness_unavailable, no_secret, liveness_after_failure
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument

scenarios("features/health.feature")

@then(parsers.parse('the response matches case "{case_id}"'))
def response_step(acceptance, case_id, datatable):
    matches_matrix(acceptance, case_id, datatable)

@given("the MongoDB readiness probe fails")
def readiness_step(acceptance, monkeypatch):
    readiness_unavailable(acceptance, monkeypatch)

@then("the error hides the database failure")
def safe_step(acceptance):
    no_secret(acceptance)

@then("liveness is still healthy")
def supporting_step(acceptance):
    liveness_after_failure(acceptance)

@pytest.fixture
def acceptance(client: TestClient, evidence: ScenarioEvidence):
    settings = cast(FastAPI, client.app).state.database.settings
    yield AcceptanceContext(client=EvidenceClient(client, evidence), evidence=evidence, orders=OrdersBoundary(),
                            settings=settings, mongo=cast(MongoClient[PaymentDocument], object()),
                            stripe=AcceptanceStripeTransport(evidence))
""")
    if fail_after_supporting:
        probe.write_text(
            probe.read_text().replace(
                "    liveness_after_failure(acceptance)",
                "    liveness_after_failure(acceptance)\n    assert False, 'deliberate probe assertion'",
            )
        )
    results = tmp_path / "results"
    environment = {**os.environ, "PYTHONPATH": os.pathsep.join((str(ROOT), str(ROOT / "src")))}
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(ROOT / "pyproject.toml"),
            "--rootdir",
            str(tmp_path),
            "-p",
            "tests.conftest",
            "-p",
            "tests.acceptance.conftest",
            str(probe),
            f"--alluredir={results}",
            "-q",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == (1 if fail_after_supporting else 0), process.stdout + process.stderr
    check_evidence_results(features, results)
    cases = [json.loads(p.read_text()) for p in results.glob("*-result.json")]
    assert len(cases) == 4
    assert sum(case["status"] == "failed" for case in cases) == int(fail_after_supporting)
    assert sum(case["status"] == "passed" for case in cases) == 4 - int(fail_after_supporting)
    failed_readiness = next(case for case in cases if case["name"].startswith("PAY11-21"))
    from scripts.bdd_evidence import attachments

    records = [
        json.loads((results / a["source"]).read_text())
        for a in attachments(failed_readiness)
        if a["type"] == "application/json"
    ]
    assert any(
        r.get("kind") == "response" and r["path"] == "/health/live" and r["stepPhase"] == "Then" for r in records
    )
