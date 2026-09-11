"""Health check endpoint verifying system and service connectivity."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.db.session import get_db
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="System Health & Readiness Check",
    description="Probes API readiness along with PostgreSQL database and Redis broker connectivity.",
)
async def health_check(
    db: AsyncSession = Depends(get_db),
) -> HealthResponse:
    """Check health of API Gateway, Database, and Redis broker."""
    components = {
        "api": "healthy",
        "database": "unknown",
        "redis": "unknown",
    }
    is_healthy = True

    # 1. Probe PostgreSQL connectivity
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            components["database"] = "healthy"
        else:
            components["database"] = "unhealthy"
            is_healthy = False
    except Exception as exc:
        logger.warning("Health check: Database probe failed: %s", exc)
        components["database"] = "unavailable"
        is_healthy = False

    # 2. Probe Redis connectivity
    try:
        redis_client = Redis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        pong = await redis_client.ping()
        await redis_client.aclose()
        if pong:
            components["redis"] = "healthy"
        else:
            components["redis"] = "unhealthy"
            is_healthy = False
    except Exception as exc:
        logger.warning("Health check: Redis probe failed: %s", exc)
        components["redis"] = "unavailable"
        is_healthy = False

    return HealthResponse(
        status="healthy" if is_healthy else "degraded",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        components=components,
        timestamp=datetime.now(UTC).isoformat(),
    )
