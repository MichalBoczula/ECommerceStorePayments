"""Check authored metadata and examples against the one generated OpenAPI document."""

from collections.abc import Iterator
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from ecommerce_store_payments.api.contracts.checkout_response import CheckoutResponse
from ecommerce_store_payments.api.contracts.payment_response import PaymentResponse
from ecommerce_store_payments.api.contracts.webhook_request import webhook_schemas
from ecommerce_store_payments.api.errors import ProblemDetails
from ecommerce_store_payments.api.routes.health import HealthResponse
from ecommerce_store_payments.api.routes.webhooks import WebhookAcknowledgement


def validator(spec: dict[str, Any], schema: dict[str, Any]) -> Draft202012Validator:
    return Draft202012Validator(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$defs": {"value": schema},
            "$ref": "#/$defs/value",
            "components": spec.get("components", {}),
        },
        format_checker=FormatChecker(),
    )


def schemas(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for key, child in value.items():
            if key not in {"examples", "example", "default", "const", "enum", "if", "then", "else", "not"}:
                yield from schemas(child)
    elif isinstance(value, list):
        for child in value:
            yield from schemas(child)


def check_metadata(spec: dict[str, Any]) -> None:
    for schema in schemas(spec):
        for name, field in schema.get("properties", {}).items():
            if not field.get("description", "").strip() or not field.get("examples"):
                raise ValueError(f"Missing authored property description/examples: {name}")
        if "examples" in schema:
            if not isinstance(schema["examples"], list) or not schema["examples"]:
                raise ValueError("Schema examples must be a nonempty typed list")
            for example in schema["examples"]:
                validator(spec, schema).validate(example)
    output_models = {"PaymentResponse", "CheckoutResponse", "HealthResponse", "WebhookAcknowledgement"}
    for name in output_models:
        schema = spec["components"]["schemas"][name]
        if (
            set(schema.get("required", [])) != set(schema["properties"])
            or schema.get("additionalProperties") is not False
        ):
            raise ValueError(f"Output member presence differs from serialized responses: {name}")
    for model in (PaymentResponse, CheckoutResponse, HealthResponse, WebhookAcknowledgement):
        native = model.model_json_schema(mode="serialization")
        if schema_shape(native, native) != schema_shape(spec["components"]["schemas"][model.__name__], spec):
            raise ValueError(f"Output schema differs from serialized source: {model.__name__}")
    for name, native in webhook_schemas().items():
        if schema_shape(native, spec) != schema_shape(spec["components"]["schemas"][name], spec):
            raise ValueError("Webhook schema differs from authored verifier documentation")
    native_problem = ProblemDetails.model_json_schema(by_alias=True, mode="serialization")
    for path, item in spec["paths"].items():
        for method, operation in item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            if path.endswith(("/pay", "/checkout")) and "requestBody" in operation:
                raise ValueError("Bodyless commands cannot advertise a JSON request body")
            for parameter in operation.get("parameters", []):
                if (
                    not parameter.get("description")
                    or not parameter["schema"].get("examples")
                    or not parameter.get("required")
                ):
                    raise ValueError("Missing required parameter description/examples")
                if parameter["in"] == "path" and (
                    parameter["schema"].get("type") != "string" or parameter["schema"].get("format") != "uuid"
                ):
                    raise ValueError("Order route parameter must retain its source UUID format")
            for status, response in operation["responses"].items():
                wanted = {"X-Trace-Id", "Content-Length"} | ({"Allow"} if status == "405" else set())
                if set(response.get("headers", {})) != wanted:
                    raise ValueError("Missing documented response headers")
                for header in response["headers"].values():
                    if (
                        not header.get("required")
                        or not header.get("description")
                        or not header["schema"].get("examples")
                    ):
                        raise ValueError("Missing response header description/examples")
                if int(status) >= 400:
                    schema = response["content"]["application/problem+json"]["schema"]
                    if set(schema["required"]) != set(schema["properties"]):
                        raise ValueError("All serialized problem members must be required")
                    if schema_shape(schema, spec) != schema_shape(native_problem, native_problem):
                        raise ValueError("Problem schema differs from serialized source")


def schema_shape(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    """Resolve local references and compare wire constraints independently of annotations."""
    if "$ref" in schema:
        target: Any = root
        for part in schema["$ref"].removeprefix("#/").split("/"):
            target = target[part.replace("~1", "/").replace("~0", "~")]
        return schema_shape(target, root)
    result = {}
    for key, value in schema.items():
        if key in {"title", "description", "examples", "default", "$defs"}:
            continue
        if key == "properties":
            result[key] = {name: schema_shape(field, root) for name, field in value.items()}
        elif key in {"items", "if", "then", "else", "not"} and isinstance(value, dict):
            result[key] = schema_shape(value, root)
        elif key in {"anyOf", "oneOf", "allOf"}:
            result[key] = [schema_shape(field, root) for field in value]
        else:
            result[key] = value
    return result
