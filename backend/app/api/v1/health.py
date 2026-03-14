import structlog
from fastapi import APIRouter
from sqlalchemy import text

from app.core import database
from app.core.config import settings
from app.schemas.common import HealthResponse

logger = structlog.get_logger("health")
router = APIRouter(tags=["Health"])


@router.get("/health/live", response_model=HealthResponse)
async def liveness():
    """Liveness probe: process is running."""
    return HealthResponse(status="alive")


@router.get("/health/ready", response_model=HealthResponse)
async def readiness():
    """Readiness probe: all critical dependencies available."""
    checks = {}

    # Database check
    try:
        if database.async_session_factory:
            async with database.async_session_factory() as session:
                await session.execute(text("SELECT 1"))
            checks["database"] = "ok"
        else:
            checks["database"] = "not_initialized"
    except Exception as e:
        logger.error("health_check_db_failed", error=str(e))
        checks["database"] = "error"

    all_ok = all(v == "ok" for v in checks.values())

    return HealthResponse(
        status="ready" if all_ok else "degraded",
        version=settings.APP_VERSION,
        checks=checks,
    )


@router.get("/health/startup", response_model=HealthResponse)
async def startup_check():
    """Startup probe: initial boot complete."""
    return HealthResponse(
        status="started",
        version=settings.APP_VERSION,
    )
