"""Submission request and response Pydantic validation schemas."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SubmissionCreate(BaseModel):
    """Payload for submitting code to the remote execution engine."""

    source_code: str = Field(
        ..., min_length=1, max_length=65536, description="Source code text (max 64KB)"
    )
    language: str = Field(default="python", description="Target programming language")
    stdin_data: str | None = Field(
        default=None, max_length=1048576, description="Optional standard input"
    )
    timeout_seconds: int | None = Field(
        default=None,
        ge=1,
        le=120,
        description="Optional custom execution timeout (seconds)",
    )


class SubmissionResponse(BaseModel):
    """Execution submission details and telemetry."""

    id: uuid.UUID
    user_id: uuid.UUID
    language: str
    source_code: str
    stdin_data: str | None = None
    status: str
    exit_code: int | None = None
    execution_time_ms: int | None = None
    peak_memory_bytes: int | None = None
    output_summary: str | None = None
    telemetry: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionListResponse(BaseModel):
    """Paginated list of user submissions."""

    items: list[SubmissionResponse]
    total: int
    page: int
    page_size: int
