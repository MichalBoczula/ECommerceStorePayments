"""Mutations prove that complete lifecycle evidence rejects plausible partial assertions."""

import hashlib
import json
from copy import deepcopy
from datetime import timedelta
from typing import Any
from uuid import UUID

import pytest
from pytest_bdd.parser import FeatureParser
from scripts.generate_operation_links import FEATURES

from tests.acceptance.evidence import table_values
from tests.acceptance.payment_checks import PUBLIC_FIELDS, Snapshot
from tests.acceptance.webhook_lifecycle_checks import DELTA_FIELDS, EVENT_INPUTS, lifecycle_delta, receipt_matches
from tests.acceptance.webhook_verification_checks import UNKNOWN_RECEIPT_FIELDS
from tests.unit.api.test_checkout_evidence import ORDER, WINDOW, sample


def authored(step_name: str, cid: str = "PAY08-01", occurrence: int = 0) -> dict[str, str]:
    feature = FeatureParser(str(FEATURES), "webhook_lifecycle.feature").parse()
    scenario = next(s for s in feature.scenarios.values() if s.name.startswith(cid + " "))
    step = [s for s in scenario.steps if s.name == step_name][occurrence]
    assert step.datatable is not None
    return table_values([[cell.value for cell in row.cells] for row in step.datatable.rows])


def receipt_sample() -> tuple[dict[str, Any], dict[str, Any], bytes]:
    payload = {
        "id": "evt_pay08_01",
        "type": "checkout.session.async_payment_succeeded",
        "data": {
            "object": {
                "id": "cs_test_current",
                "payment_intent": "pi_fixture",
                "metadata": {
                    "payment_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                    "order_id": str(ORDER),
                    "attempt_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                },
            }
        },
    }
    body = json.dumps(payload).encode()
    record = {
        "_id": payload["id"],
        "event_type": payload["type"],
        "payload_digest": hashlib.sha256(body).hexdigest(),
        "outcome": "succeeded",
        "payment_id": UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        "order_id": ORDER,
        "attempt_id": UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        "amount_minor": 1299,
        "currency": "PLN",
        "session_id": "cs_test_current",
        "provider_payment_id": "pi_fixture",
        "state": "applied",
        "reason": "payment_succeeded",
        "received_at": WINDOW[0] + timedelta(milliseconds=300),
        "completed_at": WINDOW[0] + timedelta(milliseconds=400),
        "fulfillment_status": "pending",
    }
    return record, payload, body


@pytest.mark.parametrize("field", sorted(UNKNOWN_RECEIPT_FIELDS))
def test_complete_receipt_guard_rejects_each_corrupt_field(field: str) -> None:
    record, payload, body = receipt_sample()
    receipt_matches(record, authored("the complete lifecycle receipt is"), payload, body, WINDOW, None)
    record[field] = "corrupt"
    with pytest.raises(AssertionError):
        receipt_matches(record, authored("the complete lifecycle receipt is"), payload, body, WINDOW, None)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "extra",
        "boolean_amount",
        "timestamp_precision",
        "clock_before",
        "clock_after",
        "date_order",
        "wrong_wire",
    ],
)
def test_receipt_guard_requires_exact_shape_integer_money_original_bytes_and_bounded_dates(mutation: str) -> None:
    record, payload, body = receipt_sample()
    if mutation == "missing":
        del record["provider_payment_id"]
    elif mutation == "extra":
        record["raw_payload"] = "forbidden"
    elif mutation == "boolean_amount":
        record["amount_minor"] = True
    elif mutation == "timestamp_precision":
        record["received_at"] += timedelta(microseconds=1)
    elif mutation == "clock_before":
        record["received_at"] = WINDOW[0] - timedelta(milliseconds=1)
    elif mutation == "clock_after":
        record["completed_at"] = WINDOW[1] + timedelta(milliseconds=1)
    elif mutation == "date_order":
        record["received_at"], record["completed_at"] = record["completed_at"], record["received_at"]
    else:
        body += b" "
    with pytest.raises(AssertionError):
        receipt_matches(record, authored("the complete lifecycle receipt is"), payload, body, WINDOW, None)


@pytest.mark.parametrize("pending", [True, False])
def test_existing_receipts_preserve_normalized_fields_and_completed_dates(pending: bool) -> None:
    record, payload, body = receipt_sample()
    previous = deepcopy(record)
    previous["received_at"] = WINDOW[0] - timedelta(seconds=1)
    record["received_at"] = previous["received_at"]
    values = authored("the complete lifecycle receipt is")
    values["received_at"] = "{before.received_at}"
    if pending:
        previous.update(state="pending", reason=None, completed_at=None, fulfillment_status=None)
    else:
        values["completed_at"] = "{before.completed_at}"
    receipt_matches(record, values, payload, body, WINDOW, previous)
    # Even an authored table agreeing with corrupt normalized data cannot legitimize a rewrite.
    previous["payload_digest"] = "different_original_digest"
    with pytest.raises(AssertionError):
        receipt_matches(record, values, payload, body, WINDOW, previous)


def delta_sample() -> tuple[Snapshot, Snapshot]:
    _, checkout = sample()
    before = deepcopy(checkout)
    after = deepcopy(before)
    current = after["payments"][-1]
    previous = deepcopy(current)
    current.update(
        status="succeeded",
        provider_payment_id="pi_fixture",
        version=3,
        updated_at=WINDOW[0] + timedelta(milliseconds=500),
    )
    after["payment_history"].append(
        {
            **{k: v for k, v in previous.items() if k != "_id"},
            "_id": f"{previous['_id']}:2",
            "payment_id": previous["_id"],
            "recorded_at": WINDOW[0] + timedelta(milliseconds=600),
        }
    )
    after["stripe_webhooks"].append(receipt_sample()[0])
    return before, after


@pytest.mark.parametrize(
    "field",
    [
        "_id",
        "order_id",
        "amount_minor",
        "currency",
        "status",
        "provider_session_id",
        "provider_payment_id",
        "failure_code",
        "created_at",
        "updated_at",
        "version",
        "checkout_attempt_id",
        "checkout_started_at",
        "checkout_request_version",
    ],
)
def test_full_current_guard_rejects_changes_to_each_payment_field(field: str) -> None:
    before, after = delta_sample()
    values = authored("webhook processing changes exactly this state")
    lifecycle_delta(before, after, ORDER, values, WINDOW, "cs_test_current")
    after["payments"][-1][field] = WINDOW[1] + timedelta(seconds=1) if field == "updated_at" else "corrupt"
    with pytest.raises((AssertionError, StopIteration)):
        lifecycle_delta(before, after, ORDER, values, WINDOW, "cs_test_current")


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_archive",
        "extra_archive",
        "prior_history",
        "unrelated_payment",
        "archive_amount",
        "archive_attempt",
        "archive_date",
        "receipt_count",
        "extra_current_field",
    ],
)
def test_transition_guard_requires_one_exact_archive_and_preserves_populated_unrelated_state(mutation: str) -> None:
    before, after = delta_sample()
    if mutation == "missing_archive":
        after["payment_history"].pop()
    elif mutation == "extra_archive":
        after["payment_history"].append({"_id": "unexpected"})
    elif mutation == "prior_history":
        after["payment_history"][0]["value"] = "changed"
    elif mutation == "unrelated_payment":
        after["payments"][0]["value"] = "changed"
    elif mutation == "archive_amount":
        after["payment_history"][-1]["amount_minor"] = 1300
    elif mutation == "archive_attempt":
        after["payment_history"][-1]["checkout_attempt_id"] = UUID(int=99)
    elif mutation == "archive_date":
        after["payment_history"][-1]["recorded_at"] = WINDOW[1] + timedelta(seconds=1)
    elif mutation == "receipt_count":
        after["stripe_webhooks"].pop()
    else:
        after["payments"][-1]["unexpected"] = "bad"
    with pytest.raises(AssertionError):
        lifecycle_delta(
            before, after, ORDER, authored("webhook processing changes exactly this state"), WINDOW, "cs_test_current"
        )


def test_ignored_delivery_must_preserve_updated_time_and_every_history_field() -> None:
    before, _ = delta_sample()
    after = deepcopy(before)
    after["stripe_webhooks"].append(receipt_sample()[0])
    values = authored("webhook processing changes exactly this state", "PAY08-12")
    lifecycle_delta(before, after, ORDER, values, WINDOW, "cs_test_current")
    after["payments"][-1]["updated_at"] += timedelta(milliseconds=1)
    with pytest.raises(AssertionError):
        lifecycle_delta(before, after, ORDER, values, WINDOW, "cs_test_current")


def test_lifecycle_sources_author_all_inputs_full_receipts_deltas_reads_and_recovery_results() -> None:
    feature = FeatureParser(str(FEATURES), "webhook_lifecycle.feature").parse()
    assert len(feature.scenarios) == 35
    for index, scenario in enumerate(feature.scenarios.values(), 1):
        assert scenario.name.startswith(f"PAY08-{index:02} ") and scenario.description and scenario.description.strip()
        tables = {
            "the lifecycle event is prepared": EVENT_INPUTS,
            "the complete lifecycle receipt is": UNKNOWN_RECEIPT_FIELDS,
            "webhook processing changes exactly this state": DELTA_FIELDS,
            "the complete payment read after webhook is": PUBLIC_FIELDS,
        }
        for name, fields in tables.items():
            steps = [s for s in scenario.steps if s.name == name]
            assert steps
            for step in steps:
                assert step.datatable is not None
                assert (
                    table_values([[cell.value for cell in row.cells] for row in step.datatable.rows]).keys() == fields
                )
        assert any(s.name == "an unrelated succeeded payment fills all collections" for s in scenario.steps)
        for step in scenario.steps:
            if step.name == "durable webhook recovery runs with":
                assert step.datatable is not None
                values = table_values([[cell.value for cell in row.cells] for row in step.datatable.rows])
                assert values == {"Mode": "operator", "FirstResult": "1", "RepeatedResult": "0"} or values == {
                    "Mode": "fresh_http",
                    "FirstResult": "200",
                    "RepeatedResult": "200",
                }
