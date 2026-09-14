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

    def write_stdin(self, data: str | bytes) -> None:
        """Inject interactive user input into active process or PTY."""
        return None

    def resize_terminal(self, cols: int, rows: int) -> bool:
        """Update terminal dimensions and dispatch SIGWINCH if supported."""
        return False

    def send_signal(self, sig: int) -> bool:
        """Deliver an operating system signal (e.g. SIGINT) to the active sandbox process."""
        return False
