"""Document existing public HTTP behavior without changing request binding or handlers."""

import json
from copy import deepcopy
from typing import Any

from ecommerce_store_payments.api.contracts.checkout_response import CheckoutResponse
from ecommerce_store_payments.api.contracts.payment_response import PaymentResponse
from ecommerce_store_payments.api.contracts.webhook_request import ORDER_ID, webhook_schemas

TRACE_EXAMPLE = "0123456789abcdef0123456789abcdef"


def enrich_http_schema(schema: dict[str, Any]) -> None:
    # Once the automatic 422 responses are removed, their unreferenced internal
    # validation models are not public response contracts.
    for name in ("HTTPValidationError", "ValidationError"):
        if f"#/components/schemas/{name}" not in json.dumps(schema):
            schema["components"]["schemas"].pop(name, None)
    # FastAPI's OpenAPI model serialization drops null-valued object members from
    # examples. Restore the examples from the same model metadata so required
    # nullable response fields remain visible in complete, schema-valid examples.
    for model in (PaymentResponse, CheckoutResponse):
        source = model.model_json_schema(mode="serialization")
        target = schema["components"]["schemas"][model.__name__]
        target["examples"] = deepcopy(source["examples"])
        for name, field in source["properties"].items():
            target["properties"][name]["examples"] = deepcopy(field["examples"])
    schema["components"]["schemas"].update(webhook_schemas())
    for path_item in schema["paths"].values():
        methods = sorted(method.upper() for method in path_item if method in {"get", "post", "put", "patch", "delete"})
        for method in methods:
            operation = path_item[method.lower()]
            for parameter in operation.get("parameters", []):
                if parameter["in"] == "path" and parameter["name"] == "order_id":
                    parameter["description"] = (
                        "Order UUID. The command loads authoritative order values from Orders; no "
                        "client-supplied amount is accepted."
                    )
                    parameter["schema"]["examples"] = [ORDER_ID]
            for status, response in operation["responses"].items():
                response["headers"] = deepcopy(
                    {
                        "X-Trace-Id": {
                            "description": (
                                "Fresh server-generated lowercase hexadecimal trace ID; identical to traceId in "
                                "problem bodies."
                            ),
                            "required": True,
                            "schema": {"type": "string", "pattern": "^[0-9a-f]{32}$", "examples": [TRACE_EXAMPLE]},
                        },
                        "Content-Length": {
                            "description": "Byte length of the actual response body.",
                            "required": True,
                            "schema": {"type": "string", "pattern": "^[0-9]+$", "examples": ["20"]},
                        },
                    }
                )
                if status == "405":
                    allowed = ", ".join(methods)
                    response["headers"]["Allow"] = {
                        "description": "Methods supported by the matched route.",
                        "required": True,
                        "schema": {"type": "string", "const": allowed, "examples": [allowed]},
                    }
