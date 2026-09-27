from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.infrastructure.config.settings import Settings
from tests.conftest import UnitMongoDatabase


def test_health_returns_healthy_status(client: TestClient) -> None:
    app = cast(FastAPI, client.app)
    database = cast(UnitMongoDatabase, app.state.database)
    assert database.index_calls == 1
    assert database.probe_calls == 1

    for path in ("/health", "/health/live", "/health/ready"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
    assert database.probe_calls == 2


def test_readiness_reports_unavailable_without_exposing_mongo_error(client: TestClient) -> None:
    app = cast(FastAPI, client.app)
    database = cast(UnitMongoDatabase, app.state.database)
    database.available = False

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unhealthy"}
    for path in ("/health", "/health/live"):
        live_response = client.get(path)
        assert live_response.status_code == 200
        assert live_response.json() == {"status": "healthy"}


def test_openapi_is_generated_without_starting_mongodb(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_database(_: Settings) -> None:
        raise AssertionError("OpenAPI must not create a database client")

    monkeypatch.setattr("ecommerce_store_payments.api.app.MongoDatabase", unexpected_database)

    schema = create_app(Settings(environment="test")).openapi()

    paths = schema["paths"]
    assert "/health" in paths
    assert "/health/live" in paths
    assert "503" in paths["/health/ready"]["get"]["responses"]
    assert "/payments/{order_id}/pay" in paths
