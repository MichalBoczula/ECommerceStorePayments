from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI
from httpx2 import AsyncClient

from ecommerce_store_payments.api.errors import install_error_handlers
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
        try:
            async with AsyncClient(
                base_url=resolved_settings.orders_api_base_url,
                timeout=resolved_settings.orders_api_timeout_seconds,
                trust_env=False,
            ) as orders_client:
                await database.probe()
                await database.ensure_indexes()
                app.state.database = database
                app.state.payment_service = PaymentService(
                    payment_repository=MongoPaymentRepository(database),
                    order_reader=HttpOrderReader(orders_client),
                )
                yield
        finally:
            await database.close()

    app = FastAPI(
        title=resolved_settings.app_name,
        docs_url="/swagger",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(payments_router)

    generated_openapi = app.openapi

    def openapi() -> dict[str, Any]:
        schema = generated_openapi()
        # RequestValidationError is mapped to 400 by install_error_handlers.
        for path_item in schema["paths"].values():
            for operation in path_item.values():
                if isinstance(operation, dict) and "responses" in operation:
                    cast(dict[str, Any], operation["responses"]).pop("422", None)
        return schema

    app.openapi = openapi
    return app
