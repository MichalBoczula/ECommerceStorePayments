import pytest
from fastapi.testclient import TestClient
from httpx2 import AsyncClient

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.infrastructure.config.settings import Settings
from tests.conftest import UnitMongoDatabase


@pytest.mark.parametrize("failure_stage", ["probe", "indexes"])
def test_startup_failure_closes_database_and_orders_client(monkeypatch: pytest.MonkeyPatch, failure_stage: str) -> None:
    databases: list[UnitMongoDatabase] = []
    orders_clients: list[AsyncClient] = []

    class FailingDatabase(UnitMongoDatabase):
        def __init__(self, settings: Settings) -> None:
            super().__init__(settings)
            databases.append(self)

        async def probe(self) -> None:
            await super().probe()
            if failure_stage == "probe":
                raise TimeoutError("database is unavailable")

        async def ensure_indexes(self) -> None:
            await super().ensure_indexes()
            if failure_stage == "indexes":
                raise RuntimeError("index build failed")

    class TrackingOrdersClient(AsyncClient):
        def __init__(self, base_url: str, timeout: float, trust_env: bool) -> None:
            super().__init__(base_url=base_url, timeout=timeout, trust_env=trust_env)
            orders_clients.append(self)

    monkeypatch.setattr("ecommerce_store_payments.api.app.MongoDatabase", FailingDatabase)
    monkeypatch.setattr("ecommerce_store_payments.api.app.AsyncClient", TrackingOrdersClient)

    with pytest.raises((TimeoutError, RuntimeError)):
        with TestClient(create_app(Settings(environment="test"))):
            pass

    assert len(databases) == len(orders_clients) == 1
    assert databases[0].closed
    assert orders_clients[0].is_closed
    assert databases[0].probe_calls == 1
    assert databases[0].index_calls == (0 if failure_stage == "probe" else 1)
