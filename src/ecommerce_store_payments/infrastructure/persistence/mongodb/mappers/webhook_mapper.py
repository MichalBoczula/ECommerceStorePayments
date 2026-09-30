from datetime import UTC, datetime
from typing import final

from ecommerce_store_payments.application.payments.webhook import (
    CheckoutNotification,
    CheckoutOutcome,
    VerifiedWebhook,
    WebhookReceipt,
    WebhookState,
)
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.webhook_document import WebhookDocument


@final
class WebhookMapper:
    @staticmethod
    def to_document(event: VerifiedWebhook) -> WebhookDocument:
        checkout = event.checkout
        return WebhookDocument(
            _id=event.event_id,
            event_type=event.event_type,
            payload_digest=event.payload_digest,
            outcome=event.outcome.value,
            payment_id=checkout.payment_id if checkout else None,
            order_id=checkout.order_id if checkout else None,
            attempt_id=checkout.attempt_id if checkout else None,
            amount_minor=checkout.money.amount_minor if checkout else None,
            currency=checkout.money.currency if checkout else None,
            session_id=checkout.session_id if checkout else None,
            provider_payment_id=checkout.provider_payment_id if checkout else None,
            state=WebhookState.PENDING.value,
            reason=None,
            received_at=datetime.now(UTC),
            completed_at=None,
            fulfillment_status=None,
        )

    @staticmethod
    def to_receipt(document: WebhookDocument) -> WebhookReceipt:
        checkout = None
        if document["payment_id"] is not None:
            order_id, attempt_id = document["order_id"], document["attempt_id"]
            amount, currency, session_id = document["amount_minor"], document["currency"], document["session_id"]
            assert order_id is not None and attempt_id is not None
            assert amount is not None and currency is not None and session_id is not None
            checkout = CheckoutNotification(
                document["payment_id"],
                order_id,
                attempt_id,
                Money(amount, currency),
                session_id,
                document["provider_payment_id"],
            )
        event = VerifiedWebhook(
            document["_id"],
            document["event_type"],
            document["payload_digest"],
            CheckoutOutcome(document["outcome"]),
            checkout,
        )
        return WebhookReceipt(event, WebhookState(document["state"]), document["reason"])
