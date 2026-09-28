"""Keep Invoice JSON money tokens exact while Kiota deserializes typed DTOs.

Kiota 1.34.1 maps OpenAPI number/double to Python float. The Invoice wire
contract contains decimal money, so the stock JSON factory would round it.
"""

import json
from decimal import Decimal
from typing import Any, TypeVar, cast

from kiota_abstractions.serialization.parsable import Parsable
from kiota_abstractions.serialization.parsable_factory import ParsableFactory
from kiota_abstractions.serialization.parse_node import ParseNode
from kiota_serialization_json.json_parse_node import JsonParseNode
from kiota_serialization_json.json_parse_node_factory import JsonParseNodeFactory

from ecommerce_store_payments.infrastructure.clients.orders.generated.models.order_response_dto import OrderResponseDto

T = TypeVar("T", bound=Parsable)


def _money_token(value: object) -> Decimal | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (Decimal, int)):
        return Decimal(value)
    return None


class _PreciseOrderNode(JsonParseNode):
    def get_object_value(self, factory: ParsableFactory[T]) -> T:
        model = super().get_object_value(factory)
        if isinstance(model, OrderResponseDto) and isinstance(self._json_node, dict):
            raw = cast(dict[str, object], self._json_node)  # pyright: ignore[reportUnknownMemberType]
            # The generated annotations say float, but only exact Decimal values
            # are assigned. HttpOrderReader checks their runtime types before use.
            if (amount := _money_token(raw.get("totalAmount"))) is not None:
                model.total_amount = cast(float, amount)
            lines = raw.get("lines")
            if isinstance(lines, list) and model.lines is not None:
                for line, wire in zip(model.lines, cast(list[object], lines), strict=False):
                    if isinstance(wire, dict):
                        item = cast(dict[str, object], wire)
                        if (amount := _money_token(item.get("lineTotalAmount"))) is not None:
                            line.line_total_amount = cast(float, amount)
        return model


class PreciseOrderJsonFactory(JsonParseNodeFactory):
    def get_root_parse_node(self, content_type: str, content: bytes) -> ParseNode:
        if content_type.casefold() not in {"application/json", "text/plain"} or not content:
            raise ValueError("Expected a nonempty JSON response from Orders.")

        def reject_constant(value: str) -> Any:
            raise ValueError(f"Invalid JSON numeric constant: {value}")

        payload = json.loads(content.decode("utf-8"), parse_float=Decimal, parse_constant=reject_constant)
        return _PreciseOrderNode(payload)
