"""Real Stripe sandbox scenarios; interactive 3DS remains a guided browser check."""

import argparse
import asyncio
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path
from queue import Empty, Queue
from tempfile import TemporaryDirectory
from time import monotonic, sleep, time
from typing import Any, Literal, cast
from uuid import UUID

import httpx
import stripe
from bson.binary import Binary, UuidRepresentation
from pydantic import SecretStr
from pymongo import MongoClient
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ecommerce_store_payments.infrastructure.clients.stripe.checkout_provider import STRIPE_API_VERSION
from ecommerce_store_payments.infrastructure.persistence.mongodb.fulfill_payments import run as fulfill
from scripts.stripe_card_smoke import (
    Delivery,
    DeliveryRecorder,
    card_fixtures,
    payments_server,
    stripe_listener,
    verify_card_intent,
    verify_fulfillment,
)
from scripts.stripe_sandbox_smoke import (
    AMOUNT_MINOR,
    Sandbox,
    SmokeFailure,
    checkout,
    sandbox_environment,
    verify_session,
)

Scenario = Literal["blik", "decline-retry", "expiry", "webhook-retry", "3ds-success", "3ds-failure", "3ds-cancel"]
SCENARIOS = ("blik", "decline-retry", "expiry", "webhook-retry", "3ds-success", "3ds-failure", "3ds-cancel")
EVENTS = (
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
    "checkout.session.async_payment_failed",
    "checkout.session.expired",
)


def scenario_fixtures(session_id: str, method: Literal["visa", "decline", "blik"]) -> dict[str, Any]:
    fixture = cast(dict[str, Any], card_fixtures(session_id))
    if method == "decline":
        fixture["fixtures"][1]["params"]["card"]["token"] = "tok_visa_chargeDeclined"
        fixture["fixtures"][2]["expected_error_type"] = "card_error"
    elif method == "blik":
        fixture["fixtures"][2]["expected_error_type"] = "invalid_request_error"
        fixture["fixtures"][1]["params"] = {
            "type": "blik",
            "billing_details": {"email": "sandbox-smoke@example.test", "name": "Sandbox Smoke Client"},
        }
    elif method != "visa":
        raise SmokeFailure("Unsupported sandbox fixture method.")
    return fixture


def confirm(session_id: str, secret: SecretStr, method: Literal["visa", "decline", "blik"]) -> None:
    fixture = scenario_fixtures(session_id, method)
    with TemporaryDirectory(prefix="stripe-scenario-") as directory:
        path = Path(directory) / "fixture.json"
        path.write_text(json.dumps(fixture), encoding="utf-8")
        result = subprocess.run(
            ["stripe", "fixtures", str(path), "--api-version", STRIPE_API_VERSION],
            env={**os.environ, "STRIPE_API_KEY": secret.get_secret_value(), "NO_COLOR": "1"},
            capture_output=True,
            timeout=60,
            check=False,
        )
        if result.returncode:
            # Allowlist diagnostic identifiers; never include arbitrary provider text or payloads.
            private_output = (result.stdout + result.stderr).decode(errors="replace")
            diagnostics: list[str] = []
            for field in ("code", "param"):
                match = re.search(r'"' + field + r'"\s*:\s*"([a-z][a-z0-9_.\[\]]{0,80})"', private_output)
                if match:
                    diagnostics.append(f"{field}={match.group(1)}")
            suffix = "; " + ", ".join(diagnostics) if diagnostics else ""
            raise SmokeFailure(f"Stripe CLI scenario confirmation failed{suffix}; private output suppressed.")


class ScenarioRecorder(DeliveryRecorder):
    """Test-only transient outage before the real route; never alter signed bytes on replay."""

    def __init__(self, app: ASGIApp, *, reject_once: bool = False) -> None:
        super().__init__(app, EVENTS)
        self.deliveries = Queue(maxsize=8)
        self.rejected: Queue[Delivery] = Queue(maxsize=1)
        self.reject_once = reject_once

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if not self.reject_once or scope["type"] != "http" or scope["path"] != "/payments/webhooks/stripe":
            await super().__call__(scope, receive, send)
            return
        messages: list[Message] = []
        body = bytearray()
        while True:
            message = await receive()
            messages.append(message)
            body.extend(message.get("body", b""))
            if len(body) > 1024 * 1024:
                raise SmokeFailure("Test-only outage buffer exceeded the route limit.")
            if not message.get("more_body", False):
                break
        event: dict[str, Any] = {}
        try:
            event = json.loads(body)
            matches = event["type"] == "checkout.session.completed" and event["data"]["object"]["id"] == self.session_id
        except KeyError, TypeError, ValueError:
            matches = False
        if matches:
            signature = next(value.decode() for key, value in scope["headers"] if key == b"stripe-signature")
            self.reject_once = False
            self.rejected.put_nowait(Delivery(event["id"], bytes(body), signature))
            await send({"type": "http.response.start", "status": 503, "headers": []})
            await send({"type": "http.response.body", "body": b""})
            return
        position = 0

        async def buffered_receive() -> Message:
            nonlocal position
            if position < len(messages):
                result = messages[position]
                position += 1
                return result
            return await receive()

        await super().__call__(scope, buffered_receive, send)


def payment(api: httpx.Client, order_id: UUID) -> dict[str, Any]:
    response = api.get(f"/payments/order/{order_id}")
    if response.status_code != 200:
        raise SmokeFailure("Payments lookup failed.")
    return response.json()


def wait_payment(api: httpx.Client, order_id: UUID, status: str) -> dict[str, Any]:
    deadline = monotonic() + 90
    while monotonic() < deadline:
        result = payment(api, order_id)
        if result.get("status") == status:
            return result
        sleep(0.5)
    raise SmokeFailure(f"Real signed delivery did not establish Payment {status} in time.")


def verify_unfulfilled(sandbox: Sandbox, api: httpx.Client, expected: str) -> None:
    current = payment(api, sandbox.order_id)
    if current.get("status") != expected or asyncio.run(fulfill(sandbox.settings, 10)) != 0:
        raise SmokeFailure("Unpaid checkout incorrectly changed Payment or scheduled fulfillment.")
    guid = Binary.from_uuid(sandbox.order_id, uuid_representation=UuidRepresentation.STANDARD)
    order = sandbox.invoice_database["orders"].find_one({"_id": guid})
    if order is None or order["Status"] != 2 or sandbox.invoice_database["invoices"].count_documents({"OrderId": guid}):
        raise SmokeFailure("Unpaid checkout changed Created order or generated an invoice.")


def matches_payment(intent: stripe.PaymentIntent, payment_id: UUID) -> bool:
    try:
        return intent.metadata["payment_id"] == str(payment_id)
    except KeyError:
        return False


def find_intent(provider: stripe.StripeClient, payment_id: UUID, since: int) -> stripe.PaymentIntent:
    deadline = monotonic() + 20
    while monotonic() < deadline:
        matches = [
            intent
            for intent in provider.v1.payment_intents.list({"created": {"gte": since}, "limit": 100}).auto_paging_iter()
            if matches_payment(intent, payment_id)
        ]
        if len(matches) == 1:
            return provider.v1.payment_intents.retrieve(matches[0].id, {"expand": ["latest_charge"]})
        if len(matches) > 1:
            raise SmokeFailure("Checkout unexpectedly created multiple PaymentIntents.")
        sleep(0.5)
    raise SmokeFailure("No Stripe PaymentIntent matched the Payments metadata.")


def verify_decline(intent: stripe.PaymentIntent) -> None:
    error = intent.last_payment_error
    if (
        intent.livemode is not False
        or intent.amount != AMOUNT_MINOR
        or intent.currency != "pln"
        or intent.amount_received != 0
        or intent.status != "requires_payment_method"
        or error is None
        or error.code != "card_declined"
        or error.decline_code != "generic_decline"
    ):
        raise SmokeFailure("Stripe did not report the expected genuine declined-card result.")


def verify_blik(intent: stripe.PaymentIntent) -> str:
    charge = intent.latest_charge
    if (
        intent.livemode is not False
        or intent.status != "succeeded"
        or intent.amount != AMOUNT_MINOR
        or intent.amount_received != AMOUNT_MINOR
        or intent.currency != "pln"
        or not isinstance(charge, stripe.Charge)
        or charge.livemode is not False
        or charge.paid is not True
        or charge.status != "succeeded"
        or charge.amount != AMOUNT_MINOR
        or charge.currency != "pln"
        or charge.payment_method_details is None
        or charge.payment_method_details.type != "blik"
    ):
        raise SmokeFailure("Stripe did not confirm the expected successful sandbox BLIK charge.")
    return charge.id


def verify_three_ds(intent: stripe.PaymentIntent, outcome: Literal["success", "failure", "cancel"]) -> None:
    if intent.livemode is not False or intent.amount != AMOUNT_MINOR or intent.currency != "pln":
        raise SmokeFailure("3DS result does not match the sandbox purchase.")
    if outcome == "success":
        verify_card_intent(intent, intent.id)
        charge = intent.latest_charge
        assert isinstance(charge, stripe.Charge)
        details = charge.payment_method_details
        authentication = details.card.three_d_secure if details is not None and details.card is not None else None
        if (
            authentication is None
            or authentication.result != "authenticated"
            or authentication.authentication_flow != "challenge"
        ):
            raise SmokeFailure("Successful payment did not prove an authenticated 3DS challenge.")
    elif outcome == "failure":
        if (
            intent.status != "requires_payment_method"
            or intent.amount_received != 0
            or intent.last_payment_error is None
            or intent.last_payment_error.code != "payment_intent_authentication_failure"
        ):
            raise SmokeFailure("Stripe did not record the expected failed 3DS authentication.")
    elif outcome == "cancel":
        if intent.amount_received != 0 or intent.status not in {"requires_action", "requires_payment_method"}:
            raise SmokeFailure("Canceled browser challenge unexpectedly completed the payment.")
        if intent.status == "requires_action" and (
            intent.next_action is None or intent.next_action.type != "use_stripe_sdk"
        ):
            raise SmokeFailure("Canceled scenario did not establish an outstanding authentication challenge.")
        if intent.status == "requires_payment_method":
            verify_three_ds(intent, "failure")
    else:
        raise SmokeFailure("Unsupported 3DS result.")


def replay(api: httpx.Client, delivery: Delivery) -> None:
    response = api.post(
        "/payments/webhooks/stripe",
        content=delivery.body,
        headers={"content-type": "application/json", "stripe-signature": delivery.signature},
    )
    if response.status_code != 200:
        raise SmokeFailure("Original signed delivery replay was not acknowledged.")


def receipt_snapshot(sandbox: Sandbox, payment_id: UUID) -> tuple[int, int, int]:
    settings = sandbox.settings
    with MongoClient[dict[str, Any]](settings.mongodb_connection_string, uuidRepresentation="standard") as mongo:
        database = mongo[settings.mongodb_database_name]
        stored = database[settings.mongodb_payments_collection_name].find_one({"_id": payment_id})
        if stored is None:
            raise SmokeFailure("Payment disappeared during replay.")
        return (
            stored["version"],
            database[settings.mongodb_payment_history_collection_name].count_documents({"payment_id": payment_id}),
            sandbox.invoice_database["invoices"].count_documents(
                {"OrderId": Binary.from_uuid(sandbox.order_id, uuid_representation=UuidRepresentation.STANDARD)}
            ),
        )


def await_delivery(recorder: DeliveryRecorder, event_types: tuple[str, ...]) -> Delivery:
    deadline = monotonic() + 15
    while monotonic() < deadline:
        try:
            delivery = recorder.deliveries.get(timeout=0.5)
        except Empty:
            continue
        event = json.loads(delivery.body)
        if event["type"] in event_types and (
            event["type"] == "checkout.session.expired" or event["data"]["object"]["payment_status"] == "paid"
        ):
            return delivery
    raise SmokeFailure("No matching acknowledged real account event was captured.")


def guided_challenge(session: stripe.checkout.Session, scenario: Scenario) -> None:
    if not sys.stdin.isatty() or not sys.stdout.isatty() or session.livemode is not False or not session.url:
        raise SmokeFailure("Guided 3DS requires a private interactive terminal and a sandbox Checkout URL.")
    print("Open this sandbox Checkout in your browser (the URL is shown only in this interactive terminal):")
    print(session.url)
    print("Use card 4000 0000 0000 3220, any future expiry, any three-digit CVC, and synthetic billing details.")
    action = {"3ds-success": "Complete", "3ds-failure": "Fail", "3ds-cancel": "Cancel/close"}[scenario]
    input(f"{action} the Stripe test 3DS challenge, then return here and press Enter. ")


def probe(sandbox: Sandbox, scenario: Scenario) -> dict[str, object]:
    settings = sandbox.settings
    assert settings.stripe_secret_key is not None
    provider = stripe.StripeClient(
        settings.stripe_secret_key.get_secret_value(),
        stripe_version=STRIPE_API_VERSION,
        http_client=stripe.RequestsClient(timeout=15),
        max_network_retries=1,
    )
    session_id: str | None = None
    evidence: dict[str, object] = {"scenario": scenario, "order_id": str(sandbox.order_id), "livemode": False}
    since = int(time()) - 5
    try:
        with socket.socket() as listener_socket:
            listener_socket.bind(("127.0.0.1", 0))
            base_url = f"http://127.0.0.1:{listener_socket.getsockname()[1]}"
            with stripe_listener(base_url, settings.stripe_secret_key, EVENTS) as webhook_secret:
                configured = settings.model_copy(update={"stripe_webhook_secret": webhook_secret})

                def recorder_factory(app: ASGIApp) -> DeliveryRecorder:
                    return ScenarioRecorder(app, reject_once=scenario == "webhook-retry")

                with payments_server(configured, listener_socket, recorder_factory) as recorder:
                    with httpx.Client(base_url=base_url, timeout=30, trust_env=False) as api:
                        first = checkout(api, sandbox.order_id)
                        session_id, payment_id = first.payment.provider_session_id, first.payment.id
                        if session_id is None:
                            raise SmokeFailure("Payments did not create a Checkout Session.")
                        original = provider.v1.checkout.sessions.retrieve(session_id)
                        attempt_id = verify_session(original, session_id, payment_id, sandbox.order_id)
                        recorder.session_id = session_id
                        evidence.update(payment_id=str(payment_id), session_id=session_id, attempt_id=attempt_id)
                        print(f"Checking sandbox {scenario}: {session_id}", flush=True)
                        verify_unfulfilled(sandbox, api, "pending")
                        if scenario == "expiry":
                            expired = provider.v1.checkout.sessions.expire(session_id)
                            if (
                                expired.livemode is not False
                                or expired.status != "expired"
                                or expired.payment_status != "unpaid"
                            ):
                                raise SmokeFailure("Stripe did not expire the sandbox session.")
                            current = wait_payment(api, sandbox.order_id, "failed")
                            if current.get("failure_code") != "checkout_expired":
                                raise SmokeFailure("Payments did not retain checkout_expired failure.")
                            verify_unfulfilled(sandbox, api, "failed")
                            delivery = await_delivery(recorder, ("checkout.session.expired",))
                            before = receipt_snapshot(sandbox, payment_id)
                            replay(api, delivery)
                            verify_unfulfilled(sandbox, api, "failed")
                            if receipt_snapshot(sandbox, payment_id) != before:
                                raise SmokeFailure("Repeated expiration changed payment history or invoice count.")
                            evidence.update(
                                event_id=delivery.event_id,
                                payment_status="failed",
                                failure_code="checkout_expired",
                                order_status="Created",
                                invoice_count=0,
                                duplicate_delivery_unchanged=True,
                            )
                            return evidence
                        if scenario == "decline-retry":
                            confirm(session_id, settings.stripe_secret_key, "decline")
                            declined = find_intent(provider, payment_id, since)
                            verify_decline(declined)
                            verify_unfulfilled(sandbox, api, "pending")
                            repeated = checkout(api, sandbox.order_id)
                            if repeated.payment.id != payment_id or repeated.payment.provider_session_id != session_id:
                                raise SmokeFailure("Declined-card recovery replaced the pending Payment/session.")
                            if (
                                verify_session(
                                    provider.v1.checkout.sessions.retrieve(session_id),
                                    session_id,
                                    payment_id,
                                    sandbox.order_id,
                                )
                                != attempt_id
                            ):
                                raise SmokeFailure("Declined-card recovery changed the checkout attempt.")
                            evidence.update(
                                decline_code="generic_decline",
                                unpaid_order_status="Created",
                                unpaid_invoice_count=0,
                                retry_reuses_session=True,
                                declined_intent_id=declined.id,
                            )
                        if scenario.startswith("3ds-"):
                            guided_challenge(original, scenario)
                            authenticated = find_intent(provider, payment_id, since)
                            outcome = cast(Literal["success", "failure", "cancel"], scenario.removeprefix("3ds-"))
                            verify_three_ds(authenticated, outcome)
                            evidence.update(three_ds_outcome=outcome, authentication_intent_id=authenticated.id)
                            if outcome != "success":
                                verify_unfulfilled(sandbox, api, "pending")
                                evidence.update(unpaid_order_status="Created", unpaid_invoice_count=0)
                                confirm(session_id, settings.stripe_secret_key, "visa")
                                evidence.update(retry_after_authentication=True)
                        else:
                            confirm(session_id, settings.stripe_secret_key, "blik" if scenario == "blik" else "visa")
                        if scenario == "blik":
                            blik_intent = find_intent(provider, payment_id, since)
                            if (
                                blik_intent.livemode is not False
                                or blik_intent.amount != AMOUNT_MINOR
                                or blik_intent.currency != "pln"
                            ):
                                raise SmokeFailure("BLIK confirmation encountered an unexpected PaymentIntent.")
                            if blik_intent.status != "succeeded":
                                provider.v1.payment_intents.confirm(
                                    blik_intent.id, {"payment_method_options": {"blik": {"code": "000000"}}}
                                )
                        if scenario == "webhook-retry":
                            assert isinstance(recorder, ScenarioRecorder)
                            try:
                                rejected = recorder.rejected.get(timeout=30)
                            except Empty as error:
                                raise SmokeFailure(
                                    "No actual signed delivery reached the injected HTTP 503 outage."
                                ) from error
                            verify_unfulfilled(sandbox, api, "pending")
                            replay(api, rejected)
                            evidence.update(
                                initial_http_status=503, recovery_http_status=200, replayed_original_signature=True
                            )
                        current = wait_payment(api, sandbox.order_id, "succeeded")
                        delivery = await_delivery(
                            recorder, ("checkout.session.completed", "checkout.session.async_payment_succeeded")
                        )
                        completed = provider.v1.checkout.sessions.retrieve(session_id)
                        if verify_session(completed, session_id, payment_id, sandbox.order_id, paid=True) != attempt_id:
                            raise SmokeFailure("Paid session changed its attempt association.")
                        intent_id = completed.payment_intent
                        if not isinstance(intent_id, str) or current.get("provider_payment_id") != intent_id:
                            raise SmokeFailure("PaymentIntent does not match the confirmed Payment.")
                        intent = provider.v1.payment_intents.retrieve(intent_id, {"expand": ["latest_charge"]})
                        charge_id = verify_blik(intent) if scenario == "blik" else verify_card_intent(intent, intent_id)
                        if scenario == "decline-retry" and evidence["declined_intent_id"] != intent_id:
                            raise SmokeFailure("Card retry did not reuse the original PaymentIntent.")
                        if scenario == "3ds-success":
                            verify_three_ds(intent, "success")
                        evidence.update(**verify_fulfillment(sandbox, delivery.event_id, payment_id))
                        before = receipt_snapshot(sandbox, payment_id)
                        replay(api, delivery)
                        if asyncio.run(fulfill(settings, 10)) != 0 or receipt_snapshot(sandbox, payment_id) != before:
                            raise SmokeFailure("Duplicate paid delivery changed Payment/history/invoice state.")
                        evidence.update(
                            payment_status="succeeded",
                            event_id=delivery.event_id,
                            payment_intent_id=intent_id,
                            charge_id=charge_id,
                            payment_method="blik" if scenario == "blik" else "card",
                            duplicate_delivery_unchanged=True,
                            intent_request_id=intent.last_response.request_id if intent.last_response else None,
                        )
    finally:
        if session_id is not None:
            final = provider.v1.checkout.sessions.retrieve(session_id)
            if final.livemode is not False:
                raise SmokeFailure("Cleanup encountered a live Checkout Session.")
            if final.status == "open":
                provider.v1.checkout.sessions.expire(session_id)
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=SCENARIOS)
    scenario = cast(Scenario, parser.parse_args().scenario)
    if scenario.startswith("3ds-") and (not sys.stdin.isatty() or not sys.stdout.isatty()):
        print("Guided 3DS scenarios require a private interactive terminal; no account requests made.", file=sys.stderr)
        return 1
    try:
        with sandbox_environment() as sandbox:
            evidence = probe(sandbox, scenario)
    except SmokeFailure as error:
        print(f"Scenario failed: {error}", file=sys.stderr)
        return 1
    except stripe.StripeError as error:
        code = error.code if error.code is not None and re.fullmatch(r"[a-z_]{1,80}", error.code) else "unavailable"
        print(
            f"Scenario provider failed: {type(error).__name__}; code={code}; request_id={error.request_id}",
            file=sys.stderr,
        )
        return 1
    except Exception as error:
        print(f"Scenario failed: {type(error).__name__}; private details suppressed.", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2))
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        rows = "\n".join(f"| {key} | `{value}` |" for key, value in evidence.items())
        with Path(summary).open("a", encoding="utf-8") as output:
            output.write(f"## Real sandbox {scenario} passed\n\n| Evidence | Value |\n| --- | --- |\n{rows}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
