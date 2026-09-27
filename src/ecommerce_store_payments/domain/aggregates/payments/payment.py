from datetime import UTC, datetime
from typing import Self, final
from uuid import UUID, uuid4

from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.exceptions import PaymentErrorCode
from ecommerce_store_payments.domain.aggregates.payments.payment_policy import PaymentPolicy
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money


@final
class Payment:
    __slots__ = (
        "_created_at",
        "_failure_code",
        "_id",
        "_money",
        "_order_id",
        "_provider_payment_id",
        "_provider_session_id",
        "_status",
        "_updated_at",
        "_version",
    )

    def __init__(
        self,
        payment_id: UUID,
        order_id: UUID,
        money: Money,
        status: PaymentStatus,
        provider_session_id: str | None,
        provider_payment_id: str | None,
        failure_code: str | None,
        created_at: datetime,
        updated_at: datetime | None,
        version: int,
    ) -> None:
        PaymentPolicy.validate_snapshot(
            payment_id,
            order_id,
            money,
            status,
            provider_session_id,
            provider_payment_id,
            failure_code,
            created_at,
            updated_at,
            version,
        )
        self._id = payment_id
        self._order_id = order_id
        self._money = money
        self._status = status
        self._provider_session_id = provider_session_id
        self._provider_payment_id = provider_payment_id
        self._failure_code = failure_code
        self._created_at = created_at
        self._updated_at = updated_at
        self._version = version

    @classmethod
    def create(cls, order_id: UUID, money: Money) -> Self:
        return cls(
            payment_id=uuid4(),
            order_id=order_id,
            money=money,
            status=PaymentStatus.CREATED,
            provider_session_id=None,
            provider_payment_id=None,
            failure_code=None,
            created_at=datetime.now(UTC),
            updated_at=None,
            version=0,
        )

    @classmethod
    def rehydrate(
        cls,
        payment_id: UUID,
        order_id: UUID,
        money: Money,
        status: PaymentStatus,
        provider_session_id: str | None,
        provider_payment_id: str | None,
        failure_code: str | None,
        created_at: datetime,
        updated_at: datetime | None,
        version: int = 0,
    ) -> Self:
        return cls(
            payment_id=payment_id,
            order_id=order_id,
            money=money,
            status=status,
            provider_session_id=provider_session_id,
            provider_payment_id=provider_payment_id,
            failure_code=failure_code,
            created_at=created_at,
            updated_at=updated_at,
            version=version,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def order_id(self) -> UUID:
        return self._order_id

    @property
    def money(self) -> Money:
        return self._money

    @property
    def status(self) -> PaymentStatus:
        return self._status

    @property
    def provider_session_id(self) -> str | None:
        return self._provider_session_id

    @property
    def provider_payment_id(self) -> str | None:
        return self._provider_payment_id

    @property
    def failure_code(self) -> str | None:
        return self._failure_code

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime | None:
        return self._updated_at

    @property
    def version(self) -> int:
        return self._version

    def mark_as_pending(self, provider_session_id: str) -> None:
        PaymentPolicy.require_provider_identifier(provider_session_id, PaymentErrorCode.INVALID_PROVIDER_SESSION_ID)

        if self._status is PaymentStatus.PENDING and self._provider_session_id == provider_session_id:
            return

        PaymentPolicy.require_transition(self._status, PaymentStatus.PENDING)
        self._provider_session_id = provider_session_id
        self._status = PaymentStatus.PENDING
        self._touch()

    def mark_as_succeeded(self, provider_payment_id: str) -> None:
        PaymentPolicy.require_provider_identifier(provider_payment_id, PaymentErrorCode.INVALID_PROVIDER_PAYMENT_ID)

        if self._status is PaymentStatus.SUCCEEDED and self._provider_payment_id == provider_payment_id:
            return

        PaymentPolicy.require_transition(self._status, PaymentStatus.SUCCEEDED)
        self._provider_payment_id = provider_payment_id
        self._failure_code = None
        self._status = PaymentStatus.SUCCEEDED
        self._touch()

    def mark_as_failed(self, failure_code: str | None = None) -> None:
        if failure_code is not None:
            PaymentPolicy.require_provider_identifier(failure_code, PaymentErrorCode.INVALID_FAILURE_CODE)

        if self._status is PaymentStatus.FAILED and self._failure_code == failure_code:
            return

        PaymentPolicy.require_transition(self._status, PaymentStatus.FAILED)
        self._failure_code = failure_code
        self._status = PaymentStatus.FAILED
        self._touch()

    def cancel(self) -> None:
        if self._status is PaymentStatus.CANCELED:
            return

        PaymentPolicy.require_transition(self._status, PaymentStatus.CANCELED)

        self._status = PaymentStatus.CANCELED
        self._touch()

    def retry(self) -> None:
        if self._status is PaymentStatus.CREATED:
            return

        PaymentPolicy.require_transition(self._status, PaymentStatus.CREATED)
        self._provider_session_id = None
        self._provider_payment_id = None
        self._failure_code = None
        self._status = PaymentStatus.CREATED
        self._touch()

    def _touch(self) -> None:
        self._updated_at = max(datetime.now(UTC), self._updated_at or self._created_at)
