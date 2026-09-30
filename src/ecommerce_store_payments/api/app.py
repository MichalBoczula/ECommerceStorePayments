from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI
from httpx import AsyncClient
from kiota_abstractions.authentication.anonymous_authentication_provider import AnonymousAuthenticationProvider

from ecommerce_store_payments.api.errors import install_error_handlers
from ecommerce_store_payments.api.routes.health import router as health_router
from ecommerce_store_payments.api.routes.payments import router as payments_router
from ecommerce_store_payments.api.routes.webhooks import router as webhooks_router
from ecommerce_store_payments.application.payments.payment_service import PaymentService
from ecommerce_store_payments.application.payments.webhook_service import WebhookService
from ecommerce_store_payments.infrastructure.clients.orders.generated.orders_client import OrdersClient
from ecommerce_store_payments.infrastructure.clients.orders.http_order_reader import HttpOrderReader
from ecommerce_store_payments.infrastructure.clients.orders.precise_json import PreciseOrderJsonFactory
from ecommerce_store_payments.infrastructure.clients.orders.request_adapter import OrdersRequestAdapter
from ecommerce_store_payments.infrastructure.clients.stripe.checkout_provider import StripeCheckoutProvider
from ecommerce_store_payments.infrastructure.clients.stripe.webhook_verifier import StripeWebhookVerifier
from ecommerce_store_payments.infrastructure.config.settings import Settings, get_settings
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.payment_repository import (
    MongoPaymentRepository,
)
from ecommerce_store_payments.infrastructure.persistence.mongodb.repositories.webhook_repository import (
    MongoWebhookRepository,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        database = MongoDatabase(resolved_settings)
        checkout_provider: StripeCheckoutProvider | None = None
        try:
            checkout_provider = StripeCheckoutProvider(resolved_settings)
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
                    order_reader=HttpOrderReader(
                        OrdersClient(
                            OrdersRequestAdapter(
                                AnonymousAuthenticationProvider(),
                                parse_node_factory=PreciseOrderJsonFactory(),
                                http_client=orders_client,
                                base_url=resolved_settings.orders_api_base_url,
                            )
                        )
                    ),
                    checkout_provider=checkout_provider,
                )
                app.state.webhook_service = WebhookService(
                    verifier=StripeWebhookVerifier(resolved_settings),
                    webhooks=MongoWebhookRepository(database),
                    payments=MongoPaymentRepository(database),
                )
                yield
        finally:
            try:
                if checkout_provider is not None:
                    await checkout_provider.close()
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
    app.include_router(webhooks_router)

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
