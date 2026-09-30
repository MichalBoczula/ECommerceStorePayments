from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID

from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money


@dataclass(frozen=True, slots=True)
class CheckoutRequest:
    payment_id: UUID
    order_id: UUID
    attempt_id: UUID
    money: Money
    request_version: int = 1


@dataclass(frozen=True, slots=True)
class CheckoutSession:
    session_id: str
    url: str | None
    status: Literal["open", "complete", "expired"]
    expires_at: datetime


class CheckoutProvider(Protocol):
    def require_available(self) -> None: ...

    def validate_money(self, money: Money) -> None: ...

    async def create(self, request: CheckoutRequest) -> CheckoutSession: ...

    async def get(self, session_id: str, request: CheckoutRequest) -> CheckoutSession: ...
