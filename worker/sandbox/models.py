"""Execution Engine Data Models and Status Enums."""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ExecutionStatus(StrEnum):
    """Execution outcome status classifications."""

    COMPLETED = "COMPLETED"
    COMPILE_ERROR = "COMPILE_ERROR"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    OUTPUT_LIMIT_EXCEEDED = "OUTPUT_LIMIT_EXCEEDED"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class SandboxDriverType(StrEnum):
    """Supported sandbox virtualization and containment driver types."""

    PROCESS = "process"
    DOCKER = "docker"
    MICROVM = "microvm"
    AUTO = "auto"


class StreamEventType(StrEnum):
    """Stream event types for real-time WebSocket communication."""

    STDOUT = "stdout"
    STDERR = "stderr"
    STATUS = "status"
    ERROR = "error"
    COMPLETE = "complete"


class StreamChunk(BaseModel):
    """Individual streamed output chunk frame."""

    event: StreamEventType = Field(..., description="Type of stream frame")
    data: str = Field(default="", description="Text chunk or status message")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 UTC timestamp",
    )


class ExecutionRequest(BaseModel):
    """Payload specifying untrusted code execution parameters."""

    source_code: str = Field(
        ..., description="Source code to execute", max_length=65536
    )
    language: str = Field(default="python", description="Programming language runtime")
    stdin_data: str | None = Field(
        default=None, description="Optional standard input data"
    )
    timeout_seconds: float = Field(
        default=5.0,
        ge=0.5,
        le=15.0,
        description="Wall-clock execution timeout in seconds",
    )
    memory_limit: str = Field(
        default="128m", description="cgroups memory ceiling (e.g., '128m')"
    )
    cpu_quota: int = Field(
        default=50000,
        description="CFS CPU bandwidth quota in microseconds per period (50000 = 0.5 CPU)",
    )
    max_pids: int = Field(
        default=64, description="cgroups max process/thread count ceiling"
    )
    max_output_bytes: int = Field(
        default=1048576, description="Maximum standard output byte ceiling (1MB)"
    )


class ExecutionResult(BaseModel):
    """Comprehensive telemetry and output of an execution session."""

    status: ExecutionStatus = Field(..., description="Execution outcome classification")
    exit_code: int | None = Field(default=None, description="Linux process exit code")
    stdout: str = Field(default="", description="Captured standard output")
    stderr: str = Field(default="", description="Captured standard error")
    execution_time_ms: int = Field(
        default=0, description="Execution duration in milliseconds"
    )
    peak_memory_bytes: int | None = Field(
        default=None, description="Peak memory consumed in bytes"
    )
    error_message: str | None = Field(
        default=None, description="Detailed explanation if terminated abnormally"
    )
    compile_output: str = Field(
        default="", description="Compiler diagnostic output if compilation occurred"
    )
