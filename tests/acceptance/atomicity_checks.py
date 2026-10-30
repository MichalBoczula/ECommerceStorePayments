"""Witness actual session-visible writes and actual abort before a successful retry."""

from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from fastapi import FastAPI
from pymongo.asynchronous.client_session import AsyncClientSession
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import OperationFailure

from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.webhook_repository import (
    MongoWebhookRepository,
)
from tests.acceptance.checkout_checks import checkout_delta, checkout_response, provider_request
from tests.acceptance.checkout_recovery_checks import safe_problem
from tests.acceptance.payment_checks import PaymentChecks, Snapshot, full_payment, lossless
from tests.acceptance.retry_checks import CURRENT_FIELDS, archived_snapshot, milliseconds, transition_delta
from tests.acceptance.webhook_lifecycle_checks import receipt_matches
from tests.webhook_fixtures import encode, payload_for, signature


def assert_staged_write(
    before: Snapshot,
    inside: Snapshot,
    outside: Snapshot,
    order_id: Any,
    command: str,
    point: str,
    window: tuple[datetime, datetime],
) -> None:
    assert outside == before
    prior = next(d for d in before["payments"] if d["order_id"] == order_id)
    staged = next(d for d in inside["payments"] if d["order_id"] == order_id)
    assert staged.keys() == CURRENT_FIELDS
    stamp = staged["updated_at"]
    assert isinstance(stamp, datetime) and milliseconds(window[0]) <= stamp <= milliseconds(window[1])
    expected = {**prior, "version": prior["version"] + 1, "updated_at": stamp}
    if command == "checkout":
        from uuid import UUID

        assert isinstance(staged["checkout_attempt_id"], UUID) and staged["checkout_attempt_id"].int
        expected.update(
            status="created",
            checkout_attempt_id=staged["checkout_attempt_id"],
            checkout_started_at=stamp,
            checkout_request_version=2,
        )
    else:
        assert command == "webhook"
        expected.update(status="succeeded", provider_payment_id="pi_fixture", failure_code=None)
    assert staged == expected
    assert [d for d in inside["payments"] if d["_id"] != prior["_id"]] == [
        d for d in before["payments"] if d["_id"] != prior["_id"]
    ]
    old_ids = {d["_id"] for d in before["payment_history"]}
    new = [d for d in inside["payment_history"] if d["_id"] not in old_ids]
    assert [d for d in inside["payment_history"] if d["_id"] in old_ids] == before["payment_history"]
    assert len(new) == (0 if point == "payments.replace_one" else 1)
    if new:
        archived_snapshot(prior, new[0], window)
    if point == "stripe_webhooks.replace_one":
        assert command == "webhook"
        original = next(d for d in before["stripe_webhooks"] if d["_id"] == "evt_atomic_rollback")
        receipt = next(d for d in inside["stripe_webhooks"] if d["_id"] == original["_id"])
        stamp2 = receipt["completed_at"]
        assert isinstance(stamp2, datetime) and milliseconds(window[0]) <= stamp2 <= milliseconds(window[1])
        assert receipt == {
            **original,
            "state": "applied",
            "reason": "payment_succeeded",
            "completed_at": stamp2,
            "fulfillment_status": "pending",
        }
        assert [d for d in inside["stripe_webhooks"] if d["_id"] != original["_id"]] == [
            d for d in before["stripe_webhooks"] if d["_id"] != original["_id"]
        ]
    else:
        assert inside["stripe_webhooks"] == before["stripe_webhooks"]


class AtomicityChecks:
    def __init__(self, payments: PaymentChecks) -> None:
        self.payments, self.context = payments, payments.context
        self.command = ""
        self.point = ""
        self.before: Snapshot = {}
        self.after_abort: Snapshot = {}
        self.after_retry: Snapshot = {}
        self.witnesses: list[dict[str, Any]] = []
        self.session: AsyncClientSession | None = None
        self.payload: bytes = b""
        self.recovery: Any = None
        self.recovery_window: tuple[datetime, datetime] | None = None
        self.fault_started = datetime.now(UTC)
        self.calls: tuple[int, int] = (0, 0)
        self.sessions: dict[str, Any] = {}
        self.authored: dict[str, dict[str, str]] = {}

    def configure(self, values: dict[str, str]) -> None:
        assert values.keys() == {"Command", "AfterWrite", "Exception"}
        assert values["Command"] in {"checkout", "webhook"}
        assert values["AfterWrite"] in {
            "payments.replace_one",
            "payment_history.insert_one",
            "stripe_webhooks.replace_one",
        }
        assert values["Exception"] == "OperationFailure"
        self.command, self.point = values["Command"], values["AfterWrite"]
        assert self.command == "webhook" or self.point != "stripe_webhooks.replace_one"
        if self.command == "webhook":
            stored = self.payments.target(self.payments.snapshot())
            assert stored is not None and stored["status"] == "pending"
            self.payload = encode(
                payload_for(PaymentMapper.to_domain(cast(PaymentDocument, stored)), event_id="evt_atomic_rollback")
            )
            app = cast(FastAPI, self.context.client.app)
            event = app.state.webhook_service._verifier.verify(self.payload, signature(self.payload))

            async def receive() -> None:
                database = MongoDatabase(self.context.settings)
                try:
                    await MongoWebhookRepository(database).receive(event)
                finally:
                    await database.close()

            with self.context.evidence.action(
                "Durably receive verified work before the transaction",
                {"eventId": event.event_id, "bodySha256": event.payload_digest},
            ) as output:
                asyncio.run(receive())
                output["collections"] = lossless(self.payments.snapshot())
        self.before = self.payments.snapshot()
        assert all(self.before.values())
        self.calls = len(self.context.orders.http_calls), len(self.context.stripe.calls)
        self.sessions = deepcopy(self.context.stripe.sessions)
        self.context.evidence.observation(
            "Atomic rollback inputs and baseline",
            {"expected": values, "before": lossless(self.before), "bodyUtf8": self.payload.decode()},
        )

    async def witness(self, collection: AsyncCollection[Any], session: AsyncClientSession) -> None:
        assert session.in_transaction and not self.witnesses
        self.session = session
        inside: Snapshot = {}
        for name in ("payments", "payment_history", "stripe_webhooks"):
            inside[name] = sorted(
                [dict(d) async for d in collection.database[name].find({}, session=session)],
                key=lambda d: str(d["_id"]),
            )
        outside = self.payments.snapshot()
        assert outside == self.before
        assert_staged_write(
            self.before,
            inside,
            outside,
            self.context.orders.order_id,
            self.command,
            self.point,
            (self.fault_started, datetime.now(UTC)),
        )
        self.witnesses.append(
            {
                "point": self.point,
                "exception": "OperationFailure",
                "sessionId": lossless(session.session_id),
                "transactionActive": True,
                "sessionVisible": lossless(inside),
                "outsideVisible": lossless(outside),
            }
        )
        raise OperationFailure("private controlled post-write transaction failure")

    def send(self) -> Any:
        if self.command == "checkout":
            return self.context.client.post(f"/payments/{self.context.orders.order_id}/checkout")
        return self.context.client.post(
            "/payments/webhooks/stripe",
            content=self.payload,
            headers={"content-type": "application/json", "stripe-signature": signature(self.payload)},
        )

    def fail_after_write(self, monkeypatch: pytest.MonkeyPatch) -> None:
        replace, insert = AsyncCollection[Any].replace_one, AsyncCollection[Any].insert_one
        database_name = self.context.settings.mongodb_database_name
        prior = self.payments.target(self.before)
        assert prior is not None

        async def replace_one(collection: AsyncCollection[Any], *args: Any, **kwargs: Any) -> Any:
            result = await replace(collection, *args, **kwargs)
            if collection.database.name == database_name and f"{collection.name}.replace_one" == self.point:
                document = args[1]
                if (collection.name == "payments" and document["_id"] == prior["_id"]) or (
                    collection.name == "stripe_webhooks" and document["_id"] == "evt_atomic_rollback"
                ):
                    assert result.matched_count == 1
                    await self.witness(collection, kwargs["session"])
            return result

        async def insert_one(collection: AsyncCollection[Any], *args: Any, **kwargs: Any) -> Any:
            result = await insert(collection, *args, **kwargs)
            if (
                collection.database.name == database_name
                and f"{collection.name}.insert_one" == self.point
                and args[0]["payment_id"] == prior["_id"]
            ):
                assert result.inserted_id == args[0]["_id"]
                await self.witness(collection, kwargs["session"])
            return result

        self.fault_started = datetime.now(UTC)
        with self.context.evidence.action(
            "Fail after an actual transactional write", {"command": self.command, "point": self.point}
        ) as output:
            with monkeypatch.context() as patch:
                patch.setattr(AsyncCollection, "replace_one", replace_one)
                patch.setattr(AsyncCollection, "insert_one", insert_one)
                self.context.responses = [self.send()]
            assert self.session is not None and not self.session.in_transaction and self.session.has_ended
            self.after_abort = self.payments.snapshot()
            output.update(
                witnesses=self.witnesses,
                sessionEnded=self.session.has_ended,
                transactionActive=self.session.in_transaction,
                afterAbort=lossless(self.after_abort),
            )
        self.context.last_operation = (
            "POST /payments/{order_id}/checkout" if self.command == "checkout" else "POST /payments/webhooks/stripe"
        )

    def rollback(self, problem: dict[str, str], effects: dict[str, str]) -> None:
        assert effects.keys() == {
            "WritesReached",
            "TransactionActiveAtFault",
            "SessionEnded",
            "Collections",
            "OrdersCalls",
            "StripeCalls",
            "ProviderSessions",
        }
        assert effects["WritesReached"] == str(
            1 if self.point == "payments.replace_one" else 3 if self.point == "stripe_webhooks.replace_one" else 2
        )
        assert effects["TransactionActiveAtFault"] == effects["SessionEnded"] == "true"
        assert effects["Collections"] == effects["ProviderSessions"] == "unchanged"
        assert self.after_abort == self.before and len(self.witnesses) == 1
        safe_problem(self.context.responses[0], problem)
        assert len(self.context.orders.http_calls) - self.calls[0] == int(effects["OrdersCalls"])
        assert len(self.context.stripe.calls) - self.calls[1] == int(effects["StripeCalls"])
        assert self.context.stripe.sessions == self.sessions
        self.context.evidence.observation(
            "Actual rollback preserves every collection",
            {
                "expected": effects,
                "problemExpected": problem,
                "before": lossless(self.before),
                "afterAbort": lossless(self.after_abort),
                "witnesses": self.witnesses,
                "providerSessions": self.sessions,
                "exchangeId": self.context.responses[0].extensions["payments.bdd.exchangeId"],
            },
        )

    def retry(self) -> None:
        started = datetime.now(UTC)
        self.recovery = self.send()
        self.recovery_window = started, datetime.now(UTC)
        assert self.recovery.status_code == 200
        self.after_retry = self.payments.snapshot()

    def checkout_recovery(self, values: dict[str, str], form: dict[str, str]) -> None:
        assert self.command == "checkout" and self.recovery_window is not None
        stored = self.payments.target(self.after_retry)
        assert stored is not None
        provider = next(p for p in self.context.stripe.sessions.values() if p["id"] == stored["provider_session_id"])
        checkout_response(
            self.recovery.json(), stored, provider, values, window=self.recovery_window, created=False, mutated=True
        )
        checkout_delta(self.before, self.after_retry, self.context.orders.order_id, self.recovery_window)
        new_calls = self.context.stripe.calls[self.calls[1] :]
        assert len(new_calls) == 1 and len(self.context.orders.http_calls) == self.calls[0] + 2
        actual_form = provider_request(new_calls[0], stored, form)
        self.context.evidence.observation(
            "Complete checkout after actual abort",
            {
                "expected": values,
                "formExpected": form,
                "form": actual_form,
                "before": lossless(self.before),
                "after": lossless(self.after_retry),
                "provider": provider,
                "response": self.recovery.json(),
                "exchangeId": self.recovery.extensions["payments.bdd.exchangeId"],
                "window": [v.isoformat() for v in self.recovery_window],
            },
        )

    def webhook_recovery(self, receipt: dict[str, str], payment: dict[str, str]) -> None:
        assert self.command == "webhook" and self.recovery_window is not None
        stored = self.payments.target(self.after_retry)
        assert stored is not None and self.recovery.json() == {"received": True}
        transition_delta(
            {**self.before, "stripe_webhooks": self.after_retry["stripe_webhooks"]},
            self.after_retry,
            self.context.orders.order_id,
            self.recovery_window,
        )
        document = next(d for d in self.after_retry["stripe_webhooks"] if d["_id"] == "evt_atomic_rollback")
        previous = next(d for d in self.before["stripe_webhooks"] if d["_id"] == "evt_atomic_rollback")
        receipt_matches(document, receipt, json.loads(self.payload), self.payload, self.recovery_window, previous)
        assert [d for d in self.after_retry["stripe_webhooks"] if d["_id"] != document["_id"]] == [
            d for d in self.before["stripe_webhooks"] if d["_id"] != document["_id"]
        ]
        read = self.context.client.get(f"/payments/order/{self.context.orders.order_id}")
        assert read.status_code == 200
        resolved = {
            k: json.dumps(stored["provider_session_id"]) if v == "{stored.session_id}" else v
            for k, v in payment.items()
        }
        full_payment(read.json(), stored, resolved)
        assert (len(self.context.orders.http_calls), len(self.context.stripe.calls)) == self.calls
        self.context.evidence.observation(
            "Complete webhook after actual abort",
            {
                "receiptExpected": receipt,
                "paymentExpected": payment,
                "payload": json.loads(self.payload),
                "before": lossless(self.before),
                "after": lossless(self.after_retry),
                "receipt": lossless(document),
                "body": read.json(),
                "exchangeIds": [
                    self.recovery.extensions["payments.bdd.exchangeId"],
                    read.extensions["payments.bdd.exchangeId"],
                ],
                "window": [v.isoformat() for v in self.recovery_window],
            },
        )

    def unchanged_repeat(self) -> None:
        before = self.payments.snapshot()
        calls = len(self.context.orders.http_calls), len(self.context.stripe.calls)
        # Webhook repeats are true no-ops; a Checkout repeat does make its declared provider GET.
        if self.command == "webhook":
            response = self.send()
            assert response.status_code == 200 and response.json() == {"received": True}
        else:
            response = self.context.client.get(f"/payments/order/{self.context.orders.order_id}")
            assert response.status_code == 200
        assert self.payments.snapshot() == before == self.after_retry
        assert calls == (len(self.context.orders.http_calls), len(self.context.stripe.calls))
        self.context.evidence.observation(
            "Post-abort recovery repeat is unchanged",
            {"collections": lossless(before), "exchangeId": response.extensions["payments.bdd.exchangeId"]},
        )
