from typing import Any

import pytest
import stripe
from scripts.stripe_card_smoke import Delivery, DeliveryRecorder, card_fixtures, verify_card_intent
from scripts.stripe_sandbox_smoke import AMOUNT_MINOR, SmokeFailure
from starlette.types import Message, Receive, Scope, Send


@pytest.mark.parametrize("session_id", ["cs_live_example", "cs_test_", "cs_test_example/confirm", "cs_test_ x"])
def test_card_fixture_rejects_live_or_invalid_sessions(session_id: str) -> None:
    with pytest.raises(SmokeFailure):
        card_fixtures(session_id)


@pytest.mark.parametrize(
    "field,value",
    [("livemode", True), ("status", "processing"), ("amount", 1300), ("amount_received", 0), ("currency", "eur")],
)
def test_card_probe_requires_successful_test_intent_for_exact_money(field: str, value: object) -> None:
    charge: dict[str, Any] = {
        "object": "charge",
        "id": "ch_fixture",
        "livemode": False,
        "paid": True,
        "status": "succeeded",
        "amount": AMOUNT_MINOR,
        "currency": "pln",
        "payment_method_details": {"type": "card", "card": {"brand": "visa"}},
    }
    payload: dict[str, Any] = {
        "object": "payment_intent",
        "id": "pi_fixture",
        "livemode": False,
        "status": "succeeded",
        "amount": AMOUNT_MINOR,
        "amount_received": AMOUNT_MINOR,
        "currency": "pln",
        "latest_charge": charge,
    }
    intent = stripe.PaymentIntent.construct_from(payload, "sk_test_fixture")
    assert verify_card_intent(intent, "pi_fixture") == "ch_fixture"
    payload[field] = value
    with pytest.raises(SmokeFailure):
        verify_card_intent(stripe.PaymentIntent.construct_from(payload, "sk_test_fixture"), "pi_fixture")


def test_card_delivery_repr_does_not_expose_original_payload_or_signature() -> None:
    delivery = Delivery("evt_fixture", b"private customer payload", "private signature")
    assert "private" not in repr(delivery)


async def test_card_recorder_passes_original_bytes_and_signature_without_modifying_asgi_messages() -> None:
    body = b'{ "id":"evt_fixture", "type":"checkout.session.completed", "data":{"object":{"id":"cs_test_fixture"}} }'
    incoming: Message = {"type": "http.request", "body": body, "more_body": False}
    outgoing: Message = {"type": "http.response.start", "status": 200, "headers": []}
    scope: Scope = {
        "type": "http",
        "path": "/payments/webhooks/stripe",
        "headers": [(b"stripe-signature", b"original")],
    }
    sent: list[Message] = []

    async def receive() -> Message:
        return incoming

    async def send(message: Message) -> None:
        sent.append(message)

    async def app(actual_scope: Scope, actual_receive: Receive, actual_send: Send) -> None:
        assert actual_scope is scope
        assert await actual_receive() is incoming
        await actual_send(outgoing)

    recorder = DeliveryRecorder(app)
    recorder.session_id = "cs_test_fixture"
    await recorder(scope, receive, send)
    captured = recorder.deliveries.get_nowait()
    assert captured.body == body and captured.signature == "original" and captured.event_id == "evt_fixture"
    assert sent == [outgoing] and sent[0] is outgoing
