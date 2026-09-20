from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PAYMENTS_",
        extra="ignore",
    )

    app_name: str = "ECommerce Store Payments API"
    environment: Literal["local", "test", "development", "staging", "production"] = "local"
    mongodb_connection_string: str = "mongodb://localhost:27017"
    mongodb_database_name: str = "ecommerce_store_payments"
    mongodb_payments_collection_name: str = "payments"


@lru_cache
def get_settings() -> Settings:
    return Settings()
