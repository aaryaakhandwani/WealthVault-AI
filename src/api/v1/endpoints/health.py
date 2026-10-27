from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from src.core.config import Settings, get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Structured health check response model."""

    status: str = Field(..., description="Operational status of the service", examples=["ok"])
    environment: str = Field(..., description="Current deployment environment", examples=["development"])
    version: str = Field(..., description="Application semantic version", examples=["0.1.0"])
    timestamp: datetime = Field(..., description="UTC timestamp of the health check")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service Health Check",
    description="Returns the current operational status, environment, and version of the API.",
    tags=["System"],
)
async def get_health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    """Return application health information."""
    return HealthResponse(
        status="ok",
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
        timestamp=datetime.now(timezone.utc),
    )
