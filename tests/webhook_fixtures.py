import hashlib
import hmac
import json
import time
from typing import Any

from ecommerce_store_payments.application.payments.webhook import (
    CheckoutNotification,
    CheckoutOutcome,
    VerifiedWebhook,
)
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment

WEBHOOK_SECRET = "whsec_fixture"


def notification(
    payment: Payment, outcome: CheckoutOutcome = CheckoutOutcome.SUCCEEDED, event_id: str = "evt_fixture"
) -> VerifiedWebhook:
    assert payment.checkout_attempt_id is not None
    return VerifiedWebhook(
        event_id,
        "checkout.session.completed",
        event_id + "_digest",
        outcome,
        CheckoutNotification(
            payment.id,
            payment.order_id,
            payment.checkout_attempt_id,
            payment.money,
            payment.provider_session_id or "cs_test_fixture",
            "pi_fixture",
        ),
    )


def payload_for(
    payment: Payment, event_type: str = "checkout.session.completed", event_id: str = "evt_fixture"
) -> dict[str, Any]:
    assert payment.checkout_attempt_id is not None
    return {
        "id": event_id,
        "object": "event",
        "type": event_type,
        "livemode": False,
        "api_version": "2026-08-26.dahlia",
        "created": int(time.time()),
        "data": {
            "object": {
                "id": payment.provider_session_id or "cs_test_fixture",
                "object": "checkout.session",
                "livemode": False,
                "mode": "payment",
                "status": "complete",
                "payment_status": "paid",
                "amount_total": payment.money.amount_minor,
                "currency": payment.money.currency.lower(),
                "client_reference_id": str(payment.id),
                "payment_intent": "pi_fixture",
                "metadata": {
                    "payment_id": str(payment.id),
                    "order_id": str(payment.order_id),
                    "attempt_id": str(payment.checkout_attempt_id),
                },
            }
        },
    }


def encode(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload).encode()


def signature(payload: bytes, secret: str = WEBHOOK_SECRET, timestamp: int | None = None) -> str:
    timestamp = int(time.time()) if timestamp is None else timestamp
    digest = hmac.new(secret.encode(), str(timestamp).encode() + b"." + payload, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"
