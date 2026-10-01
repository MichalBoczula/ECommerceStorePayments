from __future__ import annotations
import datetime
from collections.abc import Callable
from dataclasses import dataclass, field
from kiota_abstractions.serialization import Parsable, ParseNode, SerializationWriter
from typing import Any, Optional, TYPE_CHECKING, Union
from uuid import UUID

@dataclass
class InvoiceResponseDto(Parsable):
    # The clietDataVersionId property
    cliet_data_version_id: Optional[UUID] = None
    # The createdAt property
    created_at: Optional[datetime.datetime] = None
    # The id property
    id: Optional[UUID] = None
    # The orderId property
    order_id: Optional[UUID] = None
    # The storageUrl property
    storage_url: Optional[str] = None

    @staticmethod
    def create_from_discriminator_value(parse_node: ParseNode) -> InvoiceResponseDto:
        """
        Creates a new instance of the appropriate class based on discriminator value
        param parse_node: The parse node to use to read the discriminator value and create the object
        Returns: InvoiceResponseDto
        """
        if parse_node is None:
            raise TypeError("parse_node cannot be null.")
        return InvoiceResponseDto()

    def get_field_deserializers(self,) -> dict[str, Callable[[ParseNode], None]]:
        """
        The deserialization information for the current model
        Returns: dict[str, Callable[[ParseNode], None]]
        """
        fields: dict[str, Callable[[Any], None]] = {
            "clietDataVersionId": lambda n : setattr(self, 'cliet_data_version_id', n.get_uuid_value()),
            "createdAt": lambda n : setattr(self, 'created_at', n.get_datetime_value()),
            "id": lambda n : setattr(self, 'id', n.get_uuid_value()),
            "orderId": lambda n : setattr(self, 'order_id', n.get_uuid_value()),
            "storageUrl": lambda n : setattr(self, 'storage_url', n.get_str_value()),
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
        writer.write_uuid_value("clietDataVersionId", self.cliet_data_version_id)
        writer.write_datetime_value("createdAt", self.created_at)
        writer.write_uuid_value("id", self.id)
        writer.write_uuid_value("orderId", self.order_id)
        writer.write_str_value("storageUrl", self.storage_url)
