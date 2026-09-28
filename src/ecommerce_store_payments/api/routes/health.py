from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel
from pymongo.errors import PyMongoError

from ecommerce_store_payments.api.errors import ReadinessUnavailableError, problem_responses
from ecommerce_store_payments.infrastructure.persistence.mongodb.mongo_database import MongoDatabase

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: Literal["healthy"]


@router.get("/health", operation_id="get_health", response_model=HealthResponse, responses=problem_responses(405, 500))
async def get_health() -> HealthResponse:
    return HealthResponse(status="healthy")


@router.get(
    "/health/live", operation_id="get_liveness", response_model=HealthResponse, responses=problem_responses(405, 500)
)
async def get_liveness() -> HealthResponse:
    return HealthResponse(status="healthy")


@router.get(
    "/health/ready",
    operation_id="get_readiness",
    response_model=HealthResponse,
    responses=problem_responses(405, 500, 503),
)
async def get_readiness(request: Request) -> HealthResponse:
    database: MongoDatabase = request.app.state.database
    try:
        await database.probe()
    except PyMongoError, TimeoutError:
        raise ReadinessUnavailableError from None
    return HealthResponse(status="healthy")
