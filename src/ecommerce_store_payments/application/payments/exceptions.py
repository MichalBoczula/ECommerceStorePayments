from uuid import UUID


class PaymentNotFoundError(LookupError):
    def __init__(self, order_id: UUID) -> None:
        super().__init__(f"Payment for order {order_id} was not found.")


class OrderNotFoundError(LookupError):
    def __init__(self, order_id: UUID) -> None:
        super().__init__(f"Order {order_id} was not found.")


class OrderNotPayableError(ValueError):
    def __init__(self, order_id: UUID, status: str) -> None:
        super().__init__(f"Order {order_id} with status '{status}' cannot be paid.")
