from datetime import datetime
from typing import TypedDict
from uuid import UUID


class WebhookDocument(TypedDict):
    _id: str
    event_type: str
    payload_digest: str
    outcome: str
    payment_id: UUID | None
    order_id: UUID | None
    attempt_id: UUID | None
    amount_minor: int | None
    currency: str | None
    session_id: str | None
    provider_payment_id: str | None
    state: str
    reason: str | None
    received_at: datetime
    completed_at: datetime | None
    fulfillment_status: str | None
