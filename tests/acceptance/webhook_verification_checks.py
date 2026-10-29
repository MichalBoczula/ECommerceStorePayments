"""Signed-wire, verification-boundary and populated-state BDD evidence."""

from __future__ import annotations

import hashlib
import hmac
import importlib
import json
import re
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper
from tests.acceptance.payment_checks import PaymentChecks, lossless
from tests.acceptance.retry_checks import milliseconds
from tests.webhook_fixtures import WEBHOOK_SECRET, payload_for, signature

WIRE_INPUTS = {
    "EventType",
    "PayloadVariant",
    "MutationPath",
    "MutationValue",
    "SignatureMode",
    "TimestampOffsetSeconds",
    "ContentType",
    "BodyBytes",
}
WIRE_EXPECTED = {"SignatureHeaders", "MatchingV1Signatures", "BodyBytes", "SignedBytesEqual", "TimestampOffsetSeconds"}
UNKNOWN_RECEIPT_FIELDS = {
    "_id",
    "event_type",
    "payload_digest",
    "outcome",
    "payment_id",
    "order_id",
    "attempt_id",
    "amount_minor",
    "currency",
    "session_id",
    "provider_payment_id",
    "state",
    "reason",
    "received_at",
    "completed_at",
    "fulfillment_status",
}


@dataclass(frozen=True)
class WebhookWire:
    body: bytes
    signed_body: bytes
    headers: tuple[tuple[str, str], ...]
    verification_time: int
    event: dict[str, Any]


def prepare_wire(base: dict[str, Any], values: dict[str, str], verification_time: int) -> WebhookWire:
    assert values.keys() == WIRE_INPUTS
    payload = deepcopy(base)
    payload["type"] = values["EventType"]
    if values["MutationPath"] != "-":
        *parts, field = values["MutationPath"].split(".")
        parent = payload
        for part in parts:
            parent = parent[part]
        if values["MutationValue"] == "{omit}":
            del parent[field]
        else:
            parent[field] = json.loads(values["MutationValue"])
    else:
        assert values["MutationValue"] == "-"
    variant = values["PayloadVariant"]
    if variant == "unicode":
        payload["note"] = "Zażółć gęślą jaźń 🧾"
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    body = text.encode()
    if variant == "malformed_json":
        body = b'{"private":'
    elif variant == "duplicate_event_id":
        token = '"id":' + json.dumps(payload["id"])
        assert text.count(token) == 1
        body = text.replace(token, token + "," + token, 1).encode()
    elif variant == "duplicate_metadata":
        token = '"payment_id":' + json.dumps(payload["data"]["object"]["metadata"]["payment_id"])
        assert text.count(token) == 1
        body = text.replace(token, token + "," + token, 1).encode()
    elif variant == "invalid_utf8":
        body += b"\xff"
    elif variant == "array":
        body = b"[" + body + b"]"
    elif variant == "null":
        body = b"null"
    elif variant == "empty":
        body = b""
    else:
        assert variant in {"normal", "reencoded", "unicode"}
    if values["BodyBytes"] != "natural":
        length = int(values["BodyBytes"])
        assert length >= len(body)
        body += b" " * (length - len(body))
    signed_body = body
    timestamp = verification_time + int(values["TimestampOffsetSeconds"])
    mode = values["SignatureMode"]
    header = signature(signed_body, timestamp=timestamp)
    if mode == "wrong_secret":
        header = signature(signed_body, secret="whsec_wrong_fixture", timestamp=timestamp)
    elif mode == "empty":
        header = ""
    elif mode == "malformed_timestamp":
        header = header.replace(f"t={timestamp}", "t=not-an-integer", 1)
    elif mode == "no_v1":
        header = header.replace("v1=", "v0=", 1)
    elif mode == "bad_v1":
        header = f"t={timestamp},v1={'0' * 64}"
    elif mode == "multiple_v1":
        header = header.replace(",v1=", f",v1={'0' * 64},v1=", 1)
    elif mode == "tampered":
        body += b" "
    else:
        assert mode in {"correct", "missing", "duplicate_headers"}
    if variant == "reencoded":
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode()
        assert body != signed_body and json.loads(body) == json.loads(signed_body)
    headers: list[tuple[str, str]] = []
    if values["ContentType"] != "absent":
        headers.append(("content-type", values["ContentType"]))
    if mode != "missing":
        headers.append(("stripe-signature", header))
    if mode == "duplicate_headers":
        headers.append(("stripe-signature", header))
    return WebhookWire(body, signed_body, tuple(headers), verification_time, payload)


def wire_analysis(body: bytes, header_items: list[tuple[str, str]], verification_time: int) -> dict[str, Any]:
    headers = [value for key, value in header_items if key.lower() == "stripe-signature"]
    matches = 0
    timestamps: list[int] = []
    for header in headers:
        pairs = [part.split("=", 1) for part in header.split(",")]
        try:
            stamp = int(next(pair[1] for pair in pairs if len(pair) == 2 and pair[0] == "t"))
        except ValueError, StopIteration:
            continue
        timestamps.append(stamp)
        expected = hmac.new(WEBHOOK_SECRET.encode(), str(stamp).encode() + b"." + body, hashlib.sha256).hexdigest()
        matches += sum(hmac.compare_digest(pair[1], expected) for pair in pairs if len(pair) == 2 and pair[0] == "v1")
    offsets = {stamp - verification_time for stamp in timestamps}
    return {
        "SignatureHeaders": len(headers),
        "MatchingV1Signatures": matches,
        "BodyBytes": len(body),
        "TimestampOffsetSeconds": str(next(iter(offsets))) if len(offsets) == 1 else "unparseable",
    }


class WebhookVerificationChecks:
    def __init__(self, payments: PaymentChecks) -> None:
        self.payments, self.context = payments, payments.context
        self.wire: WebhookWire | None = None
        self.inputs: dict[str, str] | None = None
        self.before_sessions: dict[str, dict[str, Any]] | None = None

    def prepare(self, values: dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
        context = self.context
        stored = self.payments.target(self.payments.snapshot())
        assert stored is not None
        base = (
            json.loads(context.webhook_payload)
            if context.webhook_payload
            else payload_for(
                PaymentMapper.to_domain(cast(PaymentDocument, stored)),
                event_id="evt_" + str(context.evidence.identity["scenarioId"]).lower().replace("-", "_"),
            )
        )
        mode = context.webhook_delivery
        if mode == "missing":
            assert values["SignatureMode"] == "missing"
        elif mode == "tampered":
            assert values["SignatureMode"] == "tampered"
        elif mode == "media":
            assert values["ContentType"] == "text/plain"
        elif mode == "large":
            assert values["BodyBytes"] == "1048577"
        elif mode == "disabled":
            assert context.settings.stripe_webhook_secret is None
        self.inputs = values.copy()
        self.wire = prepare_wire(base, values, int(time.time()))
        # Only Stripe's timestamp comparison observes this clock; real signature verification still runs.
        monkeypatch.setattr(
            importlib.import_module("stripe._webhook"),
            "time",
            SimpleNamespace(time=lambda: self.wire.verification_time if self.wire else 0),
        )
        context.evidence.observation(
            "Webhook verification inputs",
            {
                "expected": values,
                "verificationTime": self.wire.verification_time,
                "signedByteLength": len(self.wire.signed_body),
                "signedSha256": hashlib.sha256(self.wire.signed_body).hexdigest(),
                "deliveredByteLength": len(self.wire.body),
                "deliveredSha256": hashlib.sha256(self.wire.body).hexdigest(),
            },
        )

    def remember(self) -> None:
        self.payments.remember()
        self.before_sessions = deepcopy(self.context.stripe.sessions)

    def deliver(self) -> None:
        assert self.wire is not None
        context = self.context
        started = datetime.now(UTC)
        context.responses = [
            context.client.post("/payments/webhooks/stripe", content=self.wire.body, headers=list(self.wire.headers))
        ]
        context.request_window = started, datetime.now(UTC)
        context.last_operation = "POST /payments/webhooks/stripe"

    def wire_evidence(self, authored: dict[str, str]) -> None:
        assert authored.keys() == WIRE_EXPECTED and self.wire is not None
        response = self.context.responses[0]
        request = response.request
        assert request.method == "POST" and request.url.path == "/payments/webhooks/stripe"
        actual_body, header_items = request.read(), request.headers.multi_items()
        assert actual_body == self.wire.body
        relevant = [(key, value) for key, value in header_items if key in {"content-type", "stripe-signature"}]
        assert relevant == list(self.wire.headers)
        actual = wire_analysis(actual_body, header_items, self.wire.verification_time)
        for field in ("SignatureHeaders", "MatchingV1Signatures"):
            assert actual[field] == int(authored[field])
        assert actual["BodyBytes"] == (
            len(self.wire.body) if authored["BodyBytes"] == "natural" else int(authored["BodyBytes"])
        )
        assert actual["TimestampOffsetSeconds"] == authored["TimestampOffsetSeconds"]
        same = actual_body == self.wire.signed_body
        assert type(json.loads(authored["SignedBytesEqual"])) is bool and same == json.loads(
            authored["SignedBytesEqual"]
        )
        self.context.evidence.observation(
            "Webhook signed wire evidence",
            {
                "expected": authored,
                "observed": {**actual, "SignedBytesEqual": same},
                "exchangeId": response.extensions["payments.bdd.exchangeId"],
                "verificationTime": self.wire.verification_time,
                "signatureHeaders": [v for k, v in header_items if k == "stripe-signature"],
                "contentType": request.headers.get("content-type"),
                "sha256": hashlib.sha256(actual_body).hexdigest(),
                "signedSha256": hashlib.sha256(self.wire.signed_body).hexdigest(),
            },
        )

    def _no_external_calls(self) -> None:
        assert self.payments.external_calls is not None
        assert (len(self.context.orders.http_calls), len(self.context.stripe.calls)) == self.payments.external_calls
        assert self.context.stripe.sessions == self.before_sessions

    def rejected(self, authored: dict[str, str]) -> None:
        assert authored == {
            "CurrentStatus": "pending",
            "CurrentVersion": "2",
            "NewReceipts": "0",
            "NewExternalCalls": "0",
        }
        before = self.payments.before
        assert before is not None
        after = self.payments.snapshot()
        assert after == before, "Rejected verification must preserve every field in every populated collection"
        current = self.payments.target(after)
        assert (
            current is not None
            and current["status"] == authored["CurrentStatus"]
            and current["version"] == int(authored["CurrentVersion"])
        )
        self._no_external_calls()
        response = self.context.responses[0]
        body = response.json()
        assert response.status_code >= 400 and response.headers["content-type"] == "application/problem+json"
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
        assert re.fullmatch(r"[0-9a-f]{32}", body["traceId"]) and body["traceId"] == response.headers["x-trace-id"]
        assert "private" not in json.dumps(body).lower() and WEBHOOK_SECRET not in response.text
        self.context.evidence.observation(
            "Webhook verification rejection state",
            {
                "expected": authored,
                "before": lossless(before),
                "after": lossless(after),
                "externalCallCounts": self.payments.external_calls,
                "exchangeId": response.extensions["payments.bdd.exchangeId"],
            },
        )

    def acknowledged(self) -> None:
        response = self.context.responses[0]
        assert response.status_code == 200 and response.headers["content-type"] == "application/json"
        assert response.json().keys() == {"received"} and response.json()["received"] is True
        assert re.fullmatch(r"[0-9a-f]{32}", response.headers["x-trace-id"])
        self._no_external_calls()

    def unknown_receipt(self, authored: dict[str, str]) -> None:
        assert authored.keys() == UNKNOWN_RECEIPT_FIELDS and self.wire is not None
        before = self.payments.before
        assert before is not None and self.context.request_window is not None
        after = self.payments.snapshot()
        assert after["payments"] == before["payments"] and after["payment_history"] == before["payment_history"]
        assert not any(d["_id"] == self.wire.event["id"] for d in before["stripe_webhooks"])
        new = [d for d in after["stripe_webhooks"] if d["_id"] == self.wire.event["id"]]
        assert len(new) == 1 and new[0].keys() == UNKNOWN_RECEIPT_FIELDS
        receipt = new[0]
        assert [d for d in after["stripe_webhooks"] if d["_id"] != receipt["_id"]] == before["stripe_webhooks"]
        for key, value in authored.items():
            actual = receipt[key]
            if key == "_id":
                assert value == "{event.id}" and actual == self.wire.event["id"]
            elif key == "payload_digest":
                assert value == "{request.sha256}" and actual == hashlib.sha256(self.wire.body).hexdigest()
            elif key in {"received_at", "completed_at"}:
                assert value == "{request.window}" and isinstance(actual, datetime)
                assert actual == milliseconds(actual) and milliseconds(
                    self.context.request_window[0]
                ) <= actual <= milliseconds(self.context.request_window[1])
            else:
                expected = json.loads(value)
                assert type(actual) is type(expected) and actual == expected, key
        assert receipt["completed_at"] >= receipt["received_at"]
        current = self.payments.target(after)
        assert current is not None and current["status"] == "pending" and current["version"] == 2
        self.acknowledged()
        self.context.evidence.observation(
            "Verified unknown webhook receipt",
            {
                "expected": authored,
                "before": lossless(before),
                "after": lossless(after),
                "receipt": lossless(receipt),
                "requestWindow": [t.isoformat() for t in self.context.request_window],
                "exchangeId": self.context.responses[0].extensions["payments.bdd.exchangeId"],
            },
        )

    def paid_control(self, authored: dict[str, str]) -> None:
        assert authored == {"ReceiptState": "applied", "PayloadDigest": "{request.sha256}"} and self.wire is not None
        receipt = self.context.webhooks.find_one({"_id": self.wire.event["id"]})
        assert receipt is not None and receipt["state"] == authored["ReceiptState"]
        assert receipt["payload_digest"] == hashlib.sha256(self.wire.body).hexdigest()
        self.acknowledged()
        self.context.evidence.observation(
            "Verified paid webhook digest",
            {
                "expected": authored,
                "eventId": self.wire.event["id"],
                "payloadDigest": receipt["payload_digest"],
                "exchangeId": self.context.responses[0].extensions["payments.bdd.exchangeId"],
            },
        )
