from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PAYMENTS_",
        extra="ignore",
    )

    app_name: str = Field(default="ECommerce Store Payments API", min_length=1)
    environment: Literal["local", "test", "development", "staging", "production"] = "local"
    mongodb_connection_string: str = "mongodb://localhost:27017"
    mongodb_database_name: str = Field(default="ecommerce_store_payments", pattern=r"^[A-Za-z0-9_-]+$")
    mongodb_payments_collection_name: str = Field(default="payments", pattern=r"^[A-Za-z0-9_-]+$")
    mongodb_probe_timeout_seconds: float = Field(default=2.0, gt=0, le=30)
    mongodb_server_selection_timeout_ms: int = Field(default=2000, gt=0, le=30000)
    orders_api_base_url: str = "http://localhost:5000"

    @field_validator("mongodb_connection_string")
    @classmethod
    def validate_mongodb_uri(cls, value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme not in {"mongodb", "mongodb+srv"} or not parts.hostname or any(ch.isspace() for ch in value):
            raise ValueError("MongoDB connection string must be a MongoDB URI with a host.")
        return value

    @field_validator("orders_api_base_url")
    @classmethod
    def validate_orders_url(cls, value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme not in {"http", "https"} or not parts.hostname or any(ch.isspace() for ch in value):
            raise ValueError("Orders API base URL must be an HTTP(S) URL with a host.")
        try:
            if parts.port == 0:
                raise ValueError("port 0 is not valid")
        except ValueError as error:
            raise ValueError("Orders API base URL has an invalid port.") from error
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
