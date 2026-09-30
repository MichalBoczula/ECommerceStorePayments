from datetime import datetime
from typing import NotRequired, TypedDict
from uuid import UUID


class PaymentHistoryDocument(TypedDict):
    _id: str
    payment_id: UUID
    order_id: UUID
    amount_minor: int
    currency: str
    status: str
    provider_session_id: str | None
    provider_payment_id: str | None
    failure_code: str | None
    created_at: datetime
    updated_at: datetime | None
    version: int
    recorded_at: datetime
    checkout_attempt_id: NotRequired[UUID | None]
    checkout_started_at: NotRequired[datetime | None]
    checkout_request_version: NotRequired[int]
