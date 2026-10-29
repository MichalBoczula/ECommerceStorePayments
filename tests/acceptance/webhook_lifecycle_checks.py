"""Complete normalized receipts, immutable state and real operator replay evidence."""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.application.payments.webhook import WebhookReceipt, WebhookRetryError, WebhookState
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.repositories.exceptions import PaymentConflictError
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.replay_webhooks import replay
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.webhook_repository import (
    MongoWebhookRepository,
)
from tests.acceptance.evidence import EvidenceClient
from tests.acceptance.payment_checks import PaymentChecks, Snapshot, full_payment, lossless
from tests.acceptance.retry_checks import CURRENT_FIELDS, archived_snapshot, milliseconds
from tests.acceptance.webhook_verification_checks import UNKNOWN_RECEIPT_FIELDS
from tests.webhook_fixtures import encode, payload_for, signature

EVENT_INPUTS = {
    "EventId",
    "EventType",
    "AttemptSource",
    "PaymentId",
    "OrderId",
    "AttemptId",
    "SessionId",
    "AmountMinor",
    "PaymentStatus",
    "SessionStatus",
    "PaymentIntent",
    "Encoding",
}
DELTA_FIELDS = {
    "Status",
    "Version",
    "SessionId",
    "ProviderPaymentId",
    "FailureCode",
    "NewArchives",
    "NewReceipts",
    "ExternalCalls",
    "ControlledInterruptions",
}


def receipt_matches(
    receipt: dict[str, Any],
    authored: dict[str, str],
    payload: dict[str, Any],
    body: bytes,
    window: tuple[datetime, datetime],
    previous: dict[str, Any] | None,
) -> None:
    assert receipt.keys() == authored.keys() == UNKNOWN_RECEIPT_FIELDS
    session = payload["data"]["object"]
    substitutions: dict[str, Any] = {
        "{event.id}": payload["id"],
        "{event.type}": payload["type"],
        "{request.sha256}": hashlib.sha256(body).hexdigest(),
        "{event.payment_id}": UUID(session["metadata"]["payment_id"]),
        "{event.order_id}": UUID(session["metadata"]["order_id"]),
        "{event.attempt_id}": UUID(session["metadata"]["attempt_id"]),
        "{event.session_id}": session["id"],
        "{event.provider_payment_id}": session["payment_intent"],
    }
    for key, value in authored.items():
        actual = receipt[key]
        if value == "{request.window}":
            assert key in {"received_at", "completed_at"} and isinstance(actual, datetime)
            assert actual == milliseconds(actual) and milliseconds(window[0]) <= actual <= milliseconds(window[1])
        elif value in {"{before.received_at}", "{before.completed_at}", "{before.payload_digest}"}:
            assert value == "{before." + key + "}" and previous is not None and actual == previous[key]
        else:
            expected = substitutions[value] if value in substitutions else json.loads(value)
            if key == "amount_minor" and expected is not None:
                assert type(expected) is int and isinstance(actual, int) and not isinstance(actual, bool)
            else:
                assert type(actual) is type(expected), key
            assert actual == expected, key
    assert isinstance(receipt["received_at"], datetime)
    assert receipt["received_at"] == milliseconds(receipt["received_at"])
    if receipt["completed_at"] is not None:
        assert receipt["received_at"] <= receipt["completed_at"] == milliseconds(receipt["completed_at"])

    if previous is not None:
        if previous["state"] != "pending":
            assert receipt == previous, "Completed receipts must remain byte-for-byte unchanged"
        else:
            assert {
                k: v for k, v in receipt.items() if k not in {"state", "reason", "completed_at", "fulfillment_status"}
            } == {
                k: v for k, v in previous.items() if k not in {"state", "reason", "completed_at", "fulfillment_status"}
            }


def lifecycle_delta(
    before: Snapshot,
    after: Snapshot,
    order_id: UUID,
    authored: dict[str, str],
    window: tuple[datetime, datetime],
    session_id: str,
) -> None:
    assert authored.keys() == DELTA_FIELDS and authored["ExternalCalls"] == "0"
    previous = next(d for d in before["payments"] if d["order_id"] == order_id)
    current = next(d for d in after["payments"] if d["order_id"] == order_id)
    assert current.keys() == CURRENT_FIELDS
    new_archives = int(authored["NewArchives"])
    assert new_archives in {0, 1}
    expected = {
        **previous,
        "status": authored["Status"],
        "version": int(authored["Version"]),
        "provider_session_id": session_id
        if authored["SessionId"] == "{event.session_id}"
        else previous["provider_session_id"]
        if authored["SessionId"] == "{before.session_id}"
        else json.loads(authored["SessionId"]),
        "provider_payment_id": json.loads(authored["ProviderPaymentId"]),
        "failure_code": json.loads(authored["FailureCode"]),
    }
    if new_archives:
        assert expected["version"] == previous["version"] + 1
        instant = current["updated_at"]
        assert isinstance(instant, datetime) and instant == milliseconds(instant)
        assert milliseconds(window[0]) <= instant <= milliseconds(window[1])
        assert instant >= (previous["updated_at"] or previous["created_at"])
        expected["updated_at"] = instant
        archive_id = f"{previous['_id']}:{previous['version']}"
        added = [d for d in after["payment_history"] if d["_id"] == archive_id]
        assert not any(d["_id"] == archive_id for d in before["payment_history"]) and len(added) == 1
        archived_snapshot(previous, added[0], window)
        assert [d for d in after["payment_history"] if d["_id"] != archive_id] == before["payment_history"]
    else:
        assert expected["version"] == previous["version"]
        assert after["payment_history"] == before["payment_history"]
    assert current == expected, "Every current field, including attempt/version/dates, must match"
    assert [d for d in after["payments"] if d["_id"] != current["_id"]] == [
        d for d in before["payments"] if d["_id"] != previous["_id"]
    ]
    assert len(after["stripe_webhooks"]) == len(before["stripe_webhooks"]) + int(authored["NewReceipts"])


class WebhookLifecycleChecks:
    def __init__(self, payments: PaymentChecks) -> None:
        self.payments, self.context = payments, payments.context
        self.before: Snapshot | None = None
        self.calls: tuple[int, int] | None = None
        self.sessions: dict[str, dict[str, Any]] | None = None
        self.previous_payload: dict[str, Any] | None = None
        self.body: bytes = b""
        self.window: tuple[datetime, datetime] | None = None
        self.event_id: str | None = None
        self.faults: list[dict[str, Any]] = []
        self.prepared_payloads: dict[str, dict[str, Any]] = {}
        self.observation_counts: dict[str, int] = {}

    def observe(self, name: str, value: object) -> None:
        number = self.observation_counts.get(name, 0) + 1
        self.observation_counts[name] = number
        label = name if number == 1 else f"{name} ({number})"
        self.context.evidence.observation(label, value)

    def start(self, values: dict[str, str]) -> None:
        assert values.keys() == {"State"}
        state, context = values["State"], self.context
        assert state in {"pending", "reserved", "failed", "canceled", "succeeded", "retried", "legacy_pending"}
        response = context.client.post(
            f"/payments/{context.orders.order_id}/{'pay' if state == 'reserved' else 'checkout'}"
        )
        assert response.status_code == (201 if state == "reserved" else 200)
        if state == "reserved":
            self._repository_change("reserve")
        stored = context.payments.find_one({"order_id": context.orders.order_id})
        assert stored is not None
        self.previous_payload = payload_for(PaymentMapper.to_domain(stored), event_id="evt_previous_attempt")
        if state in {"failed", "succeeded", "retried"}:
            event = deepcopy(self.previous_payload)
            event["id"] = "evt_lifecycle_setup"
            if state != "succeeded":
                event["type"] = "checkout.session.async_payment_failed"
                event["data"]["object"].update(payment_status="unpaid", payment_intent=None)
            context.webhook_payload = encode(event)
            self.deliver()
            assert context.responses[0].status_code == 200
            if state == "retried":
                assert context.client.post(f"/payments/{context.orders.order_id}/checkout").status_code == 200
                current = context.payments.find_one({"order_id": context.orders.order_id})
                assert current is not None and current["version"] == 6
                assert current.get("checkout_attempt_id") != stored.get("checkout_attempt_id")
        elif state == "canceled":
            self._repository_change("cancel")
        elif state == "legacy_pending":
            with context.evidence.action("Insert historical Pending schema without an attempt", values) as output:
                context.payments.update_one(
                    {"_id": stored["_id"]}, {"$unset": {"checkout_attempt_id": "", "checkout_started_at": ""}}
                )
                historical = context.payments.find_one({"_id": stored["_id"]})
                assert historical is not None and "checkout_attempt_id" not in historical
                PaymentMapper.to_domain(historical)
                output["stored"] = lossless(historical)
        context.webhook_payload = b""
        self.body = b""

    def _repository_change(self, change: str) -> None:
        async def mutate() -> None:
            database = MongoDatabase(self.context.settings)
            try:
                repository = MongoPaymentRepository(database)
                payment = await repository.get_by_order_id(self.context.orders.order_id)
                assert payment is not None
                if change == "reserve":
                    payment.begin_checkout(request_version=2)
                else:
                    assert change == "cancel"
                    payment.cancel()
                await repository.update(payment)
            finally:
                await database.close()

        with self.context.evidence.action("Prepare legal lifecycle repository state", {"change": change}) as output:
            asyncio.run(mutate())
            output["collections"] = lossless(self.payments.snapshot())

    def prepare(self, values: dict[str, str]) -> None:
        assert values.keys() == EVENT_INPUTS
        stored = self.context.payments.find_one({"order_id": self.context.orders.order_id})
        assert stored is not None
        # The previous snapshot also supplies a valid historical attempt for legacy/stale notifications.
        if values["EventId"] in self.prepared_payloads:
            event = deepcopy(self.prepared_payloads[values["EventId"]])
        elif values["AttemptSource"] == "previous":
            assert self.previous_payload is not None
            event = deepcopy(self.previous_payload)
        else:
            assert values["AttemptSource"] == "current"
            event = payload_for(PaymentMapper.to_domain(stored))
        session = event["data"]["object"]
        for key, source in (("payment_id", "PaymentId"), ("order_id", "OrderId"), ("attempt_id", "AttemptId")):
            value = values[source]
            if value != {"payment_id": "{payment.id}", "order_id": "{order.id}", "attempt_id": "{attempt.id}"}[key]:
                session["metadata"][key] = str(UUID(value))
        if values["SessionId"] != "{session.id}":
            session["id"] = json.loads(values["SessionId"])
        session.update(
            client_reference_id=session["metadata"]["payment_id"],
            amount_total=int(values["AmountMinor"]),
            payment_status=values["PaymentStatus"],
            status=values["SessionStatus"],
            payment_intent=json.loads(values["PaymentIntent"]),
        )
        event.update(id=values["EventId"], type=values["EventType"])
        self.prepared_payloads[values["EventId"]] = deepcopy(event)
        body = encode(event)
        assert values["Encoding"] in {"normal", "trailing_space"}
        if values["Encoding"] == "trailing_space":
            body += b" "
        self.context.webhook_payload = body
        self.observe(
            "Webhook lifecycle event inputs",
            {"expected": values, "payload": event, "sha256": hashlib.sha256(body).hexdigest()},
        )

    def remember(self) -> None:
        self.before = self.payments.snapshot()
        self.calls = len(self.context.orders.http_calls), len(self.context.stripe.calls)
        self.sessions = deepcopy(self.context.stripe.sessions)
        self.observe("Webhook lifecycle before", {"collections": lossless(self.before), "externalCalls": self.calls})

    def deliver(self, fresh: bool = False) -> None:
        context = self.context
        self.body = context.webhook_payload
        headers = {"content-type": "application/json", "stripe-signature": signature(self.body)}
        lower = datetime.now(UTC)
        if fresh:
            with TestClient(create_app(context.settings)) as client:
                response = EvidenceClient(client, context.evidence).post(
                    "/payments/webhooks/stripe", content=self.body, headers=headers
                )
        else:
            response = context.client.post("/payments/webhooks/stripe", content=self.body, headers=headers)
        context.responses = [response]
        self.window = context.request_window = lower, datetime.now(UTC)
        context.last_operation = "POST /payments/webhooks/stripe"

    def _capture(self) -> tuple[dict[str, Any], tuple[datetime, datetime], str]:
        # Existing cases send through their original bindings; use the actual prepared request for both paths.
        if self.window is None:
            assert self.context.request_window is not None
            self.window = self.context.request_window
        if not self.body:
            self.body = self.context.responses[0].request.read()
        payload = json.loads(self.body)
        self.event_id = payload["id"]
        return payload, self.window, self.context.responses[0].extensions["payments.bdd.exchangeId"]

    def receipt(self, values: dict[str, str]) -> None:
        payload, window, exchange = self._capture()
        assert self.before is not None
        after = self.payments.snapshot()
        found = [d for d in after["stripe_webhooks"] if d["_id"] == self.event_id]
        assert len(found) == 1
        previous = next((d for d in self.before["stripe_webhooks"] if d["_id"] == self.event_id), None)
        receipt_matches(found[0], values, payload, self.body, window, previous)
        assert [d for d in after["stripe_webhooks"] if d["_id"] != self.event_id] == [
            d for d in self.before["stripe_webhooks"] if d["_id"] != self.event_id
        ]
        self.observe(
            "Complete webhook lifecycle receipt",
            {
                "expected": values,
                "receipt": lossless(found[0]),
                "before": lossless(self.before),
                "after": lossless(after),
                "requestWindow": [t.isoformat() for t in window],
                "exchangeId": exchange,
            },
        )

    def delta(self, values: dict[str, str]) -> None:
        payload, window, exchange = self._capture()
        assert self.before is not None and self.calls is not None
        after = self.payments.snapshot()
        # A legacy document may physically lack attempt fields; ignored work must preserve that exact shape.
        target_before = self.payments.target(self.before)
        assert target_before is not None
        if "checkout_attempt_id" not in target_before:
            assert after["payments"] == self.before["payments"] and values["NewArchives"] == "0"
            normalized_before, normalized_after = deepcopy(self.before), deepcopy(after)
            for snapshot in (normalized_before, normalized_after):
                target = self.payments.target(snapshot)
                assert target is not None
                target.update(checkout_attempt_id=None, checkout_started_at=None)
        else:
            normalized_before, normalized_after = self.before, after
        lifecycle_delta(
            normalized_before,
            normalized_after,
            self.context.orders.order_id,
            values,
            window,
            payload["data"]["object"]["id"],
        )
        assert (len(self.context.orders.http_calls), len(self.context.stripe.calls)) == self.calls
        assert self.context.stripe.sessions == self.sessions
        assert len(self.faults) == int(values["ControlledInterruptions"])
        response = self.context.responses[0]
        assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-trace-id"])
        if response.status_code == 200:
            assert response.headers["content-type"] == "application/json" and response.json() == {"received": True}
        else:
            problem = response.json()
            assert problem.keys() == {
                "type",
                "title",
                "status",
                "detail",
                "instance",
                "code",
                "traceId",
                "errors",
                "missingProperties",
            }
            assert problem["traceId"] == response.headers["x-trace-id"] and "private" not in response.text
        self.observe(
            "Complete webhook lifecycle delta",
            {
                "expected": values,
                "before": lossless(self.before),
                "after": lossless(after),
                "requestWindow": [t.isoformat() for t in window],
                "externalCalls": self.calls,
                "exchangeId": exchange,
                "faults": self.faults,
            },
        )

    def read(self, values: dict[str, str]) -> None:
        snapshot = self.payments.snapshot()
        current = self.payments.target(snapshot)
        assert current is not None
        response = self.context.client.get(f"/payments/order/{self.context.orders.order_id}")
        assert response.status_code == 200 and response.headers["content-type"] == "application/json"
        authored = {
            key: json.dumps(str(current["order_id"]))
            if value == "{order.id}"
            else json.dumps(current["provider_session_id"])
            if value == "{stored.session_id}"
            else value
            for key, value in values.items()
        }
        full_payment(response.json(), current, authored)
        assert self.payments.snapshot() == snapshot
        assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-trace-id"])
        assert self.calls == (len(self.context.orders.http_calls), len(self.context.stripe.calls))
        self.observe(
            "Complete payment read after webhook",
            {
                "expected": values,
                "body": response.json(),
                "stored": lossless(current),
                "exchangeId": response.extensions["payments.bdd.exchangeId"],
            },
        )

    def interrupt(self, values: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
        assert values.keys() == {"Point", "Failures"}
        point, remaining = values["Point"], int(values["Failures"])
        assert point in {"before_completion", "after_completion", "conflict"} and 1 <= remaining <= 4
        original = MongoWebhookRepository.complete
        target = self.payments.target(self.payments.snapshot())
        assert target is not None
        target_payment_id = target["_id"]

        async def complete(
            repository: MongoWebhookRepository,
            receipt: WebhookReceipt,
            payment: Payment | None,
            state: WebhookState,
            reason: str,
            *,
            changed: bool,
        ) -> WebhookReceipt:
            nonlocal remaining
            if (
                remaining
                and receipt.event.checkout is not None
                and receipt.event.checkout.payment_id == target_payment_id
            ) or (remaining and receipt.event.checkout is None):
                remaining -= 1
                with self.context.evidence.action(
                    "Controlled webhook completion interruption",
                    {**values, "eventId": receipt.event.event_id, "remaining": remaining},
                ) as output:
                    output["before"] = lossless(self.payments.snapshot())
                    if point == "after_completion":
                        await original(repository, receipt, payment, state, reason, changed=changed)
                    output["after"] = lossless(self.payments.snapshot())
                    self.faults.append({"point": point, "eventId": receipt.event.event_id, "remaining": remaining})
                if point == "conflict":
                    assert payment is not None
                    raise PaymentConflictError(payment.id, payment.version)
                raise WebhookRetryError()
            return await original(repository, receipt, payment, state, reason, changed=changed)

        monkeypatch.setattr(MongoWebhookRepository, "complete", complete)

    def recover(self, values: dict[str, str]) -> None:
        assert values.keys() == {"Mode", "FirstResult", "RepeatedResult"}
        self.remember()
        if values["Mode"] == "fresh_http":
            self.deliver(fresh=True)
            first = self.context.responses[0]
            assert first.status_code == int(values["FirstResult"]) == 200
            snapshot = self.payments.snapshot()
            with TestClient(create_app(self.context.settings)) as client:
                repeated = EvidenceClient(client, self.context.evidence).post(
                    "/payments/webhooks/stripe",
                    content=self.body,
                    headers={"content-type": "application/json", "stripe-signature": signature(self.body)},
                )
            assert repeated.status_code == int(values["RepeatedResult"]) == 200
            assert repeated.json() == first.json() == {"received": True}
            assert self.payments.snapshot() == snapshot
            self.observe(
                "Fresh application redelivery results",
                {
                    "expected": values,
                    "first": first.status_code,
                    "repeated": repeated.status_code,
                    "collections": lossless(snapshot),
                    "exchangeIds": [r.extensions["payments.bdd.exchangeId"] for r in (first, repeated)],
                },
            )
            return
        assert values["Mode"] == "operator"
        settings = self.context.settings.model_copy(
            update={"stripe_enabled": False, "stripe_secret_key": None, "stripe_webhook_secret": None}
        )
        assert settings.stripe_secret_key is settings.stripe_webhook_secret is None
        lower = datetime.now(UTC)
        with self.context.evidence.action(
            "Replay durable normalized receipts in a fresh operator invocation",
            {**values, "providerCredentials": False},
        ) as output:
            processed = asyncio.run(replay(settings, 100))
            upper = datetime.now(UTC)
            snapshot = self.payments.snapshot()
            repeated = asyncio.run(replay(settings, 100))
            assert processed == int(values["FirstResult"]) and repeated == int(values["RepeatedResult"])
            assert self.payments.snapshot() == snapshot
            output.update(processed=processed, repeated=repeated, collections=lossless(snapshot))
        self.window = lower, upper
