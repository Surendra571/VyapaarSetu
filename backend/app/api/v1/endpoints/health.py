from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.database import check_db_connectivity

router = APIRouter()


class DatabaseHealth(BaseModel):
    connected: bool
    latency_ms: Optional[float] = None
    message: str
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = Field(description="Overall health status: healthy | degraded")
    app_name: str
    environment: str
    timestamp: datetime
    database: DatabaseHealth


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Application and Database Health Check",
    description="Returns the current operational status of the API and its PostgreSQL database connection.",
)
async def get_health_status() -> HealthResponse:
    db_status = await check_db_connectivity()
    is_healthy = db_status["connected"]

    return HealthResponse(
        status="healthy" if is_healthy else "degraded",
        app_name=settings.APP_NAME,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        database=DatabaseHealth(**db_status),
    )

