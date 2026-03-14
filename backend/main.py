from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_engine
from app.core.logging import setup_logging
from app.middleware.correlation import CorrelationIdMiddleware
from app.middleware.error_handler import register_exception_handlers
from app.middleware.logging import RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    setup_logging()

    import structlog
    _logger = structlog.get_logger("startup")
    _logger.info(
        "db_config_check",
        has_db_url=bool(settings.DATABASE_URL),
        has_pool_url=bool(settings.DATABASE_POOL_URL),
        db_url_prefix=settings.DATABASE_URL[:30] if settings.DATABASE_URL else "empty",
    )

    if settings.DATABASE_URL or settings.DATABASE_POOL_URL:
        try:
            init_engine()
            _logger.info("db_engine_initialized")
        except Exception as e:
            _logger.error("db_engine_init_failed", error=str(e))

    yield


app = FastAPI(
    title="MedRAG Assistant",
    description="AI Medical Document Assistant with RAG",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware stack (applied bottom-to-top: last added = first executed)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
register_exception_handlers(app)

# Routers
from app.api.v1.auth import router as auth_router  # noqa: E402
from app.api.v1.health import router as health_router  # noqa: E402
from app.api.v1.documents import router as documents_router  # noqa: E402
from app.api.v1.invitations import router as invitations_router  # noqa: E402
from app.api.v1.queries import router as queries_router  # noqa: E402
from app.api.v1.tenants import router as tenants_router  # noqa: E402
from app.api.v1.ws import router as ws_router  # noqa: E402
from app.api.v1.demo import router as demo_router  # noqa: E402
from app.api.v1.audit import router as audit_router  # noqa: E402

app.include_router(health_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(tenants_router, prefix="/api/v1")
app.include_router(invitations_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(queries_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(demo_router, prefix="/api/v1")
app.include_router(ws_router)
