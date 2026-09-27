from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pymongo.errors import PyMongoError

from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: Literal["healthy"]


class UnavailableResponse(BaseModel):
    status: Literal["unhealthy"]


@router.get("/health", operation_id="get_health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    return HealthResponse(status="healthy")


@router.get("/health/live", operation_id="get_liveness", response_model=HealthResponse)
async def get_liveness() -> HealthResponse:
    return HealthResponse(status="healthy")


@router.get(
    "/health/ready",
    operation_id="get_readiness",
    response_model=HealthResponse,
    responses={503: {"model": UnavailableResponse}},
)
async def get_readiness(request: Request) -> HealthResponse | JSONResponse:
    database: MongoDatabase = request.app.state.database
    try:
        await database.probe()
    except PyMongoError, TimeoutError:
        return JSONResponse(status_code=503, content=UnavailableResponse(status="unhealthy").model_dump())
    return HealthResponse(status="healthy")
