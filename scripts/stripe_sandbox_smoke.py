"""Real Payments checkout -> Stripe sandbox probe; run explicitly, never as a pytest suite."""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic, sleep
from typing import Any
from uuid import UUID, uuid4

import httpx
import stripe
from bson.binary import Binary, UuidRepresentation
from bson.decimal128 import Decimal128
from fastapi.testclient import TestClient
from pydantic import SecretStr
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.api.contracts.checkout_response import CheckoutResponse
from ecommerce_store_payments.infrastructure.clients.stripe.checkout_provider import STRIPE_API_VERSION
from ecommerce_store_payments.infrastructure.config.settings import Settings

ROOT = Path(__file__).resolve().parents[1]
AMOUNT_MINOR = 1299


class SmokeFailure(Exception):
    """A safe diagnostic code; provider responses and keys must not enter job logs."""


def require_test_key(raw: str | None) -> SecretStr:
    if not raw or not raw.startswith("sk_test_") or len(raw) <= 8 or any(character.isspace() for character in raw):
        raise SmokeFailure("Configure PAYMENTS_STRIPE_SECRET_KEY with a sandbox sk_test_ key.")
    return SecretStr(raw)


def verify_session(session: stripe.checkout.Session, session_id: str, payment_id: UUID, order_id: UUID) -> str:
    metadata = session.metadata
    if metadata is None:
        raise SmokeFailure("Stripe sandbox session has no attempt association.")
    try:
        attempt_id = UUID(str(metadata["attempt_id"]))
        valid = (
            session.id == session_id
            and session.id.startswith("cs_test_")
            and session.livemode is False
            and session.mode == "payment"
            and session.status == "open"
            and session.payment_status == "unpaid"
            and session.amount_total == AMOUNT_MINOR
            and session.currency == "pln"
            and set(session.payment_method_types) == {"card", "blik"}
            and session.client_reference_id == str(payment_id)
            and metadata["payment_id"] == str(payment_id)
            and metadata["order_id"] == str(order_id)
        )
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise SmokeFailure("Stripe sandbox session has invalid attempt metadata.") from error
    if not valid:
        raise SmokeFailure("Stripe sandbox session did not match the synthetic Payments order.")
    return str(attempt_id)


def wait_for_primary(database: MongoClient[dict[str, Any]]) -> None:
    deadline = monotonic() + 30
    while monotonic() < deadline:
        try:
            if database.admin.command("hello").get("isWritablePrimary"):
                return
        except PyMongoError:
            pass
        sleep(0.25)
    raise SmokeFailure("Smoke MongoDB did not elect a primary.")


def wait_for_invoice(base_url: str) -> None:
    deadline = monotonic() + 90
    with httpx.Client(timeout=2, trust_env=False) as client:
        while monotonic() < deadline:
            try:
                if client.get(f"{base_url}/health/ready").status_code == 200:
                    return
            except httpx.RequestError:
                pass
            sleep(0.5)
    raise SmokeFailure("Published Invoice image did not become ready.")


def seed_order(database: MongoClient[dict[str, Any]], database_name: str, order_id: UUID) -> None:
    def guid(value: UUID) -> Binary:
        return Binary.from_uuid(value, uuid_representation=UuidRepresentation.STANDARD)

    product_version = uuid4()
    now = datetime.now(UTC)
    database[database_name]["product-versions"].insert_one(
        {
            "_id": guid(product_version),
            "IsActive": True,
            "CreatedAt": now,
            "DeactivatedAt": None,
            "ProductId": guid(uuid4()),
            "PriceAmount": Decimal128("12.99"),
            "PriceCurrency": "PLN",
            "Name": "Stripe sandbox smoke product",
            "Brand": "Synthetic demo",
        }
    )
    database[database_name]["orders"].insert_one(
        {
            "_id": guid(order_id),
            "ClientId": guid(uuid4()),
            "Lines": [{"ProductVersionId": guid(product_version), "Quantity": 1}],
            "CreatedAt": now,
            "UpdatedAt": None,
            "Status": 2,
        }
    )


def checkout(api: TestClient, order_id: UUID) -> CheckoutResponse:
    response = api.post(f"/payments/{order_id}/checkout")
    if response.status_code != 200:
        raise SmokeFailure(f"Payments checkout returned HTTP {response.status_code}.")
    return CheckoutResponse.model_validate(response.json())


def probe(settings: Settings, order_id: UUID) -> dict[str, object]:
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
        with TestClient(create_app(settings)) as api:
            # Prepare Payment first so its ID is available even if creation times out.
            prepared = api.post(f"/payments/{order_id}/pay")
            if prepared.status_code != 201:
                raise SmokeFailure(f"Payment preparation returned HTTP {prepared.status_code}.")
            payment_id = UUID(prepared.json()["id"])
            print(f"Sandbox smoke order {order_id}; payment {payment_id}.", flush=True)
            first = checkout(api, order_id)
            session_id = first.payment.provider_session_id
            if session_id is None or not session_id.startswith("cs_test_"):
                raise SmokeFailure("Payments did not persist a sandbox session ID.")
            print(f"Created sandbox Checkout Session {session_id}.", flush=True)
            second = checkout(api, order_id)
            persisted = api.get(f"/payments/order/{order_id}")
            if (
                first.payment.id != payment_id
                or first.payment.status != "pending"
                or first.checkout_status != "open"
                or not first.checkout_url
                or second.payment.id != payment_id
                or second.payment.provider_session_id != session_id
                or second.checkout_url != first.checkout_url
                or persisted.status_code != 200
                or persisted.json().get("provider_session_id") != session_id
                or persisted.json().get("status") != "pending"
            ):
                raise SmokeFailure("Repeated Payments checkout did not reuse its persisted Pending session.")
            session = provider.v1.checkout.sessions.retrieve(session_id)
            attempt_id = verify_session(session, session_id, payment_id, order_id)
            response = session.last_response
            evidence.update(
                payment_id=str(payment_id),
                session_id=session_id,
                attempt_id=attempt_id,
                retrieve_request_id=response.request_id if response else None,
                livemode=session.livemode,
                payment_method_types=session.payment_method_types,
                repeated_session_reused=True,
            )
    finally:
        if session_id is not None and session_id.startswith("cs_test_"):
            expired = provider.v1.checkout.sessions.expire(session_id)
            if expired.livemode is not False or expired.status != "expired":
                raise SmokeFailure("Sandbox session cleanup did not confirm expiration.")
            response = expired.last_response
            evidence.update(
                cleanup_status=expired.status,
                expire_request_id=response.request_id if response else None,
            )
            print(f"Sandbox session {session_id} expired.", flush=True)
    return evidence


def run() -> dict[str, object]:
    secret = require_test_key(os.environ.get("PAYMENTS_STRIPE_SECRET_KEY"))
    provenance = json.loads((ROOT / "contracts/invoice/source.json").read_text())
    image = provenance["image"]
    if not image.startswith("mb0101/ecommerce-store-invoice-api@sha256:"):
        raise SmokeFailure("Smoke requires the reviewed immutable Invoice image.")
    suffix = uuid4().hex
    order_id = uuid4()
    invoice_database = f"sandbox_invoice_{suffix}"
    with Network() as network:
        with (
            DockerContainer("mongo:8.0")
            .with_command(["mongod", "--replSet", "rs0", "--bind_ip_all"])
            .with_network(network)
            .with_network_aliases("smoke-mongo")
            .with_exposed_ports(27017)
        ) as mongo:
            initiated = mongo.exec(
                ["mongosh", "--quiet", "--eval", "rs.initiate({_id:'rs0',members:[{_id:0,host:'smoke-mongo:27017'}]})"]
            )
            if initiated.exit_code != 0:
                raise SmokeFailure("Smoke replica-set initialization failed.")
            uri = f"mongodb://{mongo.get_container_host_ip()}:{mongo.get_exposed_port(27017)}/?directConnection=true"
            with MongoClient[dict[str, Any]](uri, serverSelectionTimeoutMS=1000) as database:
                wait_for_primary(database)
                seed_order(database, invoice_database, order_id)
                with (
                    DockerContainer(image)
                    .with_network(network)
                    .with_env("MongoDbSettings__ConnectionString", "mongodb://smoke-mongo:27017/?directConnection=true")
                    .with_env("MongoDbSettings__DatabaseName", invoice_database)
                    .with_exposed_ports(8080)
                ) as invoice:
                    base_url = f"http://{invoice.get_container_host_ip()}:{invoice.get_exposed_port(8080)}"
                    wait_for_invoice(base_url)
                    settings = Settings(
                        environment="test",
                        mongodb_connection_string=uri,
                        mongodb_database_name=f"sandbox_payments_{suffix}",
                        orders_api_base_url=base_url,
                        orders_api_timeout_seconds=30,
                        stripe_enabled=True,
                        stripe_secret_key=secret,
                        stripe_timeout_seconds=15,
                    )
                    return probe(settings, order_id)


def main() -> int:
    try:
        evidence = run()
    except SmokeFailure as error:
        print(f"Sandbox smoke failed: {error}", file=sys.stderr)
        return 1
    except stripe.StripeError as error:
        print(f"Sandbox provider failed: {type(error).__name__}; request_id={error.request_id}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Sandbox smoke failed: {type(error).__name__}; no private response details logged.", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2))
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        rows = "\n".join(f"| {key} | `{value}` |" for key, value in evidence.items())
        with Path(summary).open("a", encoding="utf-8") as output:
            output.write(
                "## Real Stripe sandbox checkout passed\n\n| Evidence | Value |\n| --- | --- |\n" + rows + "\n"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
