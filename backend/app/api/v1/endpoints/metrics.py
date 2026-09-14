"""Prometheus metrics scrape endpoint."""

from fastapi import APIRouter, Response

from app.core.metrics import get_metrics_response

router = APIRouter()


@router.get("", summary="Scrape Prometheus Telemetry Metrics")
def scrape_metrics() -> Response:
    """Export platform metrics in OpenMetrics / Prometheus exposition text format."""
    metrics_data, media_type = get_metrics_response()
    return Response(content=metrics_data, media_type=media_type)
