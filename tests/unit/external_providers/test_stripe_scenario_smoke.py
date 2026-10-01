from typing import Any, Literal, cast
from uuid import uuid4

import pytest
import stripe
from pydantic import SecretStr
from scripts.stripe_sandbox_smoke import AMOUNT_MINOR, SmokeFailure
from scripts.stripe_scenario_smoke import (
    ScenarioRecorder,
    guided_challenge,
    matches_payment,
    provider_blik_probe,
    scenario_fixtures,
    verify_blik,
    verify_decline,
    verify_three_ds,
)
from starlette.types import Message, Receive, Scope, Send


def intent_payload() -> dict[str, Any]:
    return {
        "object": "payment_intent",
        "id": "pi_fixture",
        "livemode": False,
        "amount": AMOUNT_MINOR,
        "amount_received": 0,
        "currency": "pln",
        "status": "requires_payment_method",
        "last_payment_error": {"code": "card_declined", "decline_code": "generic_decline"},
    }


def successful_payload(method: str) -> dict[str, Any]:
    payload = intent_payload()
    payload.update(status="succeeded", amount_received=AMOUNT_MINOR, last_payment_error=None)
    payload["latest_charge"] = {
        "object": "charge",
        "id": "ch_fixture",
        "livemode": False,
        "paid": True,
        "status": "succeeded",
        "amount": AMOUNT_MINOR,
        "currency": "pln",
        "payment_method_details": {
            "type": method,
            "card": {
                "brand": "visa",
                "three_d_secure": {"result": "authenticated", "authentication_flow": "challenge"},
            },
        },
    }
    return payload


@pytest.mark.parametrize("method", ["visa", "decline"])
@pytest.mark.parametrize("session_id", ["cs_live_fixture", "cs_test_", "cs_test_x/confirm"])
def test_scenario_fixtures_reject_non_sandbox_sessions(method: str, session_id: str) -> None:
    with pytest.raises(SmokeFailure):
        scenario_fixtures(session_id, cast(Literal["visa", "decline"], method))


def test_fixture_decline_is_explicit_but_not_silently_treated_as_success() -> None:
    fixture = scenario_fixtures("cs_test_fixture", "decline")
    assert fixture["fixtures"][1]["params"]["card"]["token"] == "tok_visa_chargeDeclined"
    assert fixture["fixtures"][2]["expected_error_type"] == "card_error"
    assert "expected_error_type" not in scenario_fixtures("cs_test_fixture", "visa")["fixtures"][2]
    with pytest.raises(SmokeFailure):
        scenario_fixtures("cs_test_fixture", cast(Literal["visa", "decline"], "blik"))


@pytest.mark.parametrize(
    "field,value",
    [
        ("livemode", True),
        ("amount", 1300),
        ("amount_received", 1299),
        ("currency", "eur"),
        ("status", "succeeded"),
        ("last_payment_error", {"code": "api_error"}),
    ],
)
def test_decline_requires_provider_card_decline_and_zero_received(field: str, value: object) -> None:
    payload = intent_payload()
    verify_decline(stripe.PaymentIntent.construct_from(payload, "sk_test_fixture"))
    payload[field] = value
    with pytest.raises(SmokeFailure):
        verify_decline(stripe.PaymentIntent.construct_from(payload, "sk_test_fixture"))


@pytest.mark.parametrize(
    "field,value",
    [
        ("livemode", True),
        ("paid", False),
        ("status", "failed"),
        ("amount", 1300),
        ("currency", "eur"),
        ("payment_method_details", {"type": "card"}),
    ],
)
def test_blik_success_requires_real_successful_blik_charge(field: str, value: object) -> None:
    payload = successful_payload("blik")
    assert verify_blik(stripe.PaymentIntent.construct_from(payload, "sk_test_fixture")) == "ch_fixture"
    payload["latest_charge"][field] = value
    with pytest.raises(SmokeFailure):
        verify_blik(stripe.PaymentIntent.construct_from(payload, "sk_test_fixture"))


@pytest.mark.parametrize(
    "details",
    [
        None,
        {"result": "attempt_acknowledged", "authentication_flow": "challenge"},
        {"result": "authenticated", "authentication_flow": "frictionless"},
        {"result": "failed", "authentication_flow": "challenge"},
    ],
)
def test_3ds_success_requires_actual_authenticated_challenge(details: object) -> None:
    payload = successful_payload("card")
    verify_three_ds(stripe.PaymentIntent.construct_from(payload, "sk_test_fixture"), "success")
    payload["latest_charge"]["payment_method_details"]["card"]["three_d_secure"] = details
    with pytest.raises(SmokeFailure):
        verify_three_ds(stripe.PaymentIntent.construct_from(payload, "sk_test_fixture"), "success")


def test_failed_3ds_requires_authentication_error_and_cancellation_requires_authentication_action() -> None:
    payload = intent_payload()
    with pytest.raises(SmokeFailure):
        verify_three_ds(stripe.PaymentIntent.construct_from(payload, "sk_test_fixture"), "failure")
    payload["last_payment_error"] = {"code": "payment_intent_authentication_failure"}
    verify_three_ds(stripe.PaymentIntent.construct_from(payload, "sk_test_fixture"), "failure")
    verify_three_ds(stripe.PaymentIntent.construct_from(payload, "sk_test_fixture"), "cancel")
    payload.update(status="requires_action", last_payment_error=None, next_action={"type": "use_stripe_sdk"})
    verify_three_ds(stripe.PaymentIntent.construct_from(payload, "sk_test_fixture"), "cancel")
    payload["next_action"] = {"type": "redirect_to_url"}
    with pytest.raises(SmokeFailure):
        verify_three_ds(stripe.PaymentIntent.construct_from(payload, "sk_test_fixture"), "cancel")
    with pytest.raises(SmokeFailure):
        verify_three_ds(stripe.PaymentIntent.construct_from(successful_payload("card"), "sk_test_fixture"), "cancel")


def test_guided_3ds_refuses_noninteractive_output_before_printing_checkout_url(
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = stripe.checkout.Session.construct_from(
        {"livemode": False, "url": "https://checkout.stripe.com/private"}, "sk_test_fixture"
    )
    with pytest.raises(SmokeFailure):
        guided_challenge(session, "3ds-success")
    assert "private" not in capsys.readouterr().out


@pytest.mark.parametrize("matching", [True, False])
async def test_outage_rejects_only_our_event_and_keeps_original_messages_for_recovery(matching: bool) -> None:
    session_id = "cs_test_fixture" if matching else "cs_test_unrelated"
    body = (
        '{ "id":"evt_fixture", "type":"checkout.session.completed", "data":{"object":{"id":"' + session_id + '"}} }'
    ).encode()
    incoming: Message = {"type": "http.request", "body": body, "more_body": False}
    scope: Scope = {
        "type": "http",
        "path": "/payments/webhooks/stripe",
        "headers": [(b"stripe-signature", b"original")],
    }
    sent: list[Message] = []
    called: list[bool] = []

    async def receive() -> Message:
        return incoming

    async def send(message: Message) -> None:
        sent.append(message)

    async def app(actual_scope: Scope, actual_receive: Receive, actual_send: Send) -> None:
        called.append(True)
        assert actual_scope is scope and await actual_receive() is incoming
        await actual_send({"type": "http.response.start", "status": 200, "headers": []})

    recorder = ScenarioRecorder(app, reject_once=True)
    recorder.session_id = "cs_test_fixture"
    await recorder(scope, receive, send)
    if matching:
        assert called == [] and sent[0]["status"] == 503
        delivery = recorder.rejected.get_nowait()
        assert delivery.body == body and delivery.signature == "original"
        assert "original" not in repr(delivery)
        sent.clear()
        await recorder(scope, receive, send)
        assert called == [True] and sent[0]["status"] == 200
        assert recorder.deliveries.get_nowait() == delivery
    else:
        assert called == [True] and sent[0]["status"] == 200
        assert recorder.rejected.empty() and recorder.reject_once


def test_intent_lookup_ignores_other_account_metadata() -> None:
    payment_id = uuid4()
    payload = intent_payload()
    payload["metadata"] = {}
    assert not matches_payment(stripe.PaymentIntent.construct_from(payload, "sk_test_fixture"), payment_id)
    payload["metadata"] = {"payment_id": str(uuid4())}
    assert not matches_payment(stripe.PaymentIntent.construct_from(payload, "sk_test_fixture"), payment_id)
    payload["metadata"] = {"payment_id": str(payment_id)}
    assert matches_payment(stripe.PaymentIntent.construct_from(payload, "sk_test_fixture"), payment_id)


@pytest.mark.parametrize("key", ["", "sk_live_fixture", "pk_test_fixture", "sk_test_ short"])
def test_provider_only_probe_guards_key_before_creating_stripe_client(
    key: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden_client(*args: object, **kwargs: object) -> None:
        raise AssertionError("Unsafe key reached Stripe client construction")

    monkeypatch.setattr(stripe, "StripeClient", forbidden_client)
    with pytest.raises(SmokeFailure):
        provider_blik_probe(SecretStr(key))
