from typing import final

from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument


@final
class PaymentMapper:
    @staticmethod
    def to_document(payment: Payment) -> PaymentDocument:
        return PaymentDocument(
            _id=payment.id,
            order_id=payment.order_id,
            amount_minor=payment.money.amount_minor,
            currency=payment.money.currency,
            status=payment.status.value,
            provider_session_id=payment.provider_session_id,
            provider_payment_id=payment.provider_payment_id,
            failure_code=payment.failure_code,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
        )

    @staticmethod
    def to_domain(document: PaymentDocument) -> Payment:
        return Payment.rehydrate(
            payment_id=document["_id"],
            order_id=document["order_id"],
            money=Money(
                amount_minor=document["amount_minor"],
                currency=document["currency"],
            ),
            status=PaymentStatus(document["status"]),
            provider_session_id=document["provider_session_id"],
            provider_payment_id=document["provider_payment_id"],
            failure_code=document["failure_code"],
            created_at=document["created_at"],
            updated_at=document["updated_at"],
        )
