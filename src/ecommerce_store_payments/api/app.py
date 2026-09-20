from fastapi import FastAPI

from ecommerce_store_payments.api.routes.health import router as health_router
from ecommerce_store_payments.infrastructure.config.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    app = FastAPI(
        title="ECommerce Store Payments API",
        docs_url="/swagger",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.state.settings = resolved_settings
    app.include_router(health_router)
    return app
