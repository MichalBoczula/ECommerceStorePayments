"""Replay the pinned Web Pact against the real Payments HTTP API."""

import hashlib
import json
import os
import socket
import subprocess
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from threading import Thread
from time import monotonic, sleep
from typing import Any
from uuid import UUID, uuid4

from httpx import Client, TransportError
from pact import Verifier
from pymongo import MongoClient
from pymongo.collection import Collection
from uvicorn import Config, Server

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "contracts/pact/web-payments.json"
SOURCE = CONTRACT.with_name("web-source.json")
HOST = "127.0.0.1"
PAYMENT_STATE = "a succeeded payment exists for an order and another order has no payment"


@contextmanager
def live_payments(settings: Settings) -> Generator[str]:
    with socket.socket() as listener:
        listener.bind((HOST, 0))
        origin = f"http://{HOST}:{listener.getsockname()[1]}"
        server = Server(Config(create_app(settings), loop="asyncio", ws="none", timeout_graceful_shutdown=5))
        thread = Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        thread.start()
        try:
            with Client(base_url=origin, timeout=2, trust_env=False) as http:
                deadline = monotonic() + 30
                while thread.is_alive() and monotonic() < deadline:
                    try:
                        if http.get("/health/ready").status_code == 200:
                            break
                    except TransportError:
                        pass
                    sleep(0.25)
                else:
                    raise RuntimeError("Payments did not become ready.")
            yield origin
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            if thread.is_alive():
                raise RuntimeError("Payments did not stop after verification.")


def payment_state(collection: Collection[PaymentDocument], state: str, action: str, parameters: dict[str, Any]) -> None:
    if state != PAYMENT_STATE or action not in ("setup", "teardown"):
        raise ValueError("Unknown Pact provider state or action.")
    example = parameters["payment"]
    order_id = UUID(example["order_id"])
    missing_order_id = UUID(parameters["missingOrderId"])
    if order_id == missing_order_id or example["status"] != PaymentStatus.SUCCEEDED.value:
        raise ValueError("The Pact requires a succeeded payment and a distinct missing order.")
    collection.delete_many({"order_id": {"$in": [order_id, missing_order_id]}})
    if action == "setup":
        payment = Payment.rehydrate(
            payment_id=UUID(example["id"]),
            order_id=order_id,
            money=Money(amount_minor=example["amount_minor"], currency=example["currency"]),
            status=PaymentStatus.SUCCEEDED,
            provider_session_id="cs_test_pact_fixture",
            provider_payment_id="pi_pact_fixture",
            failure_code=None,
            created_at=datetime(2026, 9, 29, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 9, 29, 12, 5, tzinfo=UTC),
        )
        collection.insert_one(PaymentMapper.to_document(payment))


def summarize(result: dict[str, Any], interactions: list[dict[str, Any]]) -> tuple[str, int, int, list[dict[str, Any]]]:
    expected = {item["description"]: item["request"] for item in interactions}
    rows: list[dict[str, Any]] = result.get("interactionResults", [])
    descriptions = [row["description"] for row in rows]
    if len(rows) != len(expected) or set(descriptions) != expected.keys() or any(row["pending"] for row in rows):
        return (
            "Error",
            0,
            0,
            [
                {
                    "kind": "ExecutionError",
                    "code": "IncompletePactExecution",
                    "message": "Pact did not report every interaction.",
                }
            ],
        )

    verified = failed = 0
    issues: list[dict[str, Any]] = []
    for row in rows:
        if row["result"] == "OK":
            verified += 1
            continue
        name = row["description"]
        mismatches = row.get("mismatch", {}).get("mismatches", [])
        if not mismatches:
            issues.append(
                {
                    "kind": "ExecutionError",
                    "code": "PactExecutionError",
                    "message": "Pact could not execute the interaction. See the CI artifact.",
                    "interaction": name,
                }
            )
            continue
        failed += 1
        for mismatch in mismatches:
            issue = {
                "kind": "Mismatch",
                "code": mismatch["type"],
                "message": mismatch["mismatch"][:4096],
                "interaction": name,
                "method": expected[name]["method"],
                "path": expected[name]["path"],
                "jsonPath": mismatch.get("path") or mismatch.get("key") or "$",
                "expected": mismatch.get("expected"),
                "actualPresent": "actual" in mismatch,
            }
            if issue["actualPresent"]:
                issue["actual"] = mismatch["actual"]
            issues.append(issue)
    if not result["result"] and not issues:
        issues.append(
            {
                "kind": "ExecutionError",
                "code": "PactExecutionError",
                "message": "Pact reported an execution error. See the CI artifact.",
            }
        )
    if any(issue["kind"] == "ExecutionError" for issue in issues):
        return "Error", verified, failed, issues
    return ("Failed" if failed else "Passed"), verified, failed, issues


def verify_web_pact(mongo_url: str, results: Path) -> dict[str, Any]:
    source = json.loads(SOURCE.read_bytes())
    content = CONTRACT.read_bytes()
    pact = json.loads(content)
    interactions = pact["interactions"]
    digest = hashlib.sha256(content).hexdigest()
    if (
        digest != source["contractSha256"]
        or len(interactions) != source["interactionCount"]
        or pact["consumer"]["name"] != "web"
        or pact["provider"]["name"] != "payments"
        or pact["metadata"]["pactSpecification"]["version"] != "4.0"
    ):
        raise ValueError("Pinned Web Pact identity or bytes changed.")

    results.mkdir(parents=True, exist_ok=True)
    os.environ["PACT_DO_NOT_TRACK"] = "true"
    settings = Settings(
        environment="test",
        mongodb_connection_string=mongo_url,
        mongodb_database_name=f"payments_pact_{uuid4().hex}",
        orders_api_base_url=f"http://{HOST}:1",
        stripe_enabled=False,
        stripe_checkout_vat_enabled=False,
        stripe_secret_key=None,
        stripe_webhook_secret=None,
    )
    started = datetime.now(UTC)
    with MongoClient[PaymentDocument](mongo_url, uuidRepresentation="standard", serverSelectionTimeoutMS=1000) as mongo:
        collection = mongo[settings.mongodb_database_name][settings.mongodb_payments_collection_name]

        def handle_state(state: str, action: str, parameters: dict[str, Any]) -> None:
            payment_state(collection, state, action, parameters)

        try:
            with live_payments(settings) as origin:
                verifier = (
                    Verifier("payments", host=HOST)
                    .add_transport(url=origin)
                    .add_source(CONTRACT)
                    .state_handler(handle_state, teardown=True)
                )
                try:
                    verifier.verify()
                except RuntimeError:
                    # Pact raises on mismatches and supplies its report for diagnosis.
                    pass
                result = verifier.results
        finally:
            mongo.drop_database(settings.mongodb_database_name)

    (results / "pact-results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    status, verified, failed, issues = summarize(result, interactions)
    configuration = b"\0".join((Path(__file__).read_bytes(), (ROOT / "uv.lock").read_bytes()))
    report = {
        "consumerCommitSha": source["commitSha"],
        "contractSha256": digest,
        "providerCommitSha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "verifierName": "pact-python",
        "verifierVersion": version("pact-python"),
        "configurationSha256": hashlib.sha256(configuration).hexdigest(),
        "status": status,
        "verifiedInteractions": verified,
        "failedInteractions": failed,
        "issues": issues,
        "summary": f"Payments HTTP provider Pact verification {status.lower()} with {verified} matching interactions.",
        "startedAt": started.isoformat(),
        "finishedAt": datetime.now(UTC).isoformat(),
    }
    (results / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def test_pinned_web_payments_pact(mongo_url: str, tmp_path: Path) -> None:
    results = Path(os.environ.get("PAYMENTS_PROVIDER_PACT_DIR", str(tmp_path)))
    report = verify_web_pact(mongo_url, results)
    assert report["status"] == "Passed", report["issues"]
