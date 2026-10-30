"""Owned native Mongo outage/topology boundaries and actual readiness cancellation."""

from __future__ import annotations

import asyncio
import json
import socket
from time import monotonic, sleep
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pymongo import MongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.errors import PyMongoError
from testcontainers.community.mongodb import MongoDbContainer

from ecommerce_store_payments.api.app import create_app
from tests.acceptance.checkout_recovery_checks import safe_problem
from tests.acceptance.evidence import AsyncEvidenceClient
from tests.acceptance.payment_checks import PaymentChecks, lossless
from tests.acceptance.technical_checks import MAIN, OTHER, HostResources, indexes, peer, populate, protocol, stored_read

if TYPE_CHECKING:
    from tests.acceptance.technical_scenarios import TechnicalChecks


class NativeMongoContainer(MongoDbContainer):
    def __init__(self, replica: bool) -> None:
        self.replica = replica
        cast(Any, super()).__init__("mongo:8.0")

    def _configure(self) -> None:
        self.with_command(["mongod", *(["--replSet", "rs0"] if self.replica else []), "--bind_ip_all"])

    def get_connection_url(self) -> str:
        return f"mongodb://{self.get_container_host_ip()}:{self.get_exposed_port(27017)}/?directConnection=true"


class OwnedMongo:
    def __init__(self, replica: bool) -> None:
        self.container = NativeMongoContainer(replica)
        self.replica = replica
        self.url = ""
        self.identity = ""
        self.events: list[dict[str, Any]] = []
        self.stopped = False

    def __enter__(self) -> OwnedMongo:
        # Docker can assign a new random host port when the same container restarts.
        # Bind an explicit available port before creation so existing clients recover
        # through the same real endpoint; Docker still owns the binding afterwards.
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
            self.container.with_bind_ports(27017, port)
        self.container.start()
        wrapped = self.container.get_wrapped_container()
        assert wrapped.client is not None
        wrapped.client.api.timeout = 15
        self.identity = cast(str, wrapped.id)
        self.url = self.container.get_connection_url()
        if self.replica:
            result = self.container.exec(
                ["mongosh", "--quiet", "--eval", "rs.initiate({_id:'rs0',members:[{_id:0,host:'localhost:27017'}]})"]
            )
            assert result.exit_code == 0
        self.wait_ready()
        self.events.append(
            {"event": "created", "containerId": self.identity, "endpoint": self.url, "replica": self.replica}
        )
        return self

    def wait_ready(self) -> None:
        client: MongoClient[dict[str, Any]] = MongoClient(self.url, serverSelectionTimeoutMS=500, connectTimeoutMS=500)
        try:
            deadline = monotonic() + 30
            while monotonic() < deadline:
                try:
                    hello = client.admin.command("hello")
                    if not self.replica or hello.get("isWritablePrimary"):
                        return
                except PyMongoError:
                    pass
                sleep(0.1)  # bounded owned-container startup polling, never winner selection
            raise AssertionError("Owned Mongo did not become ready")
        finally:
            client.close()

    def stop(self) -> None:
        assert not self.stopped
        self.container.get_wrapped_container().stop(timeout=5)
        self.stopped = True
        self.events.append({"event": "stopped", "containerId": self.identity, "endpoint": self.url})

    def restart(self) -> None:
        assert self.stopped
        self.container.get_wrapped_container().start()
        self.stopped = False
        assert self.container.get_wrapped_container().id == self.identity
        assert self.container.get_connection_url() == self.url
        self.wait_ready()
        self.events.append({"event": "restarted", "containerId": self.identity, "endpoint": self.url})

    def __exit__(self, *_: Any) -> None:
        self.container.stop()
        self.events.append({"event": "disposed", "containerId": self.identity})


def readiness_problem(path: str = "/health/ready", status: int = 503) -> dict[str, str]:
    return {
        "HTTPStatuses": str(status),
        "ContentType": "application/problem+json",
        "Code": "service_unavailable" if status == 503 else "internal_error",
        "JSON.type": '"about:blank"',
        "JSON.title": json.dumps("Service Unavailable" if status == 503 else "Internal Server Error"),
        "JSON.status": str(status),
        "JSON.detail": json.dumps(
            "Payment service is not ready." if status == 503 else "An unexpected error occurred."
        ),
        "JSON.instance": json.dumps(path),
        "JSON.errors": "[]",
        "JSON.missingProperties": "[]",
    }


class TechnicalMongo:
    def __init__(self, checks: TechnicalChecks, owned: OwnedMongo) -> None:
        self.checks, self.context, self.owned = checks, checks.context, owned
        assert owned.url != self.context.settings.mongodb_connection_string

    def run(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mode = self.checks.inputs["Mode"]
        if mode == "standalone":
            self.standalone(monkeypatch)
        elif mode == "cancel-readiness":
            self.cancel(monkeypatch)
        else:
            self.outage(monkeypatch)
        self.checks.details.update(
            ownedContainerId=self.owned.identity,
            ownedEndpoint=self.owned.url,
            sharedEndpoint=self.context.settings.mongodb_connection_string,
            containerEvents=self.owned.events,
        )

    def outage(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with peer(self.context, monkeypatch, url=self.owned.url, host="http://owned.test", retain_database=True) as (
            owned,
            resources,
        ):
            before = populate(owned, "owned outage")
            document = owned.client.get("/openapi.json")
            assert document.status_code == 200
            self.owned.stop()
            try:
                lives = [owned.client.get(p) for p in ["/health", "/health/live"]]
                for r in lives:
                    protocol(r, {"status": "healthy"})
                failed = owned.client.get("/health/ready")
                safe_problem(failed, readiness_problem())
                docs = owned.client.get("/openapi.json")
                assert docs.status_code == 200 and docs.content == document.content
                parent = self.context.client.get("/health/ready")
                protocol(parent, {"status": "healthy"})
            finally:
                self.owned.restart()
            recovered = owned.client.get("/health/ready")
            protocol(recovered, {"status": "healthy"})
            read, stored = stored_read(owned)
            after = PaymentChecks(owned).snapshot()
            assert before == after
            self.checks.details = {
                "before": lossless(before),
                "after": lossless(after),
                "database": owned.settings.mongodb_database_name,
                "indexes": indexes(owned),
                "documentationSha256": __import__("hashlib").sha256(docs.content).hexdigest(),
                "problemExpected": readiness_problem(),
                "body": read.json(),
                "stored": lossless(stored),
                "exchangeIds": [
                    document.extensions["payments.bdd.exchangeId"],
                    *[r.extensions["payments.bdd.exchangeId"] for r in lives],
                    failed.extensions["payments.bdd.exchangeId"],
                    docs.extensions["payments.bdd.exchangeId"],
                    parent.extensions["payments.bdd.exchangeId"],
                    recovered.extensions["payments.bdd.exchangeId"],
                    read.extensions["payments.bdd.exchangeId"],
                ],
            }
            self.checks.primary = failed
            self.checks.result = "observed"
        self.checks.details["resources"] = resources.closed()

    def standalone(self, monkeypatch: pytest.MonkeyPatch) -> None:
        assert not self.owned.replica
        with peer(
            self.context, monkeypatch, url=self.owned.url, host="http://standalone.test", retain_database=True
        ) as (owned, resources):
            orders = owned.orders
            for oid, amount in [(OTHER, "31.73"), (MAIN, "12.99")]:
                from decimal import Decimal

                orders.order_id, orders.amount = oid, Decimal(amount)
                response = owned.client.post(f"/payments/{oid}/pay")
                assert response.status_code == 201
            orders.order_id = MAIN
            before = PaymentChecks(owned).snapshot()
            assert [len(before[k]) for k in ["payments", "payment_history", "stripe_webhooks"]] == [2, 0, 0]
            hello = owned.mongo.admin.command("hello")
            assert "setName" not in hello and hello.get("msg") != "isdbgrid"
            ready = owned.client.get("/health/ready")
            protocol(ready, {"status": "healthy"})
            failed = owned.client.post(f"/payments/{MAIN}/checkout")
            expected = readiness_problem(f"/payments/{MAIN}/checkout", 500)
            safe_problem(failed, expected)
            after = PaymentChecks(owned).snapshot()
            assert after == before and not owned.stripe.calls
            read, stored = stored_read(owned)
            self.checks.details = {
                "hello": lossless(hello),
                "before": lossless(before),
                "after": lossless(after),
                "database": owned.settings.mongodb_database_name,
                "indexes": indexes(owned),
                "transactionProblemExpected": expected,
                "body": read.json(),
                "stored": lossless(stored),
                "exchangeIds": [
                    ready.extensions["payments.bdd.exchangeId"],
                    failed.extensions["payments.bdd.exchangeId"],
                    read.extensions["payments.bdd.exchangeId"],
                ],
            }
            self.checks.primary = ready
            self.checks.result = "observed"
        self.checks.details["resources"] = resources.closed()

    def cancel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        name = f"payments_technical_cancel_{uuid4().hex}"
        with peer(
            self.context,
            monkeypatch,
            url=self.owned.url,
            name=name,
            host="http://cancel-setup.test",
            retain_database=True,
        ) as (setup, setup_resources):
            before = populate(setup, "owned cancellation")
            settings = setup.settings
        async_resources = HostResources(self.context)
        entered = asyncio.Event()
        events: list[dict[str, Any]] = []

        async def exercise() -> dict[str, Any]:
            with async_resources.install(settings, monkeypatch):
                app = create_app(settings)
                async with app.router.lifespan_context(app):
                    database = app.state.database
                    original = AsyncDatabase[Any].command

                    async def command(db: Any, *args: Any, **kwargs: Any) -> Any:
                        if db.client is database.client and args[0] == "ping":
                            events.append({"event": "driver-await-entered", "command": "ping"})
                            entered.set()
                            try:
                                return await original(db, *args, **kwargs)
                            except asyncio.CancelledError:
                                events.append({"event": "driver-cancelled", "command": "ping"})
                                raise
                        return await original(db, *args, **kwargs)

                    async with AsyncClient(base_url="http://cancelled.test", transport=ASGITransport(app=app)) as raw:
                        client = AsyncEvidenceClient(raw, self.context.evidence)
                        self.owned.stop()
                        # Let a real failed command invalidate the stopped server's pooled connection.
                        # The cancelled request then awaits actual server selection, not an injected sleep.
                        try:
                            await database.probe()
                        except (PyMongoError, TimeoutError) as error:
                            warm_down = type(error).__name__
                        else:
                            raise AssertionError("Stopped owned Mongo unexpectedly answered its probe")
                        with monkeypatch.context() as patch:
                            patch.setattr(AsyncDatabase, "command", command)
                            task = asyncio.create_task(client.request("GET", "/health/ready"))
                            try:
                                await asyncio.wait_for(entered.wait(), 10)
                                task.cancel()
                                with pytest.raises(asyncio.CancelledError):
                                    await task
                            finally:
                                if not task.done():
                                    task.cancel()
                                await asyncio.gather(task, return_exceptions=True)
                        self.checks.failure_id = client.cancelled_exchange_id
                        assert events == [
                            {"event": "driver-await-entered", "command": "ping"},
                            {"event": "driver-cancelled", "command": "ping"},
                        ]
                        self.owned.restart()
                        recovered = await client.request("GET", "/health/ready")
                        protocol(recovered, {"status": "healthy"})
                        live = await client.request("GET", "/health/live")
                        protocol(live, {"status": "healthy"})
                    assert raw.is_closed
                return {
                    "recoveredExchangeIds": [
                        recovered.extensions["payments.bdd.exchangeId"],
                        live.extensions["payments.bdd.exchangeId"],
                    ],
                    "asyncClientClosed": raw.is_closed,
                    "warmDownException": warm_down,
                }

        try:
            recovery = asyncio.run(exercise())
        finally:
            if self.owned.stopped:
                self.owned.restart()
        # An independent actual client verifies all stored fields survived the cancelled driver call.
        client: MongoClient[dict[str, Any]] = MongoClient(self.owned.url, uuidRepresentation="standard", tz_aware=True)
        try:
            after = {
                key: sorted([dict(d) for d in client[name][key].find({})], key=lambda d: str(d["_id"]))
                for key in before
            }
        finally:
            client.close()
        assert after == before
        self.checks.result = "cancelled"
        self.checks.exception = "CancelledError"
        self.checks.details = {
            "database": name,
            "before": lossless(before),
            "after": lossless(after),
            "driverEvents": events,
            "setupResources": setup_resources.closed(),
            "asyncResources": async_resources.closed(),
            **recovery,
        }
