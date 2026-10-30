"""Validate technical HTTP/cancellation/action evidence without inflating OpenAPI coverage."""

import csv
import inspect
import json
from pathlib import Path
from typing import Any

from starlette.routing import Route

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.api.routes.health import router as health_router
from ecommerce_store_payments.infrastructure.persistence.mongodb.fulfill_payments import run
from ecommerce_store_payments.infrastructure.persistence.mongodb.replay_webhooks import main as replay_main

TECHNICAL = Path(__file__).resolve().parents[1] / "docs" / "technical-scenarios.tsv"
FIELDS = {"id", "kind", "operation", "cause", "status", "media", "code", "exception", "result", "requirement"}
COMMANDS = {"startup": create_app, "isolation": create_app, "fulfill": run, "replay": replay_main}


def technical_rows(path: Path = TECHNICAL) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    if any(row.keys() != FIELDS or any(not isinstance(v, str) or not v.strip() for v in row.values()) for row in rows):
        raise ValueError("Invalid technical matrix fields")
    if len(rows) != len({row["id"] for row in rows}):
        raise ValueError("Duplicate technical scenario ID")
    return rows


def technical_links(rows: list[dict[str, str]], requirements: set[str]) -> list[dict[str, Any]]:
    app = create_app()
    routes = [route for route in [*app.routes, *health_router.routes] if isinstance(route, Route)]
    projected: list[dict[str, Any]] = []
    for row in rows:
        if row["kind"] not in {"response", "cancelled", "action"} or row["requirement"] not in requirements:
            raise ValueError(f"Invalid technical kind/requirement: {row['id']}")
        verb, target = row["operation"].split(" ", 1)
        if verb == "COMMAND":
            if (
                target not in COMMANDS
                or row["kind"] == "response"
                or (row["kind"] == "cancelled" and target != "fulfill")
            ):
                raise ValueError(f"Unknown technical command: {row['id']}")
            function = COMMANDS[target]
            # A real source function, not an invented HTTP operation or runtime branch trace.
            inspect.getsource(function)
            source = f"{function.__module__}.{function.__qualname__}"
            operation_id = None
        else:
            matches = [route for route in routes if route.path == target and verb in (route.methods or set())]
            if (
                len(matches) != 1
                or verb != "GET"
                or row["kind"] == "action"
                or (row["kind"] == "cancelled" and target != "/health/ready")
            ):
                raise ValueError(f"Unknown technical HTTP route: {row['id']}")
            route = matches[0]
            source = f"{route.endpoint.__module__}.{route.endpoint.__qualname__}"
            operation_id = getattr(route, "operation_id", None)
        if row["kind"] == "response":
            if (
                row["status"] not in {"200", "503"}
                or row["media"]
                != (
                    "application/problem+json"
                    if row["status"] == "503"
                    else "application/json"
                    if target in {"/health/ready", "/openapi.json"}
                    else "text/html; charset=utf-8"
                )
                or row["exception"] != "<none>"
                or row["code"] != ("service_unavailable" if row["status"] == "503" else "-")
                or (row["status"] == "503" and target != "/health/ready")
            ):
                raise ValueError(f"Invalid technical HTTP result: {row['id']}")
        elif row["status"] != "<none>" or row["media"] != "<none>" or row["code"] != "-":
            raise ValueError(f"Technical action/cancellation cannot claim an HTTP status: {row['id']}")
        if row["kind"] == "cancelled" and row["exception"] != "CancelledError":
            raise ValueError(f"Cancellation must retain its actual exception: {row['id']}")
        projected.append({**row, "source": source, "operationId": operation_id})
    return projected


def check_technical_source(profile: dict[str, Any], row: dict[str, str]) -> None:
    expected = profile["expected"]
    wanted = dict(
        Outcome=row["kind"],
        HTTPStatuses=row["status"],
        ContentType=row["media"],
        Code=row["code"],
        ExceptionType=row["exception"],
        Result=row["result"],
    )
    if not profile.get("technical") or any(expected.get(k) != v for k, v in wanted.items()):
        raise ValueError(f"Authored technical table and matrix differ: {row['id']}")


def check_technical_result(
    expectation: dict[str, Any],
    expected: dict[str, str],
    pairs: dict[str, list[dict[str, Any]]],
    records: dict[str, Any],
) -> None:
    selected = expectation.get("exchangeIds", [])
    action_ids = expectation.get("actionIds", [])
    if len(action_ids) != len(set(action_ids)):
        raise ValueError("Duplicate selected technical action")
    for action_id in action_ids:
        starts = [v for v in records.values() if v.get("actionId") == action_id and v.get("kind") == "action-start"]
        ends = [v for v in records.values() if v.get("actionId") == action_id and v.get("kind") == "action-result"]
        if len(starts) != 1 or len(ends) != 1:
            raise ValueError("Missing selected technical action witnesses")
        output = ends[0]["output"]
        if output.get("result") != expected["Result"] or output.get("exceptionType", "<none>") not in expected[
            "ExceptionType"
        ].split(","):
            raise ValueError("Technical action result differs from native expectation")
    kind = expected["Outcome"]
    if kind == "action":
        if selected or len(action_ids) != 1:
            raise ValueError("Technical action needs one actual action and no invented HTTP result")
        return
    if len(selected) != 1 or selected[0] not in pairs:
        raise ValueError("Technical HTTP outcome needs one actual exchange")
    pair = pairs[selected[0]]
    request = next(v for v in pair if v["kind"] == "request")
    if kind == "cancelled":
        outcomes = [v for v in pair if v["kind"] == "failure"]
        if len(outcomes) != 1 or any(v["kind"] == "response" for v in pair):
            raise ValueError("Cancelled exchange cannot have a fabricated completed response")
        failure = outcomes[0]
        if (
            not failure["cancelled"]
            or failure["exceptionType"] != expected["ExceptionType"]
            or expected["HTTPStatuses"] != "<none>"
        ):
            raise ValueError("Missing actual cancellation failure")
        if len(action_ids) != 1 or request["actionId"] != action_ids[0]:
            raise ValueError("Cancellation must join its actual owning action")
    elif kind == "response":
        responses = [v for v in pair if v["kind"] == "response"]
        if len(responses) != 1 or action_ids:
            raise ValueError("Missing actual technical response")
        response = responses[0]
        body = response["content"]["body"]
        code = body.get("code", "-") if isinstance(body, dict) else "-"
        if (
            response["targetService"] != "payments"
            or response["status"] != int(expected["HTTPStatuses"])
            or response["content"]["contentType"] != expected["ContentType"]
            or code != expected["Code"]
        ):
            raise ValueError("Technical HTTP result differs from native expectation")
        for key, token in expected.items():
            if key.startswith("JSON."):
                actual = body
                for part in key[5:].split("."):
                    actual = actual[part]
                if type(actual) is not type(json.loads(token)) or actual != json.loads(token):
                    raise ValueError("Technical JSON differs from native expectation")
    else:
        raise ValueError("Unknown technical outcome")
