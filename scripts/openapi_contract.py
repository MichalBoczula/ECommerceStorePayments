"""Validate the generated OpenAPI and concrete acceptance responses against it."""

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate

from ecommerce_store_payments.api.app import create_app
from scripts.generate_operation_links import generate

METHODS = {"get", "post", "put", "patch", "delete"}


def document() -> dict[str, Any]:
    """Build the same schema served by the API without starting its lifespan."""
    return create_app().openapi()


def check_contract(spec: dict[str, Any], links: dict[str, Any]) -> tuple[int, int]:
    validate(spec)
    published = {
        operation["operationId"]: (method.upper(), path, operation)
        for path, path_item in spec["paths"].items()
        for method, operation in path_item.items()
        if method in METHODS
    }
    expected = {item["operationId"] for item in links["operations"]}
    if len(published) != len(expected) or set(published) != expected:
        raise ValueError("OpenAPI operation IDs differ from executable routes")

    checked = 0
    for item in links["operations"]:
        method, path, operation = published[item["operationId"]]
        if (method, path) != (item["method"], item["path"]):
            raise ValueError(f"Operation method/path drift: {item['operationId']}")
        responses = operation["responses"]
        if "422" in responses:
            raise ValueError(f"Undocumented runtime 422 in {item['operationId']}")
        for status, declared in responses.items():
            media = "application/problem+json" if int(status) >= 400 else "application/json"
            content = declared.get("content", {})
            if set(content) != {media} or not content[media].get("schema"):
                raise ValueError(f"Wrong media or missing schema: {item['operationId']} {status}")
        for case in item["scenarios"]:
            for status in case["status"].split(","):
                if status not in responses:
                    raise ValueError(f"Missing OpenAPI status: {item['operationId']} {case['id']} {status}")
                checked += 1
    if not links["unmatchedRouteScenarios"]:
        raise ValueError("Missing global unmatched-route acceptance scenario")
    return len(published), checked


def check_case(
    spec: dict[str, Any], links: dict[str, Any], case_id: str, status: int, content_type: str, body: object
) -> None:
    """Match an observed HTTP response with the matrix and its OpenAPI response schema."""
    operation = None
    case = None
    for item in links["operations"]:
        for candidate in item["scenarios"]:
            if candidate["id"] == case_id:
                operation = spec["paths"][item["path"]][item["method"].lower()]
                case = candidate
                break
    if case is None:
        case = next((item for item in links["unmatchedRouteScenarios"] if item["id"] == case_id), None)
        if case is None:
            raise ValueError(f"Unknown acceptance scenario: {case_id}")
        # A route without a matching operation uses the same global problem shape.
        operation = spec["paths"]["/payments/{order_id}/pay"]["post"]
    assert operation is not None
    if str(status) not in case["status"].split(","):
        raise ValueError(f"Unexpected HTTP status: {case_id} {status}")
    declared = operation["responses"].get(str(status))
    if declared is None:
        raise ValueError(f"Missing OpenAPI response: {case_id} {status}")
    actual_media = content_type.split(";", 1)[0].strip().lower()
    expected_media = "application/problem+json" if status >= 400 else "application/json"
    if actual_media != expected_media or expected_media not in declared.get("content", {}):
        raise ValueError(f"HTTP media differs from OpenAPI: {case_id} {status}")
    schema = declared["content"][expected_media]["schema"]
    # OpenAPI 3.1 uses JSON Schema 2020-12; retain the document components for local $refs.
    root = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": "#/$defs/response"}
    root["$defs"] = {"response": schema}
    root["components"] = spec.get("components", {})
    Draft202012Validator(root, format_checker=FormatChecker()).validate(body)


def export(path: Path) -> tuple[int, int]:
    spec = document()
    result = check_contract(spec, generate())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(spec, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return result
