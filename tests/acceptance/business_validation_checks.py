"""Authored upstream money tokens and complete isolated business-validation evidence."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from httpx import Request, Response

from tests.acceptance.payment_checks import PaymentChecks, Snapshot, full_payment, lossless

if TYPE_CHECKING:
    from tests.acceptance.conftest import AcceptanceContext

CONTRACT_FIELDS = {
    "TotalAmountToken",
    "CurrencyToken",
    "LineAmountTokens",
    "LineCurrencyToken",
    "StatusToken",
    "OrderIdToken",
}


def contract_body(values: dict[str, str]) -> bytes:
    """Strings in LineAmountTokens contain literal JSON tokens, never binary floats."""
    assert values.keys() == CONTRACT_FIELDS
    raw: object = json.loads(values["LineAmountTokens"])
    assert isinstance(raw, list)
    assert all(isinstance(token, str) for token in cast(list[object], raw))
    tokens = cast(list[str], raw)
    fields = {
        "id": values["OrderIdToken"],
        "status": values["StatusToken"],
        "totalAmount": values["TotalAmountToken"],
        "totalCurrency": values["CurrencyToken"],
    }
    for token in [*fields.values(), values["LineCurrencyToken"], *tokens]:
        if token != "<absent>":
            json.loads(token, parse_float=Decimal)
    lines = [
        '{"lineTotalAmount":' + token + ',"productVersion":{"priceCurrency":' + values["LineCurrencyToken"] + "}}"
        for token in tokens
    ]
    return (
        "{"
        + ",".join(json.dumps(key) + ":" + token for key, token in fields.items() if token != "<absent>")
        + ',"lines":['
        + ",".join(lines)
        + "]}"
    ).encode()


def safe_problem(response: Any, authored: dict[str, str]) -> None:
    assert response.status_code == int(authored["HTTPStatuses"])
    assert response.headers["content-type"] == authored["ContentType"] == "application/problem+json"
    body = response.json()
    assert body.keys() == {
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
    assert re.fullmatch(r"[0-9a-f]{32}", body["traceId"])
    assert body["traceId"] == response.headers["x-trace-id"]
    expected = {
        key.removeprefix("JSON."): json.loads(value) for key, value in authored.items() if key.startswith("JSON.")
    }
    assert body == {**expected, "code": authored["Code"], "traceId": body["traceId"]}
    assert body["errors"] == body["missingProperties"] == []


class BusinessValidationChecks:
    def __init__(self, checks: PaymentChecks) -> None:
        self.checks = checks
        self.context: AcceptanceContext = checks.context
        self.before: Snapshot | None = None
        self.calls = 0
        self.provider_calls = 0
        self.sessions: dict[str, Any] = {}
        self.contract: dict[str, str] | None = None

    def configure(self, values: dict[str, str]) -> None:
        context = self.context
        body = contract_body(values)
        self.contract = deepcopy(values)

        def handle(request: Request) -> Response:
            assert request.method == "GET" and request.url.path == f"/orders/{context.orders.order_id}"
            assert request.read() == b""
            return Response(200, content=body, headers={"content-type": "application/json"})

        # The shared optional handler retains central physical HTTP capture.
        context.orders.fulfillment_handler = handle
        context.evidence.observation("Orders business contract", {"inputs": values, "responseBytesUtf8": body.decode()})

    def remember(self) -> None:
        self.checks.remember("Business validation collections before")
        assert self.checks.before is not None and all(self.checks.before.values())
        self.before = deepcopy(self.checks.before)
        self.calls = len(self.context.orders.http_calls)
        self.provider_calls = len(self.context.stripe.calls)
        self.sessions = deepcopy(self.context.stripe.sessions)

    def rejection(self, values: dict[str, str], authored: dict[str, str]) -> None:
        assert values.keys() == {"OrdersReads", "StripeCalls", "TargetPayment", "Collections", "Repeat"}
        assert values == {
            "OrdersReads": "1",
            "StripeCalls": "0",
            "TargetPayment": "absent",
            "Collections": "unchanged",
            "Repeat": "true",
        }
        context = self.context
        assert self.before is not None and self.checks.target(self.before) is None
        first = context.responses[0]
        safe_problem(first, authored)
        assert self.checks.snapshot() == self.before
        after_first = self.checks.snapshot()
        assert context.orders.http_calls[self.calls :] == [("GET", f"/orders/{context.orders.order_id}")]
        assert len(context.stripe.calls) == self.provider_calls and context.stripe.sessions == self.sessions
        route = first.request.url.path
        repeated = context.client.post(route)
        safe_problem(repeated, authored)
        assert repeated.json()["traceId"] != first.json()["traceId"]
        assert self.checks.snapshot() == self.before
        assert context.orders.http_calls[self.calls :] == [("GET", f"/orders/{context.orders.order_id}")] * 2
        assert len(context.stripe.calls) == self.provider_calls and context.stripe.sessions == self.sessions
        context.evidence.observation(
            "Complete business rejection",
            {
                "expected": values,
                "problemExpected": authored,
                "before": lossless(self.before),
                "afterFirst": lossless(after_first),
                "after": lossless(self.checks.snapshot()),
                "exchangeIds": [r.extensions["payments.bdd.exchangeId"] for r in (first, repeated)],
                "ordersOperations": context.orders.http_calls[self.calls :],
                "stripeCalls": 0,
                "providerSessionsUnchanged": True,
                "providerSessionsBefore": self.sessions,
                "providerSessionsAfter": context.stripe.sessions,
            },
        )

    def accepted_repeat(self, values: dict[str, str]) -> None:
        assert values.keys() == {"AmountMinor", "Currency", "OrdersReads", "StripeCalls"}
        assert values["OrdersReads"] == "0" and values["StripeCalls"] == "0"
        context = self.context
        before = self.checks.snapshot()
        target = self.checks.target(before)
        assert target is not None
        calls = len(context.orders.http_calls), len(context.stripe.calls)
        sessions = deepcopy(context.stripe.sessions)
        responses = [
            context.client.get(f"/payments/order/{context.orders.order_id}"),
            context.client.post(f"/payments/{context.orders.order_id}/pay"),
        ]
        assert all(response.status_code == 200 for response in responses)
        authored = {
            "id": "{stored.id}",
            "order_id": json.dumps(str(context.orders.order_id)),
            "amount_minor": values["AmountMinor"],
            "currency": json.dumps(values["Currency"]),
            "status": json.dumps(target["status"]),
            "provider_session_id": json.dumps(target["provider_session_id"]),
            "provider_payment_id": "null",
            "failure_code": "null",
            "created_at": "{stored.created_at}",
            "updated_at": "null" if target["updated_at"] is None else "{stored.updated_at}",
        }
        for response in responses:
            full_payment(response.json(), target, authored)
        assert responses[0].json() == responses[1].json()
        assert self.checks.snapshot() == before
        assert (len(context.orders.http_calls), len(context.stripe.calls)) == calls
        assert context.stripe.sessions == sessions
        context.evidence.observation(
            "Accepted business boundary repeat",
            {
                "expected": values,
                "collections": lossless(before),
                "stored": lossless(target),
                "responses": [r.json() for r in responses],
                "exchangeIds": [r.extensions["payments.bdd.exchangeId"] for r in responses],
                "allCollectionsUnchanged": True,
                "noNewDependencyCalls": True,
            },
        )
