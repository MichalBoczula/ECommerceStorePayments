"""Validate every captured exchange, independent of which response a Then step selects."""

import base64
import json
import re
from collections import defaultdict
from http import HTTPStatus
from pathlib import Path
from typing import Any

from jsonschema import ValidationError

from scripts.contract_metadata import validator

DOCS = {
    "/swagger": "text/html",
    "/redoc": "text/html",
    "/docs/oauth2-redirect": "text/html",
    "/openapi.json": "application/json",
}
METHODS = {"get", "post", "put", "patch", "delete"}


class CapturedContracts:
    def __init__(self, spec: dict[str, Any]) -> None:
        self.spec = spec
        self.routes = [
            (
                path,
                re.compile("/".join("[^/]+" if part.startswith("{") else re.escape(part) for part in path.split("/"))),
                method.upper(),
                operation,
            )
            for path, item in spec["paths"].items()
            for method, operation in item.items()
            if method in METHODS
        ]
        self.problem = spec["paths"]["/payments/{order_id}/pay"]["post"]["responses"]["404"]["content"][
            "application/problem+json"
        ]["schema"]
        self.validators: dict[str, Any] = {}

    def validate(self, schema: dict[str, Any], body: Any) -> None:
        key = json.dumps(schema, sort_keys=True)
        if key not in self.validators:
            self.validators[key] = validator(self.spec, schema)
        self.validators[key].validate(body)

    def observe(self, request: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any]:
        # A contract failure is evidence about an existing response, never a transport
        # exception. Keep the original pair and let the post-suite gate fail explicitly.
        try:
            return {"valid": True, **self.check(request, outcome)}
        except (ValidationError, ValueError, KeyError, TypeError) as error:
            return {"valid": False, "errorType": type(error).__name__}

    def check(self, request: dict[str, Any], outcome: dict[str, Any]) -> dict[str, Any]:
        from scripts.bdd_evidence import check_content

        check_content(request["content"])
        if outcome["kind"] == "response":
            check_content(outcome["content"])
        elif outcome["kind"] != "failure":
            raise ValueError("Unknown captured outcome")
        if outcome["kind"] == "failure" and ("status" in outcome or "content" in outcome):
            raise ValueError("Transport failure cannot claim an HTTP response")
        result: dict[str, Any] = {"requestSha256": request["content"]["sha256"]}
        if request["targetService"] != "payments":
            return {
                **result,
                "classification": "external-boundary",
                "schemaValidated": False,
                "outcome": outcome["kind"],
            }
        if outcome["kind"] == "failure":
            return {
                **result,
                "classification": "transport-failure",
                "schemaValidated": False,
                "outcome": "failure",
                "exceptionType": outcome["exceptionType"],
                "cancelled": outcome["cancelled"],
            }
        status, content, headers = outcome["status"], outcome["content"], outcome["headers"]
        body = content["body"]
        actual_media = (content["contentType"] or "").split(";", 1)[0].strip().lower()
        raw = base64.b64decode(content["bodyBytesBase64"], validate=True)
        if (
            headers.get("content-length") != str(len(raw))
            or re.fullmatch("[0-9a-f]{32}", headers.get("x-trace-id", "")) is None
        ):
            raise ValueError("Missing or invalid actual response length/trace headers")
        if headers["x-trace-id"] == request["headers"].get("x-trace-id"):
            raise ValueError("Response reused the caller trace ID")
        if headers.get("content-type") != content["contentType"]:
            raise ValueError("Captured media and header differ")
        result.update(
            outcome="response",
            status=status,
            responseSha256=content["sha256"],
            headersValidated=["content-type", "content-length", "x-trace-id"],
        )
        matches = [
            (path, method, operation)
            for path, pattern, method, operation in self.routes
            if pattern.fullmatch(request["path"])
        ]
        selected = next((row for row in matches if row[1] == request["method"]), None)
        if selected is not None:
            path, _, operation = selected
            result.update(classification="operation", operationId=operation["operationId"], pathTemplate=path)
        elif matches:
            path, _, operation = matches[0]
            if status != 405:
                raise ValueError("Wrong method did not retain its real 405")
            result.update(classification="wrong-method", operationId=operation["operationId"], pathTemplate=path)
        elif request["path"] in DOCS and request["method"] == "GET" and status == 200:
            if actual_media != DOCS[request["path"]]:
                raise ValueError("Documentation media differs from its actual route")
            if request["path"] == "/openapi.json":
                if body != self.spec:
                    raise ValueError("Served OpenAPI differs from the generated contract")
            elif content["bodyFormat"] != "text" or not raw.strip() or b"<html" not in raw.lower():
                raise ValueError("Documentation response is not HTML")
            return {
                **result,
                "classification": "documentation",
                "schemaValidated": request["path"] == "/openapi.json",
                "responseSchema": "generated-openapi" if request["path"] == "/openapi.json" else "framework-html",
            }
        else:
            if status != 404:
                raise ValueError("Unmatched route did not retain its real 404")
            operation = None
            result.update(classification="unmatched-route", operationId=None, pathTemplate=None)
        if operation is None:
            media, schema = "application/problem+json", self.problem
        else:
            declared = operation["responses"].get(str(status))
            if declared is None:
                raise ValueError("Captured response status is not declared for its operation")
            media = "application/problem+json" if status >= 400 else "application/json"
            schema = declared["content"][media]["schema"]
            for name, header in declared["headers"].items():
                if name.lower() not in headers:
                    raise ValueError("Missing declared response header")
                self.validate(header["schema"], headers[name.lower()])
                if name.lower() not in result["headersValidated"]:
                    result["headersValidated"].append(name.lower())
        if actual_media != media or content["bodyFormat"] != "json":
            raise ValueError("Captured response media/body differs from its declared contract")
        self.validate(schema, body)
        if status >= 400:
            if (
                body["status"] != status
                or body["title"] != HTTPStatus(status).phrase
                or body["instance"] != request["path"]
                or body["traceId"] != headers["x-trace-id"]
            ):
                raise ValueError("Problem does not match actual wire status/path/trace")
        elif selected is not None:
            for parameter in operation.get("parameters", []):
                if parameter["in"] == "path":
                    index = path.split("/").index("{" + parameter["name"] + "}")
                    self.validate(parameter["schema"], request["path"].split("/")[index])
            if path.endswith(("/pay", "/checkout")) and request["content"]["byteLength"] != 0:
                raise ValueError("Successful bodyless command had a request body")
            if operation["operationId"] == "receiveStripeWebhook":
                signature = [v for k, v in request["headerItems"] if k == "stripe-signature"]
                if (
                    len(signature) != 1
                    or not signature[0]
                    or request["content"]["byteLength"] > 1024 * 1024
                    or request["content"]["bodyFormat"] != "json"
                    or (request["content"]["contentType"] or "").split(";", 1)[0].strip().lower() != "application/json"
                ):
                    raise ValueError("Accepted webhook is missing its original signed JSON/header evidence")
                self.validate(
                    operation["requestBody"]["content"]["application/json"]["schema"], request["content"]["body"]
                )
        return {
            **result,
            "schemaValidated": True,
            "responseSchema": "declared-response" if operation else "global-problem",
        }


def check_captured_contracts(spec: dict[str, Any], results_dir: Path) -> dict[str, int]:
    from scripts.bdd_evidence import attachments

    checks = CapturedContracts(spec)
    totals = {"exchanges": 0, "paymentsResponses": 0, "external": 0, "failures": 0}
    for path in results_dir.glob("*-result.json"):
        records: dict[str, Any] = {}
        pairs: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for attachment in attachments(json.loads(path.read_text())):
            if attachment["type"] == "application/json":
                record = json.loads((results_dir / attachment["source"]).read_text())
                if record.get("kind") in {"request", "response", "failure"}:
                    pairs[record["exchangeId"]].append(record)
                if record.get("kind") == "contract":
                    if record["exchangeId"] in records:
                        raise ValueError("Duplicate captured contract observation")
                    records[record["exchangeId"]] = record
        if pairs.keys() != records.keys():
            raise ValueError("Missing or foreign captured contract observations")
        for exchange_id, pair in pairs.items():
            if len(pair) != 2:
                raise ValueError("Contract check needs an actual paired exchange")
            requests = [record for record in pair if record["kind"] == "request"]
            outcomes = [record for record in pair if record["kind"] in {"response", "failure"}]
            if len(requests) != 1 or len(outcomes) != 1:
                raise ValueError("Contract check needs one request and one actual outcome")
            request, outcome = requests[0], outcomes[0]
            expected = {"valid": True, **checks.check(request, outcome)}
            observation = records[exchange_id]
            if observation["value"] != expected or {
                key: value for key, value in observation.items() if key not in {"kind", "value"}
            } != {
                key: value for key, value in request.items() if key not in {"kind", "headers", "headerItems", "content"}
            }:
                raise ValueError("Captured contract observation differs from actual exchange")
            totals["exchanges"] += 1
            totals["external"] += int(request["targetService"] != "payments")
            totals["failures"] += int(outcome["kind"] == "failure")
            totals["paymentsResponses"] += int(request["targetService"] == "payments" and outcome["kind"] == "response")
    return totals
