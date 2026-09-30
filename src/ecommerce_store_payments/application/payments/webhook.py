from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from ecommerce_store_payments.domain.aggregates.payments.payment import Payment
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money


class CheckoutOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXPIRED = "expired"
    WAITING = "waiting"
    UNKNOWN = "unknown"


class WebhookState(StrEnum):
    PENDING = "pending"
    APPLIED = "applied"
    IGNORED = "ignored"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class CheckoutNotification:
    payment_id: UUID
    order_id: UUID
    attempt_id: UUID
    money: Money
    session_id: str
    provider_payment_id: str | None


@dataclass(frozen=True, slots=True)
class VerifiedWebhook:
    event_id: str
    event_type: str
    payload_digest: str
    outcome: CheckoutOutcome
    checkout: CheckoutNotification | None


@dataclass(frozen=True, slots=True)
class WebhookReceipt:
    event: VerifiedWebhook
    state: WebhookState = WebhookState.PENDING
    reason: str | None = None


class WebhookVerifier(Protocol):
    def verify(self, payload: bytes, signature: str) -> VerifiedWebhook: ...


class WebhookRepository(Protocol):
    async def receive(self, event: VerifiedWebhook) -> WebhookReceipt: ...

    async def complete(
        self, receipt: WebhookReceipt, payment: Payment | None, state: WebhookState, reason: str, *, changed: bool
    ) -> WebhookReceipt:
        """Atomically compare payment version, archive changes, and finish the receipt."""
        ...


class WebhookDisabledError(Exception):
    pass


class WebhookInvalidError(ValueError):
    pass


class WebhookCollisionError(ValueError):
    pass


class WebhookRetryError(Exception):
    pass
