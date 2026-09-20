from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from ecommerce_store_payments.api.app import create_app
from ecommerce_store_payments.infrastructure.config.settings import Settings


@pytest.fixture
def client() -> Generator[TestClient]:
    settings = Settings(environment="test")
    with TestClient(create_app(settings)) as test_client:
        yield test_client
