"""Complete technical HTTP/state evidence and observed real host resource lifecycles."""

from __future__ import annotations

import json
import re
from collections.abc import Generator
from contextlib import contextmanager
from copy import deepcopy
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

import pytest
import stripe
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import AsyncClient, MockTransport, Request, Response
from pymongo import MongoClient
from pymongo.errors import InvalidOperation

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.infrastructure.clients.stripe.checkout_provider import (
    STRIPE_API_VERSION,
    StripeCheckoutProvider,
)
from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from tests.acceptance.evidence import EvidenceClient
from tests.acceptance.payment_checks import PaymentChecks, Snapshot, full_payment, lossless
from tests.webhook_fixtures import encode, payload_for, signature

if TYPE_CHECKING:
    from tests.acceptance.conftest import AcceptanceContext

MAIN = UUID("11111111-1111-4111-8111-111111111111")
CLIENT = UUID("22222222-2222-4222-8222-222222222222")
OTHER = UUID("66666666-6666-4666-8666-666666666666")
OTHER_CLIENT = UUID("77777777-7777-4777-8777-777777777777")
INDEXES = {
    "payments": {
        "_id_": {"key": [["_id", 1]], "unique": True},
        "ux_payments_order_id": {"key": [["order_id", 1]], "unique": True},
    },
    "payment_history": {
        "_id_": {"key": [["_id", 1]], "unique": True},
        "ix_payment_history_payment_id": {"key": [["payment_id", 1]], "unique": False},
    },
    "stripe_webhooks": {
        "_id_": {"key": [["_id", 1]], "unique": True},
        "ix_webhooks_pending": {"key": [["state", 1], ["received_at", 1]], "unique": False},
        "ix_webhooks_fulfillment": {"key": [["fulfillment_status", 1], ["received_at", 1]], "unique": False},
        "ix_webhooks_fulfillment_due": {
            "key": [["fulfillment_status", 1], ["fulfillment_next_attempt", 1]],
            "unique": False,
        },
        "ix_webhooks_fulfillment_lease": {
            "key": [["fulfillment_status", 1], ["fulfillment_lease_until", 1]],
            "unique": False,
        },
    },
}


def indexes(context: AcceptanceContext) -> dict[str, Any]:
    database = context.mongo[context.settings.mongodb_database_name]
    raw = {name: database[name].index_information() for name in INDEXES}
    normalized = {
        name: {
            key: {"key": [list(pair) for pair in value["key"]], "unique": value.get("unique", key == "_id_")}
            for key, value in values.items()
        }
        for name, values in raw.items()
    }
    assert normalized == INDEXES
    return {"raw": lossless(raw), "normalized": normalized}


def protocol(response: Any, expected_body: Any, media: str = "application/json") -> None:
    assert response.status_code == 200 and response.headers["content-type"] == media
    assert response.headers["content-length"] == str(len(response.content))
    assert re.fullmatch("[0-9a-f]{32}", response.headers["x-trace-id"])
    assert response.headers["x-trace-id"] != response.request.headers.get("x-trace-id")
    assert response.headers.get("cache-control") is None
    assert response.json() == expected_body if media == "application/json" else response.content == expected_body


def stored_read(context: AcceptanceContext, expected: dict[str, str] | None = None) -> tuple[Any, dict[str, Any]]:
    payments = PaymentChecks(context)
    stored = payments.target(payments.snapshot())
    assert stored is not None
    response = context.client.get(f"/payments/order/{context.orders.order_id}")
    assert response.status_code == 200
    if expected is None:
        expected = {
            k: "{stored.id}"
            if k == "id"
            else "{stored." + k + "}"
            if k.endswith("_at") and stored[k] is not None
            else json.dumps(str(stored[k]) if k == "order_id" else stored[k])
            for k in [
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
            ]
        }
    else:
        expected = {
            k: json.dumps(stored["provider_session_id"]) if v == "{stored.session_id}" else v
            for k, v in expected.items()
        }
    full_payment(response.json(), stored, expected)
    return response, stored


def populate(
    context: AcceptanceContext, label: str, main_amount: str = "12.99", other_amount: str = "31.73"
) -> Snapshot:
    orders = context.orders
    for oid, cid, amount, paid in [(OTHER, OTHER_CLIENT, other_amount, True), (MAIN, CLIENT, main_amount, False)]:
        orders.order_id, orders.client_id, orders.amount, orders.currency, orders.status = (
            oid,
            cid,
            Decimal(amount),
            "PLN",
            "Created",
        )
        response = context.client.post(f"/payments/{oid}/checkout")
        assert response.status_code == 200
        document = context.payments.find_one({"order_id": oid})
        assert document is not None
        if paid:
            event = payload_for(PaymentMapper.to_domain(document), event_id="evt_technical_unrelated")
            body = encode(event)
            delivered = context.client.post(
                "/payments/webhooks/stripe",
                content=body,
                headers={"content-type": "application/json", "stripe-signature": signature(body)},
            )
            assert delivered.status_code == 200 and delivered.json() == {"received": True}
    snapshot = PaymentChecks(context).snapshot()
    assert [len(snapshot[n]) for n in ("payments", "payment_history", "stripe_webhooks")] == [2, 5, 1]
    assert next(d for d in snapshot["payments"] if d["order_id"] == MAIN)["amount_minor"] == int(
        Decimal(main_amount) * 100
    )
    context.evidence.observation(
        f"Technical populated {label}",
        {
            "database": context.settings.mongodb_database_name,
            "mainAmount": main_amount,
            "otherAmount": other_amount,
            "collections": lossless(snapshot),
            "indexes": indexes(context),
        },
    )
    return snapshot


class HostResources:
    """Decorators allocate actual clients and observe actual closes, including failed startup."""

    def __init__(self, context: AcceptanceContext) -> None:
        self.context = context
        self.databases: list[MongoDatabase] = []
        self.clients: list[AsyncClient] = []
        self.events: list[dict[str, Any]] = []
        self.providers: list[StripeCheckoutProvider] = []
        self.close_proofs: list[dict[str, Any]] = []

    @contextmanager
    def install(
        self, settings: Settings, monkeypatch: pytest.MonkeyPatch, *, new_boundaries: bool = True
    ) -> Generator[tuple[Any, Any]]:
        from tests.acceptance.conftest import AcceptanceStripeTransport, OrdersBoundary

        orders = OrdersBoundary() if new_boundaries else self.context.orders
        transport = AcceptanceStripeTransport(self.context.evidence) if new_boundaries else self.context.stripe
        original_database = MongoDatabase

        def database_factory(resolved: Settings) -> MongoDatabase:
            database = original_database(resolved)
            self.databases.append(database)
            self.events.append({"event": "database-created", "database": resolved.mongodb_database_name})
            close, probe, ensure = database.close, database.probe, database.ensure_indexes

            async def closed() -> None:
                await close()
                try:
                    await database.client.admin.command("ping")
                except InvalidOperation:
                    self.close_proofs.append(
                        {
                            "database": resolved.mongodb_database_name,
                            "exceptionType": "InvalidOperation",
                            "closedClientRejectsPing": True,
                        }
                    )
                else:
                    raise AssertionError("Closed actual Mongo client still accepted a ping")
                self.events.append({"event": "database-closed", "database": resolved.mongodb_database_name})

            async def probed() -> None:
                self.events.append({"event": "probe-entered", "database": resolved.mongodb_database_name})
                await probe()
                self.events.append({"event": "probe-completed", "database": resolved.mongodb_database_name})

            async def indexed() -> None:
                self.events.append({"event": "indexes-entered", "database": resolved.mongodb_database_name})
                await ensure()
                self.events.append({"event": "indexes-completed", "database": resolved.mongodb_database_name})

            monkeypatch.setattr(database, "close", closed)
            monkeypatch.setattr(database, "probe", probed)
            monkeypatch.setattr(database, "ensure_indexes", indexed)
            return database

        def observed(request: Request) -> Response:
            exchange = self.context.evidence.begin(
                request.method,
                str(request.url),
                request.headers,
                request.read(),
                target="invoices" if request.url.path.startswith("/invoices/") else "orders",
                role="technical-peer-boundary",
                controlled=True,
            )
            try:
                response = orders.handle(request)
                self.context.evidence.response(exchange, response.status_code, response.headers, response.read())
                return response
            except BaseException as error:
                self.context.evidence.failure(exchange, error)
                raise

        def client_factory(*, base_url: str, timeout: float, trust_env: bool) -> AsyncClient:
            client = AsyncClient(
                base_url=base_url, timeout=timeout, trust_env=trust_env, transport=MockTransport(observed)
            )
            self.clients.append(client)
            return client

        def provider_factory(resolved: Settings) -> StripeCheckoutProvider:
            provider = StripeCheckoutProvider(
                resolved,
                stripe.StripeClient(
                    "sk_test_fixture", stripe_version=STRIPE_API_VERSION, http_client=transport, max_network_retries=0
                ),
            )
            self.providers.append(provider)
            close = provider.close

            async def closed() -> None:
                await close()
                self.events.append({"event": "provider-closed", "database": settings.mongodb_database_name})

            monkeypatch.setattr(provider, "close", closed)
            return provider

        with monkeypatch.context() as patch:
            patch.setattr("ecommerce_store_payments.api.app.MongoDatabase", database_factory)
            patch.setattr("ecommerce_store_payments.api.app.AsyncClient", client_factory)
            patch.setattr("ecommerce_store_payments.api.app.StripeCheckoutProvider", provider_factory)
            yield orders, transport

    def closed(self) -> dict[str, Any]:
        assert len(self.databases) == len(self.close_proofs) == len(self.clients) == len(self.providers)
        assert all(client.is_closed for client in self.clients)
        assert len([e for e in self.events if e["event"] == "provider-closed"]) == len(self.providers)
        return {
            "events": self.events,
            "mongoCloseProofs": self.close_proofs,
            "ordersClientsClosed": [c.is_closed for c in self.clients],
            "databaseCount": len(self.databases),
            "providerCount": len(self.providers),
        }


@contextmanager
def peer(
    context: AcceptanceContext,
    monkeypatch: pytest.MonkeyPatch,
    *,
    url: str | None = None,
    name: str | None = None,
    host: str = "http://peer.test",
    retain_database: bool = False,
) -> Generator[tuple[Any, HostResources]]:
    from tests.acceptance.conftest import AcceptanceContext

    settings = context.settings.model_copy(
        update={
            "mongodb_connection_string": url or context.settings.mongodb_connection_string,
            "mongodb_database_name": name or f"payments_technical_peer_{uuid4().hex}",
        }
    )
    resources = HostResources(context)
    sync: MongoClient[PaymentDocument] = MongoClient(
        settings.mongodb_connection_string, uuidRepresentation="standard", tz_aware=True
    )
    try:
        with resources.install(settings, monkeypatch) as (orders, transport):
            with TestClient(create_app(settings), base_url=host) as raw:
                yield (
                    AcceptanceContext(
                        client=EvidenceClient(raw, context.evidence),
                        evidence=context.evidence,
                        orders=orders,
                        settings=settings,
                        mongo=sync,
                        stripe=transport,
                    ),
                    resources,
                )
        resources.closed()
    finally:
        try:
            if not retain_database:
                assert settings.mongodb_database_name != context.settings.mongodb_database_name
                with context.evidence.action(
                    "Drop only the scoped peer database", {"database": settings.mongodb_database_name}
                ) as output:
                    sync.drop_database(settings.mongodb_database_name)
                    output["remainingDatabase"] = settings.mongodb_database_name in sync.list_database_names()
                    assert not output["remainingDatabase"]
        finally:
            sync.close()


class HealthChecks:
    def __init__(self, context: AcceptanceContext) -> None:
        self.context, self.payments = context, PaymentChecks(context)
        self.before: Snapshot = {}
        self.calls: tuple[int, int] = (0, 0)
        self.sessions: dict[str, Any] = {}
        self.probes = 0
        self.pings = 0

    def populate(self, values: dict[str, str]) -> None:
        assert values == {"Payments": "2", "History": "5", "Receipts": "1"}
        self.before = populate(self.context, "health baseline")
        self.calls = len(self.context.orders.http_calls), len(self.context.stripe.calls)
        self.sessions = deepcopy(self.context.stripe.sessions)

    def observe(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from pymongo.asynchronous.database import AsyncDatabase

        database = cast(FastAPI, self.context.client.app).state.database
        probe = database.probe
        command = AsyncDatabase[Any].command

        async def probed() -> None:
            self.probes += 1
            await probe()

        async def commanded(db: Any, *args: Any, **kwargs: Any) -> Any:
            result = await command(db, *args, **kwargs)
            if db.client is database.client and args[0] == "ping":
                self.pings += 1
            return result

        monkeypatch.setattr(database, "probe", probed)
        monkeypatch.setattr(AsyncDatabase, "command", commanded)

    def verify(self, values: dict[str, str]) -> None:
        assert values.keys() == {
            "ProbeCalls",
            "RealPings",
            "Collections",
            "ProviderSessions",
            "OrdersCalls",
            "StripeCalls",
            "CacheControl",
            "ContentLength",
            "Trace",
        }
        assert self.probes == int(values["ProbeCalls"]) and self.pings == int(values["RealPings"])
        assert values["Collections"] == values["ProviderSessions"] == "unchanged"
        assert (
            values["CacheControl"] == "<absent>" and values["ContentLength"] == "actual" and values["Trace"] == "fresh"
        )
        response = self.context.responses[0]
        if response.status_code == 200:
            protocol(response, {"status": "healthy"})
        else:
            assert response.status_code == 503 and response.headers["content-type"] == "application/problem+json"
            assert (
                response.headers["content-length"] == str(len(response.content))
                and response.headers.get("cache-control") is None
            )
            assert re.fullmatch("[0-9a-f]{32}", response.headers["x-trace-id"])
        assert self.payments.snapshot() == self.before and self.context.stripe.sessions == self.sessions
        assert len(self.context.orders.http_calls) - self.calls[0] == int(values["OrdersCalls"]) == 0
        assert len(self.context.stripe.calls) - self.calls[1] == int(values["StripeCalls"]) == 0
        index_proof = indexes(self.context)
        read, stored = stored_read(self.context)
        assert self.payments.snapshot() == self.before
        self.context.evidence.observation(
            "Complete populated health protocol",
            {
                "expected": values,
                "before": lossless(self.before),
                "after": lossless(self.payments.snapshot()),
                "indexes": index_proof,
                "probeCalls": self.probes,
                "realPings": self.pings,
                "body": response.json(),
                "exchangeIds": [
                    response.extensions["payments.bdd.exchangeId"],
                    read.extensions["payments.bdd.exchangeId"],
                ],
                "stored": lossless(stored),
                "supportingBody": read.json(),
                "providerSessions": self.sessions,
            },
        )
