"""Independent full-response and populated-state assertions for Pay/payment reads."""

from __future__ import annotations

import asyncio
import json
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from bson.binary import UuidRepresentation
from bson.json_util import CANONICAL_JSON_OPTIONS, dumps
from pymongo import MongoClient

from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)
from tests.webhook_fixtures import encode, payload_for, signature

if TYPE_CHECKING:
    from tests.acceptance.conftest import AcceptanceContext

PUBLIC_FIELDS = {
    "id",
    "order_id",
    "amount_minor",
    "currency",
    "status",
    "provider_session_id",
    "provider_payment_id",
    "failure_code",
    "created_at",
    "updated_at",
}
Snapshot = dict[str, list[dict[str, Any]]]


def lossless(value: object) -> Any:
    options = CANONICAL_JSON_OPTIONS.with_options(uuid_representation=UuidRepresentation.STANDARD)
    return json.loads(dumps(value, json_options=options))


def utc_date(value: object) -> datetime:
    assert isinstance(value, str), "A present timestamp must be a string"
    assert re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|\+00:00)", value
    ), "Expected an RFC 3339 UTC timestamp"
    parsed = datetime.fromisoformat(value)
    assert parsed.utcoffset() == timedelta(0), "Timestamps must identify UTC"
    return parsed


def full_payment(
    body: dict[str, Any],
    stored: dict[str, Any],
    authored: dict[str, str],
    *,
    reference: dict[str, Any] | None = None,
    creation_window: tuple[datetime, datetime] | None = None,
    update_window: tuple[datetime, datetime] | None = None,
) -> None:
    assert body.keys() == authored.keys() == PUBLIC_FIELDS, "All ten public fields must be present, with no extras"
    reference = stored if reference is None else reference
    for key in PUBLIC_FIELDS:
        actual = body[key]
        value = authored[key]
        if key in {"created_at", "updated_at"} and value == f"{{stored.{key}}}":
            parsed = utc_date(actual)
            expected = reference[key]
            assert isinstance(expected, datetime) and expected.utcoffset() == timedelta(0)
            window = creation_window if key == "created_at" else update_window
            if window is not None:
                assert window[0] <= parsed <= window[1], "Mutation time is outside the actual request"
                # BSON has millisecond precision; mutation responses can retain Python microseconds.
                assert parsed.replace(microsecond=parsed.microsecond // 1000 * 1000) == expected
            else:
                assert parsed == expected, key
        else:
            expected = str(reference["_id"]) if key == "id" and value == "{stored.id}" else json.loads(value)
            assert type(actual) is type(expected) and actual == expected, key
        document_value = stored["_id" if key == "id" else key]
        if key in {"id", "order_id"}:
            assert isinstance(actual, str) and UUID(actual).int != 0 and str(UUID(actual)) == actual
            assert actual == str(document_value), key
        elif key in {"created_at", "updated_at"}:
            if actual is None:
                assert document_value is None, key
            else:
                parsed = utc_date(actual)
                window = creation_window if key == "created_at" else update_window
                if window is not None:
                    parsed = parsed.replace(microsecond=parsed.microsecond // 1000 * 1000)
                assert parsed == document_value, key
        elif key == "amount_minor":
            # MongoDB decodes int64 as bson.Int64; its exact integer value is the contract.
            assert type(actual) is int and isinstance(document_value, int) and not isinstance(document_value, bool)
            assert actual == document_value, key
        else:
            assert type(actual) is type(document_value) and actual == document_value, key
    assert body["id"] != body["order_id"]
    if body["updated_at"] is not None:
        assert utc_date(body["updated_at"]) >= utc_date(body["created_at"])


class PaymentChecks:
    def __init__(self, acceptance: AcceptanceContext) -> None:
        self.context = acceptance
        self.before: Snapshot | None = None
        self.before_body: dict[str, Any] | None = None
        self.external_calls: tuple[int, int] | None = None

    def snapshot(self) -> Snapshot:
        database = cast(MongoClient[dict[str, Any]], self.context.mongo)[self.context.settings.mongodb_database_name]
        return {
            name: sorted((dict(document) for document in database[name].find({})), key=lambda d: str(d["_id"]))
            for name in ("payments", "payment_history", "stripe_webhooks")
        }

    def target(self, snapshot: Snapshot) -> dict[str, Any] | None:
        found = [doc for doc in snapshot["payments"] if doc["order_id"] == self.context.orders.order_id]
        assert len(found) <= 1
        return found[0] if found else None

    def unrelated(self, values: dict[str, str]) -> None:
        assert values.keys() == {"OrderId", "ClientId", "TotalAmount", "TotalCurrency"}
        context, orders = self.context, self.context.orders
        previous = orders.order_id, orders.client_id, orders.amount, orders.currency, orders.status
        assert UUID(values["OrderId"]) != orders.order_id and UUID(values["ClientId"]) != orders.client_id
        try:
            orders.order_id, orders.client_id = UUID(values["OrderId"]), UUID(values["ClientId"])
            orders.amount, orders.currency, orders.status = (
                Decimal(values["TotalAmount"]),
                values["TotalCurrency"],
                "Created",
            )
            checkout = context.client.post(f"/payments/{orders.order_id}/checkout")
            assert checkout.status_code == 200
            document = context.payments.find_one({"order_id": orders.order_id})
            assert document is not None
            event = payload_for(PaymentMapper.to_domain(document), event_id="evt_unrelated_payment_read")
            event["data"]["object"]["payment_intent"] = "pi_unrelated_payment_read"
            body = encode(event)
            acknowledgement = context.client.post(
                "/payments/webhooks/stripe",
                content=body,
                headers={"content-type": "application/json", "stripe-signature": signature(body)},
            )
            assert acknowledgement.status_code == 200
            populated = self.snapshot()
            assert all(populated.values()), "The unrelated fixture must populate all three collections"
            context.evidence.observation(
                "Unrelated order fixture", {"inputs": values, "collections": lossless(populated)}
            )
        finally:
            orders.order_id, orders.client_id, orders.amount, orders.currency, orders.status = previous

    def prepare(self, state: str, values: dict[str, str]) -> None:
        assert state in {"pending", "succeeded", "failed", "canceled"}
        assert values.keys() == {"provider_session_id", "provider_payment_id", "failure_code"}
        context = self.context
        context.send("POST", f"/payments/{context.orders.order_id}/pay")
        assert context.responses[0].status_code == 201
        context.initial_payment_id = UUID(context.responses[0].json()["id"])
        session, provider, failure = (
            json.loads(values[key]) for key in ("provider_session_id", "provider_payment_id", "failure_code")
        )

        async def change() -> Payment:
            database = MongoDatabase(context.settings)
            try:
                repository = MongoPaymentRepository(database)
                payment = await repository.get_by_order_id(context.orders.order_id)
                assert payment is not None
                payment.begin_checkout(request_version=2)
                payment = await repository.update(payment)
                payment.mark_as_pending(session)
                payment = await repository.update(payment)
                if state == "succeeded":
                    payment.mark_as_succeeded(provider)
                elif state == "failed":
                    payment.mark_as_failed(failure)
                elif state == "canceled":
                    payment.cancel()
                else:
                    return payment
                return await repository.update(payment)
            finally:
                await database.close()

        with context.evidence.action(
            "Prepare stored payment through legal domain/repository transitions", {"status": state, **values}
        ) as output:
            payment = asyncio.run(change())
            assert payment.status.value == state
            assert (payment.provider_session_id, payment.provider_payment_id, payment.failure_code) == (
                session,
                provider,
                failure,
            )
            output["payment"] = lossless(context.payments.find_one({"order_id": context.orders.order_id}))

    def remember(self) -> None:
        context = self.context
        self.before = self.snapshot()
        target = self.target(self.before)
        self.external_calls = len(context.orders.http_calls), len(context.stripe.calls)
        if target is not None:
            response = context.client.get(f"/payments/order/{context.orders.order_id}")
            assert response.status_code == 200
            self.before_body = response.json()
        context.evidence.observation(
            "Payment collections before",
            {"collections": lossless(self.before), "body": self.before_body, "externalCallCounts": self.external_calls},
        )

    def complete(self, authored: dict[str, str]) -> None:
        context = self.context
        stored = self.target(self.snapshot())
        assert stored is not None
        reference = self.target(self.before) if self.before is not None else None
        for response in context.responses:
            body = response.json()
            window = context.request_window if response.status_code == 201 else None
            if response.status_code == 201:
                assert window is not None
            full_payment(body, stored, authored, reference=reference, creation_window=window)
        context.evidence.observation(
            "Complete payment response",
            {
                "expected": authored,
                "stored": lossless(stored),
                "responses": [r.json() for r in context.responses],
                "exchangeIds": [r.extensions["payments.bdd.exchangeId"] for r in context.responses],
                "requestWindow": [t.isoformat() for t in context.request_window] if context.request_window else None,
                "timestampPrecision": "Exact stored UTC for reads; explicit BSON millisecond projection for create",
            },
        )

    def unchanged(self) -> None:
        assert self.before is not None and self.external_calls is not None
        context = self.context
        after = self.snapshot()
        assert after == self.before, "Every field in every current/history/receipt document must remain unchanged"
        assert (len(context.orders.http_calls), len(context.stripe.calls)) == self.external_calls
        if self.before_body is not None:
            assert all(response.json() == self.before_body for response in context.responses)
        context.evidence.observation(
            "Payment read or repeat has no effects",
            {
                "collections": lossless(after),
                "completeCollectionsUnchanged": True,
                "externalCallCounts": self.external_calls,
                "noNewExternalCalls": True,
                "responseEqualsRememberedBody": self.before_body is not None,
            },
        )

    def only_created(self) -> None:
        assert self.before is not None and self.target(self.before) is None
        context = self.context
        after = self.snapshot()
        stored = self.target(after)
        assert stored is not None
        assert stored.keys() == (PUBLIC_FIELDS - {"id"}) | {
            "_id",
            "version",
            "checkout_attempt_id",
            "checkout_started_at",
            "checkout_request_version",
        }
        assert stored["version"] == 0 and stored["updated_at"] is None
        assert stored["checkout_attempt_id"] is None and stored["checkout_started_at"] is None
        assert stored["checkout_request_version"] == 1
        assert after["payments"] == sorted([*self.before["payments"], stored], key=lambda doc: str(doc["_id"]))
        assert all(after[name] == self.before[name] for name in ("payment_history", "stripe_webhooks"))
        assert self.external_calls is not None
        assert (len(context.orders.http_calls), len(context.stripe.calls)) == (
            self.external_calls[0] + 1,
            self.external_calls[1],
        )
        context.evidence.observation(
            "Exactly one new payment",
            {
                "collections": lossless(after),
                "newPayment": lossless(stored),
                "unrelatedDocumentsUnchanged": True,
                "ordersReads": 1,
                "stripeCalls": 0,
            },
        )
