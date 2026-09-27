from uuid import UUID


class PaymentNotFoundError(LookupError):
    def __init__(self, order_id: UUID) -> None:
        super().__init__(f"Payment for order {order_id} was not found.")


class OrderNotFoundError(LookupError):
    def __init__(self, order_id: UUID) -> None:
        super().__init__(f"Order {order_id} was not found.")


class OrderIntegrationError(Exception):
    def __init__(self, order_id: UUID, reason: str) -> None:
        super().__init__(f"Cannot read order {order_id}: {reason}.")


class OrderTimeoutError(OrderIntegrationError):
    def __init__(self, order_id: UUID) -> None:
        super().__init__(order_id, "Orders service timed out")


class OrderUnavailableError(OrderIntegrationError):
    def __init__(self, order_id: UUID) -> None:
        super().__init__(order_id, "Orders service is unavailable")


class OrderInvalidResponseError(OrderIntegrationError):
    def __init__(self, order_id: UUID) -> None:
        super().__init__(order_id, "Orders service returned an invalid response")


class OrderNotPayableError(ValueError):
    def __init__(self, order_id: UUID, status: str) -> None:
        super().__init__(f"Order {order_id} with status '{status}' cannot be paid.")


class OrderTotalChangedError(ValueError):
    def __init__(self, order_id: UUID) -> None:
        super().__init__(f"Order {order_id} total changed since its payment was created.")
