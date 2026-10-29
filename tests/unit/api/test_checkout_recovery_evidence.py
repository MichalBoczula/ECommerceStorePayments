import asyncio
import json
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from typing import Any, cast
from urllib.parse import parse_qs, urlencode
from uuid import UUID, uuid4

import pytest
import stripe
from httpx2 import Request, Response
from pydantic import SecretStr
from pytest_bdd.parser import FeatureParser
from scripts.generate_operation_links import FEATURES

from ecommerce_store_payments.application.payments.checkout_provider import CheckoutRequest
from ecommerce_store_payments.application.payments.exceptions import CheckoutProviderError, CheckoutTimeoutError
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.clients.stripe.checkout_provider import (
    STRIPE_API_VERSION,
    StripeCheckoutProvider,
)
from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)
from tests.acceptance.checkout_checks import CHECKOUT_EXPECTED, REQUEST_FIELDS, CheckoutChecks, provider_request
from tests.acceptance.checkout_recovery_checks import (
    CheckoutRecoveryChecks,
    preparation_delta,
    recovery_delta,
    safe_problem,
)
from tests.acceptance.conftest import AcceptanceStripeTransport
from tests.acceptance.evidence import ScenarioEvidence, table_values
from tests.acceptance.payment_checks import PaymentChecks, Snapshot
from tests.unit.api.test_checkout_evidence import ORDER, T0, WINDOW, authored, sample
from tests.unit.external_providers.test_stripe_checkout import make_provider


def prepared(effect: str) -> tuple[Snapshot, Snapshot]:
    before, after = sample()
    if effect != "pending":
        current = after["payments"][-1]
        current.update(status="created", provider_session_id=None, version=1, updated_at=current["checkout_started_at"])
        after["payment_history"] = [d for d in after["payment_history"] if d.get("version") != 1]
        if effect == "created":
            current.update(
                version=0,
                updated_at=None,
                checkout_attempt_id=None,
                checkout_started_at=None,
                checkout_request_version=1,
            )
            after["payment_history"] = deepcopy(before["payment_history"])
    return before, after


@pytest.mark.parametrize("effect", ["created", "reserved", "pending"])
def test_failure_effects_require_the_complete_committed_state(effect: str) -> None:
    before, after = prepared(effect)
    preparation_delta(before, after, ORDER, WINDOW, effect)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_archive",
        "old_history",
        "receipt",
        "unrelated",
        "provider_id",
        "version",
        "attempt",
        "outside_time",
        "archive_field",
    ],
)
def test_reservation_failure_cannot_hide_partial_or_unrelated_writes(mutation: str) -> None:
    before, after = prepared("reserved")
    current = after["payments"][-1]
    if mutation == "missing_archive":
        after["payment_history"].pop()
    elif mutation == "old_history":
        after["payment_history"][0]["value"] = "changed"
    elif mutation == "receipt":
        after["stripe_webhooks"][0]["value"] = "changed"
    elif mutation == "unrelated":
        after["payments"][0]["value"] = "changed"
    elif mutation == "provider_id":
        current["provider_session_id"] = "cs_test_uncommitted"
    elif mutation == "version":
        current["version"] = 2
    elif mutation == "attempt":
        current["checkout_attempt_id"] = UUID(int=0)
    elif mutation == "outside_time":
        current["updated_at"] = current["checkout_started_at"] = T0
    else:
        after["payment_history"][-1]["checkout_request_version"] = 2
    with pytest.raises(AssertionError):
        preparation_delta(before, after, ORDER, WINDOW, "reserved")


@pytest.mark.parametrize("kind", ["reserved", "created", "pending"])
def test_recovery_distinguishes_replay_creation_and_read_only_acknowledgment(kind: str) -> None:
    _, before = prepared(kind)
    _, after = sample()
    assert recovery_delta(before, after, ORDER, WINDOW) == ("GET" if kind == "pending" else "POST")


@pytest.mark.parametrize(
    "mutation",
    [
        "attempt",
        "start",
        "request_version",
        "receipt",
        "old_history",
        "wrong_status",
        "provider_payment",
        "changed_read",
    ],
)
def test_recovery_cannot_replace_reserved_identity_or_mutate_completed_reads(mutation: str) -> None:
    _, before = prepared("pending" if mutation == "changed_read" else "reserved")
    _, after = sample()
    current = after["payments"][-1]
    if mutation == "attempt":
        current["checkout_attempt_id"] = uuid4()
    elif mutation == "start":
        current["checkout_started_at"] += timedelta(milliseconds=1)
    elif mutation == "request_version":
        current["checkout_request_version"] = 1
    elif mutation == "receipt":
        after["stripe_webhooks"][0]["value"] = "changed"
    elif mutation == "old_history":
        after["payment_history"][0]["value"] = "changed"
    elif mutation == "wrong_status":
        current["status"] = "created"
    elif mutation == "provider_payment":
        current["provider_payment_id"] = "pi_unverified"
    else:
        current["updated_at"] += timedelta(milliseconds=1)
    with pytest.raises(AssertionError):
        recovery_delta(before, after, ORDER, WINDOW)


def problem() -> tuple[Response, dict[str, str]]:
    feature = FeatureParser(str(FEATURES), "checkout_recovery.feature").parse()
    scenario = next(s for s in feature.scenarios.values() if s.name.startswith("PAY06-01 "))
    step = next(s for s in scenario.steps if s.name.startswith("the response matches case"))
    assert step.datatable is not None
    expected = table_values([[c.value for c in r.cells] for r in step.datatable.rows])
    body = {key[5:]: json.loads(value) for key, value in expected.items() if key.startswith("JSON.")}
    body.update(code=expected["Code"], traceId="a" * 32)
    return Response(
        502,
        json=body,
        headers={"content-type": "application/problem+json", "x-trace-id": "a" * 32},
        request=Request("POST", "http://testserver" + body["instance"]),
    ), expected


def test_complete_safe_problem_uses_authored_signature_and_correlated_trace() -> None:
    response, expected = problem()
    safe_problem(response, expected)


@pytest.mark.parametrize(
    "mutation", ["missing", "extra", "trace", "trace_header", "detail", "media", "status_type", "errors"]
)
def test_partial_unsafe_or_uncorrelated_problems_are_rejected(mutation: str) -> None:
    response, expected = problem()
    body, headers = response.json(), dict(response.headers)
    if mutation == "missing":
        del body["missingProperties"]
    elif mutation == "extra":
        body["exception"] = "private"
    elif mutation == "trace":
        body["traceId"] = "not-a-trace"
    elif mutation == "trace_header":
        headers["x-trace-id"] = "b" * 32
    elif mutation == "detail":
        body["detail"] = "private provider diagnostics"
    elif mutation == "media":
        headers["content-type"] = "application/json"
    elif mutation == "status_type":
        body["status"] = "502"
    else:
        body["errors"] = [{"message": "private"}]
    bad = Response(502, json=body, headers=headers, request=response.request)
    with pytest.raises(AssertionError):
        safe_problem(bad, expected)


@pytest.mark.parametrize("mode", ["rejection", "timeout_before", "timeout_once", "connection", "invalid_money"])
async def test_controlled_provider_recovery_keeps_accepted_sessions_and_exact_sdk_replay(mode: str) -> None:
    evidence = ScenarioEvidence("PAY99-01", "Recovery", "PAY99-01 Provider recovery", {})
    boundary = AcceptanceStripeTransport(evidence)
    sdk = stripe.StripeClient(
        "sk_test_fixture", stripe_version=STRIPE_API_VERSION, http_client=boundary, max_network_retries=0
    )
    provider = StripeCheckoutProvider(
        Settings(stripe_enabled=True, stripe_secret_key=SecretStr("sk_test_fixture")), sdk
    )
    request = CheckoutRequest(uuid4(), uuid4(), uuid4(), Money(1299, "PLN"), 2)
    boundary.mode = mode
    with pytest.raises(CheckoutTimeoutError if mode.startswith("timeout") else CheckoutProviderError):
        await provider.create(request)
    assert len(boundary.sessions) == (1 if mode in {"timeout_once", "invalid_money"} else 0)
    records: dict[str, Any] = {}
    evidence.flush(lambda name, body: records.__setitem__(name, json.loads(body)))
    outcome = next(v for v in records.values() if v.get("kind") in {"response", "failure"})
    assert outcome["kind"] == ("failure" if mode in {"timeout_once", "timeout_before", "connection"} else "response")
    if mode == "rejection":
        assert outcome["status"] == 400
    if mode == "invalid_money":
        assert outcome["content"]["body"]["amount_total"] == 1300
    first = boundary.calls[0]
    boundary.mode = "ok"
    recovered = await provider.create(request)
    assert recovered.session_id.startswith("cs_test_") and len(boundary.sessions) == 1
    assert first[3] == boundary.calls[1][3] and first[2]["Idempotency-Key"] == boundary.calls[1][2]["Idempotency-Key"]
    assert len(boundary.calls) == len(boundary.exchange_ids) == 2


@pytest.mark.parametrize("point", ["reservation_before", "pending_before", "pending_after"])
def test_persistence_fault_distinguishes_precommit_from_lost_commit_acknowledgment(
    point: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    state: Snapshot = {"payments": [{"version": 0}], "payment_history": [], "stripe_webhooks": []}
    evidence = ScenarioEvidence("PAY99-01", "Recovery", "PAY99-01 Persistence", {})
    payment = Payment.create(ORDER, Money(1299, "PLN"))
    payment.begin_checkout(request_version=2)
    if point != "reservation_before":
        payment.mark_as_pending("cs_test_fault")
    calls: list[Payment] = []

    async def save(repository: MongoPaymentRepository, value: Payment) -> Payment:
        calls.append(value)
        state["payments"][0]["version"] += 1
        return value

    monkeypatch.setattr(MongoPaymentRepository, "update", save)
    context = SimpleNamespace(orders=SimpleNamespace(order_id=ORDER), evidence=evidence)
    payments = PaymentChecks(cast(Any, context))
    monkeypatch.setattr(payments, "snapshot", lambda: deepcopy(state))
    recovery = CheckoutRecoveryChecks(payments, cast(CheckoutChecks, SimpleNamespace()))
    recovery.interrupt(point, monkeypatch)

    async def run() -> None:
        repo = cast(MongoPaymentRepository, SimpleNamespace())
        with pytest.raises(RuntimeError, match="private injected"):
            await MongoPaymentRepository.update(repo, payment)
        assert len(calls) == (1 if point == "pending_after" else 0)
        await MongoPaymentRepository.update(repo, payment)

    asyncio.run(run())
    assert len(calls) == (2 if point == "pending_after" else 1)
    records: dict[str, Any] = {}
    evidence.flush(lambda name, body: records.__setitem__(name, json.loads(body)))
    output = next(v["output"] for v in records.values() if v.get("kind") == "action-result")
    assert output["committed"] == (point == "pending_after")
    assert (output["before"] != output["after"]) == output["committed"]


@pytest.mark.parametrize("mutation", ["none", "extra_blik", "stored_version", "implicit_downgrade"])
async def test_legacy_request_requires_explicit_version_one_without_blik(mutation: str) -> None:
    provider, transport, request = make_provider()
    await provider.create(replace(request, request_version=1))
    _, after = sample()
    stored = after["payments"][-1]
    stored.update(
        _id=request.payment_id,
        order_id=request.order_id,
        checkout_attempt_id=request.attempt_id,
        checkout_request_version=1,
    )
    expected = authored("only this checkout is created with this provider request")
    del expected["form.payment_method_types[1]"]
    method, url, headers, data = transport.calls[0]
    if mutation == "extra_blik":
        form = parse_qs(str(data))
        form["payment_method_types[1]"] = ["blik"]
        data = urlencode(form, doseq=True)
    elif mutation == "stored_version":
        stored["checkout_request_version"] = 2
    if mutation == "none":
        del stored["checkout_request_version"]
        provider_request((method, url, headers, data), stored, expected, request_version=1)
    else:
        with pytest.raises(AssertionError):
            provider_request(
                (method, url, headers, data),
                stored,
                expected,
                **({} if mutation == "implicit_downgrade" else {"request_version": 1}),
            )


def test_recovery_sources_require_full_effects_safe_problems_and_native_request_response_tables() -> None:
    feature = FeatureParser(str(FEATURES), "checkout_recovery.feature").parse()
    assert len(feature.scenarios) == 18
    for scenario in feature.scenarios.values():
        cid = scenario.name.split()[0]
        names = [step.name for step in scenario.steps]
        assert (
            "I remember checkout recovery state" in names
            and "an unrelated succeeded payment fills all collections" in names
        )
        if cid in {"PAY06-06", "PAY06-07", "PAY06-09"}:
            assert "the complete recovered checkout response is" in names
        else:
            assert "checkout failure leaves this complete state" in names
        for step in scenario.steps:
            if step.name in {
                "the complete recovered checkout response is",
                "a fresh application instance recovers checkout with",
            }:
                assert step.datatable is not None
                assert (
                    table_values([[c.value for c in r.cells] for r in step.datatable.rows]).keys() == CHECKOUT_EXPECTED
                )
            elif step.name == "the recovery provider request is":
                assert step.datatable is not None
                values = table_values([[c.value for c in r.cells] for r in step.datatable.rows])
                if values["Method"] == "POST":
                    assert values.keys() == (
                        REQUEST_FIELDS - {"form.payment_method_types[1]"} if cid == "PAY06-06" else REQUEST_FIELDS
                    )
    ages: set[str] = set()
    for scenario in feature.scenarios.values():
        if scenario.name.split()[0] in {"PAY06-08", "PAY06-09", "PAY06-10"}:
            step = next(s for s in scenario.steps if s.name == "a reserved checkout fixture contains")
            assert step.datatable is not None
            ages.add(table_values([[c.value for c in r.cells] for r in step.datatable.rows])["AgeSeconds"])
    assert ages == {"82800", "82799.999", "82800.001"}
