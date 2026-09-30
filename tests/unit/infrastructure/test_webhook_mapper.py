from uuid import uuid4

import pytest

from ecommerce_store_payments.application.payments.webhook import CheckoutOutcome, WebhookState
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.webhook_mapper import WebhookMapper
from tests.webhook_fixtures import notification


@pytest.mark.parametrize("known", [True, False])
def test_normalized_work_round_trip_preserves_receipt_and_contains_no_raw_body(known: bool) -> None:
    from dataclasses import replace

    payment = Payment.create(uuid4(), Money(1299, "PLN"))
    payment.begin_checkout()
    event = notification(payment)
    if not known:
        event = replace(event, outcome=CheckoutOutcome.UNKNOWN, checkout=None)
    document = WebhookMapper.to_document(event)
    assert "payload" not in document
    assert "signature" not in document
    assert WebhookMapper.to_receipt(document).event == event
    assert WebhookMapper.to_receipt(document).state is WebhookState.PENDING
    assert document["received_at"].utcoffset() is not None
