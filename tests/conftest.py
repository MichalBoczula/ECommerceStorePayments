from collections.abc import Generator
from typing import cast

import pytest
from fastapi.testclient import TestClient
from pymongo.asynchronous.collection import AsyncCollection

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument


class UnitMongoDatabase:
    """Only HTTP unit tests use this adapter; integration tests start real MongoDB."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.payments = cast(AsyncCollection[PaymentDocument], object())
        self.available = True
        self.probe_calls = 0
        self.index_calls = 0
        self.closed = False

    async def probe(self) -> None:
        self.probe_calls += 1
        if not self.available:
            raise TimeoutError("MongoDB probe timed out")

    async def ensure_indexes(self) -> None:
        self.index_calls += 1

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient]:
    monkeypatch.setattr("ecommerce_store_payments.api.app.MongoDatabase", UnitMongoDatabase)
    settings = Settings(environment="test")
    with TestClient(create_app(settings)) as test_client:
        yield test_client
