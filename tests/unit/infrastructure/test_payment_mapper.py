from datetime import UTC, datetime
from uuid import uuid4

from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper


def test_to_document_maps_payment_aggregate() -> None:
    payment = Payment.create(uuid4(), Money(amount_minor=12999, currency="PLN"))
    payment.mark_as_pending("cs_test_123")

    document = PaymentMapper.to_document(payment)

    assert document["_id"] == payment.id
    assert document["order_id"] == payment.order_id
    assert document["amount_minor"] == 12999
    assert document["currency"] == "PLN"
    assert document["status"] == "pending"
    assert document["provider_session_id"] == "cs_test_123"


def test_to_domain_rehydrates_payment_aggregate() -> None:
    payment_id = uuid4()
    order_id = uuid4()
    created_at = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    updated_at = datetime(2026, 9, 20, 12, 1, tzinfo=UTC)
    document = PaymentDocument(
        _id=payment_id,
        order_id=order_id,
        amount_minor=12999,
        currency="PLN",
        status="succeeded",
        provider_session_id="cs_test_123",
        provider_payment_id="pi_test_123",
        failure_code=None,
        created_at=created_at,
        updated_at=updated_at,
    )

    payment = PaymentMapper.to_domain(document)

    assert payment.id == payment_id
    assert payment.order_id == order_id
    assert payment.money == Money(amount_minor=12999, currency="PLN")
    assert payment.status is PaymentStatus.SUCCEEDED
    assert payment.provider_session_id == "cs_test_123"
    assert payment.provider_payment_id == "pi_test_123"
    assert payment.created_at == created_at
    assert payment.updated_at == updated_at
