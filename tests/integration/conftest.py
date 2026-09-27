from collections.abc import AsyncGenerator, Generator
from uuid import uuid4

import pytest
from pymongo import AsyncMongoClient
from testcontainers.community.mongodb import MongoDbContainer

from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase


@pytest.fixture(scope="session")
def mongo_url() -> Generator[str]:
    with MongoDbContainer("mongo:8.0") as container:
        yield container.get_connection_url()


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
