"""Scenario-local, immutable evidence; worker threads never call the Allure API."""

import base64
import hashlib
import json
import re
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock
from typing import Any, cast
from urllib.parse import urlsplit

import allure
from fastapi.testclient import TestClient
from httpx2 import Response
from scripts.bdd_evidence import instance_id


def content_evidence(body: bytes, content_type: str | None) -> dict[str, Any]:
    def reject_constant(value: str) -> Any:
        raise ValueError(f"Non-JSON numeric constant: {value}")

    media = (content_type or "").split(";", 1)[0].lower()
    is_json = media.endswith("/json") or media.endswith("+json")
    raw: str | None = None
    value: Any = None
    body_format = "empty" if not body else "binary"
    if body and (is_json or media.startswith("text/") or media == "application/x-www-form-urlencoded"):
        try:
            raw = body.decode("utf-8")
            value, body_format = raw, "text"
            if is_json:
                try:
                    value, body_format = json.loads(raw, parse_constant=reject_constant), "json"
                except ValueError:
                    body_format = "invalid-json"
        except UnicodeDecodeError:
            body_format = "invalid-text"
    return {
        "contentType": content_type,
        "bodyFormat": body_format,
        "body": value,
        "rawBody": raw,
        "byteLength": len(body),
        "bodyBytesBase64": base64.b64encode(body).decode("ascii"),
        "sha256": hashlib.sha256(body).hexdigest(),
    }


def safe_headers(headers: Mapping[str, str]) -> dict[str, str]:
    sensitive = {"authorization", "proxy-authorization", "cookie", "set-cookie", "x-api-key"}
    return {key.lower(): "[redacted]" if key.lower() in sensitive else value for key, value in headers.items()}


def safe_header_items(headers: list[tuple[str, str]]) -> list[list[str]]:
    return [[key.lower(), safe_headers({key: value})[key.lower()]] for key, value in headers]


@dataclass(frozen=True)
class Exchange:
    number: int
    # Serialized at request start: later fixture/phase/header mutations cannot alter it.
    metadata: str


class ScenarioEvidence:
    def __init__(self, scenario_id: str, feature: str, scenario: str, parameters: Mapping[str, str]) -> None:
        if re.fullmatch(r"PAY\d+-\d+", scenario_id) is None:
            raise ValueError("A stable Payments scenario ID is required")
        self.identity = {
            "service": "payments",
            "scenarioId": scenario_id,
            "instanceId": instance_id(scenario_id, parameters),
            "feature": feature,
            "scenario": scenario,
            "parameters": dict(sorted(parameters.items())),
        }
        self.phase = "Setup"
        self.step = "Scenario setup"
        self._action_id: str | None = None
        self._sequence = 0
        self._lock = Lock()
        self._pending: list[tuple[str, str]] = []
        self._index: list[dict[str, Any]] = []

    def publish_identity(self) -> None:
        for key in ("service", "scenarioId", "instanceId"):
            cast(Any, allure.dynamic).label(key, self.identity[key])
        self.record("Scenario identity", self.identity)
        self.flush()

    def record(self, name: str, value: object) -> None:
        snapshot = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        with self._lock:
            self._pending.append((name, snapshot))

    def observation(self, name: str, value: object) -> None:
        self.record(name, {**self.identity, "stepPhase": self.phase, "step": self.step, "value": value})

    def begin(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes,
        *,
        target: str,
        role: str,
        controlled: bool = False,
        attempt: str | None = None,
        header_items: list[tuple[str, str]] | None = None,
    ) -> Exchange:
        parsed = urlsplit(url)
        with self._lock:
            self._sequence += 1
            number = self._sequence
            metadata = {
                **self.identity,
                "exchangeId": f"{self.identity['instanceId']}/{number}",
                "sequence": number,
                "stepPhase": self.phase,
                "step": self.step,
                "actionId": self._action_id,
                "targetService": target,
                "exchangeRole": role,
                "controlledBoundary": controlled,
                "requestAttempt": attempt,
                "method": method.upper(),
                "path": parsed.path,
                "query": parsed.query,
            }
            self._index.append(metadata.copy())
        exchange = Exchange(number, json.dumps(metadata, sort_keys=True))
        self.record(
            f"HTTP {number:03} request",
            {
                **metadata,
                "kind": "request",
                "headers": safe_headers(headers),
                "headerItems": safe_header_items(list(headers.items()) if header_items is None else header_items),
                "content": content_evidence(body, headers.get("content-type")),
            },
        )
        return exchange

    def response(
        self,
        exchange: Exchange,
        status: int,
        headers: Mapping[str, str],
        body: bytes,
        *,
        header_items: list[tuple[str, str]] | None = None,
    ) -> None:
        self.record(
            f"HTTP {exchange.number:03} response",
            {
                **json.loads(exchange.metadata),
                "kind": "response",
                "status": status,
                "headers": safe_headers(headers),
                "headerItems": safe_header_items(list(headers.items()) if header_items is None else header_items),
                "content": content_evidence(body, headers.get("content-type")),
            },
        )

    def failure(self, exchange: Exchange, error: BaseException) -> None:
        # Exception messages may contain credentials or private transport details.
        self.record(
            f"HTTP {exchange.number:03} failure",
            {
                **json.loads(exchange.metadata),
                "kind": "failure",
                "exceptionType": type(error).__name__,
                "cancelled": type(error).__name__ == "CancelledError",
            },
        )

    @contextmanager
    def action(self, name: str, inputs: object) -> Generator[dict[str, Any]]:
        with self._lock:
            self._sequence += 1
            number = self._sequence
        metadata: dict[str, Any] = {
            **self.identity,
            "actionId": f"{self.identity['instanceId']}/action/{number}",
            "stepPhase": self.phase,
            "step": self.step,
            "action": name,
        }
        previous = self._action_id
        self._action_id = metadata["actionId"]
        self.record(f"Action {number:03} start", {**metadata, "kind": "action-start", "inputs": inputs})
        output: dict[str, Any] = {}
        try:
            yield output
        except BaseException as error:
            self.record(
                f"Action {number:03} failure",
                {**metadata, "kind": "action-failure", "exceptionType": type(error).__name__},
            )
            raise
        else:
            self.record(f"Action {number:03} result", {**metadata, "kind": "action-result", "output": output})
        finally:
            self._action_id = previous

    def finish(self, attach: Callable[[str, str], None] | None = None) -> None:
        self.record("Scenario evidence index", {**self.identity, "exchanges": self._index})
        self.flush(attach)

    def flush(self, attach: Callable[[str, str], None] | None = None) -> None:
        with self._lock:
            pending, self._pending = self._pending, []
        for name, snapshot in pending:
            if attach is not None:
                attach(name, snapshot)
            else:
                allure.attach(snapshot, name=name, attachment_type=allure.attachment_type.JSON)


class EvidenceClient:
    """Send the actual prepared TestClient request once, preserving all exchanges."""

    def __init__(self, client: TestClient, evidence: ScenarioEvidence) -> None:
        self.client = client
        self.evidence = evidence
        self.app = client.app

    def request(
        self,
        method: str,
        path: str,
        *,
        content: bytes | None = None,
        headers: dict[str, str] | list[tuple[str, str]] | None = None,
        attempt: str | None = None,
    ) -> Response:
        request = self.client.build_request(method, path, content=content, headers=headers)
        exchange = self.evidence.begin(
            request.method,
            str(request.url),
            request.headers,
            request.read(),
            target="payments",
            role="api-concurrent" if attempt else "api",
            attempt=attempt,
            header_items=request.headers.multi_items(),
        )
        try:
            response = self.client.send(request)
            self.evidence.response(
                exchange,
                response.status_code,
                response.headers,
                response.read(),
                header_items=response.headers.multi_items(),
            )
            response.extensions["payments.bdd.exchangeId"] = json.loads(exchange.metadata)["exchangeId"]
            return response
        except BaseException as error:
            self.evidence.failure(exchange, error)
            raise

    def post(
        self,
        path: str,
        *,
        content: bytes | None = None,
        headers: dict[str, str] | list[tuple[str, str]] | None = None,
        attempt: str | None = None,
    ) -> Response:
        return self.request("POST", path, content=content, headers=headers, attempt=attempt)

    def get(self, path: str) -> Response:
        return self.request("GET", path)


def table_values(table: list[list[str]]) -> dict[str, str]:
    if not table or table[0] != ["Field", "Value"] or any(len(row) != 2 for row in table[1:]):
        raise ValueError("Expected a Field/Value Gherkin table")
    values = dict(table[1:])
    if len(values) != len(table) - 1 or not values or any(not key or not value for key, value in values.items()):
        raise ValueError("Empty or duplicate Gherkin table values")
    return values
