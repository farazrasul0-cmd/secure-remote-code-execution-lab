"""API v1 master router aggregating authentication, submissions, and health endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    health,
    languages,
    metrics,
    problems,
    submissions,
)

api_router = APIRouter()

# Register core endpoint routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["Telemetry"])
api_router.include_router(languages.router, prefix="/languages", tags=["Languages"])
api_router.include_router(
    problems.router, prefix="/problems", tags=["Problems & Autograding"]
)
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(
    submissions.router, prefix="/submissions", tags=["Submissions"]
)
