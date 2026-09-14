"""FastAPI application entrypoint for Secure Real-Time Remote Code Execution Lab."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.endpoints.metrics import router as metrics_router
from app.api.v1.endpoints.websocket import router as ws_router
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import logger
from app.core.telemetry import init_tracer
from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager handling startup and graceful shutdown."""
    logger.info(
        "Initializing %s v%s in %s mode...",
        settings.PROJECT_NAME,
        settings.VERSION,
        settings.ENVIRONMENT,
    )
    if settings.OTEL_ENABLED:
        init_tracer(service_name=settings.OTEL_SERVICE_NAME)
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(app)
            logger.info("FastAPI OpenTelemetry instrumentation active.")
        except Exception as otel_err:
            logger.warning(
                "Could not instrument FastAPI with OpenTelemetry: %s", otel_err
            )
    yield
    logger.info("Shutting down application and disposing database engine...")
    await engine.dispose()
    logger.info("Application shutdown complete.")


# Initialize FastAPI application instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    description=(
        "Production-grade, multi-tenant Remote Code Execution and Computer Lab Platform API. "
        "Provides secure sandboxing, real-time WebSocket streaming, and distributed task management."
    ),
)

# Configure Cross-Origin Resource Sharing (CORS)
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register Master API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Register WebSocket Streaming Router
app.include_router(ws_router, prefix="/ws/v1", tags=["WebSockets"])

# Register Metrics Scrape Endpoint
app.include_router(metrics_router, prefix="/metrics", tags=["Telemetry"])


@app.get("/", tags=["Root"])
async def root_index() -> JSONResponse:
    """Root endpoint providing platform status and API entrypoints."""
    return JSONResponse(
        content={
            "platform": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "online",
            "docs": "/docs",
            "health": f"{settings.API_V1_STR}/health",
        }
    )
