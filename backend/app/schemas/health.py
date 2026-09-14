"""Schemas for system health monitoring."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """System health check response schema."""

    status: str = Field(
        ..., description="Overall system health status ('healthy' or 'degraded')"
    )
    version: str = Field(..., description="Application semantic version")
    environment: str = Field(
        ..., description="Execution environment (development, staging, production)"
    )
    components: dict[str, str] = Field(
        default_factory=dict,
        description="Individual service component status (e.g., database, redis)",
    )
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp of check")
