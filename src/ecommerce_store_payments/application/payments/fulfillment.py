"""Durable downstream work created by a verified successful payment."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money


class FulfillmentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    RETRY = "retry"
    FAILED = "failed"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class FulfillmentWork:
    event_id: str
    payment_id: UUID
    order_id: UUID
    attempt_id: UUID
    money: Money
    lease_id: UUID
    attempts: int
    client_id: UUID | None = None
    order_paid: bool = False


@dataclass(frozen=True, slots=True)
class FulfillmentOrder:
    order_id: UUID
    client_id: UUID
    money: Money
    status: str


@dataclass(frozen=True, slots=True)
class CompletedInvoice:
    invoice_id: UUID
    order_id: UUID
    client_data_version_id: UUID


class FulfillmentOrders(Protocol):
    async def get(self, order_id: UUID) -> FulfillmentOrder: ...
    async def mark_paid(self, order_id: UUID) -> None: ...


class FulfillmentInvoices(Protocol):
    async def get_by_order(self, order_id: UUID) -> CompletedInvoice | None: ...
    async def create(self, client_id: UUID, order_id: UUID) -> CompletedInvoice: ...


class FulfillmentRepository(Protocol):
    async def claim(self, now: datetime) -> FulfillmentWork | None: ...
    async def save_order_paid(self, work: FulfillmentWork, client_id: UUID, now: datetime) -> None: ...
    async def complete(self, work: FulfillmentWork, invoice: CompletedInvoice, now: datetime) -> None: ...
    async def fail(self, work: FulfillmentWork, code: str, next_attempt: datetime | None, now: datetime) -> None: ...


class FulfillmentRetryError(Exception):
    """Safe persisted reason, never the upstream exception or response body."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class FulfillmentBlockedError(FulfillmentRetryError):
    pass


class FulfillmentLeaseLostError(Exception):
    pass
