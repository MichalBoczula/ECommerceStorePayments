"""Checkout fault/recovery evidence through real HTTP and MongoDB boundaries."""

from __future__ import annotations

import asyncio
import json
import re
from copy import deepcopy
from datetime import UTC, datetime, timedelta, tzinfo
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)
from tests.acceptance.checkout_checks import CheckoutChecks, checkout_delta, checkout_response, provider_request
from tests.acceptance.evidence import EvidenceClient
from tests.acceptance.payment_checks import PaymentChecks, Snapshot, lossless
from tests.acceptance.retry_checks import (
    CURRENT_FIELDS,
    archived_snapshot,
    milliseconds,
    reset_fields,
    transition_delta,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


def safe_problem(response: Response, expected: dict[str, str]) -> None:
    assert {"HTTPStatuses", "ContentType", "Code"} <= expected.keys()
    body = response.json()
    assert set(body) == {
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
    assert response.status_code == int(expected["HTTPStatuses"])
    assert response.headers["content-type"] == expected["ContentType"] == "application/problem+json"
    assert body["code"] == expected["Code"] and type(body["status"]) is int and body["status"] == response.status_code
    assert re.fullmatch(r"[0-9a-f]{32}", body["traceId"])
    assert body["traceId"] == response.headers["x-trace-id"] and body["instance"] == response.request.url.path
    for key, value in expected.items():
        if key.startswith("JSON."):
            actual, desired = body[key[5:]], json.loads(value)
            assert type(actual) is type(desired) and actual == desired, key
    assert body["errors"] == body["missingProperties"] == []
    assert "private" not in json.dumps(body).lower()


def preparation_delta(
    before: Snapshot, after: Snapshot, order_id: UUID, window: tuple[datetime, datetime], effect: str
) -> None:
    assert effect in {"created", "reserved", "pending"}
    if effect == "pending":
        checkout_delta(before, after, order_id, window)
        return
    assert not any(d["order_id"] == order_id for d in before["payments"])
    targets = [d for d in after["payments"] if d["order_id"] == order_id]
    assert len(targets) == 1
    current = targets[0]
    assert current.keys() == CURRENT_FIELDS and current["status"] == "created"
    assert current["provider_session_id"] is current["provider_payment_id"] is current["failure_code"] is None
    assert milliseconds(window[0]) <= current["created_at"] <= milliseconds(window[1])
    assert after["payments"] == sorted([*before["payments"], current], key=lambda d: str(d["_id"]))
    assert after["stripe_webhooks"] == before["stripe_webhooks"]
    if effect == "created":
        assert current["version"] == 0 and current["updated_at"] is None
        reset_fields(current)
        assert after["payment_history"] == before["payment_history"]
    else:
        assert current["version"] == 1 and current["checkout_request_version"] == 2
        assert isinstance(current["checkout_attempt_id"], UUID) and current["checkout_attempt_id"].int != 0
        assert current["checkout_started_at"] == current["updated_at"]
        assert milliseconds(window[0]) <= current["updated_at"] <= milliseconds(window[1])
        added = [d for d in after["payment_history"] if d["_id"] == f"{current['_id']}:0"]
        assert len(added) == 1
        previous = {
            **current,
            "version": 0,
            "updated_at": None,
            "checkout_attempt_id": None,
            "checkout_started_at": None,
            "checkout_request_version": 1,
        }
        archived_snapshot(previous, added[0], window)
        assert [d for d in after["payment_history"] if d["_id"] != added[0]["_id"]] == before["payment_history"]


def recovery_delta(before: Snapshot, after: Snapshot, order_id: UUID, window: tuple[datetime, datetime]) -> str:
    prior = next(d for d in before["payments"] if d["order_id"] == order_id)
    current = next(d for d in after["payments"] if d["order_id"] == order_id)
    assert current["status"] == "pending" and current["provider_payment_id"] is current["failure_code"] is None
    if prior["status"] == "pending":
        assert after == before
        return "GET"
    assert prior["status"] == "created"
    if prior.get("checkout_attempt_id") is None:
        checkout_delta(before, after, order_id, window)
    else:
        transition_delta(before, after, order_id, window)
        for key in ("checkout_attempt_id", "checkout_started_at"):
            assert current[key] == prior[key], key
        assert current["checkout_request_version"] == prior.get("checkout_request_version", 1)
    return "POST"


class CheckoutRecoveryChecks:
    def __init__(self, payments: PaymentChecks, checkout: CheckoutChecks) -> None:
        self.payments, self.checkout, self.context = payments, checkout, payments.context
        self.before_sessions: dict[str, dict[str, Any]] | None = None
        self.recovery_call: tuple[str, str, Mapping[str, str], Any] | None = None
        self.recovery_exchange: str | None = None
        self.comparison_now: datetime | None = None

    def remember(self, observation_name: str = "Payment collections before") -> None:
        self.payments.remember(observation_name)
        self.before_sessions = deepcopy(self.context.stripe.sessions)

    def earlier_problem(self, authored: dict[str, str]) -> None:
        response = self.context.responses[0]
        safe_problem(response, authored)
        self.context.evidence.observation(
            "Earlier checkout failure",
            {
                "expected": authored,
                "body": response.json(),
                "exchangeId": response.extensions["payments.bdd.exchangeId"],
            },
        )

    def effect(self, authored: dict[str, str]) -> None:
        assert authored.keys() == {"Effect", "OrdersReads", "StripeMethod", "SessionsAdded", "CurrentVersion"}
        context, before = self.context, self.payments.before
        assert before is not None and context.request_window is not None and self.payments.external_calls is not None
        after = self.payments.snapshot()
        for response in context.responses:
            assert response.status_code >= 400
            body = response.json()
            assert re.fullmatch(r"[0-9a-f]{32}", body["traceId"])
            assert body["traceId"] == response.headers["x-trace-id"]
            assert "private" not in json.dumps(body).lower()
        if authored["Effect"] == "unchanged":
            assert after == before, "Every field in every populated collection must remain unchanged"
        else:
            preparation_delta(before, after, context.orders.order_id, context.request_window, authored["Effect"])
        current = self.payments.target(after)
        if authored["CurrentVersion"] == "none":
            assert current is None
        else:
            assert current is not None and current.get("version", 0) == int(authored["CurrentVersion"])
            assert current["amount_minor"] == 1299 and current["currency"] == "PLN"
        o, s = self.payments.external_calls
        assert context.orders.http_calls[o:] == [("GET", f"/orders/{context.orders.order_id}")] * int(
            authored["OrdersReads"]
        )
        calls = context.stripe.calls[s:]
        assert len(calls) == (0 if authored["StripeMethod"] == "none" else 1)
        if calls:
            method, url, headers, data = calls[0]
            assert method.upper() == authored["StripeMethod"]
            assert headers["Stripe-Version"] == "2026-08-26.dahlia"
            if method == "get":
                assert (
                    current is not None
                    and url == f"https://api.stripe.com/v1/checkout/sessions/{current['provider_session_id']}"
                )
                assert not data and not any(key.lower() == "idempotency-key" for key in headers)
            else:
                assert url == "https://api.stripe.com/v1/checkout/sessions"
        assert self.before_sessions is not None
        sessions = context.stripe.sessions
        added = {key: value for key, value in sessions.items() if key not in self.before_sessions}
        assert len(added) == int(authored["SessionsAdded"])
        assert sessions == {**self.before_sessions, **added}
        if added:
            assert current is not None
            key = f"checkout:{current['_id']}:{current['checkout_attempt_id']}"
            assert set(added) == {key}
            assert added[key]["metadata"] == {
                "payment_id": str(current["_id"]),
                "order_id": str(current["order_id"]),
                "attempt_id": str(current["checkout_attempt_id"]),
            }
        self.context.evidence.observation(
            "Checkout failure state",
            {
                "expected": authored,
                "before": lossless(before),
                "after": lossless(after),
                "providerSessionsBefore": self.before_sessions,
                "providerSessionsAfter": sessions,
                "requestWindow": [t.isoformat() for t in context.request_window],
                "exchangeIds": [r.extensions["payments.bdd.exchangeId"] for r in context.responses],
                "stripeExchangeIds": context.stripe.exchange_ids[s:],
                "comparisonNow": self.comparison_now.isoformat() if self.comparison_now else None,
            },
        )

    def failed_request(self, authored: dict[str, str]) -> None:
        current = self.payments.target(self.payments.snapshot())
        assert current is not None
        form = provider_request(self.context.stripe.calls[-1], current, authored)
        self.context.evidence.observation(
            "Failed checkout provider request",
            {
                "expected": authored,
                "form": form,
                "exchangeIds": [self.context.stripe.exchange_ids[-1]],
            },
        )

    def reserve(self, values: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
        assert values.keys() == {"RequestVersion", "AgeSeconds", "OmittedFields"}
        context = self.context
        anchor = milliseconds(datetime.now(UTC))
        self.comparison_now = anchor
        age = timedelta(microseconds=int(Decimal(values["AgeSeconds"]) * 1_000_000))
        start = anchor - age
        payment = Payment.rehydrate(
            uuid4(),
            context.orders.order_id,
            Money(1299, "PLN"),
            PaymentStatus.CREATED,
            None,
            None,
            None,
            start - timedelta(seconds=1),
            start,
            1,
            uuid4(),
            start,
            int(values["RequestVersion"]),
        )

        async def insert() -> None:
            db = MongoDatabase(context.settings)
            try:
                await MongoPaymentRepository(db).create(payment)
            finally:
                await db.close()

        with context.evidence.action("Prepare valid historical reserved payment through repository", values) as output:
            asyncio.run(insert())
            omitted = [] if values["OmittedFields"] == "-" else values["OmittedFields"].split(",")
            assert omitted in ([], ["checkout_request_version"])
            if omitted:
                assert values["RequestVersion"] == "1"
                context.payments.update_one({"_id": payment.id}, {"$unset": {key: "" for key in omitted}})
            stored = context.payments.find_one({"_id": payment.id})
            assert stored is not None and all(key not in stored for key in omitted)
            assert PaymentMapper.to_domain(stored).checkout_request_version == int(values["RequestVersion"])
            output.update(stored=lossless(stored), comparisonNow=anchor.isoformat())

        class ComparisonClock(datetime):
            @classmethod
            def now(cls, tz: tzinfo | None = None) -> datetime:
                return anchor.astimezone(tz) if tz is not None else anchor.replace(tzinfo=None)

        # Freeze only the application's age comparison; domain mutation timestamps and HTTP windows remain real.
        monkeypatch.setattr("ecommerce_store_payments.application.payments.payment_service.datetime", ComparisonClock)

    def legacy_pending(self, values: dict[str, str]) -> None:
        assert values == {
            "OmittedFields": "checkout_attempt_id,checkout_started_at,checkout_request_version",
            "ProviderSessionId": "cs_test_historical",
        }
        payment = Payment.create(self.context.orders.order_id, Money(1299, "PLN"))
        payment.mark_as_pending(values["ProviderSessionId"])
        document: dict[str, Any] = dict(PaymentMapper.to_document(payment))
        for field in values["OmittedFields"].split(","):
            del document[field]
        with self.context.evidence.action(
            "Insert historical Pending fixture with absent checkout identity", values
        ) as output:
            self.context.payments.insert_one(cast(PaymentDocument, document))
            output["stored"] = lossless(document)
            assert PaymentMapper.to_domain(cast(PaymentDocument, document)).checkout_attempt_id is None

    def interrupt(self, point: str, monkeypatch: pytest.MonkeyPatch) -> None:
        assert point in {"reservation_before", "pending_before", "pending_after"}
        original = MongoPaymentRepository.update
        remaining = 1
        context = self.context

        async def interrupted(repository: MongoPaymentRepository, payment: Payment) -> Payment:
            nonlocal remaining
            target = payment.order_id == context.orders.order_id
            stage = payment.status is (
                PaymentStatus.CREATED if point == "reservation_before" else PaymentStatus.PENDING
            )
            if target and stage and remaining:
                remaining -= 1
                with context.evidence.action(
                    "Interrupt checkout persistence acknowledgement",
                    {"point": point, "candidate": lossless(PaymentMapper.to_document(payment))},
                ) as output:
                    output["before"] = lossless(self.payments.snapshot())
                    if point == "pending_after":
                        await original(repository, payment)
                    output["after"] = lossless(self.payments.snapshot())
                    output["committed"] = point == "pending_after"
                raise RuntimeError("private injected persistence acknowledgement loss")
            return await original(repository, payment)

        monkeypatch.setattr(MongoPaymentRepository, "update", interrupted)

    def _recover(
        self,
        response: Response,
        before: Snapshot,
        sessions_before: dict[str, dict[str, Any]],
        calls: tuple[int, int],
        window: tuple[datetime, datetime],
        authored: dict[str, str],
        fresh: bool,
    ) -> None:
        context = self.context
        after = self.payments.snapshot()
        method = recovery_delta(before, after, context.orders.order_id, window)
        current = self.payments.target(after)
        assert (
            current is not None
            and response.status_code == 200
            and response.headers["content-type"] == "application/json"
        )
        provider = self.checkout.provider()
        checkout_response(
            response.json(), current, provider, authored, window=window, created=False, mutated=after != before
        )
        o, s = calls
        assert context.orders.http_calls[o:] == [("GET", f"/orders/{context.orders.order_id}")]
        assert len(context.stripe.calls) == s + 1
        self.recovery_call = context.stripe.calls[-1]
        self.recovery_exchange = context.stripe.exchange_ids[-1]
        assert self.recovery_call[0].upper() == method
        key = f"checkout:{current['_id']}:{current['checkout_attempt_id']}"
        if method == "POST":
            assert context.stripe.sessions == {**sessions_before, key: provider}
            earlier = [
                call for call in context.stripe.calls[:s] if call[0] == "post" and call[2].get("Idempotency-Key") == key
            ]
            assert all(
                call[3] == self.recovery_call[3]
                and call[2]["Idempotency-Key"] == self.recovery_call[2]["Idempotency-Key"]
                for call in earlier
            )
        else:
            assert context.stripe.sessions == sessions_before
        context.evidence.observation(
            "Recovered checkout response and state",
            {
                "expected": authored,
                "before": lossless(before),
                "after": lossless(after),
                "provider": provider,
                "body": response.json(),
                "exchangeId": response.extensions["payments.bdd.exchangeId"],
                "providerSessionsBefore": sessions_before,
                "providerSessionsAfter": context.stripe.sessions,
                "requestWindow": [t.isoformat() for t in window],
                "freshApplicationInstance": fresh,
                "stripeExchangeId": self.recovery_exchange,
                "stripeMethod": method,
            },
        )

    def current_recovery(self, authored: dict[str, str]) -> None:
        assert (
            self.payments.before is not None
            and self.before_sessions is not None
            and self.payments.external_calls is not None
            and self.context.request_window is not None
        )
        self._recover(
            self.context.responses[0],
            self.payments.before,
            self.before_sessions,
            self.payments.external_calls,
            self.context.request_window,
            authored,
            False,
        )

    def fresh_recovery(self, authored: dict[str, str]) -> None:
        context = self.context
        before = self.payments.snapshot()
        sessions = deepcopy(context.stripe.sessions)
        calls = len(context.orders.http_calls), len(context.stripe.calls)
        context.stripe.mode = "ok"
        with context.evidence.action(
            "Recover checkout through a fresh application instance", {"collections": lossless(before)}
        ) as output:
            with TestClient(create_app(context.settings)) as raw:
                assert raw.app is not context.client.app
                started = datetime.now(UTC)
                response = EvidenceClient(raw, context.evidence).post(f"/payments/{context.orders.order_id}/checkout")
                window = started, datetime.now(UTC)
                self._recover(response, before, sessions, calls, window, authored, True)
                output["exchangeId"] = response.extensions["payments.bdd.exchangeId"]

    def recovery_request(self, authored: dict[str, str]) -> None:
        assert self.recovery_call is not None
        current = self.payments.target(self.payments.snapshot())
        assert current is not None
        method, url, headers, data = self.recovery_call
        if method == "post":
            form = provider_request(
                self.recovery_call, current, authored, request_version=current["checkout_request_version"]
            )
        else:
            assert authored == {
                "Method": "GET",
                "Path": "/v1/checkout/sessions/{session.id}",
                "StripeVersion": "2026-08-26.dahlia",
                "IdempotencyKey": "absent",
                "Body": "empty",
            }
            assert url == f"https://api.stripe.com/v1/checkout/sessions/{current['provider_session_id']}" and not data
            assert headers["Stripe-Version"] == authored["StripeVersion"] and not any(
                k.lower() == "idempotency-key" for k in headers
            )
            form = {}
        self.context.evidence.observation(
            "Recovery provider request", {"expected": authored, "form": form, "exchangeIds": [self.recovery_exchange]}
        )

    def repeat_failure(self, values: dict[str, str]) -> None:
        assert values.keys() == {"Repeats"}
        context = self.context
        before, sessions = self.payments.snapshot(), deepcopy(context.stripe.sessions)
        first = context.responses[0]
        original_call = context.stripe.calls[-1]
        exchanges: list[str] = []
        for _ in range(int(values["Repeats"])):
            response = context.client.post(f"/payments/{context.orders.order_id}/checkout")
            body = response.json()
            assert (
                response.status_code == first.status_code
                and response.headers["content-type"] == "application/problem+json"
            )
            assert {k: v for k, v in body.items() if k != "traceId"} == {
                k: v for k, v in first.json().items() if k != "traceId"
            }
            assert re.fullmatch(r"[0-9a-f]{32}", body["traceId"]) and body["traceId"] == response.headers["x-trace-id"]
            assert self.payments.snapshot() == before and context.stripe.sessions == sessions
            call = context.stripe.calls[-1]
            assert (
                call[0] == "post"
                and call[3] == original_call[3]
                and call[2]["Idempotency-Key"] == original_call[2]["Idempotency-Key"]
            )
            exchanges.append(response.extensions["payments.bdd.exchangeId"])
        context.evidence.observation(
            "Repeated checkout failure preserves attempt",
            {"expected": values, "collections": lossless(before), "exchangeIds": exchanges},
        )
