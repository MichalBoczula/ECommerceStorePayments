from enum import StrEnum
from typing import final


class PaymentErrorCode(StrEnum):
    INVALID_AMOUNT = "invalid_money_amount"
    INVALID_CURRENCY = "invalid_currency"
    INVALID_PAYMENT_ID = "invalid_payment_id"
    INVALID_ORDER_ID = "invalid_order_id"
    INVALID_PROVIDER_SESSION_ID = "invalid_provider_session_id"
    INVALID_PROVIDER_PAYMENT_ID = "invalid_provider_payment_id"
    INVALID_FAILURE_CODE = "invalid_failure_code"
    INVALID_PAYMENT_STATE = "invalid_payment_state"
    INVALID_PAYMENT_TIMESTAMP = "invalid_payment_timestamp"
    INVALID_PAYMENT_VERSION = "invalid_payment_version"
    INVALID_PAYMENT_TRANSITION = "invalid_payment_transition"
    INVALID_CHECKOUT_ATTEMPT = "invalid_checkout_attempt"


class PaymentDomainError(ValueError):
    def __init__(self, code: PaymentErrorCode, message: str) -> None:
        self.code = code
        super().__init__(message)


@final
class MoneyValidationError(PaymentDomainError):
    pass


@final
class PaymentValidationError(PaymentDomainError):
    pass


@final
class PaymentTransitionError(PaymentDomainError):
    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(
            PaymentErrorCode.INVALID_PAYMENT_TRANSITION, f"Payment cannot transition from {current} to {target}."
        )
