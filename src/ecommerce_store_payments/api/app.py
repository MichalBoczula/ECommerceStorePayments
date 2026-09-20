from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from httpx2 import AsyncClient

from ecommerce_store_payments.api.routes.health import router as health_router
from ecommerce_store_payments.api.routes.payments import router as payments_router
from ecommerce_store_payments.application.payments.payment_service import PaymentService
from ecommerce_store_payments.infrastructure.clients.orders.http_order_reader import HttpOrderReader
from ecommerce_store_payments.infrastructure.config.settings import Settings, get_settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        database = MongoDatabase(resolved_settings)
        orders_client = AsyncClient(base_url=resolved_settings.orders_api_base_url, trust_env=False)
        app.state.payment_service = PaymentService(
            payment_repository=MongoPaymentRepository(database.payments),
            order_reader=HttpOrderReader(orders_client),
        )

        if resolved_settings.environment != "test":
            await database.ensure_indexes()

        try:
            yield
        finally:
            await orders_client.aclose()
            await database.close()

    app = FastAPI(
        title="ECommerce Store Payments API",
        docs_url="/swagger",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.include_router(health_router)
    app.include_router(payments_router)
    return app
