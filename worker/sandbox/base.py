"""Abstract Base Class for Sandbox Runtimes."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from worker.sandbox.models import ExecutionRequest, ExecutionResult, StreamChunk


class BaseSandbox(ABC):
    """Abstract interface defining the execution sandbox lifecycle contract."""

    @abstractmethod
    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute the untrusted code payload to completion and return full telemetry."""
        pass

    @abstractmethod
    async def stream_execute(
        self, request: ExecutionRequest
    ) -> AsyncGenerator[StreamChunk, None]:
        """Execute the untrusted code and yield real-time output chunks as generated."""
        pass
