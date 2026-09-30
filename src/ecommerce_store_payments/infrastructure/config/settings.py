from functools import lru_cache
from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
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
    mongodb_payment_history_collection_name: str = Field(default="payment_history", pattern=r"^[A-Za-z0-9_-]+$")
    mongodb_probe_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    mongodb_server_selection_timeout_ms: int = Field(default=5000, gt=0, le=30000)
    orders_api_base_url: str = "http://localhost:5000"
    orders_api_timeout_seconds: float = Field(default=5.0, gt=0, le=30)
    stripe_enabled: bool = False
    stripe_secret_key: SecretStr | None = None
    stripe_success_url: str = "http://localhost:4200/orders?checkout=success"
    stripe_cancel_url: str = "http://localhost:4200/orders?checkout=cancel"
    stripe_timeout_seconds: float = Field(default=5.0, gt=0, le=15)

    @field_validator("stripe_secret_key")
    @classmethod
    def validate_stripe_key(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None:
            key = value.get_secret_value()
            if not key:
                return None
            if not key.startswith("sk_test_") or len(key) <= len("sk_test_") or any(ch.isspace() for ch in key):
                raise ValueError("Stripe requires a test-mode secret key.")
        return value

    @field_validator("stripe_success_url", "stripe_cancel_url")
    @classmethod
    def validate_return_url(cls, value: str) -> str:
        parts = urlsplit(value)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or parts.fragment
            or any(ch.isspace() for ch in value)
            or "{" in value
            or "}" in value
        ):
            raise ValueError("Checkout return URL must be a fixed HTTP(S) URL without credentials or fragments.")
        if parts.scheme == "http" and parts.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("Nonlocal checkout return URLs require HTTPS.")
        try:
            if parts.port == 0:
                raise ValueError("port 0 is not valid")
        except ValueError as error:
            raise ValueError("Checkout return URL has an invalid port.") from error
        return value

    @model_validator(mode="after")
    def validate_stripe_configuration(self) -> Self:
        if self.stripe_enabled and self.stripe_secret_key is None:
            raise ValueError("Enabled Stripe checkout requires a test secret key.")
        return self

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
