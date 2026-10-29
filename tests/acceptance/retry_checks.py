"""Full retry/history assertions independent of the production history mapper."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.clients.orders.currency_units import to_minor_units
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)
from tests.acceptance.payment_checks import PUBLIC_FIELDS, PaymentChecks, Snapshot, full_payment, lossless

OPTIONAL_LEGACY_FIELDS = {"version", "checkout_attempt_id", "checkout_started_at", "checkout_request_version"}
CURRENT_FIELDS = (PUBLIC_FIELDS - {"id"}) | {"_id", *OPTIONAL_LEGACY_FIELDS}


def milliseconds(value: datetime) -> datetime:
    assert value.utcoffset() == timedelta(0)
    return value.replace(microsecond=value.microsecond // 1000 * 1000)


def archived_snapshot(previous: dict[str, Any], archived: dict[str, Any], window: tuple[datetime, datetime]) -> None:
    assert previous.keys() <= CURRENT_FIELDS and CURRENT_FIELDS - OPTIONAL_LEGACY_FIELDS <= previous.keys()
    version = previous.get("version", 0)
    assert isinstance(version, int) and not isinstance(version, bool) and version >= 0
    expected = {key: value for key, value in previous.items() if key != "_id"}
    expected.update(
        _id=f"{previous['_id']}:{version}",
        payment_id=previous["_id"],
        version=version,
        checkout_attempt_id=previous.get("checkout_attempt_id"),
        checkout_started_at=previous.get("checkout_started_at"),
        checkout_request_version=previous.get("checkout_request_version", 1),
    )
    assert archived.keys() == expected.keys() | {"recorded_at"}
    assert {key: value for key, value in archived.items() if key != "recorded_at"} == expected
    recorded = archived["recorded_at"]
    assert isinstance(recorded, datetime) and recorded == milliseconds(recorded)
    assert milliseconds(window[0]) <= recorded <= milliseconds(window[1])


def transition_delta(
    before: Snapshot, after: Snapshot, order_id: UUID, window: tuple[datetime, datetime]
) -> dict[str, Any]:
    previous_rows = [doc for doc in before["payments"] if doc["order_id"] == order_id]
    current_rows = [doc for doc in after["payments"] if doc["order_id"] == order_id]
    assert len(previous_rows) == len(current_rows) == 1
    previous, current = previous_rows[0], current_rows[0]
    assert current.keys() == CURRENT_FIELDS
    for key in ("_id", "order_id", "amount_minor", "currency", "created_at"):
        assert current[key] == previous[key], key
    assert type(current["version"]) is int and current["version"] == previous.get("version", 0) + 1
    updated = current["updated_at"]
    assert isinstance(updated, datetime) and updated == milliseconds(updated)
    assert milliseconds(window[0]) <= updated <= milliseconds(window[1])
    assert updated >= (previous["updated_at"] or previous["created_at"])
    assert [doc for doc in after["payments"] if doc["_id"] != current["_id"]] == [
        doc for doc in before["payments"] if doc["_id"] != previous["_id"]
    ]
    archive_id = f"{previous['_id']}:{previous.get('version', 0)}"
    assert not any(doc["_id"] == archive_id for doc in before["payment_history"])
    added = [doc for doc in after["payment_history"] if doc["_id"] == archive_id]
    assert len(added) == 1
    archived_snapshot(previous, added[0], window)
    assert [doc for doc in after["payment_history"] if doc["_id"] != archive_id] == before["payment_history"]
    assert after["stripe_webhooks"] == before["stripe_webhooks"]
    return added[0]


def reset_fields(current: dict[str, Any]) -> None:
    assert current["status"] == "created"
    assert all(
        current[field] is None
        for field in (
            "provider_session_id",
            "provider_payment_id",
            "failure_code",
            "checkout_attempt_id",
            "checkout_started_at",
        )
    )
    assert type(current["checkout_request_version"]) is int and current["checkout_request_version"] == 1


class RetryChecks:
    def __init__(self, payments: PaymentChecks) -> None:
        self.payments = payments
        self.context = payments.context
        self.authored: dict[str, str] | None = None

    def complete(self, authored: dict[str, str]) -> None:
        self.authored = authored.copy()
        context = self.context
        stored = self.payments.target(self.payments.snapshot())
        assert stored is not None and context.request_window is not None
        for response in context.responses:
            assert response.status_code == 200
            full_payment(response.json(), stored, authored, update_window=context.request_window)
        context.evidence.observation(
            "Complete retry response",
            {
                "expected": authored,
                "stored": lossless(stored),
                "responses": [r.json() for r in context.responses],
                "exchangeIds": [r.extensions["payments.bdd.exchangeId"] for r in context.responses],
                "requestWindow": [instant.isoformat() for instant in context.request_window],
            },
        )

    def changed(self, authored: dict[str, str]) -> None:
        assert authored.keys() == {
            "PreviousVersion",
            "CurrentVersion",
            "HistoryVersions",
            "HistoryStatuses",
            "CheckoutRequestVersion",
        }
        context, before = self.context, self.payments.before
        assert before is not None and context.request_window is not None
        after = self.payments.snapshot()
        previous, current = self.payments.target(before), self.payments.target(after)
        assert previous is not None and current is not None
        assert previous["status"] in {"failed", "canceled"}
        archive = transition_delta(before, after, context.orders.order_id, context.request_window)
        reset_fields(current)
        assert previous.get("version", 0) == int(authored["PreviousVersion"])
        assert current["version"] == int(authored["CurrentVersion"])
        assert current["checkout_request_version"] == int(authored["CheckoutRequestVersion"])
        history = sorted(
            (doc for doc in after["payment_history"] if doc["payment_id"] == current["_id"]),
            key=lambda doc: doc["version"],
        )
        assert [doc["version"] for doc in history] == list(map(int, authored["HistoryVersions"].split(",")))
        assert [doc["status"] for doc in history] == authored["HistoryStatuses"].split(",")
        assert self.payments.external_calls is not None
        assert (len(context.orders.http_calls), len(context.stripe.calls)) == (
            self.payments.external_calls[0] + 1,
            self.payments.external_calls[1],
        )
        context.evidence.observation(
            "Retry changes one version and one archive",
            {
                "expected": authored,
                "before": lossless(before),
                "after": lossless(after),
                "archive": lossless(archive),
                "requestWindow": [instant.isoformat() for instant in context.request_window],
                "externalCallsBefore": self.payments.external_calls,
                "externalCallsAfter": (len(context.orders.http_calls), len(context.stripe.calls)),
            },
        )

    def rejected(self) -> None:
        context, before = self.context, self.payments.before
        assert before is not None and self.payments.external_calls is not None
        after = self.payments.snapshot()
        assert after == before
        actual = len(context.orders.http_calls), len(context.stripe.calls)
        assert actual == (self.payments.external_calls[0] + 1, self.payments.external_calls[1])
        context.evidence.observation(
            "Rejected retry preserves every document",
            {
                "before": lossless(before),
                "after": lossless(after),
                "externalCallsBefore": self.payments.external_calls,
                "externalCallsAfter": actual,
                "noPaymentHistoryOrReceiptWrites": True,
            },
        )

    def repeat(self) -> None:
        context = self.context
        before = self.payments.snapshot()
        current = self.payments.target(before)
        assert current is not None
        calls = len(context.orders.http_calls), len(context.stripe.calls)
        context.orders.mode = "outage"
        expected = context.client.get(f"/payments/order/{context.orders.order_id}")
        assert expected.status_code == 200
        repeated = context.client.post(f"/payments/{context.orders.order_id}/pay")
        assert repeated.status_code == 200 and repeated.json() == expected.json()
        assert self.authored is not None
        full_payment(repeated.json(), current, self.authored)
        assert self.payments.snapshot() == before
        assert (len(context.orders.http_calls), len(context.stripe.calls)) == calls
        context.evidence.observation(
            "Repeated retry is a read",
            {
                "before": lossless(before),
                "after": lossless(self.payments.snapshot()),
                "expectedBody": expected.json(),
                "actualBody": repeated.json(),
                "externalCalls": calls,
                "exchangeIds": [r.extensions["payments.bdd.exchangeId"] for r in (expected, repeated)],
            },
        )

    def legacy(self, state: str, values: dict[str, str]) -> None:
        assert state in {"created", "failed", "canceled"}
        assert values.keys() == {"OmittedFields", "ProviderSessionId", "FailureCode"}
        assert set(values["OmittedFields"].split(",")) == OPTIONAL_LEGACY_FIELDS
        context = self.context
        payment = Payment.create(
            context.orders.order_id,
            Money(to_minor_units(context.orders.amount, context.orders.currency), context.orders.currency),
        )
        if state != "created":
            payment.mark_as_pending(json.loads(values["ProviderSessionId"]))
            if state == "failed":
                payment.mark_as_failed(json.loads(values["FailureCode"]))
            else:
                payment.cancel()
        document: dict[str, Any] = dict(PaymentMapper.to_document(payment))
        for key in OPTIONAL_LEGACY_FIELDS:
            del document[key]
        with context.evidence.action(
            "Insert historical-schema fixture with physically absent fields", {"state": state, **values}
        ) as output:
            # Ordinary setup uses the repository; only a raw historical fixture can keep these fields absent.
            context.payments.insert_one(cast(PaymentDocument, document))
            stored = context.payments.find_one({"order_id": context.orders.order_id})
            assert stored is not None and not (OPTIONAL_LEGACY_FIELDS & stored.keys())
            assert PaymentMapper.to_domain(stored).version == 0
            output["stored"] = lossless(stored)

    def later_cycle(self, values: dict[str, str]) -> None:
        assert values.keys() == {"SessionId", "FailureCode", "FinalVersion", "HistoryStatuses"}
        context = self.context
        first = self.payments.snapshot()
        initial = self.payments.target(self.payments.before) if self.payments.before is not None else None
        assert initial is not None and initial["checkout_attempt_id"] is not None
        steps: list[dict[str, Any]] = []

        async def prepare() -> None:
            database = MongoDatabase(context.settings)
            try:
                repository = MongoPaymentRepository(database)
                payment = await repository.get_by_order_id(context.orders.order_id)
                assert payment is not None
                for stage in ("reserve", "pending", "failed"):
                    before = self.payments.snapshot()
                    lower = datetime.now(UTC)
                    if stage == "reserve":
                        payment.begin_checkout(request_version=2)
                    elif stage == "pending":
                        payment.mark_as_pending(values["SessionId"])
                    else:
                        payment.mark_as_failed(values["FailureCode"])
                    payment = await repository.update(payment)
                    upper = datetime.now(UTC)
                    after = self.payments.snapshot()
                    archive = transition_delta(before, after, context.orders.order_id, (lower, upper))
                    steps.append(
                        {
                            "before": lossless(before),
                            "after": lossless(after),
                            "archive": lossless(archive),
                            "window": [lower.isoformat(), upper.isoformat()],
                        }
                    )
                    if payment.status.value == "created":
                        assert payment.checkout_attempt_id != initial["checkout_attempt_id"]
            finally:
                await database.close()

        with context.evidence.action("Prepare later failed attempt through repository", values) as output:
            asyncio.run(prepare())
            output["transitions"] = steps
        before = self.payments.snapshot()
        calls = len(context.orders.http_calls), len(context.stripe.calls)
        lower = datetime.now(UTC)
        response = context.client.post(f"/payments/{context.orders.order_id}/pay")
        upper = datetime.now(UTC)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json" and response.headers["x-trace-id"]
        assert (len(context.orders.http_calls), len(context.stripe.calls)) == (calls[0] + 1, calls[1])
        after = self.payments.snapshot()
        current = self.payments.target(after)
        assert current is not None and current["version"] == int(values["FinalVersion"])
        archive = transition_delta(before, after, context.orders.order_id, (lower, upper))
        reset_fields(current)
        for old in first["payment_history"]:
            assert old in after["payment_history"]
        history = sorted(
            (doc for doc in after["payment_history"] if doc["payment_id"] == current["_id"]),
            key=lambda doc: doc["version"],
        )
        assert [doc["version"] for doc in history] == list(range(int(values["FinalVersion"])))
        assert [doc["status"] for doc in history] == values["HistoryStatuses"].split(",")
        body = response.json()
        assert self.authored is not None
        full_payment(body, current, self.authored, update_window=(lower, upper))
        assert body["id"] == str(initial["_id"]) and body["order_id"] == str(initial["order_id"])
        assert all(body[key] is None for key in ("provider_session_id", "provider_payment_id", "failure_code"))
        context.evidence.observation(
            "Later retry preserves all older snapshots",
            {
                "externalCallsBefore": calls,
                "externalCallsAfter": (len(context.orders.http_calls), len(context.stripe.calls)),
                "first": lossless(first),
                "before": lossless(before),
                "after": lossless(after),
                "archive": lossless(archive),
                "expected": values,
                "expectedResponse": self.authored,
                "response": body,
                "exchangeId": response.extensions["payments.bdd.exchangeId"],
                "requestWindow": [lower.isoformat(), upper.isoformat()],
            },
        )
