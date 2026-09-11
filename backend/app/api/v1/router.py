"""API v1 master router aggregating feature endpoint routers."""

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()

# Register health check endpoint
api_router.include_router(health.router, tags=["Health"])
