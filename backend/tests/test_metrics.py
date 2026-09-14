"""Prometheus metrics scrape and telemetry validation tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.metrics import SUBMISSIONS_TOTAL, get_metrics_response
from app.main import app


@pytest.mark.asyncio
async def test_metrics_endpoint_at_root():
    """Verify that root /metrics endpoint exposes Prometheus metrics with 200 OK."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        body = response.text
        assert "rce_submissions_total" in body
        assert "rce_execution_duration_seconds" in body
        assert "rce_memory_peak_bytes" in body


@pytest.mark.asyncio
async def test_metrics_endpoint_under_api_v1():
    """Verify that /api/v1/metrics endpoint is accessible for Prometheus scraping."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/metrics")
        assert response.status_code == 200
        assert "rce_submissions_total" in response.text


def test_metrics_generation_utility():
    """Verify get_metrics_response returns valid bytes and content-type."""
    SUBMISSIONS_TOTAL.labels(language="python", status="COMPLETED").inc()
    data, media_type = get_metrics_response()
    assert isinstance(data, bytes)
    assert len(data) > 0
    assert "rce_submissions_total" in data.decode("utf-8")
