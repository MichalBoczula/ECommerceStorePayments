"""Documentation metadata only: the route still verifies original bytes before parsing.

These schemas describe the verifier's supported snapshot variants. They are never
used as FastAPI request bindings or as a replacement for signature, duplicate-key,
UUID association, account/context or payment-state verification.
"""

from copy import deepcopy
from typing import Any

CHECKOUT_EVENTS = (
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
    "checkout.session.async_payment_failed",
    "checkout.session.expired",
)
PAYMENT_ID = "33333333-3333-4333-8333-333333333333"
ORDER_ID = "11111111-1111-4111-8111-111111111111"
ATTEMPT_ID = "44444444-4444-4444-8444-444444444444"


def identifier(description: str, example: str, prefix: str = "") -> dict[str, Any]:
    return {
        "type": "string",
        "description": description,
        "examples": [example],
        "minLength": len(prefix) + 1,
        "maxLength": 255,
        "pattern": "^" + prefix + "[!-~]+$",
    }


def event_example(event_type: str, *, paid: bool = True) -> dict[str, Any]:
    expired = event_type == "checkout.session.expired"
    succeeded = event_type in CHECKOUT_EVENTS[:2] and paid
    return {
        "id": "evt_documentation",
        "object": "event",
        "type": event_type,
        "livemode": False,
        "data": {
            "object": {
                "id": "cs_test_fixture",
                "object": "checkout.session",
                "livemode": False,
                "mode": "payment",
                "status": "expired" if expired else "complete",
                "payment_status": "paid" if succeeded else "unpaid",
                "amount_total": 1299,
                "currency": "pln",
                "client_reference_id": PAYMENT_ID,
                "payment_intent": "pi_fixture" if succeeded else None,
                "metadata": {"payment_id": PAYMENT_ID, "order_id": ORDER_ID, "attempt_id": ATTEMPT_ID},
            }
        },
    }


def webhook_schemas() -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "type": "object",
        "description": "Payment, order and checkout-attempt associations verified against durable state.",
        "required": ["payment_id", "order_id", "attempt_id"],
        "additionalProperties": True,
        "properties": {
            key: {"type": "string", "format": "uuid", "description": description, "examples": [example]}
            for key, description, example in [
                ("payment_id", "Nonzero payment UUID; must match client_reference_id.", PAYMENT_ID),
                ("order_id", "Nonzero order UUID for this payment.", ORDER_ID),
                ("attempt_id", "Nonzero UUID of the existing checkout attempt.", ATTEMPT_ID),
            ]
        },
    }
    session: dict[str, Any] = {
        "type": "object",
        "description": "Test-mode PLN payment checkout snapshot; extra provider fields are allowed.",
        "additionalProperties": True,
        "required": [
            "id",
            "object",
            "livemode",
            "mode",
            "status",
            "payment_status",
            "amount_total",
            "currency",
            "client_reference_id",
            "metadata",
        ],
        "properties": {
            "id": identifier("Test-mode session identifier for this checkout attempt.", "cs_test_fixture", "cs_test_"),
            "object": {
                "type": "string",
                "const": "checkout.session",
                "description": "Stripe checkout snapshot object discriminator.",
                "examples": ["checkout.session"],
            },
            "livemode": {
                "type": "boolean",
                "const": False,
                "description": "Only test-mode snapshots are accepted.",
                "examples": [False],
            },
            "mode": {
                "type": "string",
                "const": "payment",
                "description": "Only one-time payment checkout is supported.",
                "examples": ["payment"],
            },
            "status": {
                "type": "string",
                "enum": ["complete", "expired"],
                "description": "Complete for completion/async events; expired for expiry events.",
                "examples": ["complete", "expired"],
            },
            "payment_status": {
                "type": "string",
                "enum": ["paid", "unpaid"],
                "description": "Unpaid completion remains waiting; paid completion requires a payment_intent.",
                "examples": ["paid", "unpaid"],
            },
            "amount_total": {
                "type": "integer",
                "minimum": 200,
                "maximum": 99_999_999,
                "description": "PLN minor units; booleans are not amounts.",
                "examples": [1299],
            },
            "currency": {
                "type": "string",
                "const": "pln",
                "description": "Provider checkout currency, lowercase PLN.",
                "examples": ["pln"],
            },
            "client_reference_id": {
                "type": "string",
                "description": "Must exactly equal the canonical payment_id UUID string.",
                "examples": [PAYMENT_ID],
            },
            "payment_intent": {
                "anyOf": [identifier("Provider payment identifier.", "pi_fixture", "pi_"), {"type": "null"}],
                "description": "Required and non-null for paid outcomes; optional/nullable for unpaid outcomes.",
                "examples": ["pi_fixture", None],
            },
            "metadata": {
                **metadata,
                "examples": [{"payment_id": PAYMENT_ID, "order_id": ORDER_ID, "attempt_id": ATTEMPT_ID}],
            },
        },
    }
    base: dict[str, Any] = {
        "type": "object",
        "additionalProperties": True,
        "required": ["id", "object", "type", "livemode"],
        "properties": {
            "id": identifier(
                "Stable Stripe event identity; duplicate deliveries reconcile through its durable receipt.",
                "evt_documentation",
                "evt_",
            ),
            "object": {
                "type": "string",
                "const": "event",
                "description": "Snapshot event envelope discriminator.",
                "examples": ["event"],
            },
            "type": identifier(
                "Event type; supported checkout types are processed, other valid types are acknowledged as ignored.",
                CHECKOUT_EVENTS[0],
            ),
            "livemode": {
                "type": "boolean",
                "const": False,
                "description": "Only test-mode events are accepted.",
                "examples": [False],
            },
            "account": {
                "type": "null",
                "description": "Connect account must be absent or null; the endpoint secret identifies the account.",
                "examples": [None],
            },
            "context": {
                "type": "null",
                "description": "Organization context must be absent or null.",
                "examples": [None],
            },
        },
    }
    variants: list[dict[str, Any]] = []
    for event_type in CHECKOUT_EVENTS:
        variant = deepcopy(base)
        variant["properties"]["type"]["const"] = event_type
        variant["properties"]["type"]["examples"] = [event_type]
        variant["required"].append("data")
        current = deepcopy(session)
        current["properties"]["status"]["const"] = "expired" if event_type == CHECKOUT_EVENTS[3] else "complete"
        current["properties"]["status"]["examples"] = [current["properties"]["status"]["const"]]
        if event_type in CHECKOUT_EVENTS[2:]:
            current["properties"]["payment_status"]["const"] = "unpaid"
            current["properties"]["payment_status"]["examples"] = ["unpaid"]
        else:
            current["if"] = {"properties": {"payment_status": {"const": "paid"}}, "required": ["payment_status"]}
            current["then"] = {"required": ["payment_intent"], "properties": {"payment_intent": {"type": "string"}}}
        variant["properties"]["data"] = {
            "type": "object",
            "description": "Original provider snapshot container.",
            "required": ["object"],
            "properties": {"object": {**current, "examples": [event_example(event_type)["data"]["object"]]}},
            "examples": [event_example(event_type)["data"]],
            "additionalProperties": True,
        }
        variant["title"] = event_type
        variants.append(variant)
    unknown = deepcopy(base)
    unknown["title"] = "Other event types"
    unknown["properties"]["type"]["not"] = {"enum": list(CHECKOUT_EVENTS)}
    unknown["properties"]["type"]["examples"] = ["payment_intent.created"]
    variants.append(unknown)
    return {
        "StripeWebhookEvent": {
            "description": (
                "Supported verified snapshot shapes and the ignored-event envelope. Signature "
                "freshness, original signed bytes, unique JSON keys and cross-field/state associations "
                "remain verifier responsibilities."
            ),
            "oneOf": variants,
            "examples": [
                *(event_example(t) for t in CHECKOUT_EVENTS),
                event_example(CHECKOUT_EVENTS[0], paid=False),
                {"id": "evt_ignored", "object": "event", "type": "payment_intent.created", "livemode": False},
            ],
        }
    }


def webhook_request() -> dict[str, Any]:
    return {
        "parameters": [
            {
                "name": "Stripe-Signature",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "minLength": 1, "examples": ["t=1790856000,v1=" + "0" * 64]},
                "description": (
                    "Exactly one nonempty signature header. Timestamp/v1 signatures cover the original "
                    "UTF-8 bytes with a 300-second tolerance. Example is illustrative; recompute for each "
                    "body and timestamp."
                ),
            }
        ],
        "requestBody": {
            "required": True,
            "description": (
                "Original JSON snapshot bytes, at most 1 MiB. Signature verification precedes JSON "
                "parsing; reserialization invalidates the signature. Duplicate JSON keys, "
                "live/Connect/organization events and invalid associations are rejected. Schema "
                "metadata adds no request-binding layer."
            ),
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/StripeWebhookEvent"}}},
        },
    }
