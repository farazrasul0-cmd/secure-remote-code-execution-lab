"""Output Stream Consumer with Byte Capping and Rate Throttling."""

from worker.sandbox.models import StreamChunk, StreamEventType


class StreamConsumer:
    """Consumes raw output stream chunks, enforces size caps, and formats events."""

    def __init__(self, max_bytes: int = 1048576):
        self.max_bytes = max_bytes
        self.total_bytes = 0
        self.limit_exceeded = False
        self.stdout_buffer = []
        self.stderr_buffer = []

    def consume_stdout(self, chunk: str) -> StreamChunk | None:
        """Process standard output text chunk."""
        if self.limit_exceeded:
            return None

        chunk_bytes = len(chunk.encode("utf-8"))
        if self.total_bytes + chunk_bytes > self.max_bytes:
            allowed_bytes = max(0, self.max_bytes - self.total_bytes)
            truncated_chunk = chunk.encode("utf-8")[:allowed_bytes].decode(
                "utf-8", errors="ignore"
            )
            self.total_bytes += allowed_bytes
            self.limit_exceeded = True
            self.stdout_buffer.append(truncated_chunk)
            return StreamChunk(
                event=StreamEventType.STDOUT,
                data=f"{truncated_chunk}\n\n[SYSTEM: Output limit of {self.max_bytes} bytes exceeded. Stream terminated.]",
            )

        self.total_bytes += chunk_bytes
        self.stdout_buffer.append(chunk)
        return StreamChunk(event=StreamEventType.STDOUT, data=chunk)

    def consume_stderr(self, chunk: str) -> StreamChunk | None:
        """Process standard error text chunk."""
        if self.limit_exceeded:
            return None

        chunk_bytes = len(chunk.encode("utf-8"))
        if self.total_bytes + chunk_bytes > self.max_bytes:
            self.limit_exceeded = True
            return StreamChunk(
                event=StreamEventType.STDERR,
                data="\n[SYSTEM: Output limit exceeded. Standard error stream truncated.]",
            )

        self.total_bytes += chunk_bytes
        self.stderr_buffer.append(chunk)
        return StreamChunk(event=StreamEventType.STDERR, data=chunk)

    def get_full_stdout(self) -> str:
        """Return aggregated standard output text."""
        return "".join(self.stdout_buffer)

    def get_full_stderr(self) -> str:
        """Return aggregated standard error text."""
        return "".join(self.stderr_buffer)
