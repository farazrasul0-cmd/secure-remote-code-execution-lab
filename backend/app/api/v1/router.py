"""API v1 master router aggregating authentication, submissions, and health endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, submissions

api_router = APIRouter()

# Register core endpoint routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(
    submissions.router, prefix="/submissions", tags=["Submissions"]
)
