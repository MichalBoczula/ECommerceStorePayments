"""Real atomic claims, lease boundaries and stale-worker commands through HTTP adapters."""

from __future__ import annotations

import asyncio
import importlib
import json
from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

import pytest

from ecommerce_store_payments.application.payments.fulfillment import (
    CompletedInvoice,
    FulfillmentLeaseLostError,
    FulfillmentWork,
)
from ecommerce_store_payments.application.payments.fulfillment_service import FulfillmentService
from ecommerce_store_payments.infrastructure.persistence.mongodb.fulfill_payments import run
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.fulfillment_repository import (
    MongoFulfillmentRepository,
)
from tests.acceptance.concurrency_checks import WriteGates, attempt
from tests.acceptance.evidence import REQUEST_ATTEMPT, attempt_scope
from tests.acceptance.fulfillment_checks import (
    OPTIONAL_WORK_FIELDS,
    WORK_FIELDS,
    FulfillmentChecks,
    immutable_worker_state,
)
from tests.acceptance.payment_checks import Snapshot, full_payment, lossless
from tests.acceptance.retry_checks import milliseconds


def work_value(work: FulfillmentWork) -> dict[str, Any]:
    return {
        "eventId": work.event_id,
        "paymentId": str(work.payment_id),
        "orderId": str(work.order_id),
        "attemptId": str(work.attempt_id),
        "amountMinor": work.money.amount_minor,
        "currency": work.money.currency,
        "leaseId": str(work.lease_id),
        "attempts": work.attempts,
        "clientId": str(work.client_id) if work.client_id else None,
        "orderPaid": work.order_paid,
    }


class WorkerConcurrencyChecks:
    def __init__(self, fulfillment: FulfillmentChecks) -> None:
        self.fulfillment = fulfillment
        self.context, self.payments = fulfillment.context, fulfillment.payments
        self.inputs: dict[str, str] = {}
        self.before: Snapshot = {}
        self.active: Snapshot = {}
        self.winning: Snapshot = {}
        self.after: Snapshot = {}
        self.gates = WriteGates()
        self.clock = milliseconds(datetime.now(UTC))
        self.clocks: dict[str, datetime] = {}
        self.claim_clock = self.clock
        self.work: FulfillmentWork | None = None
        self.claims: list[dict[str, Any]] = []
        self.stale: list[dict[str, Any]] = []
        self.processed: dict[str, int] = {}
        self.upstream_before: dict[str, Any] = {}
        self.upstream_winner: dict[str, Any] = {}
        self.http: list[dict[str, Any]] = []
        self.stripe_calls = 0
        self.sessions: dict[str, Any] = {}

    def configure(self, values: dict[str, str]) -> None:
        assert values.keys() == {"Mode", "Winner", "Participants", "AdvanceMilliseconds"}
        assert values["Mode"] in {
            "claims",
            "lease-boundary",
            "lease-expiry",
            "stale-save_order_paid",
            "stale-complete",
            "stale-fail",
        }
        assert values["Winner"] in {f"worker-{n}" for n in range(1, 9)}
        assert int(values["Participants"]) == (
            8 if values["Mode"] == "claims" else 1 if values["Mode"] == "lease-expiry" else 2
        )
        assert int(values["AdvanceMilliseconds"]) in {0, 299999, 300000, 300001}
        self.inputs = values
        assert self.fulfillment.boundary is not None
        self.before = self.payments.snapshot()
        self.upstream_before = self.fulfillment.boundary.snapshot()
        self.clock = milliseconds(datetime.now(UTC))
        self.claim_clock = self.clock
        self.stripe_calls, self.sessions = len(self.context.stripe.calls), deepcopy(self.context.stripe.sessions)
        self.context.evidence.observation(
            "Worker concurrency schedule",
            {
                "expected": values,
                "clock": self.clock.isoformat(),
                "before": lossless(self.before),
                "upstream": self.upstream_before,
            },
        )

    def target(self, snapshot: Snapshot) -> dict[str, Any]:
        return next(d for d in snapshot["stripe_webhooks"] if d["_id"] == self.fulfillment.event_id)

    def execute(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert self.inputs
        module = importlib.import_module("ecommerce_store_payments.infrastructure.persistence.mongodb.fulfill_payments")
        original_claim = MongoFulfillmentRepository.claim
        original_handler = self.context.orders.fulfillment_handler
        assert original_handler is not None
        mode, winner = self.inputs["Mode"], self.inputs["Winner"]
        database_name = self.context.settings.mongodb_database_name
        settings = self.context.settings.model_copy(
            update={"stripe_enabled": False, "stripe_secret_key": None, "stripe_webhook_secret": None}
        )

        def service(work: Any, payments: Any, orders: Any, invoices: Any) -> FulfillmentService:
            return FulfillmentService(
                work, payments, orders, invoices, lambda: self.clocks[cast(str, REQUEST_ATTEMPT.get())]
            )

        def handler(request: Any) -> Any:
            response = original_handler(request)
            self.http.append(
                {
                    "attempt": attempt(),
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                }
            )
            return response

        async def claim(repository: MongoFulfillmentRepository, now: datetime) -> FulfillmentWork | None:
            if cast(Any, repository)._collection.database.name != database_name:
                return await original_claim(repository, now)
            label = attempt()
            if mode == "claims":
                await self.gates.pause(label, "claim", now=now)
            work = await original_claim(repository, now)
            snapshot = self.payments.snapshot()
            self.claims.append(
                {
                    "attempt": label,
                    "clock": now.isoformat(),
                    "work": work_value(work) if work else None,
                    "collections": lossless(snapshot),
                }
            )
            if work is not None:
                self.work = work
                self.claim_clock = now
                if mode == "claims":
                    assert label == winner
                    self.active = snapshot
                    await self.gates.pause(label, "active", work=work_value(work), collections=snapshot)
            return work

        async def worker(label: str) -> int:
            with attempt_scope(label):
                count = await run(settings, 1)
                self.processed[label] = count
                return count

        async def compete() -> None:
            labels = tuple(f"worker-{n}" for n in range(1, 9))
            self.clocks = dict.fromkeys(labels, self.clock)
            tasks = {label: asyncio.create_task(worker(label)) for label in labels}
            try:
                await self.gates.wait_async(labels, "claim")
                self.gates.release(winner, "claim")
                await self.gates.wait_async((winner,), "active")
                others = tuple(label for label in labels if label != winner)
                for label in others:
                    self.gates.release(label, "claim")
                assert await asyncio.gather(*(tasks[label] for label in others)) == [0] * 7
                assert self.payments.snapshot() == self.active and not self.http
                self.gates.release(winner, "active")
                assert await tasks[winner] == 1
                self.winning = self.payments.snapshot()
            finally:
                self.gates.open_all()
                await asyncio.gather(*tasks.values(), return_exceptions=True)

        async def stale_workers(patch: pytest.MonkeyPatch) -> None:
            point = mode.removeprefix("stale-")
            original = getattr(MongoFulfillmentRepository, point)
            self.clocks = {
                "worker-1": self.clock,
                "worker-2": self.clock + timedelta(milliseconds=int(self.inputs["AdvanceMilliseconds"])),
            }

            async def fenced(repository: MongoFulfillmentRepository, *args: Any, **kwargs: Any) -> Any:
                if cast(Any, repository)._collection.database.name != database_name or attempt() != "worker-1":
                    return await original(repository, *args, **kwargs)
                old_work = args[0]
                assert isinstance(old_work, FulfillmentWork)
                await self.gates.pause(
                    "worker-1",
                    "stale",
                    work=work_value(old_work),
                    invokedAt=args[-1],
                    collections=self.payments.snapshot(),
                )
                try:
                    return await original(repository, *args, **kwargs)
                except FulfillmentLeaseLostError:
                    self.stale.append(
                        {
                            "point": point,
                            "exception": "FulfillmentLeaseLostError",
                            "work": work_value(old_work),
                            "invokedAt": lossless(args[-1]),
                            "after": lossless(self.payments.snapshot()),
                        }
                    )
                    raise

            patch.setattr(MongoFulfillmentRepository, point, fenced)
            old = asyncio.create_task(worker("worker-1"))
            try:
                await self.gates.wait_async(("worker-1",), "stale")
                self.active = self.payments.snapshot()
                assert await worker("worker-2") == 1
                self.winning = self.payments.snapshot()
                assert self.fulfillment.boundary is not None
                self.upstream_winner = self.fulfillment.boundary.snapshot()
                self.gates.release("worker-1", "stale")
                assert await old == 1
                assert self.payments.snapshot() == self.winning
                assert self.fulfillment.boundary.snapshot() == self.upstream_winner
            finally:
                self.gates.open_all()
                await asyncio.gather(old, return_exceptions=True)

        with self.context.evidence.action("Run real coordinated fulfillment commands", self.inputs) as output:
            with monkeypatch.context() as patch:
                patch.setattr(module, "FulfillmentService", service)
                if not mode.startswith("lease-"):
                    patch.setattr(MongoFulfillmentRepository, "claim", claim)
                patch.setattr(self.context.orders, "fulfillment_handler", handler)
                if mode == "claims":
                    asyncio.run(compete())
                elif mode.startswith("lease-"):
                    asyncio.run(self.lease_boundary())
                else:
                    if mode == "stale-fail":
                        assert self.fulfillment.boundary is not None
                        self.fulfillment.boundary.mode = "pdf_failure"
                    asyncio.run(stale_workers(patch))
            self.after = self.payments.snapshot()
            output.update(
                claims=self.claims,
                stale=self.stale,
                processed=self.processed,
                witnesses=self.gates.witnesses,
                active=lossless(self.active),
                winning=lossless(self.winning),
                after=lossless(self.after),
            )
        self.context.evidence.observation(
            "Complete worker coordination",
            {
                "inputs": self.inputs,
                "clock": self.clock.isoformat(),
                "claimClock": self.claim_clock.isoformat(),
                "before": lossless(self.before),
                "active": lossless(self.active),
                "winning": lossless(self.winning),
                "after": lossless(self.after),
                "claims": self.claims,
                "stale": self.stale,
                "processed": self.processed,
                "http": self.http,
                "upstreamBefore": self.upstream_before,
                "upstreamAfter": self.fulfillment.boundary.snapshot() if self.fulfillment.boundary else None,
            },
        )

    async def lease_boundary(self) -> None:
        # Call the real repository directly. This action is not reported as a worker batch or HTTP request.
        database = MongoDatabase(self.context.settings)
        repository = MongoFulfillmentRepository(database)
        try:
            first = await repository.claim(self.clock)
            assert first is not None
            self.claims.append(
                {
                    "attempt": "worker-1",
                    "clock": self.clock.isoformat(),
                    "work": work_value(first),
                    "collections": lossless(self.payments.snapshot()),
                }
            )
            self.active = self.payments.snapshot()
            later = self.clock + timedelta(milliseconds=int(self.inputs["AdvanceMilliseconds"]))
            second = await repository.claim(later) if self.inputs["Mode"] == "lease-boundary" else None
            if self.inputs["Mode"] == "lease-boundary":
                self.claims.append(
                    {
                        "attempt": "worker-2",
                        "clock": later.isoformat(),
                        "work": work_value(second) if second else None,
                        "collections": lossless(self.payments.snapshot()),
                    }
                )
            self.work, self.claim_clock = (second, later) if second else (first, self.clock)
            self.winning = self.payments.snapshot()
            if second or self.inputs["Mode"] == "lease-expiry":
                if second:
                    assert second.lease_id != first.lease_id and second.attempts == 2
                invoice = CompletedInvoice(
                    UUID("44444444-4444-4444-8444-444444444444"),
                    first.order_id,
                    UUID("33333333-3333-4333-8333-333333333333"),
                )
                commands: dict[str, Callable[[], Any]] = {
                    "save_order_paid": lambda: repository.save_order_paid(first, self.context.orders.client_id, later),
                    "complete": lambda: repository.complete(first, invoice, later),
                    "fail": lambda: repository.fail(first, "stale", later + timedelta(seconds=60), later),
                }
                for point, command in commands.items():
                    try:
                        await command()
                    except FulfillmentLeaseLostError:
                        self.stale.append(
                            {
                                "point": point,
                                "exception": "FulfillmentLeaseLostError",
                                "work": work_value(first),
                                "invokedAt": lossless(later),
                                "after": lossless(self.payments.snapshot()),
                            }
                        )
                    else:
                        raise AssertionError("An old lease changed the replacement owner")
                    assert self.payments.snapshot() == self.winning
            else:
                assert self.winning == self.active
        finally:
            await database.close()

    def record(self, values: dict[str, str]) -> None:
        assert values.keys() == WORK_FIELDS and self.work is not None
        before, after = self.target(self.before), self.target(self.after)
        assert set(after) == {k for k, value in values.items() if value != "<absent>"}
        boundary = self.fulfillment.boundary
        assert boundary is not None
        substitutions: dict[str, Any] = {
            "{clock}": self.claim_clock,
            "{lease.id}": self.work.lease_id,
            "{lease.until}": self.claim_clock + timedelta(seconds=300),
            "{client.id}": self.context.orders.client_id,
            "{invoice.id}": UUID(boundary.invoice["id"]) if boundary.invoice else None,
            "{invoice.version}": UUID(boundary.invoice["clietDataVersionId"]) if boundary.invoice else None,
        }
        for key, value in values.items():
            if value == "<absent>":
                assert key in OPTIONAL_WORK_FIELDS and key not in after
                continue
            if value == "{before}":
                assert after[key] == before[key]
            else:
                expected = substitutions[value] if value in substitutions else json.loads(value)
                assert type(after[key]) is type(expected) and after[key] == expected, key
        immutable_worker_state(self.before, self.after, self.fulfillment.event_id)
        self.context.evidence.observation(
            "Complete coordinated worker receipt",
            {
                "expected": values,
                "before": lossless(before),
                "receipt": lossless(after),
                "claimClock": self.claim_clock.isoformat(),
                "work": work_value(self.work),
            },
        )

    def effects(self, values: dict[str, str]) -> None:
        assert values.keys() == {
            "Claims",
            "Processed",
            "StaleRejections",
            "LogicalPaidWrites",
            "LogicalInvoices",
            "StripeCalls",
            "FinalStatus",
        }
        assert len([c for c in self.claims if c["work"] is not None]) == int(values["Claims"])
        assert sum(self.processed.values()) == int(values["Processed"])
        assert len(self.stale) == int(values["StaleRejections"])
        boundary = self.fulfillment.boundary
        assert boundary is not None and boundary.logical_paid == int(values["LogicalPaidWrites"])
        assert boundary.logical_invoices == int(values["LogicalInvoices"])
        assert len(self.context.stripe.calls) - self.stripe_calls == int(values["StripeCalls"]) == 0
        assert self.context.stripe.sessions == self.sessions
        assert self.target(self.after)["fulfillment_status"] == values["FinalStatus"]
        assert self.after == self.winning == self.payments.snapshot()
        if values["FinalStatus"] == "completed":
            assert self.context.orders.status == "Paid" and boundary.invoice is not None
            assert (
                self.target(self.after)["fulfillment_lease_id"]
                is self.target(self.after)["fulfillment_lease_until"]
                is None
            )
        for rejection in self.stale:
            assert rejection["after"] == lossless(self.winning)
        self.context.evidence.observation(
            "Coordinated worker effects",
            {
                "expected": values,
                "processed": self.processed,
                "claims": self.claims,
                "stale": self.stale,
                "before": lossless(self.before),
                "after": lossless(self.after),
                "http": self.http,
                "upstream": boundary.snapshot(),
            },
        )

    def supporting(self, payment: dict[str, str]) -> None:
        before = self.payments.snapshot()
        calls = len(self.context.orders.http_calls), len(self.context.stripe.calls)
        response = self.context.client.get(f"/payments/order/{self.context.orders.order_id}")
        stored = self.payments.target(before)
        assert stored is not None and response.status_code == 200
        resolved = {
            k: json.dumps(stored["provider_session_id"]) if v == "{stored.session_id}" else v
            for k, v in payment.items()
        }
        full_payment(response.json(), stored, resolved)
        assert self.payments.snapshot() == before == self.after
        assert calls == (len(self.context.orders.http_calls), len(self.context.stripe.calls))
        self.context.evidence.observation(
            "Complete payment read after worker coordination",
            {
                "expected": payment,
                "stored": lossless(stored),
                "body": response.json(),
                "collections": lossless(before),
                "exchangeId": response.extensions["payments.bdd.exchangeId"],
            },
        )
