"""Unit and integration tests for API root and health endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Verify that root endpoint returns valid platform metadata."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "version" in data
    assert data["docs"] == "/docs"
    assert data["health"] == "/api/v1/health"


@pytest.mark.asyncio
async def test_health_check_endpoint(async_client: AsyncClient):
    """Verify that the health check endpoint returns valid service statuses."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "components" in data
    assert data["components"]["api"] == "healthy"
    assert "timestamp" in data
    assert "version" in data
