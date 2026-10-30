"""Reject lost scope, unbounded coordination and incomplete real-write witnesses."""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pytest_bdd.parser import FeatureParser
from scripts.generate_operation_links import FEATURES

from tests.acceptance.atomicity_checks import assert_staged_write
from tests.acceptance.concurrency_checks import WriteGates, assert_schedule, coordinated_payload
from tests.acceptance.evidence import REQUEST_ATTEMPT, EvidenceClient, ScenarioEvidence, attempt_scope, table_values
from tests.acceptance.payment_checks import Snapshot, lossless

NOW = datetime(2026, 10, 1, 12, tzinfo=UTC)
ORDER, PAYMENT, OTHER, ATTEMPT = (UUID(int=i) for i in (1, 2, 3, 4))


def current() -> dict[str, Any]:
    return dict(
        _id=PAYMENT,
        order_id=ORDER,
        amount_minor=1299,
        currency="PLN",
        status="created",
        provider_session_id=None,
        provider_payment_id=None,
        failure_code=None,
        created_at=NOW - timedelta(seconds=10),
        updated_at=None,
        version=0,
        checkout_attempt_id=None,
        checkout_started_at=None,
        checkout_request_version=1,
    )


def collections() -> Snapshot:
    return dict(
        payments=[{**current(), "_id": OTHER, "order_id": OTHER, "amount_minor": 3173}],
        payment_history=[{"_id": "unrelated", "value": "preserve"}],
        stripe_webhooks=[{"_id": "unrelated", "state": "applied", "value": "preserve"}],
    )


def capture() -> ScenarioEvidence:
    return ScenarioEvidence("PAY12-03", "Concurrency", "Wire scope", {})


def drain(evidence: ScenarioEvidence) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    evidence.flush(lambda _name, body: records.append(json.loads(body)))
    return records


def test_actual_attempt_header_and_async_outbound_capture_keep_each_request_scope() -> None:
    evidence, gates, app = capture(), WriteGates(), FastAPI()

    @app.post("/work")
    async def endpoint(request: Request) -> dict[str, str]:
        label = request.headers["x-bdd-attempt"]
        assert REQUEST_ATTEMPT.get() == label
        await gates.pause(label, "wire")
        exchange = evidence.begin("GET", "https://orders.test/order", {}, b"", target="orders", role="boundary")
        evidence.response(exchange, 200, {"content-type": "application/json"}, b"{}")
        return {"attempt": label}

    with TestClient(app) as raw, ThreadPoolExecutor(max_workers=2) as pool:
        client = EvidenceClient(raw, evidence)
        futures = {label: pool.submit(client.post, "/work", attempt=label) for label in ("first", "second")}
        try:
            gates.wait(("first", "second"), "wire")
            gates.release("second", "wire")
            assert futures["second"].result(timeout=5).json() == {"attempt": "second"}
            assert not futures["first"].done()
            gates.release("first", "wire")
            assert futures["first"].result(timeout=5).json() == {"attempt": "first"}
        finally:
            gates.open_all()
    assert REQUEST_ATTEMPT.get() is None
    requests = [r for r in drain(evidence) if r.get("kind") == "request"]
    assert len(requests) == 4
    for label in ("first", "second"):
        matching = [r for r in requests if r["requestAttempt"] == label]
        assert {r["targetService"] for r in matching} == {"payments", "orders"}
        assert next(r for r in matching if r["targetService"] == "payments")["headers"]["x-bdd-attempt"] == label


@pytest.mark.parametrize("failure", [False, True])
def test_nested_attempt_scope_restores_its_parent_and_never_leaks(failure: bool) -> None:
    assert REQUEST_ATTEMPT.get() is None
    with attempt_scope("first"):
        try:
            with attempt_scope("second"):
                assert REQUEST_ATTEMPT.get() == "second"
                if failure:
                    raise ValueError("controlled scope failure")
        except ValueError:
            assert failure
        assert REQUEST_ATTEMPT.get() == "first"
    assert REQUEST_ATTEMPT.get() is None


def test_mismatched_wire_and_coordination_attempt_are_rejected_before_sending() -> None:
    app = FastAPI()
    with TestClient(app) as raw, pytest.raises(AssertionError):
        EvidenceClient(raw, capture()).post("/work", attempt="first", headers={"x-bdd-attempt": "second"})
    assert REQUEST_ATTEMPT.get() is None


@pytest.mark.parametrize("winner", ["first", "second"])
async def test_gates_do_not_block_the_loop_and_only_release_the_selected_write(winner: str) -> None:
    gates = WriteGates()
    tasks = {label: asyncio.create_task(gates.pause(label, "write", version=0)) for label in ("first", "second")}
    try:
        await gates.wait_async(("first", "second"), "write")
        gates.release(winner, "write")
        await tasks[winner]
        loser = "second" if winner == "first" else "first"
        assert not tasks[loser].done()
        gates.release(loser, "write")
        await tasks[loser]
        assert {w["attempt"] for w in gates.witnesses} == {"first", "second"}
    finally:
        gates.open_all()
        await asyncio.gather(*tasks.values())


async def test_cleanup_opens_existing_and_future_waiters_and_deduplicates_retry_arrivals() -> None:
    gates = WriteGates()
    task = asyncio.create_task(gates.pause("first", "write", version=0))
    await gates.wait_async(("first",), "write")
    gates.open_all()
    await task
    await gates.pause("first", "write", version=1)
    await gates.pause("second", "write", version=0)
    assert len(gates.witnesses) == 2 and gates.witnesses[0]["version"] == 0


def test_missing_arrival_is_bounded_and_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    gates = WriteGates()
    monkeypatch.setattr(gates, "TIMEOUT", 0.001)
    with pytest.raises(AssertionError, match="did not reach"):
        gates.wait(("first",), "write")


async def test_missing_release_is_bounded_and_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    gates = WriteGates()
    monkeypatch.setattr(gates, "TIMEOUT", 0.001)
    with pytest.raises(TimeoutError):
        await gates.pause("first", "write")
    gates.open_all()


def schedule() -> tuple[Snapshot, Snapshot, list[dict[str, Any]]]:
    before = collections()
    first, second = current(), {**current(), "_id": UUID(int=99)}
    after = deepcopy(before)
    after["payments"].append(first)
    witnesses: list[dict[str, Any]] = [
        dict(attempt=label, point="write", proposed=lossless(proposed), collections=lossless(before))
        for label, proposed in [("first", first), ("second", second)]
    ]
    witnesses.append(
        dict(attempt="second", point="rejected-write", exception="PaymentDuplicateError", expectedVersion=0)
    )
    return before, after, witnesses


@pytest.mark.parametrize(
    "mutation",
    [
        "none",
        "missing",
        "duplicate",
        "scope",
        "version",
        "order",
        "outside",
        "exception",
        "conflict_scope",
        "conflict_version",
        "winner_id",
        "winner_money",
        "winner_time",
        "winner_extra",
    ],
)
def test_complete_schedule_joins_real_scope_proposal_conflict_and_exact_winner(mutation: str) -> None:
    before, after, witnesses = schedule()
    proposal = witnesses[0]
    if mutation == "missing":
        witnesses.pop(0)
    elif mutation == "duplicate":
        witnesses.append(deepcopy(proposal))
    elif mutation == "scope":
        proposal["attempt"] = "not-a-participant"
    elif mutation == "version":
        proposal["proposed"]["version"] = lossless(1)
    elif mutation == "order":
        proposal["proposed"]["order_id"] = lossless(OTHER)
    elif mutation == "outside":
        proposal["collections"]["stripe_webhooks"] = []
    elif mutation == "exception":
        witnesses[-1]["exception"] = "RuntimeError"
    elif mutation == "conflict_scope":
        witnesses[-1]["attempt"] = "first"
    elif mutation == "conflict_version":
        witnesses[-1]["expectedVersion"] = 1
    elif mutation == "winner_id":
        after["payments"][-1]["_id"] = UUID(int=99)
    elif mutation == "winner_money":
        after["payments"][-1]["amount_minor"] = 1300
    elif mutation == "winner_time":
        after["payments"][-1]["created_at"] += timedelta(seconds=1)
    elif mutation == "winner_extra":
        after["payments"][-1]["extra"] = True
    if mutation == "none":
        assert_schedule("pay-create", "first", witnesses, before, after, ORDER)
    else:
        with pytest.raises((AssertionError, StopIteration)):
            assert_schedule("pay-create", "first", witnesses, before, after, ORDER)


def staged(command: str, point: str) -> tuple[Snapshot, Snapshot, Snapshot]:
    before = collections()
    prior = current()
    if command == "webhook":
        prior.update(
            status="pending",
            version=2,
            updated_at=NOW - timedelta(seconds=1),
            provider_session_id="cs_fixture",
            checkout_attempt_id=ATTEMPT,
            checkout_started_at=NOW - timedelta(seconds=2),
            checkout_request_version=2,
        )
        before["stripe_webhooks"].append(
            dict(
                _id="evt_atomic_rollback",
                state="pending",
                reason=None,
                completed_at=None,
                fulfillment_status=None,
                received_at=NOW - timedelta(seconds=1),
                payload_digest="exact",
                payment_id=PAYMENT,
            )
        )
    before["payments"].append(prior)
    inside = deepcopy(before)
    changed = inside["payments"][-1]
    changed.update(version=prior["version"] + 1, updated_at=NOW)
    if command == "checkout":
        changed.update(checkout_attempt_id=ATTEMPT, checkout_started_at=NOW, checkout_request_version=2)
    else:
        changed.update(status="succeeded", provider_payment_id="pi_fixture", failure_code=None)
    if point != "payments.replace_one":
        archive = {k: v for k, v in prior.items() if k != "_id"}
        archive.update(_id=f"{PAYMENT}:{prior['version']}", payment_id=PAYMENT, recorded_at=NOW)
        inside["payment_history"].append(archive)
    if point == "stripe_webhooks.replace_one":
        inside["stripe_webhooks"][-1].update(
            state="applied", reason="payment_succeeded", completed_at=NOW, fulfillment_status="pending"
        )
    return before, inside, deepcopy(before)


@pytest.mark.parametrize(
    ("command", "point"),
    [
        ("checkout", "payments.replace_one"),
        ("checkout", "payment_history.insert_one"),
        ("webhook", "payments.replace_one"),
        ("webhook", "payment_history.insert_one"),
        ("webhook", "stripe_webhooks.replace_one"),
    ],
)
def test_each_post_write_stage_requires_complete_session_and_outside_state(command: str, point: str) -> None:
    before, inside, outside = staged(command, point)
    assert_staged_write(before, inside, outside, ORDER, command, point, (NOW, NOW))


@pytest.mark.parametrize(
    "mutation",
    [
        "outside",
        "version",
        "order",
        "money",
        "session",
        "created",
        "updated",
        "unrelated_payment",
        "lost_history",
        "extra_history",
        "archive_amount",
        "archive_version",
        "extra_receipt",
        "receipt_received",
        "receipt_reason",
        "receipt_marker",
        "wrong_stage",
    ],
)
def test_partial_or_visible_transaction_witnesses_are_rejected(mutation: str) -> None:
    point = "stripe_webhooks.replace_one"
    before, inside, outside = staged("webhook", point)
    main = inside["payments"][-1]
    if mutation == "outside":
        outside["payments"][-1]["status"] = "succeeded"
    elif mutation == "version":
        main["version"] += 1
    elif mutation == "order":
        main["order_id"] = OTHER
    elif mutation == "money":
        main["amount_minor"] += 1
    elif mutation == "session":
        main["provider_session_id"] = "different"
    elif mutation == "created":
        main["created_at"] += timedelta(seconds=1)
    elif mutation == "updated":
        main["updated_at"] += timedelta(milliseconds=1)
    elif mutation == "unrelated_payment":
        inside["payments"][0]["amount_minor"] += 1
    elif mutation == "lost_history":
        inside["payment_history"].pop(0)
    elif mutation == "extra_history":
        inside["payment_history"].append({"_id": "extra"})
    elif mutation == "archive_amount":
        inside["payment_history"][-1]["amount_minor"] += 1
    elif mutation == "archive_version":
        inside["payment_history"][-1]["version"] += 1
    elif mutation == "extra_receipt":
        inside["stripe_webhooks"].append({"_id": "extra"})
    elif mutation == "receipt_received":
        inside["stripe_webhooks"][-1]["received_at"] += timedelta(seconds=1)
    elif mutation == "receipt_reason":
        inside["stripe_webhooks"][-1]["reason"] = "different"
    elif mutation == "receipt_marker":
        inside["stripe_webhooks"][-1]["fulfillment_status"] = None
    elif mutation == "wrong_stage":
        point = "payments.replace_one"
    with pytest.raises((AssertionError, StopIteration)):
        assert_staged_write(before, inside, outside, ORDER, "webhook", point, (NOW, NOW))


def test_all_new_cases_author_full_contracts_and_explicit_real_actions() -> None:
    feature = FeatureParser(str(FEATURES), "concurrency_atomicity.feature").parse()
    assert len(feature.scenarios) == 28
    kinds: dict[str, int] = {}
    for scenario in feature.scenarios.values():
        steps = {s.name: s for s in scenario.steps}
        assert "an unrelated succeeded payment fills all collections" in steps
        if "the real write schedule is" in steps:
            step = steps["the real write schedule is"]
            kind = "race"
            assert "the coordinated database effects are" in steps
        elif "the post-write rollback boundary is" in steps:
            step = steps["the post-write rollback boundary is"]
            kind = "rollback"
            assert "the real abort preserves this populated state" in steps
            assert "the fault is removed and the public request is retried" in steps
        else:
            step = steps["the worker coordination schedule is"]
            kind = "worker"
            assert {
                "the complete coordinated worker receipt is",
                "the coordinated worker effects are",
                "the complete payment after worker coordination is",
            } <= steps.keys()
        assert step.datatable is not None
        assert table_values([[c.value for c in r.cells] for r in step.datatable.rows])
        kinds[kind] = kinds.get(kind, 0) + 1
    assert kinds == dict(race=14, rollback=5, worker=9)
    source = (Path(__file__).parents[2] / "acceptance/concurrency_checks.py").read_text()
    assert "asyncio.sleep" not in source and "time.sleep" not in source


@pytest.mark.parametrize("mode", ["webhook-success-first", "webhook-expiry-first"])
@pytest.mark.parametrize("winner", ["first", "second"])
@pytest.mark.parametrize("label", ["first", "second"])
def test_race_events_cross_real_sdk_validation_before_any_write_gate(mode: str, winner: str, label: str) -> None:
    from pydantic import SecretStr

    from ecommerce_store_payments.application.payments.webhook import CheckoutOutcome
    from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
    from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
    from ecommerce_store_payments.infrastructure.clients.stripe.webhook_verifier import StripeWebhookVerifier
    from ecommerce_store_payments.infrastructure.config.settings import Settings
    from tests.webhook_fixtures import signature

    payment = Payment.create(ORDER, Money(1299, "PLN"))
    payment.begin_checkout(request_version=2)
    payment.mark_as_pending("cs_test_coordinated")
    body = coordinated_payload(payment, mode, label, winner)
    expired = (mode == "webhook-expiry-first" and label == winner) or (
        mode == "webhook-success-first" and label != winner
    )
    event = StripeWebhookVerifier(
        Settings(environment="test", stripe_webhook_secret=SecretStr("whsec_fixture"))
    ).verify(body, signature(body))
    assert event.outcome is (CheckoutOutcome.EXPIRED if expired else CheckoutOutcome.SUCCEEDED)
    assert event.checkout is not None and event.checkout.payment_id == payment.id
    assert event.checkout.attempt_id == payment.checkout_attempt_id and event.checkout.money == payment.money
    obj = json.loads(body)["data"]["object"]
    assert obj["status"] == ("expired" if expired else "complete")
    assert obj["payment_status"] == ("unpaid" if expired else "paid")
