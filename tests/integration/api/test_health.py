from time import monotonic
from typing import cast
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo import AsyncMongoClient
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.infrastructure.config.settings import Settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.documents.payment_document import PaymentDocument
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase


async def test_startup_creates_named_index_and_readiness_uses_real_mongodb(mongo_url: str) -> None:
    database_name = f"payments_startup_{uuid4().hex}"
    cleanup_client: AsyncMongoClient[PaymentDocument] = AsyncMongoClient(mongo_url)
    try:
        settings = Settings(
            environment="test", mongodb_connection_string=mongo_url, mongodb_database_name=database_name
        )
        with TestClient(create_app(settings)) as client:
            response = client.get("/health/ready")
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}

            async def unavailable() -> None:
                raise ServerSelectionTimeoutError("private connection detail")

            app = cast(FastAPI, client.app)
            database = cast(MongoDatabase, app.state.database)
            database.probe = unavailable
            failed = client.get("/health/ready")
            assert failed.status_code == 503
            assert failed.json()["code"] == "service_unavailable"
            assert failed.headers["content-type"] == "application/problem+json"
            assert "private connection detail" not in failed.text
            assert client.get("/health/live").status_code == 200

        indexes = await cleanup_client[database_name]["payments"].index_information()
        assert indexes["ux_payments_order_id"]["key"] == [("order_id", 1)]
        assert indexes["ux_payments_order_id"]["unique"] is True
        history_indexes = await cleanup_client[database_name]["payment_history"].index_information()
        assert history_indexes["ix_payment_history_payment_id"]["key"] == [("payment_id", 1)]
    finally:
        try:
            await cleanup_client.drop_database(database_name)
        finally:
            await cleanup_client.close()


async def test_startup_rejects_conflicting_named_index(mongo_url: str) -> None:
    database_name = f"payments_bad_index_{uuid4().hex}"
    cleanup_client: AsyncMongoClient[PaymentDocument] = AsyncMongoClient(mongo_url)
    try:
        await cleanup_client[database_name]["payments"].create_index(
            "order_id", unique=False, name="ux_payments_order_id"
        )
        settings = Settings(
            environment="test", mongodb_connection_string=mongo_url, mongodb_database_name=database_name
        )
        with pytest.raises(OperationFailure):
            with TestClient(create_app(settings)):
                pass
    finally:
        try:
            await cleanup_client.drop_database(database_name)
        finally:
            await cleanup_client.close()


def test_startup_fails_quickly_when_mongodb_is_unreachable() -> None:
    settings = Settings(
        environment="test",
        mongodb_connection_string="mongodb://127.0.0.1:1",
        mongodb_probe_timeout_seconds=0.2,
        mongodb_server_selection_timeout_ms=100,
    )
    started_at = monotonic()

    with pytest.raises((ServerSelectionTimeoutError, TimeoutError)):
        with TestClient(create_app(settings)):
            pass

    assert monotonic() - started_at < 2.0
