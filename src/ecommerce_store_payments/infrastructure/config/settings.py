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


@lru_cache
def get_settings() -> Settings:
    return Settings()
