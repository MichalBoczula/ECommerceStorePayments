import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest
from pytest_bdd.parser import FeatureParser
from scripts.generate_operation_links import FEATURES

from tests.acceptance.evidence import table_values
from tests.acceptance.payment_checks import PUBLIC_FIELDS, PaymentChecks, full_payment
from tests.acceptance.retry_checks import (
    OPTIONAL_LEGACY_FIELDS,
    RetryChecks,
    archived_snapshot,
    reset_fields,
    transition_delta,
)

T0 = datetime(2026, 10, 1, 10, tzinfo=UTC)
T1 = T0 + timedelta(minutes=1)
WINDOW = T1, T1 + timedelta(seconds=1)
ORDER_ID = UUID("11111111-1111-4111-8111-111111111111")
PAYMENT_ID = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")


def sample(legacy: bool = False) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    previous: dict[str, Any] = {
        "_id": PAYMENT_ID,
        "order_id": ORDER_ID,
        "amount_minor": 1299,
        "currency": "PLN",
        "status": "failed",
        "provider_session_id": "cs_first",
        "provider_payment_id": None,
        "failure_code": "declined",
        "created_at": T0,
        "updated_at": T0 + timedelta(seconds=5),
        "version": 3,
        "checkout_attempt_id": UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        "checkout_started_at": T0 + timedelta(seconds=1),
        "checkout_request_version": 2,
    }
    if legacy:
        for key in OPTIONAL_LEGACY_FIELDS:
            del previous[key]
    archive = {key: value for key, value in previous.items() if key != "_id"}
    version = 0 if legacy else 3
    archive.update(
        _id=f"{PAYMENT_ID}:{version}",
        payment_id=PAYMENT_ID,
        version=version,
        recorded_at=T1,
        checkout_attempt_id=previous.get("checkout_attempt_id"),
        checkout_started_at=previous.get("checkout_started_at"),
        checkout_request_version=previous.get("checkout_request_version", 1),
    )
    current = {
        **previous,
        "status": "created",
        "updated_at": T1,
        "version": version + 1,
        "provider_session_id": None,
        "provider_payment_id": None,
        "failure_code": None,
        "checkout_attempt_id": None,
        "checkout_started_at": None,
        "checkout_request_version": 1,
    }
    unrelated = {
        **current,
        "_id": UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
        "order_id": UUID("dddddddd-dddd-4ddd-8ddd-dddddddddddd"),
    }
    older = {**archive, "_id": "older", "payment_id": unrelated["_id"], "recorded_at": T0}
    before = {
        "payments": [previous, unrelated],
        "payment_history": [older],
        "stripe_webhooks": [{"_id": "receipt", "digest": "original"}],
    }
    after = {
        "payments": [current, deepcopy(unrelated)],
        "payment_history": [deepcopy(older), archive],
        "stripe_webhooks": deepcopy(before["stripe_webhooks"]),
    }
    return previous, archive, before, after


@pytest.mark.parametrize("legacy", [False, True])
def test_retry_delta_retains_exact_business_fields_archive_and_unrelated_collections(legacy: bool) -> None:
    previous, archive, before, after = sample(legacy)
    archived_snapshot(previous, archive, WINDOW)
    assert transition_delta(before, after, ORDER_ID, WINDOW) == archive
    reset_fields(after["payments"][0])
    if legacy:
        assert not (previous.keys() & OPTIONAL_LEGACY_FIELDS)
        assert archive["version"] == 0 and archive["checkout_request_version"] == 1
        assert after["payments"][0]["version"] == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "business_field",
        "missing_field",
        "provider",
        "failure",
        "attempt",
        "request_version",
        "created_time",
        "recorded_time",
        "recorded_timezone",
        "extra",
        "archive_identity",
        "version",
    ],
)
def test_partial_or_changed_history_snapshots_are_rejected(mutation: str) -> None:
    previous, archive, _, _ = sample()
    if mutation == "business_field":
        archive["amount_minor"] += 1
    elif mutation == "missing_field":
        del archive["provider_payment_id"]
    elif mutation == "provider":
        archive["provider_session_id"] = "cs_wrong"
    elif mutation == "failure":
        archive["failure_code"] = None
    elif mutation == "attempt":
        archive["checkout_attempt_id"] = None
    elif mutation == "request_version":
        archive["checkout_request_version"] = 1
    elif mutation == "created_time":
        archive["created_at"] += timedelta(milliseconds=1)
    elif mutation == "recorded_time":
        archive["recorded_at"] = T0
    elif mutation == "recorded_timezone":
        archive["recorded_at"] = T1.replace(tzinfo=None)
    elif mutation == "extra":
        archive["ignored"] = "not-part-of-snapshot"
    elif mutation == "archive_identity":
        archive["_id"] = "wrong"
    else:
        archive["version"] = 0
    with pytest.raises(AssertionError):
        archived_snapshot(previous, archive, WINDOW)


@pytest.mark.parametrize(
    "mutation",
    [
        "skip_version",
        "wrong_identity",
        "changed_created",
        "changed_money",
        "duplicate_archive",
        "old_history",
        "old_recorded_time",
        "unrelated_current",
        "receipt",
        "extra_current",
        "missing_archive",
    ],
)
def test_transition_guard_rejects_extra_writes_even_at_unchanged_collection_counts(mutation: str) -> None:
    _, _, before, after = sample()
    if mutation == "skip_version":
        after["payments"][0]["version"] += 1
    elif mutation == "wrong_identity":
        after["payments"][0]["_id"] = UUID(int=9)
    elif mutation == "changed_created":
        after["payments"][0]["created_at"] += timedelta(milliseconds=1)
    elif mutation == "changed_money":
        after["payments"][0]["amount_minor"] += 1
    elif mutation == "duplicate_archive":
        after["payment_history"].append(deepcopy(after["payment_history"][-1]))
    elif mutation == "old_history":
        after["payment_history"][0]["provider_session_id"] = "changed"
    elif mutation == "old_recorded_time":
        after["payment_history"][0]["recorded_at"] = T1
    elif mutation == "unrelated_current":
        after["payments"][1]["currency"] = "USD"
    elif mutation == "receipt":
        after["stripe_webhooks"][0]["digest"] = "changed"
    elif mutation == "extra_current":
        after["payments"].append(deepcopy(after["payments"][0]))
    else:
        after["payment_history"].pop()
    with pytest.raises(AssertionError):
        transition_delta(before, after, ORDER_ID, WINDOW)


@pytest.mark.parametrize(
    "field",
    [
        "provider_session_id",
        "provider_payment_id",
        "failure_code",
        "checkout_attempt_id",
        "checkout_started_at",
        "checkout_request_version",
    ],
)
def test_retry_must_reset_all_provider_and_checkout_metadata(field: str) -> None:
    _, _, _, after = sample()
    current = after["payments"][0]
    current[field] = 2 if field == "checkout_request_version" else "retained"
    with pytest.raises(AssertionError):
        reset_fields(current)


@pytest.mark.parametrize("windowed", [False, True])
def test_retry_update_timestamp_requires_explicit_mutation_window(windowed: bool) -> None:
    _, _, _, after = sample()
    current = after["payments"][0]
    body = {
        key: str(current["_id"])
        if key == "id"
        else str(current[key])
        if key == "order_id"
        else current[key].isoformat()
        if isinstance(current[key], datetime)
        else current[key]
        for key in PUBLIC_FIELDS
    }
    body["updated_at"] = (T1 + timedelta(microseconds=123)).isoformat()
    expected = {
        key: "{stored.id}" if key == "id" else "{stored." + key + "}" if key.endswith("_at") else json.dumps(body[key])
        for key in PUBLIC_FIELDS
    }
    if windowed:
        full_payment(body, current, expected, update_window=WINDOW)
    else:
        with pytest.raises(AssertionError):
            full_payment(body, current, expected)


@pytest.mark.parametrize("collection", ["payments", "payment_history", "stripe_webhooks"])
def test_rejected_retry_checks_every_populated_collection(collection: str, monkeypatch: pytest.MonkeyPatch) -> None:
    _, _, before, _ = sample()
    after = deepcopy(before)
    after[collection][0]["changed"] = True
    payments = PaymentChecks(cast(Any, SimpleNamespace()))
    payments.before, payments.external_calls = before, (0, 0)
    monkeypatch.setattr(payments, "snapshot", lambda: after)
    with pytest.raises(AssertionError):
        RetryChecks(payments).rejected()


def test_retry_sources_require_complete_outcomes_history_and_rejected_state_checks() -> None:
    success = {"PAY11-10", "PAY11-11", *{f"PAY04-{n:02d}" for n in range(1, 6)}}
    rejected = {"PAY11-12", *{f"PAY04-{n:02d}" for n in range(7, 15)}}
    found: set[str] = set()
    for filename in ("payments.feature", "retries.feature"):
        feature = FeatureParser(str(FEATURES), filename).parse()
        for scenario in feature.scenarios.values():
            cid = scenario.name.split()[0]
            if cid not in success | rejected:
                continue
            names = [step.name for step in scenario.steps]
            assert "I remember the payment and every collection" in names
            if cid in success:
                complete = next(step for step in scenario.steps if step.name == "the complete retry response is")
                assert complete.datatable is not None
                assert (
                    table_values([[cell.value for cell in row.cells] for row in complete.datatable.rows]).keys()
                    == PUBLIC_FIELDS
                )
                assert "the retry changes only this version and archive" in names
            else:
                assert "the rejected retry preserves every document" in names
            found.add(cid)
    assert found == success | rejected
