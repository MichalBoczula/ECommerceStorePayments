"""Technical actions are evidence of real operations, not fabricated API outcomes."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from time import monotonic
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.testclient import TestClient
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.infrastructure.config.settings import Settings
from tests.acceptance.payment_checks import PaymentChecks, Snapshot, lossless
from tests.acceptance.technical_checks import HostResources, indexes, peer, populate, protocol, stored_read


class TechnicalChecks:
    def __init__(self, payments: PaymentChecks) -> None:
        self.payments, self.context = payments, payments.context
        self.inputs: dict[str, str] = {}
        self.before: Snapshot = {}
        self.after: Snapshot = {}
        self.primary: Any = None
        self.failure_id: str | None = None
        self.action_id: str | None = None
        self.result = ""
        self.exception = "<none>"
        self.details: dict[str, Any] = {}
        self.command: Any = None

    def configure(self, values: dict[str, str]) -> None:
        assert values.keys() == {"Mode", "Target", "Value"}
        assert values["Mode"] in {
            "docs",
            "offline-docs",
            "outage",
            "standalone",
            "cancel-readiness",
            "cancel-worker",
            "isolation",
            "startup",
            "limits",
            "batch",
        }
        self.inputs = values
        self.context.evidence.observation("Technical scenario inputs", values)

    def ready(self, values: dict[str, str]) -> None:
        assert self.inputs and values.keys() == {"Payments", "History", "Receipts"}
        populate(self.context, "primary")
        if self.inputs["Mode"] in {"cancel-worker", "batch"}:
            from tests.acceptance.technical_commands import TechnicalCommands

            self.command = TechnicalCommands(self)
            self.command.prepare()
        self.before = self.payments.snapshot()
        assert [len(self.before[k]) for k in ["payments", "payment_history", "stripe_webhooks"]] == [
            int(values[k]) for k in ["Payments", "History", "Receipts"]
        ]
        self.context.evidence.observation(
            "Technical operation baseline",
            {
                "expected": values,
                "collections": lossless(self.before),
                "indexes": indexes(self.context),
                "providerSessions": deepcopy(self.context.stripe.sessions),
                "database": self.context.settings.mongodb_database_name,
            },
        )

    def run(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, owned: Any = None) -> None:
        with self.context.evidence.action("Run explicit technical scenario", self.inputs) as output:
            self.action_id = self.context.evidence.active_action_id
            mode = self.inputs["Mode"]
            if mode == "docs":
                self.docs()
            elif mode == "offline-docs":
                self.offline(monkeypatch, tmp_path)
            elif mode == "isolation":
                self.isolation(monkeypatch)
            elif mode == "startup":
                self.startup(monkeypatch)
            elif mode in {"outage", "standalone", "cancel-readiness"}:
                from tests.acceptance.technical_mongo import TechnicalMongo

                TechnicalMongo(self, owned).run(monkeypatch)
            else:
                if self.command is None:
                    from tests.acceptance.technical_commands import TechnicalCommands

                    self.command = TechnicalCommands(self)
                self.command.run(monkeypatch)
            self.after = self.payments.snapshot()
            if mode not in {"batch", "cancel-worker"}:
                assert self.after == self.before
            output.update(
                result=self.result,
                exceptionType=self.exception,
                details=self.details,
                before=lossless(self.before),
                after=lossless(self.after),
                failureExchangeId=self.failure_id,
            )
        self.context.evidence.observation(
            "Complete technical scenario",
            {
                "inputs": self.inputs,
                "result": self.result,
                "exceptionType": self.exception,
                "before": lossless(self.before),
                "after": lossless(self.after),
                "actionId": self.action_id,
                "failureExchangeId": self.failure_id,
                "primaryExchangeId": self.primary.extensions["payments.bdd.exchangeId"]
                if self.primary is not None
                else None,
                "details": self.details,
            },
        )

    def expected(self, values: dict[str, str]) -> None:
        assert values["Result"] == self.result
        assert self.exception in values["ExceptionType"].split(",")
        kind = values["Outcome"]
        if kind == "response":
            assert self.primary is not None and self.primary.status_code == int(values["HTTPStatuses"])
            assert self.primary.headers["content-type"] == values["ContentType"]
            body = (
                self.primary.json()
                if values["ContentType"] == "application/json" or values["ContentType"] == "application/problem+json"
                else self.primary.content
            )
            for k, v in values.items():
                if k.startswith("JSON."):
                    actual = body
                    for part in k[5:].split("."):
                        actual = actual[part]
                    assert type(actual) is type(json.loads(v)) and actual == json.loads(v)
            exchange_ids = [self.primary.extensions["payments.bdd.exchangeId"]]
            action_ids = []
        elif kind == "cancelled":
            assert self.failure_id is not None and self.primary is None and self.exception == "CancelledError"
            assert values["HTTPStatuses"] == values["ContentType"] == "<none>"
            exchange_ids = [self.failure_id]
            action_ids = [self.action_id]
        else:
            assert kind == "action" and self.primary is None and self.failure_id is None
            assert values["HTTPStatuses"] == values["ContentType"] == "<none>"
            exchange_ids = []
            action_ids = [self.action_id]
        self.context.evidence.record(
            "Expected technical outcome",
            {
                **self.context.evidence.identity,
                "stepPhase": self.context.evidence.phase,
                "value": values,
                "exchangeIds": exchange_ids,
                "actionIds": action_ids,
            },
        )

    def support(self, values: dict[str, str]) -> None:
        assert values == {"Collections": "unchanged", "OrdersCalls": "0", "StripeCalls": "0"}
        before = self.payments.snapshot()
        calls = len(self.context.orders.http_calls), len(self.context.stripe.calls)
        read, stored = stored_read(self.context)
        ready = self.context.client.get("/health/ready")
        protocol(ready, {"status": "healthy"})
        assert self.payments.snapshot() == before == self.after
        assert calls == (len(self.context.orders.http_calls), len(self.context.stripe.calls))
        self.context.evidence.observation(
            "Technical supporting reads preserve final state",
            {
                "expected": values,
                "collections": lossless(before),
                "body": read.json(),
                "stored": lossless(stored),
                "exchangeIds": [
                    read.extensions["payments.bdd.exchangeId"],
                    ready.extensions["payments.bdd.exchangeId"],
                ],
            },
        )

    def docs(self) -> None:
        app = cast(FastAPI, self.context.client.app)
        path = self.inputs["Target"]
        if path == "/swagger":
            source = get_swagger_ui_html(
                openapi_url=cast(str, app.openapi_url),
                title=app.title + " - Swagger UI",
                oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
                init_oauth=app.swagger_ui_init_oauth,
                swagger_ui_parameters=app.swagger_ui_parameters,
            ).body
        elif path == "/redoc":
            source = get_redoc_html(openapi_url=cast(str, app.openapi_url), title=app.title + " - ReDoc").body
        else:
            assert path == "/docs/oauth2-redirect"
            source = get_swagger_ui_oauth2_redirect_html().body
        responses = [self.context.client.get(path) for _ in range(2)]
        for response in responses:
            protocol(response, bytes(source), "text/html; charset=utf-8")
        assert (
            responses[0].content == responses[1].content
            and responses[0].headers["x-trace-id"] != responses[1].headers["x-trace-id"]
        )
        self.primary = responses[0]
        self.result = "rendered"
        self.details = {
            "path": path,
            "sourceUtf8": bytes(source).decode(),
            "sha256": hashlib.sha256(bytes(source)).hexdigest(),
            "exchangeIds": [r.extensions["payments.bdd.exchangeId"] for r in responses],
            "openapiReference": app.openapi_url if path in {"/swagger", "/redoc"} else "<none>",
        }

    def offline(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        from scripts.openapi_contract import export

        from tests.acceptance.evidence import EvidenceClient

        allocations: list[str] = []

        def forbidden(_: Settings) -> Any:
            allocations.append("database")
            raise AssertionError("Cold documentation allocated a database client")

        with monkeypatch.context() as patch:
            patch.setattr("ecommerce_store_payments.api.app.MongoDatabase", forbidden)
            app = create_app(
                self.context.settings.model_copy(update={"mongodb_connection_string": "mongodb://127.0.0.1:1"})
            )
            # No lifespan is entered; real documentation routes need no serving database.
            raw = TestClient(app, base_url="http://cold-docs.test")
            try:
                client = EvidenceClient(raw, self.context.evidence)
                response = client.get("/openapi.json")
                protocol(response, app.openapi())
                again = client.get("/openapi.json")
                protocol(again, app.openapi())
                assert response.content == again.content
                exported = tmp_path / "openapi.json"
                result = export(exported)
                assert response.json() == json.loads(exported.read_text())
                docs = [client.get(path) for path in ["/swagger", "/redoc"]]
                assert all(r.status_code == 200 and "/openapi.json" in r.text for r in docs)
            finally:
                raw.close()
        assert not allocations and raw.is_closed
        self.primary = response
        self.result = "rendered"
        self.details = {
            "coldHost": "cold-docs.test",
            "lifespanEntered": False,
            "allocations": allocations,
            "clientClosed": raw.is_closed,
            "exportResult": list(result),
            "exports": {p.name: json.loads(p.read_text()) for p in tmp_path.glob("*.json")},
            "exchangeIds": [r.extensions["payments.bdd.exchangeId"] for r in [response, again, *docs]],
        }

    def isolation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        with peer(self.context, monkeypatch) as (other, resources):
            peer_before = populate(other, "peer", main_amount="20.99", other_amount="50.01")
            main_read, main_stored = stored_read(self.context)
            peer_read, peer_stored = stored_read(other)
            assert (
                main_stored["order_id"] == peer_stored["order_id"]
                and main_stored["amount_minor"] == 1299
                and peer_stored["amount_minor"] == 2099
            )
            assert main_stored["_id"] != peer_stored["_id"]
            assert self.payments.snapshot() == self.before
            assert PaymentChecks(other).snapshot() == peer_before
            name = other.settings.mongodb_database_name
            self.details = {
                "primaryDatabase": self.context.settings.mongodb_database_name,
                "peerDatabase": name,
                "peerBefore": lossless(peer_before),
                "primaryBody": main_read.json(),
                "peerBody": peer_read.json(),
                "primaryStored": lossless(main_stored),
                "peerStored": lossless(peer_stored),
                "exchangeIds": [
                    main_read.extensions["payments.bdd.exchangeId"],
                    peer_read.extensions["payments.bdd.exchangeId"],
                ],
            }
        assert name not in self.context.mongo.list_database_names()
        assert self.context.settings.mongodb_database_name in self.context.mongo.list_database_names()
        self.details.update(resources=resources.closed(), peerDatabaseDropped=True)
        self.result = "isolated"

    def startup(self, monkeypatch: pytest.MonkeyPatch) -> None:
        variant = self.inputs["Value"]
        assert variant in {"index-conflict", "duplicate-order", "unreachable"}
        name = f"payments_technical_startup_{uuid4().hex}"
        settings = self.context.settings.model_copy(update={"mongodb_database_name": name})
        database = cast(Any, self.context.mongo[name])
        duplicate: dict[str, Any] | None = None
        if variant != "unreachable":
            for collection, docs in self.before.items():
                database[collection].insert_many(deepcopy(docs))
            if variant == "index-conflict":
                database["payments"].create_index("order_id", unique=False, name="ux_payments_order_id")
            else:
                duplicate = deepcopy(self.payments.target(self.before))
                assert duplicate is not None
                duplicate["_id"] = uuid4()
                database["payments"].insert_one(duplicate)
            fixture = {n: list(database[n].find({})) for n in self.before}
        else:
            settings = settings.model_copy(
                update={
                    "mongodb_connection_string": "mongodb://127.0.0.1:1",
                    "mongodb_probe_timeout_seconds": 0.2,
                    "mongodb_server_selection_timeout_ms": 100,
                }
            )
            fixture = {}
        resources = HostResources(self.context)
        started = monotonic()
        host_yielded = False
        try:
            with resources.install(settings, monkeypatch):
                try:
                    with TestClient(create_app(settings)):
                        host_yielded = True
                except (OperationFailure, TimeoutError, ServerSelectionTimeoutError) as error:
                    self.exception = type(error).__name__
                    self.result = "rejected"
                    failure = {"exceptionType": self.exception, "driverCode": getattr(error, "code", None)}
                else:
                    raise AssertionError("Invalid startup unexpectedly served a host")
            assert not host_yielded
            elapsed = monotonic() - started
            if variant == "unreachable":
                assert elapsed < 2
            closed_failure = resources.closed()
            if variant != "unreachable":
                failed = {n: list(database[n].find({})) for n in self.before}
                assert lossless(failed) == lossless(fixture)
                if variant == "index-conflict":
                    database["payments"].drop_index("ux_payments_order_id")
                else:
                    assert duplicate is not None
                    assert database["payments"].delete_one({"_id": duplicate["_id"]}).deleted_count == 1
                with peer(self.context, monkeypatch, name=name, host="http://repaired.test", retain_database=True) as (
                    repaired,
                    recovery_resources,
                ):
                    repaired_snapshot = PaymentChecks(repaired).snapshot()
                    assert repaired_snapshot == self.before
                    response = repaired.client.get("/health/ready")
                    protocol(response, {"status": "healthy"})
                    body, stored = stored_read(repaired)
                    recovery = {
                        "collections": lossless(repaired_snapshot),
                        "indexes": indexes(repaired),
                        "body": body.json(),
                        "stored": lossless(stored),
                        "exchangeIds": [
                            response.extensions["payments.bdd.exchangeId"],
                            body.extensions["payments.bdd.exchangeId"],
                        ],
                    }
                recovery["resources"] = recovery_resources.closed()
            else:
                failed = {}
                recovery = None
            self.details = {
                "variant": variant,
                "hostYielded": host_yielded,
                "elapsedSeconds": elapsed,
                "failure": failure,
                "failureResources": closed_failure,
                "fixture": lossless(fixture),
                "afterFailure": lossless(failed),
                "recovery": recovery,
                "candidateDatabase": name,
            }
        finally:
            self.context.mongo.drop_database(name)
