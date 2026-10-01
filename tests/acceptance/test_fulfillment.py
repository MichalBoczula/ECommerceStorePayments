import asyncio
from datetime import UTC, datetime

from pytest_bdd import given, scenarios, then, when

from ecommerce_store_payments.infrastructure.persistence.mongodb.fulfill_payments import run
from tests.acceptance.conftest import AcceptanceContext
from tests.acceptance.test_api import matches_matrix as matches_matrix
from tests.webhook_fixtures import encode, signature

scenarios("features/fulfillment.feature")


@given('a verified successful checkout with fulfillment mode "ok"')
def success(acceptance: AcceptanceContext) -> None:
    prepare(acceptance, "ok")


@given('a verified successful checkout with fulfillment mode "paid_ack_lost"')
def paid_lost(acceptance: AcceptanceContext) -> None:
    prepare(acceptance, "paid_ack_lost")


@given('a verified successful checkout with fulfillment mode "invoice_ack_lost"')
def invoice_lost(acceptance: AcceptanceContext) -> None:
    prepare(acceptance, "invoice_ack_lost")


@given('a verified successful checkout with fulfillment mode "pdf_failure"')
def pdf_failure(acceptance: AcceptanceContext) -> None:
    prepare(acceptance, "pdf_failure")


def prepare(acceptance: AcceptanceContext, mode: str) -> None:
    response = acceptance.client.post(f"/payments/{acceptance.orders.order_id}/checkout")
    assert response.status_code == 200
    session = next(iter(acceptance.stripe.sessions.values()))
    acceptance.webhook_payload = encode(
        {
            "id": "evt_fulfillment",
            "object": "event",
            "type": "checkout.session.completed",
            "livemode": False,
            "data": {
                "object": {**session, "status": "complete", "payment_status": "paid", "payment_intent": "pi_fixture"}
            },
        }
    )
    acceptance.orders.fulfillment_mode = mode
    redeliver(acceptance)
    assert acceptance.orders.paid_writes == acceptance.orders.invoice_creates == 0


@when("the successful webhook is delivered again")
def redeliver(acceptance: AcceptanceContext) -> None:
    response = acceptance.client.post(
        "/payments/webhooks/stripe",
        content=acceptance.webhook_payload,
        headers={"content-type": "application/json", "stripe-signature": signature(acceptance.webhook_payload)},
    )
    assert response.status_code == 200
    acceptance.responses = [response]
    acceptance.last_operation = "POST /payments/webhooks/stripe"


@when("the durable fulfillment command runs")
def fulfill(acceptance: AcceptanceContext) -> None:
    asyncio.run(run(acceptance.settings, 100))


@then("one paid order and one completed invoice are recorded")
def completed(acceptance: AcceptanceContext) -> None:
    assert acceptance.orders.status == "Paid" and acceptance.orders.invoice_id is not None
    work = acceptance.webhooks.find_one({"_id": "evt_fulfillment"})
    assert work is not None and work["fulfillment_status"] == "completed"
    assert work.get("fulfillment_invoice_id") == acceptance.orders.invoice_id
    assert acceptance.orders.paid_writes == 1
    payment = acceptance.payments.find_one()
    assert payment is not None and payment["status"] == "succeeded"


@then("fulfillment stays completed without repeating downstream writes")
def repeated(acceptance: AcceptanceContext) -> None:
    completed(acceptance)
    assert acceptance.orders.invoice_creates == 1


@then("the order is paid and invoice fulfillment is scheduled for retry")
def retry(acceptance: AcceptanceContext) -> None:
    work = acceptance.webhooks.find_one({"_id": "evt_fulfillment"})
    assert work is not None and work["fulfillment_status"] == "retry" and work.get("fulfillment_order_paid")
    assert work.get("fulfillment_next_attempt") is not None and acceptance.orders.status == "Paid"


@when("the invoice retry becomes due and the durable fulfillment command runs")
def retry_due(acceptance: AcceptanceContext) -> None:
    acceptance.webhooks.update_one(
        {"_id": "evt_fulfillment"}, {"$set": {"fulfillment_next_attempt": datetime.now(UTC)}}
    )
    fulfill(acceptance)
