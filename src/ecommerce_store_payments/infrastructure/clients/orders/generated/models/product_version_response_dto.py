from __future__ import annotations
import datetime
from collections.abc import Callable
from dataclasses import dataclass, field
from kiota_abstractions.serialization import Parsable, ParseNode, SerializationWriter
from typing import Any, Optional, TYPE_CHECKING, Union
from uuid import UUID

@dataclass
class ProductVersionResponseDto(Parsable):
    # The brand property
    brand: Optional[str] = None
    # The createdAt property
    created_at: Optional[datetime.datetime] = None
    # The deactivatedAt property
    deactivated_at: Optional[datetime.datetime] = None
    # The id property
    id: Optional[UUID] = None
    # The isActive property
    is_active: Optional[bool] = None
    # The name property
    name: Optional[str] = None
    # The priceAmount property
    price_amount: Optional[float] = None
    # The priceCurrency property
    price_currency: Optional[str] = None
    # The productId property
    product_id: Optional[UUID] = None

    @staticmethod
    def create_from_discriminator_value(parse_node: ParseNode) -> ProductVersionResponseDto:
        """
        Creates a new instance of the appropriate class based on discriminator value
        param parse_node: The parse node to use to read the discriminator value and create the object
        Returns: ProductVersionResponseDto
        """
        if parse_node is None:
            raise TypeError("parse_node cannot be null.")
        return ProductVersionResponseDto()

    def get_field_deserializers(self,) -> dict[str, Callable[[ParseNode], None]]:
        """
        The deserialization information for the current model
        Returns: dict[str, Callable[[ParseNode], None]]
        """
        fields: dict[str, Callable[[Any], None]] = {
            "brand": lambda n : setattr(self, 'brand', n.get_str_value()),
            "createdAt": lambda n : setattr(self, 'created_at', n.get_datetime_value()),
            "deactivatedAt": lambda n : setattr(self, 'deactivated_at', n.get_datetime_value()),
            "id": lambda n : setattr(self, 'id', n.get_uuid_value()),
            "isActive": lambda n : setattr(self, 'is_active', n.get_bool_value()),
            "name": lambda n : setattr(self, 'name', n.get_str_value()),
            "priceAmount": lambda n : setattr(self, 'price_amount', n.get_float_value()),
            "priceCurrency": lambda n : setattr(self, 'price_currency', n.get_str_value()),
            "productId": lambda n : setattr(self, 'product_id', n.get_uuid_value()),
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
        writer.write_str_value("brand", self.brand)
        writer.write_datetime_value("createdAt", self.created_at)
        writer.write_datetime_value("deactivatedAt", self.deactivated_at)
        writer.write_uuid_value("id", self.id)
        writer.write_bool_value("isActive", self.is_active)
        writer.write_str_value("name", self.name)
        writer.write_float_value("priceAmount", self.price_amount)
        writer.write_str_value("priceCurrency", self.price_currency)
        writer.write_uuid_value("productId", self.product_id)
