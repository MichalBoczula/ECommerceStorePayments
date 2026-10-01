from uuid import uuid4

import pytest
import stripe
from scripts.stripe_sandbox_smoke import AMOUNT_MINOR, SmokeFailure, require_test_key, verify_session


@pytest.mark.parametrize("key", [None, "", "sk_test_", "sk_live_private", "pk_test_private", "sk_test_ private"])
def test_sandbox_probe_rejects_missing_live_or_invalid_keys_without_exposing_them(key: str | None) -> None:
    with pytest.raises(SmokeFailure) as error:
        require_test_key(key)
    if key and "private" in key:
        assert key not in str(error.value)


def test_sandbox_probe_accepts_test_key_without_displaying_it() -> None:
    secret = require_test_key("sk_test_fixture")
    assert secret.get_secret_value() == "sk_test_fixture"
    assert "sk_test_fixture" not in str(secret)


@pytest.mark.parametrize(
    "field,value",
    [
        ("livemode", True),
        ("id", "cs_test_unrelated"),
        ("amount_total", AMOUNT_MINOR + 1),
        ("currency", "eur"),
        ("payment_method_types", ["card"]),
        ("payment_status", "paid"),
        ("status", "expired"),
        ("client_reference_id", str(uuid4())),
        ("metadata", None),
        ("metadata", {}),
        ("metadata", {"payment_id": str(uuid4()), "order_id": str(uuid4()), "attempt_id": str(uuid4())}),
    ],
)
def test_sandbox_probe_rejects_wrong_mode_money_methods_or_association(field: str, value: object) -> None:
    payment_id, order_id = uuid4(), uuid4()
    payload: dict[str, object] = {
        "id": "cs_test_fixture",
        "object": "checkout.session",
        "livemode": False,
        "mode": "payment",
        "status": "open",
        "payment_status": "unpaid",
        "amount_total": AMOUNT_MINOR,
        "currency": "pln",
        "payment_method_types": ["card", "blik"],
        "client_reference_id": str(payment_id),
        "metadata": {"payment_id": str(payment_id), "order_id": str(order_id), "attempt_id": str(uuid4())},
    }
    session = stripe.checkout.Session.construct_from(payload, "sk_test_fixture")
    verify_session(session, "cs_test_fixture", payment_id, order_id)
    payload[field] = value
    session = stripe.checkout.Session.construct_from(payload, "sk_test_fixture")
    with pytest.raises(SmokeFailure):
        verify_session(session, "cs_test_fixture", payment_id, order_id)
