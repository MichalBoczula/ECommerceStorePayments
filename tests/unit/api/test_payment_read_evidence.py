import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID

import pytest
from bson.int64 import Int64
from httpx import Request
from pytest_bdd.parser import FeatureParser
from scripts.generate_operation_links import FEATURES

from ecommerce_store_payments.infrastructure.clients.orders.generated.models.order_response_dto import OrderResponseDto
from ecommerce_store_payments.infrastructure.clients.orders.http_order_reader import HttpOrderReader
from ecommerce_store_payments.infrastructure.clients.orders.precise_json import PreciseOrderJsonFactory
from tests.acceptance.conftest import OrdersBoundary
from tests.acceptance.evidence import table_values
from tests.acceptance.payment_checks import PUBLIC_FIELDS, PaymentChecks, full_payment, lossless


def example() -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    stored: dict[str, Any] = {
        "_id": UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        "order_id": UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
        "amount_minor": 1299,
        "currency": "PLN",
        "status": "pending",
        "provider_session_id": "cs_expected",
        "provider_payment_id": None,
        "failure_code": None,
        "created_at": datetime(2026, 10, 1, 12, 0, 0, 123000, UTC),
        "updated_at": datetime(2026, 10, 1, 12, 1, 0, 456000, UTC),
    }
    body = {
        key: str(stored["_id"])
        if key == "id"
        else str(stored[key])
        if key == "order_id"
        else stored[key].isoformat()
        if isinstance(stored[key], datetime)
        else stored[key]
        for key in PUBLIC_FIELDS
    }
    expected = {
        key: "{stored.id}" if key == "id" else "{stored." + key + "}" if key.endswith("_at") else json.dumps(body[key])
        for key in PUBLIC_FIELDS
    }
    return body, stored, expected


def test_complete_payment_checks_every_field_and_exact_bson_integer_without_using_api_mapper() -> None:
    body, stored, expected = example()
    full_payment(body, stored, expected)
    body["amount_minor"] = 9007199254740991
    stored["amount_minor"] = Int64(9007199254740991)
    expected["amount_minor"] = "9007199254740991"
    full_payment(body, stored, expected)
    stored["amount_minor"] += 1
    with pytest.raises(AssertionError):
        full_payment(body, stored, expected)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_null",
        "missing_date",
        "extra_internal",
        "money_bool",
        "money_float",
        "currency",
        "order",
        "id",
        "session",
        "provider",
        "failure",
        "naive_date",
        "non_utc_date",
        "space_separator",
        "read_microseconds",
        "missing_expected",
    ],
)
def test_partial_or_corrupt_payment_bodies_are_rejected(mutation: str) -> None:
    body, stored, expected = example()
    if mutation == "missing_null":
        del body["provider_payment_id"]
    elif mutation == "missing_date":
        del body["updated_at"]
    elif mutation == "extra_internal":
        body["checkout_attempt_id"] = "internal"
    elif mutation == "money_bool":
        body["amount_minor"] = True
    elif mutation == "money_float":
        body["amount_minor"] = 1299.0
    elif mutation == "currency":
        body["currency"] = "pln"
    elif mutation == "order":
        body["order_id"] = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    elif mutation == "id":
        body["id"] = "00000000-0000-0000-0000-000000000000"
    elif mutation == "session":
        body["provider_session_id"] = "cs_other"
    elif mutation == "provider":
        body["provider_payment_id"] = "pi_wrong"
    elif mutation == "failure":
        body["failure_code"] = "wrong"
    elif mutation == "naive_date":
        body["created_at"] = "2026-10-01T12:00:00.123000"
    elif mutation == "non_utc_date":
        body["created_at"] = "2026-10-01T14:00:00.123000+02:00"
    elif mutation == "space_separator":
        body["created_at"] = "2026-10-01 12:00:00.123000Z"
    elif mutation == "read_microseconds":
        body["created_at"] = "2026-10-01T12:00:00.123001Z"
    else:
        del expected["failure_code"]
    with pytest.raises(AssertionError):
        full_payment(body, stored, expected)


@pytest.mark.parametrize("mutation", ["valid", "wrong_millisecond", "outside_request"])
def test_creation_timestamp_has_explicit_request_bounds_and_exact_bson_precision(mutation: str) -> None:
    body, stored, expected = example()
    stored.update(status="created", updated_at=None, provider_session_id=None)
    body.update(status="created", updated_at=None, provider_session_id=None, created_at="2026-10-01T12:00:00.123456Z")
    expected.update(status='"created"', updated_at="null", provider_session_id="null")
    parsed = datetime.fromisoformat(body["created_at"])
    window = parsed - timedelta(microseconds=10), parsed + timedelta(microseconds=10)
    if mutation == "wrong_millisecond":
        stored["created_at"] += timedelta(milliseconds=1)
    elif mutation == "outside_request":
        window = parsed + timedelta(seconds=1), parsed + timedelta(seconds=2)
    if mutation == "valid":
        full_payment(body, stored, expected, creation_window=window)
    else:
        with pytest.raises(AssertionError):
            full_payment(body, stored, expected, creation_window=window)


@pytest.mark.parametrize(
    ("amount", "currency", "minor"), [("12.99", "PLN", 1299), ("90071992547409.91", "USD", 9007199254740991)]
)
def test_order_fixture_keeps_exact_json_number_through_real_kiota_parser(
    amount: str, currency: str, minor: int
) -> None:
    boundary = OrdersBoundary(amount=Decimal(amount), currency=currency)
    response = boundary.handle(Request("GET", f"https://orders.example.test/orders/{boundary.order_id}"))
    tokens = json.loads(response.content, parse_float=Decimal)
    assert tokens["totalAmount"] == tokens["lines"][0]["lineTotalAmount"] == Decimal(amount)
    assert isinstance(tokens["totalAmount"], Decimal)
    node = PreciseOrderJsonFactory().get_root_parse_node("application/json", response.content)
    order = node.get_object_value(OrderResponseDto)
    parsed = HttpOrderReader.from_response(boundary.order_id, order)
    assert parsed.money.amount_minor == minor and parsed.money.currency == currency
    if minor > 2**52:
        assert Decimal(str(float(amount))) != Decimal(amount), "This case must expose the former float conversion"


@pytest.mark.parametrize("collection", ["payments", "payment_history", "stripe_webhooks"])
def test_populated_state_guard_detects_changed_unrelated_fields_at_the_same_counts(
    collection: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = {
        name: [{"_id": "unrelated", "value": "original"}] for name in ("payments", "payment_history", "stripe_webhooks")
    }
    after = deepcopy(before)
    after[collection][0]["value"] = "changed"
    checks = PaymentChecks(cast(Any, SimpleNamespace()))
    checks.before, checks.external_calls = before, (0, 0)
    monkeypatch.setattr(checks, "snapshot", lambda: after)
    with pytest.raises(AssertionError, match="Every field"):
        checks.unchanged()


def test_collection_evidence_preserves_bson_int64_uuid_and_millisecond_values() -> None:
    _, stored, _ = example()
    stored["amount_minor"] = Int64(9007199254740991)
    snapshot = lossless(stored)
    assert snapshot["amount_minor"] == {"$numberLong": "9007199254740991"}
    assert snapshot["_id"]["$binary"]["subType"] == "04"
    assert "$numberLong" in snapshot["created_at"]["$date"]
    stored["currency"] = "CHANGED"
    assert snapshot["currency"] == "PLN"


def test_pay_read_source_keeps_full_response_and_effect_assertions() -> None:
    expected = {"PAY11-01", "PAY11-02", "PAY11-03", *{f"PAY03-{n:02d}" for n in (*range(1, 8), 9)}}
    found: set[str] = set()
    for filename in ("payments.feature", "payment_reads.feature"):
        feature = FeatureParser(str(FEATURES), filename).parse()
        for scenario in feature.scenarios.values():
            cid = scenario.name.split()[0]
            if cid not in expected:
                continue
            complete = [step for step in scenario.steps if step.name == "the complete payment response is"]
            assert len(complete) == 1 and complete[0].datatable is not None
            table = [[cell.value for cell in row.cells] for row in complete[0].datatable.rows]
            assert table_values(table).keys() == PUBLIC_FIELDS
            assert any(step.name == "I remember the payment and every collection" for step in scenario.steps)
            assert any(
                step.name
                in {
                    "only the requested payment is inserted",
                    "every payment collection and external call count is unchanged",
                }
                for step in scenario.steps
            )
            found.add(cid)
    assert found == expected
