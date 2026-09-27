from datetime import UTC, datetime
from typing import final

from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_history_document import (
    PaymentHistoryDocument,
)


@final
class PaymentHistoryMapper:
    @staticmethod
    def from_payment(document: PaymentDocument) -> PaymentHistoryDocument:
        version = document.get("version", 0)
        return PaymentHistoryDocument(
            _id=f"{document['_id']}:{version}",
            payment_id=document["_id"],
            order_id=document["order_id"],
            amount_minor=document["amount_minor"],
            currency=document["currency"],
            status=document["status"],
            provider_session_id=document["provider_session_id"],
            provider_payment_id=document["provider_payment_id"],
            failure_code=document["failure_code"],
            created_at=document["created_at"],
            updated_at=document["updated_at"],
            version=version,
            recorded_at=datetime.now(UTC),
        )

    @staticmethod
    def to_payment(document: PaymentHistoryDocument) -> PaymentDocument:
        return PaymentDocument(
            _id=document["payment_id"],
            order_id=document["order_id"],
            amount_minor=document["amount_minor"],
            currency=document["currency"],
            status=document["status"],
            provider_session_id=document["provider_session_id"],
            provider_payment_id=document["provider_payment_id"],
            failure_code=document["failure_code"],
            created_at=document["created_at"],
            updated_at=document["updated_at"],
            version=document["version"],
        )
