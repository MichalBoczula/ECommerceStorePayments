"""Actual CLI limits, deterministic batches and cancelled real worker recovery."""

from __future__ import annotations

import asyncio
import importlib
import io
import json
import sys
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, MockTransport, Request, Response
from pymongo.errors import InvalidOperation

from ecommerce_store_payments.application.payments.fulfillment_service import FulfillmentService
from ecommerce_store_payments.application.payments.webhook import VerifiedWebhook
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.webhook_repository import (
    MongoWebhookRepository,
)
from tests.acceptance.evidence import REQUEST_ATTEMPT, attempt_scope
from tests.acceptance.fulfillment_boundary import FulfillmentBoundary
from tests.acceptance.fulfillment_checks import FulfillmentChecks
from tests.acceptance.payment_checks import Snapshot, lossless
from tests.acceptance.retry_checks import milliseconds
from tests.acceptance.technical_checks import CLIENT, MAIN
from tests.webhook_fixtures import encode, payload_for, signature

if TYPE_CHECKING:
    from tests.acceptance.technical_scenarios import TechnicalChecks

SECOND = UUID("88888888-8888-4888-8888-888888888888")
SECOND_CLIENT = UUID("99999999-9999-4999-8999-999999999999")


class TechnicalCommands:
    def __init__(self, checks: TechnicalChecks) -> None:
        self.checks, self.context, self.payments = checks, checks.context, checks.payments
        self.boundaries: dict[UUID, FulfillmentBoundary] = {}
        self.events: list[dict[str, Any]] = []
        self.close_proofs: list[dict[str, Any]] = []
        self.clients: list[AsyncClient] = []
        self.http: list[dict[str, Any]] = []
        self.clock = milliseconds(datetime.now(UTC))
        self.pause = ""
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.failure_id: str | None = None
        self.paused = False
        self.prepared: dict[str, Any] = {}
        self.counts: list[int] = []
        self.payloads: dict[str, bytes] = {}

    def prepare(self) -> None:
        fulfillment = FulfillmentChecks(self.payments)
        fulfillment.settle_unrelated()
        mode, target = self.checks.inputs["Mode"], self.checks.inputs["Target"]
        if mode == "cancel-worker":
            fulfillment.prepare({"Mode": "ok", "PriorRetries": "0", "ReceiptFixture": "none"})
            assert fulfillment.boundary is not None
            self.boundaries[MAIN] = fulfillment.boundary
            return
        assert mode == "batch"
        from tests.acceptance.conftest import OrdersBoundary

        orders = self.context.orders
        for index, (oid, cid, amount) in enumerate([(MAIN, CLIENT, "12.99"), (SECOND, SECOND_CLIENT, "23.41")]):
            orders.order_id, orders.client_id, orders.amount, orders.currency, orders.status = (
                oid,
                cid,
                Decimal(amount),
                "PLN",
                "Created",
            )
            response = self.context.client.post(f"/payments/{oid}/checkout")
            assert response.status_code == 200
            document = self.context.payments.find_one({"order_id": oid})
            assert document is not None
            event_id = "evt_technical_first" if index == 0 else "evt_technical_second"
            body = encode(payload_for(PaymentMapper.to_domain(document), event_id=event_id))
            self.payloads[event_id] = body
            if target == "fulfill":
                response = self.context.client.post(
                    "/payments/webhooks/stripe",
                    content=body,
                    headers={"content-type": "application/json", "stripe-signature": signature(body)},
                )
                assert response.status_code == 200 and response.json() == {"received": True}
            else:
                app = cast(FastAPI, self.context.client.app)
                event = app.state.webhook_service._verifier.verify(body, signature(body))

                async def receive(event: VerifiedWebhook = event) -> None:
                    database = MongoDatabase(self.context.settings)
                    try:
                        await MongoWebhookRepository(database).receive(event)
                    finally:
                        await database.close()

                with self.context.evidence.action(
                    "Durably receive actual SDK-verified batch event",
                    {"eventId": event_id, "bodySha256": event.payload_digest},
                ) as output:
                    asyncio.run(receive())
                    output["receipt"] = lossless(self.context.webhooks.find_one({"_id": event_id}))
            child = OrdersBoundary(order_id=oid, client_id=cid, amount=Decimal(amount), currency="PLN")
            self.boundaries[oid] = FulfillmentBoundary(child, "ok")
        orders.order_id, orders.client_id, orders.amount, orders.currency, orders.status = (
            MAIN,
            CLIENT,
            Decimal("12.99"),
            "PLN",
            "Created",
        )

        def dispatch(request: Request) -> Response:
            oid = next(oid for oid in self.boundaries if str(oid) in request.url.path)
            return self.boundaries[oid].handle(request)

        orders.fulfillment_handler = dispatch
        first = self.context.webhooks.find_one({"_id": "evt_technical_first"})
        second = self.context.webhooks.find_one({"_id": "evt_technical_second"})
        assert first is not None and second is not None
        before = self.payments.snapshot()
        received = min(first["received_at"], second["received_at"]) - timedelta(milliseconds=1)
        with self.context.evidence.action(
            "Set explicit oldest-event scheduling fixture",
            {"eventId": "evt_technical_first", "receivedAt": received.isoformat()},
        ) as output:
            self.context.webhooks.update_one({"_id": "evt_technical_first"}, {"$set": {"received_at": received}})
            after = self.payments.snapshot()
            output.update(before=lossless(before), after=lossless(after))
        assert (
            next(d for d in after["stripe_webhooks"] if d["_id"] == "evt_technical_first")["received_at"]
            < second["received_at"]
        )

    def resources(self) -> dict[str, Any]:
        created = [e for e in self.events if e["event"] == "database-created"]
        assert len(created) == len(self.close_proofs)
        assert all(c.is_closed for c in self.clients)
        return {
            "events": self.events,
            "mongoCloseProofs": self.close_proofs,
            "ordersClientsClosed": [c.is_closed for c in self.clients],
        }

    def install(self, module: Any, patch: pytest.MonkeyPatch) -> None:
        original_database = MongoDatabase

        def database_factory(settings: Any) -> MongoDatabase:
            database = original_database(settings)
            label = REQUEST_ATTEMPT.get()
            self.events.append(
                {"event": "database-created", "scope": label, "database": settings.mongodb_database_name}
            )
            close = database.close

            async def closed() -> None:
                await close()
                try:
                    await database.client.admin.command("ping")
                except InvalidOperation:
                    self.close_proofs.append(
                        {"scope": label, "closedClientRejectsPing": True, "exceptionType": "InvalidOperation"}
                    )
                else:
                    raise AssertionError("Closed command Mongo client accepted another ping")
                self.events.append({"event": "database-closed", "scope": label})

            patch.setattr(database, "close", closed)
            return database

        patch.setattr(module, "MongoDatabase", database_factory)
        if hasattr(module, "FulfillmentService"):

            def service(work: Any, payments: Any, orders: Any, invoices: Any) -> FulfillmentService:
                return FulfillmentService(work, payments, orders, invoices, lambda: self.clock)

            patch.setattr(module, "FulfillmentService", service)

            async def handler(request: Request) -> Response:
                label = REQUEST_ATTEMPT.get()
                exchange = self.context.evidence.begin(
                    request.method,
                    str(request.url),
                    request.headers,
                    request.read(),
                    target="invoices" if request.url.path.startswith("/invoices/") else "orders",
                    role="technical-command-boundary",
                    controlled=True,
                )
                try:
                    oid = next(oid for oid in self.boundaries if str(oid) in request.url.path)
                    boundary = self.boundaries[oid]
                    response = boundary.handle(request)
                    matches = (
                        self.pause == "order" and request.method == "GET" and request.url.path == f"/orders/{MAIN}"
                    ) or (self.pause == "paid" and request.method == "PATCH")
                    if matches and not self.paused:
                        self.paused = True
                        self.prepared = {
                            "scope": label,
                            "stage": self.pause,
                            "preparedStatus": response.status_code,
                            "delivered": False,
                            "upstream": boundary.snapshot(),
                        }
                        self.entered.set()
                        await asyncio.wait_for(self.release.wait(), 15)
                    self.context.evidence.response(exchange, response.status_code, response.headers, response.read())
                    self.http.append(
                        {
                            "scope": label,
                            "method": request.method,
                            "path": request.url.path,
                            "result": response.status_code,
                        }
                    )
                    return response
                except BaseException as error:
                    self.context.evidence.failure(exchange, error)
                    self.failure_id = json.loads(exchange.metadata)["exchangeId"]
                    self.http.append(
                        {
                            "scope": label,
                            "method": request.method,
                            "path": request.url.path,
                            "result": type(error).__name__,
                        }
                    )
                    raise

            def client_factory(*, base_url: str, timeout: float, trust_env: bool) -> AsyncClient:
                client = AsyncClient(
                    base_url=base_url, timeout=timeout, trust_env=trust_env, transport=MockTransport(handler)
                )
                self.clients.append(client)
                return client

            patch.setattr(module, "AsyncClient", client_factory)

    def run(self, monkeypatch: pytest.MonkeyPatch) -> None:
        if self.checks.inputs["Mode"] == "limits":
            self.limits(monkeypatch)
        elif self.checks.inputs["Mode"] == "cancel-worker":
            self.cancel(monkeypatch)
        else:
            self.batch(monkeypatch)

    def limits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        target, limit = self.checks.inputs["Target"], int(self.checks.inputs["Value"])
        assert target in {"fulfill", "replay"} and limit in {0, 1001}
        module = importlib.import_module(
            "ecommerce_store_payments.infrastructure.persistence.mongodb."
            + ("fulfill_payments" if target == "fulfill" else "replay_webhooks")
        )
        allocations: list[str] = []

        def forbidden(*_args: Any, **_kwargs: Any) -> Any:
            allocations.append("forbidden")
            raise AssertionError("Invalid command allocated a client/settings instance")

        stderr = io.StringIO()
        with monkeypatch.context() as patch:
            patch.setattr(module, "MongoDatabase", forbidden)
            patch.setattr(module, "Settings", forbidden)
            patch.setattr(sys, "argv", [target + "-payments", "--limit", str(limit)])
            with redirect_stderr(stderr), pytest.raises(SystemExit) as exit_info:
                module.main()
            assert exit_info.value.code == 2 and "--limit must be between 1 and 1000" in stderr.getvalue()
            if target == "fulfill":
                with pytest.raises(ValueError, match="between 1 and 1000"):
                    asyncio.run(module.run(self.context.settings, limit))
        assert not allocations
        self.checks.result = "rejected"
        self.checks.exception = "ValueError" if target == "fulfill" else "SystemExit"
        self.checks.details = {
            "target": target,
            "limit": limit,
            "cliExitCode": exit_info.value.code,
            "stderr": stderr.getvalue(),
            "allocations": allocations,
            "directFulfillGuardChecked": target == "fulfill",
            "replayLibraryInvoked": False,
        }

    def cli(self, module: Any, limit: int, patch: pytest.MonkeyPatch, label: str) -> dict[str, Any]:
        output = io.StringIO()
        patch.setattr(sys, "argv", ["technical-command", "--limit", str(limit)])
        before = self.payments.snapshot()
        start = len(self.counts)
        with attempt_scope(label), redirect_stdout(output):
            module.main()
        assert len(self.counts) == start + 1
        count = self.counts[-1]
        expected = f"Processed {count} " + (
            "fulfillment records.\n" if self.checks.inputs["Target"] == "fulfill" else "pending webhook receipts.\n"
        )
        assert output.getvalue() == expected
        return {
            "scope": label,
            "limit": limit,
            "processed": count,
            "stdout": output.getvalue(),
            "before": lossless(before),
            "after": lossless(self.payments.snapshot()),
        }

    def batch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        target, limit = self.checks.inputs["Target"], int(self.checks.inputs["Value"])
        assert limit in {1, 1000}
        module = importlib.import_module(
            "ecommerce_store_payments.infrastructure.persistence.mongodb."
            + ("fulfill_payments" if target == "fulfill" else "replay_webhooks")
        )
        settings = self.context.settings.model_copy(
            update={"stripe_enabled": False, "stripe_secret_key": None, "stripe_webhook_secret": None}
        )
        original = module.run if target == "fulfill" else module.replay

        async def observed(*args: Any, **kwargs: Any) -> int:
            result = await original(*args, **kwargs)
            assert type(result) is int
            self.counts.append(result)
            return result

        def no_verify(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError("Stored verified work required another signature/credential")

        self.clock = milliseconds(datetime.now(UTC))
        with monkeypatch.context() as patch:
            self.install(module, patch)
            patch.setattr(module, "Settings", lambda: settings)
            patch.setattr(module, "run" if target == "fulfill" else "replay", observed)
            if target == "replay":
                patch.setattr(module.StripeWebhookVerifier, "verify", no_verify)
            primary = self.cli(module, limit, patch, "batch-primary")
            expected = 1 if limit == 1 else 2
            assert primary["processed"] == expected
            after_first = self.payments.snapshot()
            self.verify_batch(
                self.checks.before, after_first, {"evt_technical_first"} if limit == 1 else set(self.payloads), target
            )
            remaining = self.cli(module, 1000, patch, "batch-remaining")
            assert remaining["processed"] == 2 - expected
            after_remaining = self.payments.snapshot()
            self.verify_batch(self.checks.before, after_remaining, set(self.payloads), target)
            repeated = self.cli(module, 1000, patch, "batch-repeat")
            assert repeated["processed"] == 0 and self.payments.snapshot() == after_remaining
        if target == "replay":
            assert not self.http and not self.clients
        self.checks.result = "processed"
        self.checks.details = {
            "target": target,
            "limit": limit,
            "clock": self.clock.isoformat(),
            "primary": primary,
            "remaining": remaining,
            "repeated": repeated,
            "payloads": {k: json.loads(v) for k, v in self.payloads.items()},
            "upstream": {str(k): v.snapshot() for k, v in self.boundaries.items()},
            "http": self.http,
            "resources": self.resources(),
            "providerCredentials": False,
        }

    def verify_batch(self, before: Snapshot, after: Snapshot, processed: set[str], target: str) -> None:
        before_receipts = {d["_id"]: d for d in before["stripe_webhooks"]}
        for document in after["stripe_webhooks"]:
            event = document["_id"]
            prior = before_receipts[event]
            if event not in processed:
                assert document == prior
                continue
            if target == "fulfill":
                boundary = self.boundaries[document["order_id"]]
                assert boundary.invoice is not None
                expected = {
                    **prior,
                    "fulfillment_status": "completed",
                    "fulfillment_attempts": 1,
                    "fulfillment_lease_id": None,
                    "fulfillment_lease_until": None,
                    "fulfillment_next_attempt": None,
                    "fulfillment_error": None,
                    "fulfillment_order_paid": True,
                    "fulfillment_client_id": boundary.orders.client_id,
                    "fulfillment_invoice_id": UUID(boundary.invoice["id"]),
                    "fulfillment_client_data_version_id": UUID(boundary.invoice["clietDataVersionId"]),
                    "fulfillment_completed_at": self.clock,
                }
                assert document == expected and boundary.logical_paid == boundary.logical_invoices == 1
            else:
                assert (
                    document["state"] == "applied"
                    and document["reason"] == "payment_succeeded"
                    and document["fulfillment_status"] == "pending"
                )
                assert {
                    k: v
                    for k, v in document.items()
                    if k not in {"state", "reason", "completed_at", "fulfillment_status"}
                } == {
                    k: v for k, v in prior.items() if k not in {"state", "reason", "completed_at", "fulfillment_status"}
                }
                assert document["completed_at"] is not None
        if target == "fulfill":
            assert after["payments"] == before["payments"] and after["payment_history"] == before["payment_history"]
        else:
            from tests.acceptance.retry_checks import archived_snapshot

            processed_orders = {d["order_id"] for d in after["stripe_webhooks"] if d["_id"] in processed}
            for prior in before["payments"]:
                current = next(d for d in after["payments"] if d["_id"] == prior["_id"])
                if prior["order_id"] not in processed_orders:
                    assert current == prior
                    continue
                assert current == {
                    **prior,
                    "status": "succeeded",
                    "version": 3,
                    "provider_payment_id": "pi_fixture",
                    "failure_code": None,
                    "updated_at": current["updated_at"],
                }
                added = next(d for d in after["payment_history"] if d["_id"] == f"{prior['_id']}:2")
                archived_snapshot(prior, added, (prior["created_at"], datetime.now(UTC)))
            old_ids = {d["_id"] for d in before["payment_history"]}
            assert [d for d in after["payment_history"] if d["_id"] in old_ids] == before["payment_history"]
            assert len(after["payment_history"]) == len(before["payment_history"]) + len(processed)

    def cancel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = importlib.import_module("ecommerce_store_payments.infrastructure.persistence.mongodb.fulfill_payments")
        settings = self.context.settings.model_copy(
            update={"stripe_enabled": False, "stripe_secret_key": None, "stripe_webhook_secret": None}
        )
        self.pause = self.checks.inputs["Value"]
        assert self.pause in {"order", "paid"}
        self.clock = milliseconds(datetime.now(UTC))
        original_clock = self.clock
        before = self.payments.snapshot()
        main = next(d for d in before["stripe_webhooks"] if d["_id"] == "evt_fulfillment")

        async def cancelled() -> None:
            with attempt_scope("cancelled-worker"):
                task = asyncio.create_task(module.run(settings, 1))
                try:
                    await asyncio.wait_for(self.entered.wait(), 10)
                    task.cancel()
                    with pytest.raises(asyncio.CancelledError):
                        await task
                finally:
                    if not task.done():
                        task.cancel()
                    await asyncio.gather(task, return_exceptions=True)

        with monkeypatch.context() as patch:
            self.install(module, patch)
            asyncio.run(cancelled())
            after_cancel = self.payments.snapshot()
            document = next(d for d in after_cancel["stripe_webhooks"] if d["_id"] == "evt_fulfillment")
            assert document == {
                **main,
                "fulfillment_status": "processing",
                "fulfillment_attempts": 1,
                "fulfillment_lease_id": document["fulfillment_lease_id"],
                "fulfillment_lease_until": original_clock + timedelta(seconds=300),
            }
            assert isinstance(document["fulfillment_lease_id"], UUID) and document["fulfillment_lease_id"].int
            assert (
                after_cancel["payments"] == before["payments"]
                and after_cancel["payment_history"] == before["payment_history"]
            )
            boundary = self.boundaries[MAIN]
            upstream_cancel = deepcopy(boundary.snapshot())
            assert boundary.logical_paid == (1 if self.pause == "paid" else 0) and boundary.logical_invoices == 0
            self.pause = ""
            self.clock = original_clock + timedelta(seconds=300)

            async def recover() -> int:
                with attempt_scope("recovery-worker"):
                    return await module.run(settings, 1000)

            assert asyncio.run(recover()) == 1
        after = self.payments.snapshot()
        winner = next(d for d in after["stripe_webhooks"] if d["_id"] == "evt_fulfillment")
        assert boundary.invoice is not None
        expected = {
            **main,
            "fulfillment_status": "completed",
            "fulfillment_attempts": 2,
            "fulfillment_lease_id": None,
            "fulfillment_lease_until": None,
            "fulfillment_next_attempt": None,
            "fulfillment_error": None,
            "fulfillment_order_paid": True,
            "fulfillment_client_id": CLIENT,
            "fulfillment_invoice_id": UUID(boundary.invoice["id"]),
            "fulfillment_client_data_version_id": UUID(boundary.invoice["clietDataVersionId"]),
            "fulfillment_completed_at": self.clock,
        }
        assert winner == expected and boundary.logical_paid == boundary.logical_invoices == 1
        assert after["payments"] == before["payments"] and after["payment_history"] == before["payment_history"]
        assert [d for d in before["stripe_webhooks"] if d["_id"] != "evt_fulfillment"] == [
            d for d in after["stripe_webhooks"] if d["_id"] != "evt_fulfillment"
        ]
        assert self.failure_id is not None
        self.checks.failure_id = self.failure_id
        self.checks.result = "cancelled"
        self.checks.exception = "CancelledError"
        self.checks.details = {
            "before": lossless(before),
            "afterCancel": lossless(after_cancel),
            "afterRecovery": lossless(after),
            "cancelClock": original_clock.isoformat(),
            "recoveryClock": self.clock.isoformat(),
            "preparedUpstreamResponse": self.prepared,
            "upstreamAfterCancel": upstream_cancel,
            "upstreamAfterRecovery": boundary.snapshot(),
            "http": self.http,
            "resources": self.resources(),
            "providerCredentials": False,
        }
