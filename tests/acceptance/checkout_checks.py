"""Complete checkout, encoded-provider and stored-state assertions."""

from __future__ import annotations

import json
from collections.abc import Mapping
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, cast
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

from tests.acceptance.payment_checks import PUBLIC_FIELDS, PaymentChecks, Snapshot, full_payment, lossless, utc_date
from tests.acceptance.retry_checks import CURRENT_FIELDS, archived_snapshot, milliseconds, reset_fields

CHECKOUT_FIELDS = {"payment", "checkout_url", "checkout_status", "expires_at"}
CHECKOUT_EXPECTED = {*(f"payment.{field}" for field in PUBLIC_FIELDS), "checkout_url", "checkout_status", "expires_at"}
FORM_FIELDS = {
    "mode",
    "payment_method_types[0]",
    "payment_method_types[1]",
    "client_reference_id",
    *(f"metadata[{key}]" for key in ("payment_id", "order_id", "attempt_id")),
    *(f"payment_intent_data[metadata][{key}]" for key in ("payment_id", "order_id", "attempt_id")),
    "success_url",
    "cancel_url",
    "line_items[0][quantity]",
    "line_items[0][price_data][currency]",
    "line_items[0][price_data][unit_amount]",
    "line_items[0][price_data][product_data][name]",
}
REQUEST_FIELDS = {
    "Method",
    "Path",
    "StripeVersion",
    "ContentType",
    "IdempotencyKey",
    *(f"form.{k}" for k in FORM_FIELDS),
}


def checkout_response(
    body: dict[str, Any],
    stored: dict[str, Any],
    provider: dict[str, Any],
    authored: dict[str, str],
    *,
    window: tuple[datetime, datetime],
    created: bool,
    mutated: bool,
) -> None:
    assert body.keys() == CHECKOUT_FIELDS and authored.keys() == CHECKOUT_EXPECTED
    assert type(body["payment"]) is dict
    payment_expected = {k.removeprefix("payment."): v for k, v in authored.items() if k.startswith("payment.")}
    assert payment_expected["provider_session_id"] == "{stored.provider_session_id}"
    payment_expected["provider_session_id"] = json.dumps(stored["provider_session_id"])
    full_payment(
        cast(dict[str, Any], body["payment"]),
        stored,
        payment_expected,
        creation_window=window if created else None,
        update_window=window if mutated else None,
    )
    assert stored["provider_session_id"] == provider["id"]
    assert type(body["checkout_status"]) is str
    assert body["checkout_status"] == json.loads(authored["checkout_status"]) == provider["status"]
    assert type(provider["expires_at"]) is int and authored["expires_at"] == "{provider.expires_at}"
    assert utc_date(body["expires_at"]) == datetime.fromtimestamp(provider["expires_at"], UTC)
    if body["checkout_status"] == "open":
        assert authored["checkout_url"] == "{provider.url}"
        assert type(body["checkout_url"]) is str and body["checkout_url"] == provider["url"]
        url = urlsplit(body["checkout_url"])
        assert url.scheme == "https" and url.netloc == "checkout.stripe.com" and url.path.startswith("/c/pay/")
    else:
        assert body["checkout_status"] in {"complete", "expired"}
        assert authored["checkout_url"] == "null" and body["checkout_url"] is None
    # Reading Stripe's complete/expired status does not confirm or cancel a payment.
    assert body["payment"]["status"] == "pending"
    assert body["payment"]["provider_payment_id"] is None and body["payment"]["failure_code"] is None


def provider_request(
    call: tuple[str, str, Mapping[str, str], Any], stored: dict[str, Any], authored: dict[str, str]
) -> dict[str, list[str]]:
    assert authored.keys() == REQUEST_FIELDS
    method, url, headers, data = call
    headers = {key.lower(): value for key, value in headers.items()}
    assert method.upper() == authored["Method"] == "POST"
    assert url == "https://api.stripe.com" + authored["Path"] and authored["Path"] == "/v1/checkout/sessions"
    assert headers["stripe-version"] == authored["StripeVersion"] == "2026-08-26.dahlia"
    assert headers["content-type"] == authored["ContentType"] == "application/x-www-form-urlencoded"
    replacements = {
        "{payment.id}": str(stored["_id"]),
        "{order.id}": str(stored["order_id"]),
        "{attempt.id}": str(stored["checkout_attempt_id"]),
    }

    def resolve(value: str) -> str:
        for token, actual in replacements.items():
            value = value.replace(token, actual)
        assert "{" not in value and "}" not in value
        return value

    assert headers["idempotency-key"] == resolve(authored["IdempotencyKey"])
    assert headers["idempotency-key"] == f"checkout:{stored['_id']}:{stored['checkout_attempt_id']}"
    assert isinstance(stored["checkout_attempt_id"], UUID) and stored["checkout_attempt_id"].int != 0
    assert stored["checkout_request_version"] == 2
    body = parse_qs(str(data), keep_blank_values=True, strict_parsing=True)
    expected = {k.removeprefix("form."): [resolve(v)] for k, v in authored.items() if k.startswith("form.")}
    assert body == expected, "The entire encoded form, including absence of extra fields, must match"
    assert body["payment_method_types[0]"] == ["card"] and body["payment_method_types[1]"] == ["blik"]
    assert body["line_items[0][price_data][unit_amount]"] == [str(stored["amount_minor"])]
    assert body["line_items[0][price_data][currency]"] == [stored["currency"].lower()]
    return body


def checkout_delta(
    before: Snapshot, after: Snapshot, order_id: UUID, window: tuple[datetime, datetime]
) -> list[dict[str, Any]]:
    current_rows = [d for d in after["payments"] if d["order_id"] == order_id]
    prior_rows = [d for d in before["payments"] if d["order_id"] == order_id]
    assert len(current_rows) == 1 and len(prior_rows) <= 1
    current = current_rows[0]
    assert current.keys() == CURRENT_FIELDS and current["status"] == "pending"
    assert current["provider_payment_id"] is None and current["failure_code"] is None
    assert isinstance(current["provider_session_id"], str) and current["provider_session_id"].startswith("cs_test_")
    assert isinstance(current["checkout_attempt_id"], UUID) and current["checkout_attempt_id"].int != 0
    assert current["checkout_request_version"] == 2
    assert milliseconds(window[0]) <= current["checkout_started_at"] <= current["updated_at"] <= milliseconds(window[1])
    assert current["created_at"] <= current["checkout_started_at"]
    assert [d for d in after["payments"] if d["_id"] != current["_id"]] == [
        d for d in before["payments"] if d["order_id"] != order_id
    ]
    assert after["stripe_webhooks"] == before["stripe_webhooks"]
    old_ids = {d["_id"] for d in before["payment_history"]}
    assert [d for d in after["payment_history"] if d["_id"] in old_ids] == before["payment_history"]
    added = sorted((d for d in after["payment_history"] if d["_id"] not in old_ids), key=lambda d: d["version"])
    previous = prior_rows[0] if prior_rows else None
    base = 0 if previous is None else previous["version"]
    terminal = previous is not None and previous["status"] in {"failed", "canceled"}
    assert previous is None or previous["status"] in {"created", "failed", "canceled"}
    assert [d["version"] for d in added] == list(range(base, base + (3 if terminal else 2)))
    assert current["version"] == base + len(added)
    if previous is not None:
        for key in ("_id", "order_id", "amount_minor", "currency", "created_at"):
            assert current[key] == previous[key], key
        archived_snapshot(previous, added[0], window)
    else:
        assert milliseconds(window[0]) <= current["created_at"] <= milliseconds(window[1])
    # Each expected historical state is authored from the known lifecycle and current identity,
    # never round-tripped through the production history mapper.
    for index, archive in enumerate(added):
        if previous is not None and index == 0:
            continue
        version = archive["version"]
        expected = {**current, "version": version, "status": "created", "provider_session_id": None}
        if index == len(added) - 1:
            expected["updated_at"] = current["checkout_started_at"]
        else:
            expected.update(checkout_attempt_id=None, checkout_started_at=None, checkout_request_version=1)
            expected["updated_at"] = archive["updated_at"] if terminal else None
            if terminal:
                retried_at = expected["updated_at"]
                assert isinstance(retried_at, datetime)
                assert milliseconds(window[0]) <= retried_at <= current["checkout_started_at"]
                reset_fields(expected)
        archived_snapshot(expected, archive, window)
    if terminal:
        assert previous is not None and current["checkout_attempt_id"] != previous["checkout_attempt_id"]
    return added


class CheckoutChecks:
    def __init__(self, payments: PaymentChecks) -> None:
        self.payments = payments
        self.context = payments.context
        self.authored: dict[str, str] | None = None
        self.before_sessions: dict[str, dict[str, Any]] | None = None

    def remember(self) -> None:
        self.payments.remember()
        self.before_sessions = deepcopy(self.context.stripe.sessions)

    def provider(self) -> dict[str, Any]:
        current = self.payments.target(self.payments.snapshot())
        assert current is not None
        rows = [
            payload
            for payload in self.context.stripe.sessions.values()
            if payload["id"] == current["provider_session_id"]
        ]
        assert len(rows) == 1
        return rows[0]

    def complete(self, authored: dict[str, str]) -> None:
        self.authored = authored.copy()
        context, before = self.context, self.payments.before
        assert before is not None and context.request_window is not None
        stored = self.payments.target(self.payments.snapshot())
        assert stored is not None
        previous = self.payments.target(before)
        changed = previous != stored
        provider = self.provider()
        for response in context.responses:
            assert response.status_code == 200
            checkout_response(
                response.json(),
                stored,
                provider,
                authored,
                window=context.request_window,
                created=previous is None,
                mutated=changed,
            )
        context.evidence.observation(
            "Complete checkout response",
            {
                "expected": authored,
                "stored": lossless(stored),
                "provider": provider,
                "responses": [r.json() for r in context.responses],
                "exchangeIds": [r.extensions["payments.bdd.exchangeId"] for r in context.responses],
                "requestWindow": [v.isoformat() for v in context.request_window],
                "createdPayment": previous is None,
                "mutatedPayment": changed,
            },
        )

    def created(self, authored: dict[str, str]) -> None:
        context, before = self.context, self.payments.before
        assert before is not None and context.request_window is not None and self.payments.external_calls is not None
        after = self.payments.snapshot()
        added = checkout_delta(before, after, context.orders.order_id, context.request_window)
        stored, previous = self.payments.target(after), self.payments.target(before)
        assert stored is not None
        orders_before, stripe_before = self.payments.external_calls
        assert len(context.stripe.calls) == stripe_before + 1
        expected_reads = 2 if previous is None or previous["status"] in {"failed", "canceled"} else 1
        assert (
            context.orders.http_calls[orders_before:]
            == [("GET", f"/orders/{context.orders.order_id}")] * expected_reads
        )
        form = provider_request(context.stripe.calls[-1], stored, authored)
        assert self.before_sessions is not None
        key = f"checkout:{stored['_id']}:{stored['checkout_attempt_id']}"
        assert key not in self.before_sessions
        assert context.stripe.sessions == {**self.before_sessions, key: self.provider()}
        assert len({v["id"] for v in context.stripe.sessions.values()}) == len(context.stripe.sessions)
        context.evidence.observation(
            "Checkout provider request",
            {
                "expected": authored,
                "form": form,
                "exchangeIds": [context.stripe.exchange_ids[-1]],
                "ordersReads": expected_reads,
                "stripeCreates": 1,
            },
        )
        context.evidence.observation(
            "Checkout state effects",
            {
                "before": lossless(before),
                "after": lossless(after),
                "addedArchives": lossless(added),
                "requestWindow": [v.isoformat() for v in context.request_window],
                "unrelatedDocumentsUnchanged": True,
                "providerSessionsBefore": self.before_sessions,
                "providerSessionsAfter": context.stripe.sessions,
            },
        )

    def retrieved(self) -> None:
        context, before = self.context, self.payments.before
        assert before is not None and self.payments.external_calls is not None
        after = self.payments.snapshot()
        assert after == before
        assert context.stripe.sessions == self.before_sessions
        orders_before, stripe_before = self.payments.external_calls
        assert context.orders.http_calls[orders_before:] == [("GET", f"/orders/{context.orders.order_id}")]
        assert len(context.stripe.calls) == stripe_before + 1
        method, url, headers, data = context.stripe.calls[-1]
        current = self.payments.target(before)
        assert current is not None
        assert (
            method == "get" and url == f"https://api.stripe.com/v1/checkout/sessions/{current['provider_session_id']}"
        )
        assert not data and "Idempotency-Key" not in headers
        assert headers["Stripe-Version"] == "2026-08-26.dahlia"
        context.evidence.observation(
            "Checkout retrieval has no writes",
            {
                "collections": lossless(after),
                "stripeReads": 1,
                "stripeCreates": 0,
                "ordersReads": 1,
                "exchangeIds": [context.stripe.exchange_ids[-1]],
            },
        )

    def repeat(self, values: dict[str, str]) -> None:
        assert values.keys() == {"Repeats"} and self.authored is not None
        count = int(values["Repeats"])
        assert count >= 2
        context = self.context
        baseline = self.payments.snapshot()
        provider_baseline = deepcopy(context.stripe.sessions)
        original = context.responses[0].json()
        stored = self.payments.target(baseline)
        assert stored is not None
        calls = len(context.orders.http_calls), len(context.stripe.calls)
        for _ in range(count):
            started = datetime.now(UTC)
            response = context.client.post(f"/payments/{context.orders.order_id}/checkout")
            assert response.status_code == 200 and response.headers["content-type"] == "application/json"
            checkout_response(
                response.json(),
                stored,
                self.provider(),
                self.authored,
                window=(started, datetime.now(UTC)),
                created=False,
                mutated=False,
            )
            assert response.json() == original
            assert self.payments.snapshot() == baseline
            assert context.stripe.sessions == provider_baseline
        new_calls = context.stripe.calls[calls[1] :]
        assert len(new_calls) == count and all(
            method == "get"
            and url == f"https://api.stripe.com/v1/checkout/sessions/{stored['provider_session_id']}"
            and not data
            for method, url, _, data in new_calls
        )
        assert context.orders.http_calls[calls[0] :] == [("GET", f"/orders/{context.orders.order_id}")] * count
        context.evidence.observation(
            "Repeated checkout retains session and state",
            {
                "expected": values,
                "collections": lossless(baseline),
                "response": original,
                "stripeExchangeIds": context.stripe.exchange_ids[calls[1] :],
                "stripeReads": count,
                "stripeCreates": 0,
                "ordersReads": count,
            },
        )
