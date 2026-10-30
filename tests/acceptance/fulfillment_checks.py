"""Full durable-worker state, explicit actions, HTTP ordering and immutable Payment evidence."""

from __future__ import annotations

import asyncio
import importlib
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import pytest

from ecommerce_store_payments.application.payments.fulfillment import (
    CompletedInvoice,
    FulfillmentInvoices,
    FulfillmentOrders,
    FulfillmentRepository,
    FulfillmentWork,
)
from ecommerce_store_payments.application.payments.fulfillment_service import FulfillmentService
from ecommerce_store_payments.domain.aggregates.payments.repositories.payment_repository import PaymentRepository
from ecommerce_store_payments.infrastructure.persistence.mongodb.fulfill_payments import run
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.fulfillment_repository import (
    MongoFulfillmentRepository,
)
from tests.acceptance.fulfillment_boundary import FulfillmentBoundary
from tests.acceptance.payment_checks import PaymentChecks, Snapshot, full_payment, lossless
from tests.acceptance.retry_checks import milliseconds
from tests.acceptance.webhook_verification_checks import UNKNOWN_RECEIPT_FIELDS
from tests.webhook_fixtures import encode, payload_for, signature

OPTIONAL_WORK_FIELDS = {
    "fulfillment_attempts",
    "fulfillment_lease_id",
    "fulfillment_lease_until",
    "fulfillment_next_attempt",
    "fulfillment_error",
    "fulfillment_order_paid",
    "fulfillment_client_id",
    "fulfillment_invoice_id",
    "fulfillment_client_data_version_id",
    "fulfillment_completed_at",
}
WORK_FIELDS = UNKNOWN_RECEIPT_FIELDS | OPTIONAL_WORK_FIELDS


def complete_work(
    previous: dict[str, Any],
    actual: dict[str, Any],
    authored: dict[str, str],
    clock: datetime,
    client_id: UUID,
    invoice: dict[str, Any] | None,
) -> None:
    assert authored.keys() == WORK_FIELDS
    assert actual.keys() == {k for k, v in authored.items() if v != "<absent>"}
    for key, value in authored.items():
        if value == "<absent>":
            assert key in OPTIONAL_WORK_FIELDS and key not in actual
            continue
        if value == "{before}":
            assert key in previous and lossless(actual[key]) == lossless(previous[key]), key
            continue
        expected: Any
        if value == "{clock}":
            expected = clock
        elif value.startswith("{clock+"):
            expected = clock + timedelta(seconds=int(value.removeprefix("{clock+").removesuffix("s}")))
        elif value == "{client.id}":
            expected = client_id
        elif value in {"{invoice.id}", "{invoice.version}"}:
            assert invoice is not None
            expected = UUID(invoice["id" if value == "{invoice.id}" else "clietDataVersionId"])
        else:
            expected = json.loads(value)
        observed = actual[key]
        assert type(observed) is type(expected) and observed == expected, key
        if isinstance(observed, datetime):
            assert observed == milliseconds(observed)
    if actual.get("fulfillment_completed_at") is not None:
        assert actual["fulfillment_completed_at"] >= actual["completed_at"]


def immutable_worker_state(before: Snapshot, after: Snapshot, event_id: str) -> None:
    assert lossless(after["payments"]) == lossless(before["payments"])
    assert lossless(after["payment_history"]) == lossless(before["payment_history"])
    assert lossless([d for d in after["stripe_webhooks"] if d["_id"] != event_id]) == lossless(
        [d for d in before["stripe_webhooks"] if d["_id"] != event_id]
    )
    assert len(after["stripe_webhooks"]) == len(before["stripe_webhooks"])


class FulfillmentChecks:
    def __init__(self, payments: PaymentChecks) -> None:
        self.payments, self.context = payments, payments.context
        self.boundary: FulfillmentBoundary | None = None
        self.before: Snapshot | None = None
        self.after: Snapshot | None = None
        self.clock: datetime | None = None
        self.window: tuple[datetime, datetime] | None = None
        self.batch: dict[str, Any] | None = None
        self.counts: dict[str, int] = {}
        self.event_id = "evt_fulfillment"
        self.saved_client = self.context.orders.client_id

    def observe(self, name: str, value: object) -> None:
        n = self.counts.get(name, 0) + 1
        self.counts[name] = n
        self.context.evidence.observation(name if n == 1 else f"{name} ({n})", value)

    def settle_unrelated(self) -> None:
        context, orders = self.context, self.context.orders
        document = next(d for d in self.payments.snapshot()["payments"] if d["order_id"] != orders.order_id)
        saved = orders.order_id, orders.client_id, orders.amount, orders.currency, orders.status, orders.invoice_id
        try:
            from decimal import Decimal

            orders.order_id, orders.client_id = document["order_id"], UUID("77777777-7777-4777-8777-777777777777")
            orders.amount, orders.currency, orders.status, orders.invoice_id = Decimal("31.73"), "PLN", "Created", None
            with context.evidence.action(
                "Settle unrelated work through the real worker",
                {"orderId": str(orders.order_id)},
                source_id="payments.command.fulfill",
            ) as output:
                assert asyncio.run(run(context.settings, 100)) == 1
                assert context.webhooks.count_documents({"fulfillment_status": "completed"}) == 1
                output["collections"] = lossless(self.payments.snapshot())
        finally:
            orders.order_id, orders.client_id, orders.amount, orders.currency, orders.status, orders.invoice_id = saved

    def prepare(self, values: dict[str, str]) -> None:
        assert values.keys() == {"Mode", "PriorRetries", "ReceiptFixture"}
        context = self.context
        response = context.client.post(f"/payments/{context.orders.order_id}/checkout")
        assert response.status_code == 200
        document = context.payments.find_one({"order_id": context.orders.order_id})
        assert document is not None
        context.webhook_payload = encode(payload_for(PaymentMapper.to_domain(document), event_id=self.event_id))
        context.send(
            "POST",
            "/payments/webhooks/stripe",
            content=context.webhook_payload,
            content_type="application/json",
            headers={"stripe-signature": signature(context.webhook_payload)},
        )
        assert context.responses[0].status_code == 200 and context.responses[0].json() == {"received": True}
        self.bind(values["Mode"])
        fixture = values["ReceiptFixture"]
        if fixture != "none":
            changes = {
                "missing_payment": {"payment_id": UUID(int=99)},
                "stale_attempt": {"attempt_id": UUID(int=99)},
                "attempts_ten": {"fulfillment_attempts": 10},
            }[fixture]
            with context.evidence.action(
                "Prepare explicit historical work association/count", {"fixture": fixture, "changes": lossless(changes)}
            ) as output:
                context.webhooks.update_one({"_id": self.event_id}, {"$set": changes})
                output["receipt"] = lossless(context.webhooks.find_one({"_id": self.event_id}))
        for _ in range(int(values["PriorRetries"])):
            self.run_batch({"Limit": "100", "Clock": "now" if self.clock is None else "due", "Processed": "1"})
        self.observe("Worker fixture inputs", values)

    def bind(self, mode: str) -> None:
        assert self.boundary is None
        self.boundary = FulfillmentBoundary(self.context.orders, mode)
        self.context.orders.fulfillment_handler = self.boundary.handle
        self.saved_client = self.context.orders.client_id

    def remember(self) -> None:
        if self.boundary is None:
            self.bind(self.context.orders.fulfillment_mode)
        self.before = self.payments.snapshot()
        self.observe("Worker collections before", {"collections": lossless(self.before)})

    def target(self, snapshot: Snapshot) -> dict[str, Any]:
        return next(d for d in snapshot["stripe_webhooks"] if d["_id"] == self.event_id)

    def run_batch(self, values: dict[str, str]) -> None:
        assert values.keys() == {"Limit", "Clock", "Processed"} and self.boundary is not None
        context = self.context
        before = self.payments.snapshot()
        upstream = self.boundary.snapshot()
        stripe_calls, stripe_sessions = len(context.stripe.calls), deepcopy(context.stripe.sessions)
        start = len(self.boundary.trace)
        previous = self.target(before)
        choice = values["Clock"]
        if choice == "now":
            self.clock = None
        else:
            assert choice in {"due", "before_due"} and isinstance(previous.get("fulfillment_next_attempt"), datetime)
            self.clock = previous["fulfillment_next_attempt"] - timedelta(
                milliseconds=1 if choice == "before_due" else 0
            )

        def service(
            work: FulfillmentRepository,
            payments: PaymentRepository,
            orders: FulfillmentOrders,
            invoices: FulfillmentInvoices,
        ) -> FulfillmentService:
            if self.clock is None:
                self.clock = milliseconds(datetime.now(UTC))
            return FulfillmentService(
                work, payments, orders, invoices, lambda: self.clock if self.clock is not None else datetime.now(UTC)
            )

        settings = context.settings.model_copy(
            update={"stripe_enabled": False, "stripe_secret_key": None, "stripe_webhook_secret": None}
        )
        lower = datetime.now(UTC)
        with context.evidence.action(
            "Run durable fulfillment command",
            {**values, "providerCredentials": False},
            source_id="payments.command.fulfill",
        ) as output:
            with pytest.MonkeyPatch.context() as patch:
                patch.setattr(
                    importlib.import_module(
                        "ecommerce_store_payments.infrastructure.persistence.mongodb.fulfill_payments"
                    ),
                    "FulfillmentService",
                    service,
                )
                processed = asyncio.run(run(settings, int(values["Limit"])))
            assert processed == int(values["Processed"])
            if self.clock is None:
                self.clock = milliseconds(datetime.now(UTC))
            self.window = lower, datetime.now(UTC)
            self.before, self.after = before, self.payments.snapshot()
            self.batch = {
                "inputs": values,
                "processed": processed,
                "before": lossless(before),
                "after": lossless(self.after),
                "clock": self.clock.isoformat(),
                "window": [t.isoformat() for t in self.window],
                "upstreamBefore": upstream,
                "upstreamAfter": self.boundary.snapshot(),
                "calls": deepcopy(self.boundary.trace[start:]),
            }
            assert len(context.stripe.calls) == stripe_calls and context.stripe.sessions == stripe_sessions
            if processed == 0:
                assert self.after == before and self.boundary.snapshot() == upstream and not self.batch["calls"]
            output.update(self.batch)

    def state(self, values: dict[str, str]) -> None:
        assert (
            self.before is not None and self.after is not None and self.clock is not None and self.boundary is not None
        )
        assert self.payments.snapshot() == self.after
        complete_work(
            self.target(self.before),
            self.target(self.after),
            values,
            self.clock,
            self.saved_client,
            self.boundary.invoice,
        )
        immutable_worker_state(self.before, self.after, self.event_id)
        assert not [c for c in self.boundary.trace if "stripe" in c["path"]]
        self.observe(
            "Complete fulfillment receipt and isolation",
            {"expected": values, "batch": self.batch, "receipt": lossless(self.target(self.after))},
        )

    def http(self, values: dict[str, str]) -> None:
        assert (
            values.keys() == {"Sequence", "LogicalPaidWrites", "LogicalInvoices", "InvoiceVersion"}
            and self.boundary is not None
            and self.batch is not None
        )
        sequence: list[str] = []
        for call in self.batch["calls"]:
            label = (
                "paid"
                if call["method"] == "PATCH"
                else "create"
                if call["method"] == "POST"
                else "invoice"
                if "/invoices/" in call["path"]
                else "order"
            )
            sequence.append(f"{label}:{call['result']}")
        assert " ".join(sequence) == values["Sequence"].replace("<none>", "")
        assert self.boundary.logical_paid == int(values["LogicalPaidWrites"]) and self.boundary.logical_invoices == int(
            values["LogicalInvoices"]
        )
        if values["InvoiceVersion"] != "null":
            assert self.boundary.invoice is not None and self.boundary.invoice["clietDataVersionId"] == json.loads(
                values["InvoiceVersion"]
            )
            assert UUID(self.boundary.invoice["clietDataVersionId"]) != self.saved_client
        self.observe("Exact fulfillment HTTP sequence", {"expected": values, "batch": self.batch})

    def read(self, values: dict[str, str]) -> None:
        snapshot = self.payments.snapshot()
        current = self.payments.target(snapshot)
        assert current is not None
        response = self.context.client.get(f"/payments/order/{self.context.orders.order_id}")
        assert response.status_code == 200 and response.headers["content-type"] == "application/json"
        resolved = {
            key: json.dumps(str(current["order_id"]))
            if value == "{order.id}"
            else json.dumps(current["provider_session_id"])
            if value == "{stored.session_id}"
            else value
            for key, value in values.items()
        }
        full_payment(response.json(), current, resolved)
        assert self.payments.snapshot() == snapshot
        self.observe(
            "Complete payment read after fulfillment",
            {
                "expected": values,
                "body": response.json(),
                "stored": lossless(current),
                "exchangeId": response.extensions["payments.bdd.exchangeId"],
            },
        )

    def change(self, values: dict[str, str]) -> None:
        assert values.keys() == {"Mode", "OrderStatus", "ClientId"} and self.boundary is not None
        with self.context.evidence.action(
            "Repair or change controlled authoritative downstream state", values
        ) as output:
            self.boundary.mode = values["Mode"]
            if values["OrderStatus"] != "unchanged":
                self.context.orders.status = values["OrderStatus"]
            if values["ClientId"] != "unchanged":
                self.context.orders.client_id = UUID(values["ClientId"])
            output["upstream"] = self.boundary.snapshot()

    def interrupt(self, values: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
        assert values.keys() == {"Point"}
        point = values["Point"]
        assert point in {"paid_before", "paid_after", "complete_before", "complete_after"}
        method = "save_order_paid" if point.startswith("paid_") else "complete"
        original = getattr(MongoFulfillmentRepository, method)
        remaining = True

        async def interrupted(
            repository: MongoFulfillmentRepository,
            work: FulfillmentWork,
            argument: UUID | CompletedInvoice,
            now: datetime,
        ) -> None:
            nonlocal remaining
            if work.event_id == self.event_id and remaining:
                remaining = False
                with self.context.evidence.action(
                    "Interrupt local fulfillment persistence acknowledgement", values
                ) as output:
                    output["before"] = lossless(self.payments.snapshot())
                    if point.endswith("after"):
                        await original(repository, work, argument, now)
                    output["after"] = lossless(self.payments.snapshot())
                raise RuntimeError("controlled local fulfillment acknowledgement loss")
            await original(repository, work, argument, now)

        monkeypatch.setattr(MongoFulfillmentRepository, method, interrupted)

    def resume(self, values: dict[str, str]) -> None:
        assert values == {"Result": "1", "PreservePaidProgress": "true"}
        before = self.payments.snapshot()
        old = self.target(before)
        assert old["fulfillment_status"] == "failed"
        with self.context.evidence.action(
            "Resume repaired failed work through the operator command", values, source_id="payments.command.fulfill"
        ) as output:
            lower = datetime.now(UTC)
            assert asyncio.run(run(self.context.settings, 100, resume=self.event_id)) == 1
            upper = datetime.now(UTC)
            after = self.payments.snapshot()
            new = self.target(after)
            expected = {
                **old,
                "fulfillment_status": "pending",
                "fulfillment_attempts": 0,
                "fulfillment_error": None,
                "fulfillment_next_attempt": new["fulfillment_next_attempt"],
            }
            assert new == expected and milliseconds(lower) <= new["fulfillment_next_attempt"] <= milliseconds(upper)
            immutable_worker_state(before, after, self.event_id)
            output.update(before=lossless(before), after=lossless(after), window=[lower.isoformat(), upper.isoformat()])
