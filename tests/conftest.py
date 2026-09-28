from collections.abc import AsyncGenerator, Generator
from time import monotonic, sleep
from typing import cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pymongo import AsyncMongoClient, MongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.errors import PyMongoError
from testcontainers.community.mongodb import MongoDbContainer

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase


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


class _ReplicaSetMongoContainer(MongoDbContainer):
    def _configure(self) -> None:
        self.with_command(["mongod", "--replSet", "rs0", "--bind_ip_all"])

    def get_connection_url(self) -> str:
        return f"mongodb://{self.get_container_host_ip()}:{self.get_exposed_port(27017)}/?directConnection=true"


@pytest.fixture(scope="session")
def mongo_url() -> Generator[str]:
    with _ReplicaSetMongoContainer("mongo:8.0") as container:
        initiated = container.exec(
            ["mongosh", "--quiet", "--eval", "rs.initiate({_id:'rs0',members:[{_id:0,host:'localhost:27017'}]})"]
        )
        assert initiated.exit_code == 0, initiated.output.decode()
        url = container.get_connection_url()
        client: MongoClient[PaymentDocument] = MongoClient(url, serverSelectionTimeoutMS=1000)
        try:
            deadline = monotonic() + 30
            while monotonic() < deadline:
                try:
                    if client.admin.command("hello").get("isWritablePrimary"):
                        break
                except PyMongoError:
                    pass
                sleep(0.25)
            else:
                raise RuntimeError("MongoDB replica set did not elect a primary")
        finally:
            client.close()
        yield url


@pytest.fixture
async def mongo_database(mongo_url: str) -> AsyncGenerator[MongoDatabase]:
    database_name = f"payments_test_{uuid4().hex}"
    settings = Settings(
        environment="test",
        mongodb_connection_string=mongo_url,
        mongodb_database_name=database_name,
    )
    database = MongoDatabase(settings)
    cleanup_client: AsyncMongoClient[PaymentDocument] = AsyncMongoClient(mongo_url)
    try:
        await database.ensure_indexes()
        yield database
    finally:
        try:
            await cleanup_client.drop_database(database_name)
        finally:
            await database.close()
            await cleanup_client.close()
