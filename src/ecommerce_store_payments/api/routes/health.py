from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: Literal["healthy"]


@router.get("/health", operation_id="get_health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    return HealthResponse(status="healthy")
