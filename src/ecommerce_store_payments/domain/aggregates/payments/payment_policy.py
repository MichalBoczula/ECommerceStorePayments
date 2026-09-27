from datetime import datetime
from typing import ClassVar, final
from uuid import UUID

from ecommerce_store_payments.domain.aggregates.payments.enums.payment_status import PaymentStatus
from ecommerce_store_payments.domain.aggregates.payments.exceptions import (
    PaymentErrorCode,
    PaymentTransitionError,
    PaymentValidationError,
)
from ecommerce_store_payments.domain.aggregates.payments.value_objects.money import Money


@final
class PaymentPolicy:
    """Rules executed both when a payment is created and when it is rehydrated."""

    _ALLOWED_TRANSITIONS: ClassVar[dict[PaymentStatus, frozenset[PaymentStatus]]] = {
        PaymentStatus.CREATED: frozenset({PaymentStatus.PENDING, PaymentStatus.CANCELED}),
        PaymentStatus.PENDING: frozenset({PaymentStatus.SUCCEEDED, PaymentStatus.FAILED, PaymentStatus.CANCELED}),
    }

    @staticmethod
    def require_identifier(value: object, code: PaymentErrorCode) -> None:
        if not isinstance(value, UUID) or value.int == 0:
            raise PaymentValidationError(code, "Payment and order identifiers must be nonzero UUIDs.")

    @staticmethod
    def require_provider_identifier(value: object, code: PaymentErrorCode) -> None:
        if not isinstance(value, str) or not value or not value.isascii() or not value.isprintable():
            raise PaymentValidationError(code, "Provider identifier must contain printable ASCII without whitespace.")
        if any(character.isspace() for character in value):
            raise PaymentValidationError(code, "Provider identifier must contain printable ASCII without whitespace.")

    @staticmethod
    def validate_snapshot(
        payment_id: UUID,
        order_id: UUID,
        money: object,
        status: object,
        provider_session_id: str | None,
        provider_payment_id: str | None,
        failure_code: str | None,
        created_at: object,
        updated_at: object,
    ) -> None:
        """Reject invalid persisted states instead of bypassing aggregate invariants."""
        PaymentPolicy.require_identifier(payment_id, PaymentErrorCode.INVALID_PAYMENT_ID)
        PaymentPolicy.require_identifier(order_id, PaymentErrorCode.INVALID_ORDER_ID)
        if not isinstance(money, Money) or not isinstance(status, PaymentStatus):
            raise PaymentValidationError(PaymentErrorCode.INVALID_PAYMENT_STATE, "Payment money or status is invalid.")

        if not isinstance(created_at, datetime) or created_at.utcoffset() is None:
            raise PaymentValidationError(
                PaymentErrorCode.INVALID_PAYMENT_TIMESTAMP, "Creation time must be timezone-aware."
            )
        if updated_at is not None and (
            not isinstance(updated_at, datetime) or updated_at.utcoffset() is None or updated_at < created_at
        ):
            raise PaymentValidationError(
                PaymentErrorCode.INVALID_PAYMENT_TIMESTAMP, "Update time must follow creation time."
            )

        if provider_session_id is not None:
            PaymentPolicy.require_provider_identifier(provider_session_id, PaymentErrorCode.INVALID_PROVIDER_SESSION_ID)
        if provider_payment_id is not None:
            PaymentPolicy.require_provider_identifier(provider_payment_id, PaymentErrorCode.INVALID_PROVIDER_PAYMENT_ID)
        if failure_code is not None:
            PaymentPolicy.require_provider_identifier(failure_code, PaymentErrorCode.INVALID_FAILURE_CODE)

        if status is PaymentStatus.CREATED:
            valid = (
                updated_at is None
                and provider_session_id is None
                and provider_payment_id is None
                and failure_code is None
            )
        elif status is PaymentStatus.PENDING:
            valid = (
                updated_at is not None
                and provider_session_id is not None
                and provider_payment_id is None
                and failure_code is None
            )
        elif status is PaymentStatus.SUCCEEDED:
            valid = (
                updated_at is not None
                and provider_session_id is not None
                and provider_payment_id is not None
                and failure_code is None
            )
        elif status is PaymentStatus.FAILED:
            valid = updated_at is not None and provider_session_id is not None and provider_payment_id is None
        else:
            valid = updated_at is not None and provider_payment_id is None and failure_code is None

        if not valid:
            raise PaymentValidationError(
                PaymentErrorCode.INVALID_PAYMENT_STATE, f"Payment state is inconsistent for {status}."
            )

    @classmethod
    def require_transition(cls, current: PaymentStatus, target: PaymentStatus) -> None:
        """Only Created -> Pending/Canceled and Pending -> terminal are new transitions."""
        if target not in cls._ALLOWED_TRANSITIONS.get(current, frozenset()):
            raise PaymentTransitionError(current.value, target.value)
