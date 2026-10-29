"""Negative checks for complete durable evidence and strict controlled HTTP fixtures."""

from copy import deepcopy
from datetime import timedelta
from typing import Any
from uuid import UUID

import pytest
from httpx import Request
from pytest_bdd.parser import FeatureParser
from scripts.generate_operation_links import FEATURES

from tests.acceptance.conftest import OrdersBoundary
from tests.acceptance.evidence import table_values
from tests.acceptance.fulfillment_boundary import DATA_VERSION, FulfillmentBoundary
from tests.acceptance.fulfillment_checks import WORK_FIELDS, complete_work, immutable_worker_state
from tests.acceptance.payment_checks import PUBLIC_FIELDS, Snapshot
from tests.unit.api.test_checkout_evidence import WINDOW
from tests.unit.api.test_webhook_lifecycle_evidence import receipt_sample

CLIENT = UUID("22222222-2222-4222-8222-222222222222")
CLOCK = WINDOW[0] + timedelta(milliseconds=500)


def authored() -> dict[str, str]:
    feature = FeatureParser(str(FEATURES), "fulfillment_recovery.feature").parse()
    scenario = next(s for s in feature.scenarios.values() if s.name.startswith("PAY09-01 "))
    step = next(s for s in scenario.steps if s.name == "the complete durable fulfillment record is")
    assert step.datatable is not None
    return table_values([[cell.value for cell in row.cells] for row in step.datatable.rows])


def sample() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    previous, _, _ = receipt_sample()
    invoice = {"id": "55555555-5555-4555-8555-555555555555", "clietDataVersionId": str(DATA_VERSION)}
    actual = {
        **previous,
        "fulfillment_status": "completed",
        "fulfillment_attempts": 1,
        "fulfillment_lease_id": None,
        "fulfillment_lease_until": None,
        "fulfillment_next_attempt": None,
        "fulfillment_error": None,
        "fulfillment_order_paid": True,
        "fulfillment_client_id": CLIENT,
        "fulfillment_invoice_id": UUID(invoice["id"]),
        "fulfillment_client_data_version_id": DATA_VERSION,
        "fulfillment_completed_at": CLOCK,
    }
    return previous, actual, invoice


@pytest.mark.parametrize("field", sorted(WORK_FIELDS))
def test_complete_worker_guard_rejects_corruption_of_every_field(field: str) -> None:
    before, after, invoice = sample()
    complete_work(before, after, authored(), CLOCK, CLIENT, invoice)
    after[field] = "corrupt"
    with pytest.raises(AssertionError):
        complete_work(before, after, authored(), CLOCK, CLIENT, invoice)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "extra",
        "boolean_attempts",
        "date_precision",
        "wrong_version",
        "wrong_invoice",
        "completion_clock",
        "explicit_null_for_absent",
    ],
)
def test_worker_guard_requires_presence_types_ids_and_exact_clock(mutation: str) -> None:
    before, after, invoice = sample()
    values = authored()
    if mutation == "missing":
        del after["fulfillment_error"]
    elif mutation == "extra":
        after["raw_event"] = "forbidden"
    elif mutation == "boolean_attempts":
        after["fulfillment_attempts"] = True
    elif mutation == "date_precision":
        after["fulfillment_completed_at"] += timedelta(microseconds=1)
    elif mutation == "wrong_version":
        after["fulfillment_client_data_version_id"] = CLIENT
    elif mutation == "wrong_invoice":
        after["fulfillment_invoice_id"] = UUID(int=99)
    elif mutation == "completion_clock":
        after["fulfillment_completed_at"] += timedelta(milliseconds=1)
    else:
        values["fulfillment_error"] = "<absent>"
    with pytest.raises(AssertionError):
        complete_work(before, after, values, CLOCK, CLIENT, invoice)


@pytest.mark.parametrize("collection", ["payments", "payment_history", "stripe_webhooks"])
@pytest.mark.parametrize("mutation", ["changed", "added", "removed"])
def test_worker_isolation_rejects_changes_to_populated_current_history_and_other_receipts(
    collection: str, mutation: str
) -> None:
    before: Snapshot = {
        name: [{"_id": name, "value": "preserved"}] for name in ["payments", "payment_history", "stripe_webhooks"]
    }
    before["stripe_webhooks"].append({"_id": "evt_target", "fulfillment_status": "pending"})
    after = deepcopy(before)
    after["stripe_webhooks"][-1]["fulfillment_status"] = "completed"
    immutable_worker_state(before, after, "evt_target")
    if mutation == "changed":
        after[collection][0]["value"] = "corrupt"
    elif mutation == "added":
        after[collection].append({"_id": "unexpected"})
    else:
        after[collection].pop(0)
    with pytest.raises(AssertionError):
        immutable_worker_state(before, after, "evt_target")


@pytest.mark.parametrize("mutation", ["wrong_client", "post_body", "patch_status", "wrong_order"])
def test_controlled_boundary_cannot_accept_wrong_owner_body_status_or_route(mutation: str) -> None:
    orders = OrdersBoundary()
    boundary = FulfillmentBoundary(orders, "ok")
    method, path, body = "POST", f"/invoices/{orders.client_id}/{orders.order_id}", b""
    if mutation == "wrong_client":
        path = f"/invoices/{UUID(int=99)}/{orders.order_id}"
    elif mutation == "post_body":
        body = b'{"invented":true}'
    elif mutation == "patch_status":
        method, path, body = "PATCH", f"/orders/{orders.order_id}/status", b'{"status":"Created"}'
    else:
        method, path = "GET", f"/orders/{UUID(int=99)}"
    with pytest.raises(AssertionError):
        boundary.handle(Request(method, "https://orders.example.test" + path, content=body))
    assert not boundary.trace and boundary.logical_paid == boundary.logical_invoices == 0


def test_all_worker_cases_author_complete_presence_isolation_http_and_read_tables() -> None:
    total = 0
    for filename in ["fulfillment.feature", "fulfillment_recovery.feature", "fulfillment_invoice.feature"]:
        feature = FeatureParser(str(FEATURES), filename).parse()
        for scenario in feature.scenarios.values():
            total += 1
            assert scenario.description and len(scenario.description.split()) >= 10
            for name, fields in {
                "the complete durable fulfillment record is": WORK_FIELDS,
                "the worker performs exactly these HTTP operations": {
                    "Sequence",
                    "LogicalPaidWrites",
                    "LogicalInvoices",
                    "InvoiceVersion",
                },
                "the complete payment read after fulfillment is": PUBLIC_FIELDS,
            }.items():
                steps = [s for s in scenario.steps if s.name == name]
                assert steps
                for step in steps:
                    assert step.datatable is not None
                    assert table_values([[c.value for c in row.cells] for row in step.datatable.rows]).keys() == fields
            for step in scenario.steps:
                if step.name in {
                    "the durable fulfillment command runs",
                    "the invoice retry becomes due and the durable fulfillment command runs",
                }:
                    assert step.datatable is not None
                    assert table_values([[c.value for c in row.cells] for row in step.datatable.rows]).keys() == {
                        "Limit",
                        "Clock",
                        "Processed",
                    }
    assert total == 40
