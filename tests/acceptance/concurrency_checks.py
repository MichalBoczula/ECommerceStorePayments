"""Bounded coordination around real writes; no synthetic successful persistence."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from threading import Event, Lock
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx2 import Response

from ecommerce_store_payments.application.payments.checkout_provider import CheckoutRequest
from ecommerce_store_payments.application.payments.webhook import WebhookReceipt, WebhookState
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import (
    PaymentConflictError,
    PaymentDuplicateError,
)
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)
from tests.acceptance.checkout_checks import checkout_delta, checkout_response, provider_request
from tests.acceptance.evidence import REQUEST_ATTEMPT, attempt_scope
from tests.acceptance.payment_checks import PaymentChecks, Snapshot, full_payment, lossless
from tests.acceptance.retry_checks import (
    CURRENT_FIELDS,
    archived_snapshot,
    reset_fields,
    transition_delta,
)
from tests.acceptance.webhook_lifecycle_checks import receipt_matches
from tests.webhook_fixtures import encode, payload_for, signature

if TYPE_CHECKING:
    pass


def witness_values(details: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value if value is None or isinstance(value, (str, int, float, bool)) else lossless(value)
        for key, value in details.items()
    }


class WriteGates:
    """Thread-visible arrival witnesses and nonblocking async releases, all bounded."""

    TIMEOUT = 15

    def __init__(self) -> None:
        self.lock = Lock()
        self.arrivals: dict[tuple[str, str], Event] = {}
        self.waiters: dict[tuple[str, str], tuple[asyncio.AbstractEventLoop, asyncio.Event]] = {}
        self.released: set[tuple[str, str]] = set()
        self.seen: set[tuple[str, str]] = set()
        self.witnesses: list[dict[str, Any]] = []
        self.opened = False

    def record(self, label: str, point: str, **details: Any) -> None:
        with self.lock:
            self.witnesses.append({"attempt": label, "point": point, **witness_values(details)})

    async def pause(self, label: str, point: str, **details: Any) -> None:
        key = label, point
        event = asyncio.Event()
        with self.lock:
            if key in self.seen:
                return
            self.seen.add(key)
            self.waiters[key] = asyncio.get_running_loop(), event
            self.witnesses.append({"attempt": label, "point": point, **witness_values(details)})
            self.arrivals.setdefault(key, Event()).set()
            if self.opened or key in self.released:
                event.set()
        await asyncio.wait_for(event.wait(), self.TIMEOUT)

    def wait(self, labels: tuple[str, ...], point: str) -> None:
        for label in labels:
            with self.lock:
                event = self.arrivals.setdefault((label, point), Event())
            assert event.wait(self.TIMEOUT), f"Real operation did not reach {label}/{point}"

    async def wait_async(self, labels: tuple[str, ...], point: str) -> None:
        await asyncio.to_thread(self.wait, labels, point)

    def release(self, label: str, point: str) -> None:
        with self.lock:
            key = label, point
            self.released.add(key)
            waiter = self.waiters.get(key)
        if waiter:
            waiter[0].call_soon_threadsafe(waiter[1].set)

    def open_all(self) -> None:
        with self.lock:
            self.opened = True
            waiters = list(self.waiters.values())
        for loop, event in waiters:
            if not loop.is_closed():
                loop.call_soon_threadsafe(event.set)


def attempt() -> str:
    value = REQUEST_ATTEMPT.get()
    assert value in {"first", "second", *[f"worker-{n}" for n in range(1, 9)]}
    return value


def unchanged_except_target(before: Snapshot, after: Snapshot, order_id: UUID) -> None:
    assert [d for d in before["payments"] if d["order_id"] != order_id] == [
        d for d in after["payments"] if d["order_id"] != order_id
    ]
    ids = {d["_id"] for d in before["payment_history"]}
    assert [d for d in after["payment_history"] if d["_id"] in ids] == before["payment_history"]
    assert not (ids - {d["_id"] for d in after["payment_history"]})


def assert_schedule(
    mode: str, winner: str, witnesses: list[dict[str, Any]], before: Snapshot, after: Snapshot, order_id: UUID
) -> None:
    arrivals = [w for w in witnesses if w["point"] == "write"]
    assert len(arrivals) == 2
    proposals = {w["attempt"]: w for w in arrivals}
    assert set(proposals) == {"first", "second"}
    loser = "second" if winner == "first" else "first"
    stored = next(d for d in after["payments"] if d["order_id"] == order_id)
    prior = next((d for d in before["payments"] if d["order_id"] == order_id), None)
    version = prior["version"] if prior else 0
    for proposal in proposals.values():
        assert proposal["collections"] == lossless(before)
        assert proposal["proposed"]["version"] == lossless(version)
        assert proposal["proposed"]["order_id"] == lossless(order_id)
    conflicts = [w for w in witnesses if w["point"] == "rejected-write"]
    expected_conflict = "PaymentDuplicateError" if mode == "pay-create" else "PaymentConflictError"
    assert len(conflicts) == (2 if mode == "checkout" else 1)
    assert all(w["attempt"] == loser and w["exception"] == expected_conflict for w in conflicts)
    assert sorted(w["expectedVersion"] for w in conflicts) == ([0, 1] if mode == "checkout" else [version])
    proposed = proposals[winner]["proposed"]
    if mode == "checkout":
        assert lossless(stored["checkout_attempt_id"]) == proposed["checkout_attempt_id"]
        providers = [w for w in witnesses if w["point"] == "provider"]
        assert {w["attempt"] for w in providers} == {"first", "second"}
        for w in providers:
            staged = next(d for d in w["collections"]["payments"] if d["_id"] == lossless(stored["_id"]))
            assert staged["version"] == lossless(1) and staged["status"] == "created"
            assert staged["checkout_attempt_id"] == proposed["checkout_attempt_id"]
    else:
        assert lossless(stored) == {**proposed, "version": lossless(version if mode == "pay-create" else version + 1)}


class ConcurrencyChecks:
    def __init__(self, payments: PaymentChecks) -> None:
        self.payments, self.context = payments, payments.context
        self.mode = ""
        self.winner = "first"
        self.gates = WriteGates()
        self.before: Snapshot = {}
        self.winning: Snapshot = {}
        self.after: Snapshot = {}
        self.calls: tuple[int, int] = (0, 0)
        self.sessions: dict[str, Any] = {}
        self.window: tuple[datetime, datetime] | None = None
        self.results: dict[str, Any] = {}
        self.payloads: dict[str, bytes] = {}
        self.authored: dict[str, dict[str, str]] = {}

    def configure(self, values: dict[str, str]) -> None:
        assert values.keys() == {"Mode", "Winner"}
        assert values["Mode"] in {
            "pay-create",
            "pay-retry",
            "checkout",
            "repository-pending",
            "repository-canceled",
            "webhook-same",
            "webhook-distinct",
            "webhook-success-first",
            "webhook-expiry-first",
        }
        assert values["Winner"] in {"first", "second"}
        self.mode, self.winner = values["Mode"], values["Winner"]
        self.context.evidence.observation("Concurrency schedule", values)

    @property
    def loser(self) -> str:
        return "second" if self.winner == "first" else "first"

    def start(self) -> None:
        assert self.mode
        self.before = self.payments.snapshot()
        self.calls = len(self.context.orders.http_calls), len(self.context.stripe.calls)
        self.sessions = deepcopy(self.context.stripe.sessions)
        self.window = datetime.now(UTC), datetime.now(UTC)
        self.context.evidence.observation("Coordinated collections before", {"collections": lossless(self.before)})

    def finish(self) -> None:
        assert self.window is not None
        self.window = self.window[0], datetime.now(UTC)
        self.context.request_window = self.window
        self.after = self.payments.snapshot()
        self.context.evidence.observation(
            "Real write coordination",
            {
                "mode": self.mode,
                "winner": self.winner,
                "before": lossless(self.before),
                "winning": lossless(self.winning),
                "after": lossless(self.after),
                "window": [d.isoformat() for d in self.window],
                "witnesses": self.gates.witnesses,
                "results": lossless(self.results),
                "exchangeIds": [r.extensions["payments.bdd.exchangeId"] for r in self.context.responses],
                "providerSessionsBefore": self.sessions,
                "providerSessionsAfter": self.context.stripe.sessions,
                "externalCallsBefore": self.calls,
                "externalCallsAfter": [len(self.context.orders.http_calls), len(self.context.stripe.calls)],
            },
        )

    def paired_http(self, send: Callable[[str], Response], *, provider_gate: bool = False) -> None:
        futures: dict[str, Any] = {}
        with ThreadPoolExecutor(max_workers=2) as executor:
            try:
                futures = {label: executor.submit(send, label) for label in ("first", "second")}
                self.gates.wait(("first", "second"), "write")
                self.gates.release(self.winner, "write")
                if provider_gate:
                    self.gates.wait((self.winner,), "provider")
                    self.gates.release(self.loser, "write")
                    self.gates.wait((self.loser,), "provider")
                    self.gates.release(self.winner, "provider")
                winning_response = futures[self.winner].result(timeout=30)
                assert winning_response.status_code < 400
                self.winning = self.payments.snapshot()
                self.gates.release(self.loser, "provider" if provider_gate else "write")
                self.context.responses = [futures[label].result(timeout=30) for label in ("first", "second")]
            finally:
                self.gates.open_all()
                # All gates are bounded; drain both real requests before patch/database cleanup.
                for future in futures.values():
                    future.result(timeout=30)

    def pay(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert self.mode in {"pay-create", "pay-retry"}
        self.start()
        app = cast(FastAPI, self.context.client.app)
        repository = app.state.payment_service._payment_repository
        original = repository.create if self.mode == "pay-create" else repository.update

        async def write(payment: Payment) -> Payment:
            label = attempt()
            await self.gates.pause(
                label, "write", proposed=PaymentMapper.to_document(payment), collections=self.payments.snapshot()
            )
            try:
                saved = await original(payment)
            except (PaymentDuplicateError, PaymentConflictError) as error:
                self.gates.record(
                    label, "rejected-write", exception=type(error).__name__, expectedVersion=payment.version
                )
                raise
            self.gates.record(label, "committed-write", saved=PaymentMapper.to_document(saved))
            return saved

        with monkeypatch.context() as patch:
            patch.setattr(repository, "create" if self.mode == "pay-create" else "update", write)
            self.paired_http(
                lambda label: self.context.client.post(f"/payments/{self.context.orders.order_id}/pay", attempt=label)
            )
        self.context.last_operation = "POST /payments/{order_id}/pay x2"
        self.finish()

    def checkout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert self.mode == "checkout"
        self.start()
        app = cast(FastAPI, self.context.client.app)
        repository, provider = (
            app.state.payment_service._payment_repository,
            app.state.payment_service._checkout_provider,
        )
        update, create = repository.update, provider.create

        async def write(payment: Payment) -> Payment:
            label = attempt()
            if payment.version == 0:
                await self.gates.pause(
                    label, "write", proposed=PaymentMapper.to_document(payment), collections=self.payments.snapshot()
                )
            try:
                saved = await update(payment)
            except PaymentConflictError:
                self.gates.record(
                    label,
                    "rejected-write",
                    exception="PaymentConflictError",
                    expectedVersion=payment.version,
                    proposed=PaymentMapper.to_document(payment),
                    collections=self.payments.snapshot(),
                )
                raise
            self.gates.record(label, "committed-write", saved=PaymentMapper.to_document(saved))
            return saved

        async def provider_create(request: CheckoutRequest) -> Any:
            await self.gates.pause(
                attempt(),
                "provider",
                paymentId=str(request.payment_id),
                attemptId=str(request.attempt_id),
                collections=self.payments.snapshot(),
            )
            return await create(request)

        with monkeypatch.context() as patch:
            patch.setattr(repository, "update", write)
            patch.setattr(provider, "create", provider_create)
            self.paired_http(
                lambda label: self.context.client.post(
                    f"/payments/{self.context.orders.order_id}/checkout", attempt=label
                ),
                provider_gate=True,
            )
        self.context.last_operation = "POST /payments/{order_id}/checkout x2"
        self.finish()

    def repository(self) -> None:
        assert self.mode.startswith("repository-")
        self.start()

        async def run() -> None:
            database = MongoDatabase(self.context.settings)
            repository = MongoPaymentRepository(database)
            tasks: dict[str, asyncio.Task[None]] = {}

            async def change(label: str) -> None:
                with attempt_scope(label):
                    payment = await repository.get_by_order_id(self.context.orders.order_id)
                    assert payment is not None and payment.version == 0
                    if (label == self.winner) == (self.mode == "repository-pending"):
                        payment.mark_as_pending("cs_coordinated")
                    else:
                        payment.cancel()
                    await self.gates.pause(
                        label,
                        "write",
                        proposed=PaymentMapper.to_document(payment),
                        collections=self.payments.snapshot(),
                    )
                    try:
                        saved = await repository.update(payment)
                    except PaymentConflictError as error:
                        self.results[label] = {
                            "exception": type(error).__name__,
                            "expectedVersion": error.expected_version,
                        }
                        self.gates.record(label, "rejected-write", **self.results[label])
                    else:
                        self.results[label] = {"saved": PaymentMapper.to_document(saved)}
                        self.gates.record(label, "committed-write", **self.results[label])

            try:
                tasks = {label: asyncio.create_task(change(label)) for label in ("first", "second")}
                await self.gates.wait_async(("first", "second"), "write")
                self.gates.release(self.winner, "write")
                await asyncio.wait_for(asyncio.shield(tasks[self.winner]), 30)
                self.winning = self.payments.snapshot()
                self.gates.release(self.loser, "write")
                await asyncio.gather(*tasks.values())
            finally:
                self.gates.open_all()
                await asyncio.gather(*tasks.values(), return_exceptions=True)
                await database.close()

        with self.context.evidence.action(
            "Run two stale repository commands", {"mode": self.mode, "winner": self.winner}
        ) as output:
            asyncio.run(run())
            output["results"] = lossless(self.results)
        self.context.send("GET", f"/payments/order/{self.context.orders.order_id}")
        self.finish()

    def webhook(self, monkeypatch: pytest.MonkeyPatch, *, existing: bool = False) -> None:
        assert self.mode.startswith("webhook-")
        self.start()
        app = cast(FastAPI, self.context.client.app)
        repository = app.state.webhook_service._webhooks
        original = repository.complete
        stored = self.payments.target(self.before)
        assert stored is not None
        for label in ("first", "second"):
            if existing:
                body = self.context.webhook_payload
            else:
                payload = payload_for(
                    PaymentMapper.to_domain(cast(PaymentDocument, stored)),
                    event_id="evt_coordinated" if self.mode == "webhook-same" else f"evt_coordinated_{label}",
                )
                expires = (self.mode == "webhook-expiry-first" and label == self.winner) or (
                    self.mode == "webhook-success-first" and label == self.loser
                )
                if expires:
                    payload["type"] = "checkout.session.expired"
                    payload["data"]["object"].update(payment_status="unpaid", payment_intent=None)
                body = encode(payload)
            self.payloads[label] = body
        if self.mode == "webhook-same":
            self.payloads["second"] = self.payloads["first"]

        async def complete(
            receipt: WebhookReceipt, payment: Payment | None, state: WebhookState, reason: str, *, changed: bool
        ) -> WebhookReceipt:
            label = attempt()
            await self.gates.pause(
                label,
                "write",
                receiptId=receipt.event.event_id,
                state=state.value,
                reason=reason,
                changed=changed,
                proposed=PaymentMapper.to_document(payment) if payment else None,
            )
            try:
                result = await original(receipt, payment, state, reason, changed=changed)
            except PaymentConflictError:
                self.gates.record(
                    label,
                    "rejected-write",
                    exception="PaymentConflictError",
                    expectedVersion=payment.version if payment else None,
                )
                raise
            self.gates.record(
                label,
                "completed-receipt",
                receiptId=result.event.event_id,
                state=result.state.value,
                reason=result.reason,
            )
            return result

        def send(label: str) -> Response:
            body = self.payloads[label]
            return self.context.client.post(
                "/payments/webhooks/stripe",
                content=body,
                headers={"content-type": "application/json", "stripe-signature": signature(body)},
                attempt=label,
            )

        with monkeypatch.context() as patch:
            patch.setattr(repository, "complete", complete)
            self.paired_http(send)
        self.context.last_operation = "POST /payments/webhooks/stripe x2"
        self.finish()

    def payment_responses(self, values: dict[str, str]) -> None:
        stored = self.payments.target(self.after)
        assert stored is not None and self.window is not None
        for response in self.context.responses:
            assert response.status_code < 400 and response.request.headers.get("x-bdd-attempt") in (
                {"first", "second"} if len(self.context.responses) == 2 else {None}
            )
            full_payment(
                response.json(),
                stored,
                values,
                creation_window=self.window if response.status_code == 201 else None,
                update_window=self.window if self.mode == "pay-retry" else None,
            )
        self.context.evidence.observation(
            "Complete coordinated payment responses",
            {
                "expected": values,
                "stored": lossless(stored),
                "responses": [r.json() for r in self.context.responses],
                "exchangeIds": [r.extensions["payments.bdd.exchangeId"] for r in self.context.responses],
            },
        )

    def checkout_responses(self, values: dict[str, str], form: dict[str, str]) -> None:
        stored = self.payments.target(self.after)
        assert stored is not None and self.window is not None
        provider = next(v for v in self.context.stripe.sessions.values() if v["id"] == stored["provider_session_id"])
        for response in self.context.responses:
            assert response.status_code == 200 and response.request.headers["x-bdd-attempt"] in {"first", "second"}
            checkout_response(
                response.json(), stored, provider, values, window=self.window, created=False, mutated=True
            )
        calls = self.context.stripe.calls[self.calls[1] :]
        assert len(calls) == 2
        forms = [provider_request(call, stored, form) for call in calls]
        assert forms[0] == forms[1]
        self.context.evidence.observation(
            "Complete coordinated checkout responses",
            {
                "expected": values,
                "formExpected": form,
                "stored": lossless(stored),
                "provider": provider,
                "forms": forms,
                "responses": [r.json() for r in self.context.responses],
                "exchangeIds": [r.extensions["payments.bdd.exchangeId"] for r in self.context.responses],
            },
        )

    def effects(self, values: dict[str, str]) -> None:
        assert values.keys() == {
            "Status",
            "Version",
            "NewArchives",
            "NewReceipts",
            "OrdersCalls",
            "StripeCalls",
            "Conflicts",
            "SessionsAdded",
        }
        assert (
            self.after == self.winning
            if self.mode
            in {"pay-create", "pay-retry", "checkout", "repository-pending", "repository-canceled", "webhook-same"}
            else True
        )
        assert self.payments.snapshot() == self.after and self.window is not None
        stored = self.payments.target(self.after)
        assert stored is not None and stored.keys() == CURRENT_FIELDS
        assert stored["status"] == values["Status"] and stored["version"] == int(values["Version"])
        unchanged_except_target(self.before, self.after, self.context.orders.order_id)
        added = [
            d
            for d in self.after["payment_history"]
            if d["_id"] not in {p["_id"] for p in self.before["payment_history"]}
        ]
        assert len(added) == int(values["NewArchives"])
        assert len(self.after["stripe_webhooks"]) == len(self.before["stripe_webhooks"]) + int(values["NewReceipts"])
        for previous in self.before["stripe_webhooks"]:
            assert previous in self.after["stripe_webhooks"]
        assert len(self.context.orders.http_calls) - self.calls[0] == int(values["OrdersCalls"])
        assert len(self.context.stripe.calls) - self.calls[1] == int(values["StripeCalls"])
        assert len(self.context.stripe.sessions) - len(self.sessions) == int(values["SessionsAdded"])
        assert all(self.context.stripe.sessions[k] == v for k, v in self.sessions.items())
        conflicts = [w for w in self.gates.witnesses if w["point"] == "rejected-write"]
        assert len(conflicts) == int(values["Conflicts"])
        proposals = [w["proposed"] for w in self.gates.witnesses if w["point"] == "write"]
        assert len(proposals) == 2
        if not self.mode.startswith("webhook-"):
            assert_schedule(
                self.mode, self.winner, self.gates.witnesses, self.before, self.after, self.context.orders.order_id
            )
        if self.mode == "pay-create":
            assert len({p["_id"]["$binary"]["base64"] for p in proposals}) == 2
            assert stored["version"] == 0 and stored["updated_at"] is None
            reset_fields(stored)
            assert self.after["payment_history"] == self.before["payment_history"]
            assert self.after["payments"] == sorted([*self.before["payments"], stored], key=lambda d: str(d["_id"]))
        elif self.mode == "checkout":
            checkout_delta(self.before, self.after, self.context.orders.order_id, self.window)
            attempts = [p["checkout_attempt_id"] for p in proposals]
            assert attempts[0] != attempts[1]
            assert {w["attemptId"] for w in self.gates.witnesses if w["point"] == "provider"} == {
                str(stored["checkout_attempt_id"])
            }
        elif self.mode == "pay-retry" or self.mode.startswith("repository-"):
            transition_delta(self.before, self.after, self.context.orders.order_id, self.window)
            if self.mode == "pay-retry":
                reset_fields(stored)
            else:
                assert self.results[self.loser] == {"exception": "PaymentConflictError", "expectedVersion": 0}
        self.context.evidence.observation(
            "Complete coordinated state effects",
            {
                "expected": values,
                "before": lossless(self.before),
                "winning": lossless(self.winning),
                "after": lossless(self.after),
                "newArchives": lossless(added),
                "witnesses": self.gates.witnesses,
            },
        )

    def receipts(self, first: dict[str, str], second: dict[str, str]) -> None:
        assert self.mode.startswith("webhook-") and self.window is not None
        prior = self.payments.target(self.before)
        current = self.payments.target(self.after)
        assert prior is not None and current is not None
        intermediate = self.payments.target(self.winning)
        assert intermediate is not None
        expected = {
            **prior,
            "status": "succeeded",
            "version": 4 if self.mode == "webhook-expiry-first" else 3,
            "provider_payment_id": "pi_fixture",
            "failure_code": None,
            "updated_at": current["updated_at"],
        }
        assert current == expected
        previous = prior
        added = sorted(
            [
                d
                for d in self.after["payment_history"]
                if d["_id"] not in {p["_id"] for p in self.before["payment_history"]}
            ],
            key=lambda d: d["version"],
        )
        for index, archive in enumerate(added):
            archived_snapshot(previous, archive, self.window)
            previous = intermediate if index == 0 else current
        for label, authored in zip(("first", "second"), (first, second), strict=True):
            body = self.payloads[label]
            payload = json.loads(body)
            document = next(d for d in self.after["stripe_webhooks"] if d["_id"] == payload["id"])
            receipt_matches(document, authored, payload, body, self.window, None)
        self.context.evidence.observation(
            "Complete coordinated receipts",
            {
                "expected": {"first": first, "second": second},
                "payloads": {label: json.loads(body) for label, body in self.payloads.items()},
                "bodyDigests": {label: hashlib.sha256(body).hexdigest() for label, body in self.payloads.items()},
                "before": lossless(self.before),
                "winning": lossless(self.winning),
                "after": lossless(self.after),
            },
        )

    def supporting(self) -> None:
        assert self.window is not None
        before = self.payments.snapshot()
        calls = len(self.context.orders.http_calls), len(self.context.stripe.calls)
        response = self.context.client.get(f"/payments/order/{self.context.orders.order_id}")
        assert response.status_code == 200
        stored = self.payments.target(before)
        assert stored is not None
        values = {
            k: (
                "{stored.id}"
                if k == "id"
                else "{stored." + k + "}"
                if k.endswith("_at") and stored[k] is not None
                else json.dumps(str(stored[k]) if k == "order_id" else stored[k])
            )
            for k in response.json()
        }
        full_payment(response.json(), stored, values)
        ids = [response.extensions["payments.bdd.exchangeId"]]
        if self.mode.startswith("webhook-"):
            for body in dict.fromkeys(self.payloads.values()):
                repeated = self.context.client.post(
                    "/payments/webhooks/stripe",
                    content=body,
                    headers={"content-type": "application/json", "stripe-signature": signature(body)},
                )
                assert repeated.status_code == 200 and repeated.json() == {"received": True}
                ids.append(repeated.extensions["payments.bdd.exchangeId"])
        assert self.payments.snapshot() == before == self.after
        assert calls == (len(self.context.orders.http_calls), len(self.context.stripe.calls))
        self.context.evidence.observation(
            "Coordinated supporting reads and repeats",
            {"collections": lossless(before), "body": response.json(), "exchangeIds": ids, "externalCalls": calls},
        )
