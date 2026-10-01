from datetime import datetime
from typing import NotRequired, TypedDict
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
    fulfillment_attempts: NotRequired[int]
    fulfillment_lease_id: NotRequired[UUID | None]
    fulfillment_lease_until: NotRequired[datetime | None]
    fulfillment_next_attempt: NotRequired[datetime | None]
    fulfillment_error: NotRequired[str | None]
    fulfillment_order_paid: NotRequired[bool]
    fulfillment_client_id: NotRequired[UUID | None]
    fulfillment_invoice_id: NotRequired[UUID | None]
    fulfillment_client_data_version_id: NotRequired[UUID | None]
    fulfillment_completed_at: NotRequired[datetime | None]
