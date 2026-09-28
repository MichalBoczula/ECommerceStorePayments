from __future__ import annotations
import datetime
from collections.abc import Callable
from dataclasses import dataclass, field
from kiota_abstractions.serialization import Parsable, ParseNode, SerializationWriter
from typing import Any, Optional, TYPE_CHECKING, Union
from uuid import UUID

if TYPE_CHECKING:
    from .order_line_response_dto import OrderLineResponseDto

@dataclass
class OrderResponseDto(Parsable):
    # The clientId property
    client_id: Optional[UUID] = None
    # The createdAt property
    created_at: Optional[datetime.datetime] = None
    # The id property
    id: Optional[UUID] = None
    # The lines property
    lines: Optional[list[OrderLineResponseDto]] = None
    # The status property
    status: Optional[str] = None
    # The totalAmount property
    total_amount: Optional[float] = None
    # The totalCurrency property
    total_currency: Optional[str] = None
    # The updatedAt property
    updated_at: Optional[datetime.datetime] = None

    @staticmethod
    def create_from_discriminator_value(parse_node: ParseNode) -> OrderResponseDto:
        """
        Creates a new instance of the appropriate class based on discriminator value
        param parse_node: The parse node to use to read the discriminator value and create the object
        Returns: OrderResponseDto
        """
        if parse_node is None:
            raise TypeError("parse_node cannot be null.")
        return OrderResponseDto()

    def get_field_deserializers(self,) -> dict[str, Callable[[ParseNode], None]]:
        """
        The deserialization information for the current model
        Returns: dict[str, Callable[[ParseNode], None]]
        """
        from .order_line_response_dto import OrderLineResponseDto

        from .order_line_response_dto import OrderLineResponseDto

        fields: dict[str, Callable[[Any], None]] = {
            "clientId": lambda n : setattr(self, 'client_id', n.get_uuid_value()),
            "createdAt": lambda n : setattr(self, 'created_at', n.get_datetime_value()),
            "id": lambda n : setattr(self, 'id', n.get_uuid_value()),
            "lines": lambda n : setattr(self, 'lines', n.get_collection_of_object_values(OrderLineResponseDto)),
            "status": lambda n : setattr(self, 'status', n.get_str_value()),
            "totalAmount": lambda n : setattr(self, 'total_amount', n.get_float_value()),
            "totalCurrency": lambda n : setattr(self, 'total_currency', n.get_str_value()),
            "updatedAt": lambda n : setattr(self, 'updated_at', n.get_datetime_value()),
        }
        return fields

    def serialize(self,writer: SerializationWriter) -> None:
        """
        Serializes information the current object
        param writer: Serialization writer to use to serialize this model
        Returns: None
        """
        if writer is None:
            raise TypeError("writer cannot be null.")
        writer.write_uuid_value("clientId", self.client_id)
        writer.write_datetime_value("createdAt", self.created_at)
        writer.write_uuid_value("id", self.id)
        writer.write_collection_of_object_values("lines", self.lines)
        writer.write_str_value("status", self.status)
        writer.write_float_value("totalAmount", self.total_amount)
        writer.write_str_value("totalCurrency", self.total_currency)
        writer.write_datetime_value("updatedAt", self.updated_at)
