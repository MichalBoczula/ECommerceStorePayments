from uuid import uuid4

from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.persistence.mongodb.mappers.payment_mapper import PaymentMapper


def test_mapper_preserves_reserved_attempt_and_supports_legacy_documents() -> None:
    payment = Payment.create(uuid4(), Money(1299, "PLN"))
    legacy = PaymentMapper.to_document(payment)
    legacy.pop("checkout_attempt_id", None)
    legacy.pop("checkout_started_at", None)
    assert PaymentMapper.to_domain(legacy).checkout_attempt_id is None
    payment.begin_checkout()
    document = PaymentMapper.to_document(payment)
    document["version"] = 1
    restored = PaymentMapper.to_domain(document)
    assert restored.checkout_attempt_id == payment.checkout_attempt_id
    assert restored.checkout_started_at == payment.checkout_started_at
