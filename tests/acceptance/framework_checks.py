"""Actual framework requests, explicit failure boundaries and full populated-state proof."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, NoReturn, cast
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import FastAPI
from httpx2 import Response

from ecommerce_store_payments.api.routes import health
from tests.acceptance.business_validation_checks import safe_problem
from tests.acceptance.payment_checks import PaymentChecks, Snapshot, lossless
from tests.webhook_fixtures import signature

if TYPE_CHECKING:
    import pytest

REQUEST_FIELDS = {"Method", "Path", "BodyKind", "BodyValue", "ContentType", "TraceHeader", "Signature"}
FAILURE_MESSAGE = "private controlled framework fixture failure"


def request_body(values: dict[str, str]) -> bytes | None:
    assert values.keys() == REQUEST_FIELDS
    assert values["Method"] in {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}
    assert values["Path"].startswith("/") and not values["Path"].startswith("//")
    kind, value = values["BodyKind"], values["BodyValue"]
    if kind in {"none", "empty"}:
        assert value == "<empty>"
        return None if kind == "none" else b""
    if kind == "text":
        return value.encode()
    if kind == "hex":
        return bytes.fromhex(value)
    if kind == "repeat":
        spec = json.loads(value)
        assert spec.keys() == {"Token", "Count"} and type(spec["Count"]) is int and 0 < spec["Count"] <= 65537
        assert isinstance(spec["Token"], str) and len(spec["Token"].encode()) == 1
        return spec["Token"].encode() * spec["Count"]
    assert kind == "json-padding"
    length = int(value)
    assert 2 <= length <= 65537
    return b'"' + b"a" * (length - 2) + b'"'


def framework_protocol(response: Response, expected: dict[str, str], allow: str) -> None:
    safe_problem(response, expected)
    assert response.headers.get("allow") == (None if allow == "<absent>" else allow)
    assert response.headers["content-length"] == str(len(response.content))
    incoming = response.request.headers.get("x-trace-id")
    assert response.json()["traceId"] != incoming


class FrameworkChecks:
    def __init__(self, checks: PaymentChecks) -> None:
        self.checks, self.context = checks, checks.context
        self.inputs: dict[str, str] | None = None
        self.body: bytes | None = None
        self.before: Snapshot | None = None
        self.calls: tuple[int, int] | None = None
        self.sessions: dict[str, Any] = {}
        self.fault_point: str | None = None
        self.hits: list[dict[str, Any]] = []

    def prepare(self, values: dict[str, str]) -> None:
        self.body = request_body(values)
        assert values["Signature"] in {"valid", "absent"}
        self.inputs = deepcopy(values)
        self.context.evidence.observation(
            "Framework request inputs",
            {
                "expected": values,
                "bodyBytesHex": (self.body or b"").hex(),
                "byteLength": len(self.body or b""),
                "sha256": hashlib.sha256(self.body or b"").hexdigest(),
            },
        )

    def once(self) -> Response:
        assert self.inputs is not None
        values = self.inputs
        headers: dict[str, str] = {}
        if values["ContentType"] != "<absent>":
            headers["content-type"] = values["ContentType"]
        if values["TraceHeader"] != "<absent>":
            headers["x-trace-id"] = values["TraceHeader"]
        if values["Signature"] == "valid":
            headers["stripe-signature"] = signature(self.body or b"")
        path = values["Path"].replace("{order_id}", str(self.context.orders.order_id))
        return self.context.client.request(values["Method"], path, content=self.body, headers=headers)

    def send(self) -> None:
        assert self.inputs is not None
        started = datetime.now(UTC)
        response = self.once()
        self.context.responses = [response]
        self.context.request_window = started, datetime.now(UTC)
        self.context.last_operation = self.inputs["Method"] + " " + urlsplit(self.inputs["Path"]).path

    def remember(self) -> None:
        self.checks.remember("Framework collections before")
        assert self.checks.before is not None and all(self.checks.before.values())
        self.before = deepcopy(self.checks.before)
        self.calls = len(self.context.orders.http_calls), len(self.context.stripe.calls)
        self.sessions = deepcopy(self.context.stripe.sessions)

    def install_fault(self, values: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
        assert values.keys() == {"Point", "Exception"} and values["Exception"] == "RuntimeError"
        assert self.before is not None
        point = values["Point"]
        self.fault_point = point
        app = cast(FastAPI, self.context.client.app)

        def fail(details: dict[str, Any]) -> NoReturn:
            self.hits.append({"point": point, **details})
            raise RuntimeError(FAILURE_MESSAGE)

        with self.context.evidence.action("Install explicit framework failure boundary", values) as output:
            if point == "HealthResponse":
                original = health.HealthResponse

                def health_failure(*, status: Any) -> NoReturn:
                    built = original(status=status)
                    fail({"constructedStatus": built.status})

                monkeypatch.setattr(health, "HealthResponse", health_failure)
            elif point == "MongoDatabase.probe":
                probe = app.state.database.probe

                async def readiness_failure() -> NoReturn:
                    await probe()
                    fail({"realProbeCompleted": True})

                monkeypatch.setattr(app.state.database, "probe", readiness_failure)
            elif point == "StripeWebhookVerifier.verify":
                verifier = app.state.webhook_service._verifier
                verify = verifier.verify

                def verified_failure(payload: bytes, signature_header: str) -> NoReturn:
                    event = verify(payload, signature_header)
                    fail({"verifiedEventId": event.event_id, "bodySha256": hashlib.sha256(payload).hexdigest()})

                monkeypatch.setattr(verifier, "verify", verified_failure)
            else:
                assert point in {"PaymentService.pay", "PaymentService.checkout", "PaymentService.get_by_order_id"}

                async def service_failure(order_id: UUID) -> NoReturn:
                    assert order_id == self.context.orders.order_id
                    fail({"orderId": str(order_id)})

                monkeypatch.setattr(app.state.payment_service, point.split(".")[1], service_failure)
            output["installed"] = True
            output["point"] = point

    def rejected(self, expected: dict[str, str], effects: dict[str, str]) -> None:
        assert effects == {
            "Payments": "2",
            "History": "5",
            "Receipts": "1",
            "TargetStatus": "pending",
            "OrdersCalls": "0",
            "StripeCalls": "0",
            "ProviderSessions": "unchanged",
            "Repeat": "true",
            "Allow": effects["Allow"],
            "FaultHits": "2" if self.fault_point else "0",
        }
        assert self.before is not None and self.calls is not None and self.inputs is not None
        assert [len(self.before[name]) for name in ("payments", "payment_history", "stripe_webhooks")] == [2, 5, 1]
        target = self.checks.target(self.before)
        assert target is not None and target["status"] == "pending" and target["version"] == 2
        first = self.context.responses[0]
        framework_protocol(first, expected, effects["Allow"])
        self.wire(first)
        after_first = self.checks.snapshot()
        self._unchanged(after_first)
        repeated = self.once()
        framework_protocol(repeated, expected, effects["Allow"])
        self.wire(repeated)
        assert first.json()["traceId"] != repeated.json()["traceId"]
        after_repeat = self.checks.snapshot()
        self._unchanged(after_repeat)
        assert len(self.hits) == int(effects["FaultHits"])
        self.context.evidence.observation(
            "Complete framework rejection and state",
            {
                "expected": effects,
                "problemExpected": expected,
                "inputs": self.inputs,
                "before": lossless(self.before),
                "afterFirst": lossless(after_first),
                "afterRepeated": lossless(after_repeat),
                "providerSessionsBefore": self.sessions,
                "providerSessionsAfter": self.context.stripe.sessions,
                "externalCallsBefore": self.calls,
                "externalCallsAfter": self.calls,
                "exchangeIds": [r.extensions["payments.bdd.exchangeId"] for r in (first, repeated)],
                "faultPoint": self.fault_point,
                "faultHits": self.hits,
            },
        )

    def _unchanged(self, after: Snapshot) -> None:
        assert after == self.before, "Every field in both populated payments, history and receipts must survive"
        assert (len(self.context.orders.http_calls), len(self.context.stripe.calls)) == self.calls
        assert self.context.stripe.sessions == self.sessions

    def wire(self, response: Response) -> None:
        assert self.inputs is not None
        assert response.request.method == self.inputs["Method"]
        assert (
            response.request.url.path
            == urlsplit(self.inputs["Path"].replace("{order_id}", str(self.context.orders.order_id))).path
        )
        assert response.request.url.query.decode() == urlsplit(self.inputs["Path"]).query
        assert response.request.content == (self.body or b"")
        assert response.request.headers.get("content-type") == (
            None if self.inputs["ContentType"] == "<absent>" else self.inputs["ContentType"]
        )
        assert response.request.headers.get("x-trace-id") == (
            None if self.inputs["TraceHeader"] == "<absent>" else self.inputs["TraceHeader"]
        )
        actual_signature = response.request.headers.get("stripe-signature")
        if self.inputs["Signature"] == "valid":
            assert actual_signature is not None
            timestamp = int(actual_signature.split(",")[0].removeprefix("t="))
            assert actual_signature == signature(response.request.content, timestamp=timestamp)
        else:
            assert actual_signature is None

    def accepted(self, expected: dict[str, str]) -> None:
        assert expected.keys() == {"BodyBytes", "OrdersCalls", "StripeCalls", "ResultStatus"}
        assert self.before is not None and self.calls is not None
        response = self.context.responses[0]
        self.wire(response)
        assert len(response.request.content) == int(expected["BodyBytes"])
        assert (len(self.context.orders.http_calls), len(self.context.stripe.calls)) == (
            self.calls[0] + int(expected["OrdersCalls"]),
            self.calls[1] + int(expected["StripeCalls"]),
        )
        after = self.checks.snapshot()
        target = self.checks.target(after)
        assert target is not None and target["status"] == expected["ResultStatus"]
        self.context.evidence.observation(
            "Accepted framework input and state",
            {
                "expected": expected,
                "inputs": self.inputs,
                "before": lossless(self.before),
                "after": lossless(after),
                "stored": lossless(target),
                "exchangeId": response.extensions["payments.bdd.exchangeId"],
            },
        )
