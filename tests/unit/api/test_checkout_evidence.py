import json
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlencode
from uuid import UUID

import pytest
from pytest_bdd.parser import FeatureParser
from scripts.generate_operation_links import FEATURES

from tests.acceptance.checkout_checks import (
    CHECKOUT_EXPECTED,
    REQUEST_FIELDS,
    checkout_delta,
    checkout_response,
    provider_request,
)
from tests.acceptance.evidence import table_values
from tests.acceptance.payment_checks import PUBLIC_FIELDS, Snapshot
from tests.unit.external_providers.test_stripe_checkout import make_provider

T0 = datetime(2026, 10, 1, tzinfo=UTC)
T1 = T0 + timedelta(minutes=1)
WINDOW = T1, T1 + timedelta(seconds=1)
ORDER = UUID("11111111-1111-4111-8111-111111111111")
PAYMENT = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
ATTEMPT = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")


def authored(step_name: str) -> dict[str, str]:
    feature = FeatureParser(str(FEATURES), "checkout.feature").parse()
    scenario = next(s for s in feature.scenarios.values() if s.name.startswith("PAY21-01 "))
    step = next(s for s in scenario.steps if s.name == step_name)
    assert step.datatable is not None
    return table_values([[cell.value for cell in row.cells] for row in step.datatable.rows])


def sample(state: str = "new") -> tuple[Snapshot, Snapshot]:
    terminal = state in {"failed", "canceled"}
    base = 3 if terminal else 0
    current: dict[str, Any] = {
        "_id": PAYMENT,
        "order_id": ORDER,
        "amount_minor": 1299,
        "currency": "PLN",
        "status": "pending",
        "provider_session_id": "cs_test_current",
        "provider_payment_id": None,
        "failure_code": None,
        "created_at": T1 if state == "new" else T0,
        "updated_at": T1 + timedelta(milliseconds=100),
        "version": base + (3 if terminal else 2),
        "checkout_attempt_id": ATTEMPT,
        "checkout_started_at": T1 + timedelta(milliseconds=50),
        "checkout_request_version": 2,
    }
    initial = {
        **current,
        "status": state,
        "version": base,
        "updated_at": T0 + timedelta(seconds=2),
        "checkout_attempt_id": UUID(int=1),
        "checkout_started_at": T0 + timedelta(seconds=1),
        "provider_session_id": "cs_test_old",
        "failure_code": "declined" if state == "failed" else None,
    }
    created = {
        **current,
        "status": "created",
        "provider_session_id": None,
        "checkout_attempt_id": None,
        "checkout_started_at": None,
        "checkout_request_version": 1,
        "version": base + 1 if terminal else 0,
        "updated_at": T1 + timedelta(milliseconds=20) if terminal else None,
    }
    reserved = {
        **current,
        "status": "created",
        "provider_session_id": None,
        "version": current["version"] - 1,
        "updated_at": current["checkout_started_at"],
    }
    states = [initial, created, reserved] if terminal else [created, reserved]

    def archive(previous: dict[str, Any]) -> dict[str, Any]:
        return {
            **{k: v for k, v in previous.items() if k != "_id"},
            "_id": f"{PAYMENT}:{previous['version']}",
            "payment_id": PAYMENT,
            "recorded_at": T1 + timedelta(milliseconds=200),
        }

    other = {"_id": UUID(int=10), "order_id": UUID(int=11), "value": "untouched"}
    before: Snapshot = {
        "payments": [other] + ([] if state == "new" else [initial if terminal else created]),
        "payment_history": [{"_id": "older", "value": "untouched"}],
        "stripe_webhooks": [{"_id": "receipt", "value": "untouched"}],
    }
    after = {
        "payments": [deepcopy(other), current],
        "payment_history": [*deepcopy(before["payment_history"]), *map(archive, states)],
        "stripe_webhooks": deepcopy(before["stripe_webhooks"]),
    }
    return before, after


@pytest.mark.parametrize("state", ["new", "created", "failed", "canceled"])
def test_checkout_guard_accepts_complete_creation_reservation_pending_archives(state: str) -> None:
    before, after = sample(state)
    added = checkout_delta(before, after, ORDER, WINDOW)
    assert len(added) == (3 if state in {"failed", "canceled"} else 2)


@pytest.mark.parametrize(
    "mutation",
    ["quantity", "metadata", "intent_metadata", "key", "version", "missing_blik", "extra_form", "duplicate_amount"],
)
async def test_encoded_request_guard_rejects_partial_wrong_and_reused_provider_parameters(mutation: str) -> None:
    provider, transport, request = make_provider()
    await provider.create(replace(request, request_version=2))
    _, after = sample()
    stored = after["payments"][-1]
    stored.update(_id=request.payment_id, order_id=request.order_id, checkout_attempt_id=request.attempt_id)
    expected = authored("only this checkout is created with this provider request")
    # The authored order fixture is fixed; this probe uses real random SDK request identities.
    method, url, headers, data = transport.calls[0]
    provider_request((method, url, headers, data), stored, expected)
    headers = dict(headers)
    form = parse_qs(str(data))
    if mutation == "quantity":
        form["line_items[0][quantity]"] = ["2"]
    elif mutation == "metadata":
        form["metadata[attempt_id]"] = [str(UUID(int=2))]
    elif mutation == "intent_metadata":
        form["payment_intent_data[metadata][payment_id]"] = [str(UUID(int=3))]
    elif mutation == "key":
        headers["Idempotency-Key"] = "checkout:other:attempt"
    elif mutation == "version":
        headers["Stripe-Version"] = "different"
    elif mutation == "missing_blik":
        del form["payment_method_types[1]"]
    elif mutation == "extra_form":
        form["allow_promotion_codes"] = ["true"]
    else:
        form["line_items[0][price_data][unit_amount]"].append("1299")
    with pytest.raises(AssertionError):
        provider_request((method, url, headers, urlencode(form, doseq=True)), stored, expected)


@pytest.mark.parametrize("state", ["open", "complete", "expired"])
def test_complete_nested_response_matches_exact_provider_time_nullable_url_and_pending_payment(state: str) -> None:
    _, after = sample()
    stored = after["payments"][-1]
    body = {
        k: str(stored["_id"] if k == "id" else stored[k])
        if k in {"id", "order_id"}
        else stored[k].isoformat()
        if isinstance(stored[k], datetime)
        else stored[k]
        for k in PUBLIC_FIELDS
    }
    provider = {
        "id": stored["provider_session_id"],
        "status": state,
        "url": "https://checkout.stripe.com/c/pay/demo",
        "expires_at": 1796068800,
    }
    response = {
        "payment": body,
        "checkout_url": provider["url"] if state == "open" else None,
        "checkout_status": state,
        "expires_at": datetime.fromtimestamp(1796068800, UTC).isoformat(),
    }
    expected = authored("the complete checkout response is")
    expected["checkout_status"] = json.dumps(state)
    expected["checkout_url"] = "{provider.url}" if state == "open" else "null"
    checkout_response(response, stored, provider, expected, window=WINDOW, created=True, mutated=True)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_nested",
        "extra_nested",
        "missing_outer",
        "wrong_expiry",
        "bool_expiry",
        "wrong_session",
        "wrong_url",
        "float_amount",
        "confirmed_payment",
    ],
)
def test_complete_checkout_rejects_partial_types_times_and_wrong_session_fields(mutation: str) -> None:
    _, after = sample()
    stored = after["payments"][-1]
    nested = {
        k: str(stored["_id"] if k == "id" else stored[k])
        if k in {"id", "order_id"}
        else stored[k].isoformat()
        if isinstance(stored[k], datetime)
        else stored[k]
        for k in PUBLIC_FIELDS
    }
    provider = {
        "id": stored["provider_session_id"],
        "status": "open",
        "url": "https://checkout.stripe.com/c/pay/demo",
        "expires_at": 1796068800,
    }
    response = {
        "payment": nested,
        "checkout_url": provider["url"],
        "checkout_status": "open",
        "expires_at": datetime.fromtimestamp(1796068800, UTC).isoformat(),
    }
    if mutation == "missing_nested":
        del nested["provider_payment_id"]
    elif mutation == "extra_nested":
        nested["unexpected"] = None
    elif mutation == "missing_outer":
        del response["expires_at"]
    elif mutation == "wrong_expiry":
        response["expires_at"] = (datetime.fromtimestamp(1796068800, UTC) + timedelta(seconds=1)).isoformat()
    elif mutation == "bool_expiry":
        provider["expires_at"] = True
    elif mutation == "wrong_session":
        provider["id"] = "cs_test_other"
    elif mutation == "wrong_url":
        response["checkout_url"] = "https://attacker.example.test/c/pay/demo"
    elif mutation == "float_amount":
        nested["amount_minor"] = 1299.0
    else:
        nested["status"] = "succeeded"
    with pytest.raises(AssertionError):
        checkout_response(
            response,
            stored,
            provider,
            authored("the complete checkout response is"),
            window=WINDOW,
            created=True,
            mutated=True,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "old_history",
        "unrelated_current",
        "receipt",
        "extra_archive",
        "missing_archive",
        "old_attempt",
        "reset_failure",
        "changed_money",
        "reserved_version",
        "recorded_time",
        "wrong_created",
        "wrong_reservation_time",
    ],
)
def test_checkout_effect_guard_rejects_changed_archives_and_other_populated_state(mutation: str) -> None:
    before, after = sample("failed")
    current = after["payments"][-1]
    if mutation == "old_history":
        after["payment_history"][0]["value"] = "changed"
    elif mutation == "unrelated_current":
        after["payments"][0]["value"] = "changed"
    elif mutation == "receipt":
        after["stripe_webhooks"][0]["value"] = "changed"
    elif mutation == "extra_archive":
        after["payment_history"].append(deepcopy(after["payment_history"][-1]))
    elif mutation == "missing_archive":
        after["payment_history"].pop()
    elif mutation == "old_attempt":
        current["checkout_attempt_id"] = before["payments"][-1]["checkout_attempt_id"]
    elif mutation == "reset_failure":
        after["payment_history"][-2]["failure_code"] = "not-reset"
    elif mutation == "changed_money":
        current["amount_minor"] += 1
    elif mutation == "reserved_version":
        after["payment_history"][-1]["checkout_request_version"] = 1
    elif mutation == "recorded_time":
        after["payment_history"][-1]["recorded_at"] = T0
    elif mutation == "wrong_created":
        after["payment_history"][-2]["created_at"] += timedelta(milliseconds=1)
    else:
        after["payment_history"][-1]["updated_at"] += timedelta(milliseconds=1)
    with pytest.raises(AssertionError):
        checkout_delta(before, after, ORDER, WINDOW)


def test_checkout_success_sources_require_complete_nested_contract_provider_or_no_write_checks() -> None:
    required = {"PAY21-01", "PAY21-02", "PAY22-16", *{f"PAY05-{n:02d}" for n in range(1, 8)}}
    reads = {"PAY21-02", "PAY05-02", "PAY05-03", "PAY05-04"}
    found: set[str] = set()
    for filename in ("checkout.feature", "webhooks.feature", "checkout_success.feature"):
        for scenario in FeatureParser(str(FEATURES), filename).parse().scenarios.values():
            cid = scenario.name.split()[0]
            if cid not in required:
                continue
            names = [s.name for s in scenario.steps]
            assert "I remember checkout state and provider calls" in names
            complete = next(s for s in scenario.steps if s.name == "the complete checkout response is")
            assert complete.datatable is not None
            assert (
                table_values([[c.value for c in r.cells] for r in complete.datatable.rows]).keys() == CHECKOUT_EXPECTED
            )
            if cid in reads:
                assert "checkout reads only the existing provider session without writes" in names
            else:
                request = next(
                    s for s in scenario.steps if s.name == "only this checkout is created with this provider request"
                )
                assert request.datatable is not None
                assert (
                    table_values([[c.value for c in r.cells] for r in request.datatable.rows]).keys() == REQUEST_FIELDS
                )
            found.add(cid)
    assert found == required
