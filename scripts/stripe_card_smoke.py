"""Real sandbox Visa Checkout, CLI-signed delivery and durable invoice fulfillment."""

import asyncio
import json
import os
import re
import socket
import subprocess
import sys
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from queue import Empty, Full, Queue
from tempfile import TemporaryDirectory
from threading import Thread
from time import monotonic, sleep
from typing import Any
from uuid import UUID

import httpx
import stripe
import uvicorn
from bson.binary import Binary, UuidRepresentation
from pydantic import SecretStr
from pymongo import MongoClient
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.infrastructure.clients.stripe.checkout_provider import STRIPE_API_VERSION
from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.fulfill_payments import run as fulfill
from scripts.stripe_sandbox_smoke import (
    AMOUNT_MINOR,
    Sandbox,
    SmokeFailure,
    checkout,
    sandbox_environment,
    verify_session,
)


def card_fixtures(session_id: str) -> dict[str, object]:
    """Adapt Stripe CLI's pinned checkout.session.completed fixture to our existing session."""
    if not re.fullmatch(r"cs_test_[A-Za-z0-9]+", session_id):
        raise SmokeFailure("Card fixtures require a sandbox Checkout Session ID.")
    return {
        "_meta": {"template_version": 0},
        "fixtures": [
            {"name": "payment_page", "path": f"/v1/payment_pages/{session_id}", "method": "get"},
            {
                "name": "payment_method",
                "path": "/v1/payment_methods",
                "method": "post",
                "params": {
                    "type": "card",
                    "card": {"token": "tok_visa"},
                    "billing_details": {"email": "sandbox-smoke@example.test", "name": "Sandbox Smoke Client"},
                },
            },
            {
                "name": "payment_page_confirm",
                "path": f"/v1/payment_pages/{session_id}/confirm",
                "method": "post",
                "params": {"payment_method": "${payment_method:id}", "expected_amount": AMOUNT_MINOR},
            },
        ],
    }


@dataclass(frozen=True, slots=True)
class Delivery:
    event_id: str
    body: bytes = field(repr=False)
    signature: str = field(repr=False)


class DeliveryRecorder:
    """Pass ASGI messages unchanged; retain only our acknowledged delivery in memory for replay."""

    def __init__(self, app: ASGIApp, event_types: tuple[str, ...] = ("checkout.session.completed",)) -> None:
        self.app = app
        self.event_types = event_types
        self.session_id: str | None = None
        self.deliveries: Queue[Delivery] = Queue(maxsize=1)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] != "/payments/webhooks/stripe":
            await self.app(scope, receive, send)
            return
        body = bytearray()
        statuses: list[int] = []
        oversize = False

        async def capture_receive() -> Message:
            nonlocal oversize
            message = await receive()
            chunk = message.get("body", b"")
            if not oversize and len(body) + len(chunk) <= 1024 * 1024:
                body.extend(chunk)
            else:
                oversize = True
                body.clear()
            return message

        async def capture_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                statuses.append(message["status"])
            await send(message)

        await self.app(scope, capture_receive, capture_send)
        if statuses != [200] or oversize or self.session_id is None:
            return
        try:
            event = json.loads(body)
            if event["type"] not in self.event_types or event["data"]["object"]["id"] != self.session_id:
                return
            signature = next(value.decode() for key, value in scope["headers"] if key == b"stripe-signature")
            self.deliveries.put_nowait(Delivery(event["id"], bytes(body), signature))
        except KeyError, TypeError, ValueError, StopIteration, Full:
            return


@contextmanager
def stripe_listener(
    base_url: str, secret: SecretStr, events: tuple[str, ...] = ("checkout.session.completed",)
) -> Generator[SecretStr]:
    # Credentials stay in the child's environment, never command arguments or printed CLI output.
    process = subprocess.Popen(
        [
            "stripe",
            "listen",
            "--skip-update",
            "--events-from",
            "@self",
            "--events",
            ",".join(events),
            "--forward-to",
            f"{base_url}/payments/webhooks/stripe",
        ],
        env={**os.environ, "STRIPE_API_KEY": secret.get_secret_value(), "NO_COLOR": "1"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    secrets: Queue[str] = Queue(maxsize=1)

    def consume() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            if match := re.search(r"whsec_[A-Za-z0-9]+", line):
                try:
                    secrets.put_nowait(match.group())
                except Full:
                    pass

    reader = Thread(target=consume, daemon=True)
    reader.start()
    try:
        deadline = monotonic() + 45
        while monotonic() < deadline:
            if process.poll() is not None:
                raise SmokeFailure("Stripe CLI listener exited before readiness; private output suppressed.")
            try:
                signing_secret = secrets.get(timeout=0.5)
                break
            except Empty:
                pass
        else:
            raise SmokeFailure("Stripe CLI listener did not provide its signing secret in time.")
        yield SecretStr(signing_secret)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        reader.join(timeout=5)
        if process.stdout is not None:
            process.stdout.close()


@contextmanager
def payments_server(
    settings: Settings,
    listener_socket: socket.socket,
    recorder_factory: Callable[[ASGIApp], DeliveryRecorder] = DeliveryRecorder,
) -> Generator[DeliveryRecorder]:
    recorder = recorder_factory(create_app(settings))
    server = uvicorn.Server(uvicorn.Config(recorder, log_config=None, access_log=False, log_level="critical"))
    thread = Thread(target=lambda: server.run(sockets=[listener_socket]), daemon=True)
    thread.start()
    try:
        deadline = monotonic() + 30
        while monotonic() < deadline:
            if server.started:
                break
            if not thread.is_alive():
                raise SmokeFailure("Payments server failed to start.")
            sleep(0.1)
        else:
            raise SmokeFailure("Payments server did not start in time.")
        yield recorder
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        if thread.is_alive():
            server.force_exit = True
            thread.join(timeout=5)


def pay_card(session_id: str, secret: SecretStr) -> None:
    with TemporaryDirectory(prefix="stripe-card-") as directory:
        fixture = Path(directory) / "card.json"
        fixture.write_text(json.dumps(card_fixtures(session_id)), encoding="utf-8")
        result = subprocess.run(
            ["stripe", "fixtures", str(fixture), "--api-version", STRIPE_API_VERSION],
            env={**os.environ, "STRIPE_API_KEY": secret.get_secret_value(), "NO_COLOR": "1"},
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if result.returncode != 0:
            raise SmokeFailure("Stripe CLI card fixture failed; private provider output suppressed.")


def verify_card_intent(intent: stripe.PaymentIntent, intent_id: str) -> str:
    charge = intent.latest_charge
    if (
        intent.id != intent_id
        or intent.livemode is not False
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
        or charge.payment_method_details.type != "card"
        or charge.payment_method_details.card is None
        or charge.payment_method_details.card.brand != "visa"
    ):
        raise SmokeFailure("Stripe did not confirm the expected successful sandbox Visa charge.")
    return charge.id


def verify_fulfillment(sandbox: Sandbox, event_id: str, payment_id: UUID) -> dict[str, object]:
    settings = sandbox.settings
    guid = Binary.from_uuid(sandbox.order_id, uuid_representation=UuidRepresentation.STANDARD)
    with MongoClient[dict[str, Any]](settings.mongodb_connection_string, uuidRepresentation="standard") as mongo:
        database = mongo[settings.mongodb_database_name]
        receipt = database[settings.mongodb_webhook_collection_name].find_one({"_id": event_id})
        if receipt is None or receipt["state"] != "applied" or receipt["fulfillment_status"] != "pending":
            raise SmokeFailure("Real signed delivery did not commit Applied receipt and Pending fulfillment.")
        if asyncio.run(fulfill(settings, 10)) != 1:
            raise SmokeFailure("Fulfillment worker did not process exactly our payment.")
        receipt = database[settings.mongodb_webhook_collection_name].find_one({"_id": event_id})
        order = sandbox.invoice_database["orders"].find_one({"_id": guid})
        invoices = list(sandbox.invoice_database["invoices"].find({"OrderId": guid}))
        if (
            receipt is None
            or receipt["fulfillment_status"] != "completed"
            or order is None
            or order["Status"] != 0
            or len(invoices) != 1
            or invoices[0]["GenerationStatus"] != "Completed"
            or not invoices[0]["StorageUrl"].endswith(".pdf")
            or str(invoices[0]["_id"].as_uuid()) != str(receipt["fulfillment_invoice_id"])
        ):
            raise SmokeFailure("Worker did not establish Paid order and exactly one completed PDF invoice.")
        payment = database[settings.mongodb_payments_collection_name].find_one({"_id": payment_id})
        if payment is None or payment["status"] != "succeeded":
            raise SmokeFailure("Persisted Payment is not Succeeded.")
        return {
            "invoice_id": str(receipt["fulfillment_invoice_id"]),
            "order_status": "Paid",
            "fulfillment_status": "completed",
            "invoice_count": 1,
            "payment_version": payment["version"],
            "history_count": database[settings.mongodb_payment_history_collection_name].count_documents(
                {"payment_id": payment_id}
            ),
        }


def probe(sandbox: Sandbox) -> dict[str, object]:
    settings, order_id = sandbox.settings, sandbox.order_id
    assert settings.stripe_secret_key is not None
    provider = stripe.StripeClient(
        settings.stripe_secret_key.get_secret_value(),
        stripe_version=STRIPE_API_VERSION,
        http_client=stripe.RequestsClient(timeout=15),
        max_network_retries=1,
    )
    session_id: str | None = None
    evidence: dict[str, object] = {"order_id": str(order_id), "amount_minor": AMOUNT_MINOR, "currency": "pln"}
    try:
        with socket.socket() as listener_socket:
            listener_socket.bind(("127.0.0.1", 0))
            base_url = f"http://127.0.0.1:{listener_socket.getsockname()[1]}"
            with stripe_listener(base_url, settings.stripe_secret_key) as webhook_secret:
                configured = settings.model_copy(update={"stripe_webhook_secret": webhook_secret})
                with payments_server(configured, listener_socket) as recorder:
                    with httpx.Client(base_url=base_url, timeout=30, trust_env=False) as api:
                        first = checkout(api, order_id)
                        payment_id = first.payment.id
                        session_id = first.payment.provider_session_id
                        if session_id is None:
                            raise SmokeFailure("Payments did not provide a Checkout Session.")
                        original = provider.v1.checkout.sessions.retrieve(session_id)
                        attempt_id = verify_session(original, session_id, payment_id, order_id)
                        recorder.session_id = session_id
                        print(f"Paying sandbox session {session_id} with Stripe's Visa test token.", flush=True)
                        pay_card(session_id, settings.stripe_secret_key)
                        print("Stripe CLI card confirmation completed.", flush=True)
                        deadline = monotonic() + 60
                        while monotonic() < deadline:
                            payment_response = api.get(f"/payments/order/{order_id}")
                            if (
                                payment_response.status_code == 200
                                and payment_response.json().get("status") == "succeeded"
                            ):
                                break
                            sleep(0.5)
                        else:
                            raise SmokeFailure("Signed account webhook did not establish Succeeded Payment in time.")
                        try:
                            delivery = recorder.deliveries.get(timeout=5)
                        except Empty as error:
                            raise SmokeFailure("No acknowledged real CLI-signed delivery was captured.") from error
                        print(f"Signed account event {delivery.event_id} acknowledged with HTTP 200.", flush=True)
                        completed = provider.v1.checkout.sessions.retrieve(session_id)
                        if verify_session(completed, session_id, payment_id, order_id, paid=True) != attempt_id:
                            raise SmokeFailure("Paid session changed its checkout attempt association.")
                        intent_id = completed.payment_intent
                        if (
                            not isinstance(intent_id, str)
                            or payment_response.json().get("provider_payment_id") != intent_id
                        ):
                            raise SmokeFailure("PaymentIntent association did not match Payments.")
                        intent = provider.v1.payment_intents.retrieve(intent_id, {"expand": ["latest_charge"]})
                        charge_id = verify_card_intent(intent, intent_id)
                        print(f"Verified sandbox Visa charge {charge_id}; PaymentIntent {intent_id}.", flush=True)
                        before_replay = verify_fulfillment(sandbox, delivery.event_id, payment_id)
                        print(f"Paid order has completed invoice {before_replay['invoice_id']}.", flush=True)
                        replay = api.post(
                            "/payments/webhooks/stripe",
                            content=delivery.body,
                            headers={"content-type": "application/json", "stripe-signature": delivery.signature},
                        )
                        if replay.status_code != 200 or asyncio.run(fulfill(settings, 10)) != 0:
                            raise SmokeFailure("Duplicate signed delivery or repeated worker created new work.")
                        with MongoClient[dict[str, Any]](
                            settings.mongodb_connection_string, uuidRepresentation="standard"
                        ) as mongo:
                            database = mongo[settings.mongodb_database_name]
                            persisted = database[settings.mongodb_payments_collection_name].find_one(
                                {"_id": payment_id}
                            )
                            history_count = database[settings.mongodb_payment_history_collection_name].count_documents(
                                {"payment_id": payment_id}
                            )
                            if (
                                persisted is None
                                or persisted["version"] != before_replay["payment_version"]
                                or history_count != before_replay["history_count"]
                                or sandbox.invoice_database["invoices"].count_documents(
                                    {
                                        "OrderId": Binary.from_uuid(
                                            order_id, uuid_representation=UuidRepresentation.STANDARD
                                        )
                                    }
                                )
                                != 1
                            ):
                                raise SmokeFailure("Duplicate delivery changed payment history or invoice count.")
                        evidence.update(
                            payment_id=str(payment_id),
                            session_id=session_id,
                            attempt_id=attempt_id,
                            payment_intent_id=intent_id,
                            charge_id=charge_id,
                            event_id=delivery.event_id,
                            livemode=False,
                            payment_status="succeeded",
                            card_brand="visa",
                            webhook_http_status=200,
                            duplicate_delivery_unchanged=True,
                            intent_request_id=intent.last_response.request_id if intent.last_response else None,
                            **before_replay,
                        )
    finally:
        if session_id is not None:
            final = provider.v1.checkout.sessions.retrieve(session_id)
            if final.livemode is not False:
                raise SmokeFailure("Card probe cleanup encountered an unexpected live session.")
            if final.status == "open":
                provider.v1.checkout.sessions.expire(session_id)
            # Keep the completed sandbox charge visible as evidence; all local data is ephemeral.
    return evidence


def main() -> int:
    try:
        with sandbox_environment() as sandbox:
            evidence = probe(sandbox)
    except SmokeFailure as error:
        print(f"Card smoke failed: {error}", file=sys.stderr)
        return 1
    except stripe.StripeError as error:
        print(f"Card provider failed: {type(error).__name__}; request_id={error.request_id}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Card smoke failed: {type(error).__name__}; private details suppressed.", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2))
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        rows = "\n".join(f"| {key} | `{value}` |" for key, value in evidence.items())
        with Path(summary).open("a", encoding="utf-8") as output:
            output.write("## Real sandbox card payment passed\n\n| Evidence | Value |\n| --- | --- |\n" + rows + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
