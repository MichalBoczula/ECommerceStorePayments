from typing import final
from uuid import UUID


@final
class PaymentMissingError(LookupError):
    def __init__(self, payment_id: UUID) -> None:
        self.payment_id = payment_id
        super().__init__(f"Payment {payment_id} does not exist.")


@final
class PaymentConflictError(RuntimeError):
    def __init__(self, payment_id: UUID, expected_version: int) -> None:
        self.payment_id = payment_id
        self.expected_version = expected_version
        super().__init__(f"Payment {payment_id} has changed since version {expected_version} was read.")


@final
class PaymentDuplicateError(ValueError):
    def __init__(self, payment_id: UUID, order_id: UUID) -> None:
        self.payment_id = payment_id
        self.order_id = order_id
        super().__init__(f"A payment already exists for order {order_id} or payment ID {payment_id}.")
