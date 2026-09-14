"""Isolated Subprocess Sandbox Implementation for Local Testing and Fallback."""

import asyncio
import contextlib
import json
import sys
import time
from collections.abc import AsyncGenerator

from worker.sandbox.base import BaseSandbox
from worker.sandbox.models import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    StreamChunk,
    StreamEventType,
)
from worker.sandbox.stream_consumer import StreamConsumer


class ProcessSandbox(BaseSandbox):
    """Subprocess sandbox executing unprivileged code with watchdog timers."""

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute request and return complete execution telemetry."""
        consumer = StreamConsumer(max_bytes=request.max_output_bytes)
        start_time = time.perf_counter()
        timed_out = False
        exit_code = None

        # Execute isolated Python process
        cmd = [sys.executable, "-u", "-B", "-c", request.source_code]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE if request.stdin_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdin_bytes = (
                request.stdin_data.encode("utf-8") if request.stdin_data else None
            )

            try:
                stdout_data, stderr_data = await asyncio.wait_for(
                    process.communicate(input=stdin_bytes),
                    timeout=request.timeout_seconds,
                )
                exit_code = process.returncode
                if stdout_data:
                    consumer.consume_stdout(
                        stdout_data.decode("utf-8", errors="replace")
                    )
                if stderr_data:
                    consumer.consume_stderr(
                        stderr_data.decode("utf-8", errors="replace")
                    )

            except TimeoutError:
                timed_out = True
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
                exit_code = -9

        except Exception as exc:
            return ExecutionResult(
                status=ExecutionStatus.SYSTEM_ERROR,
                stdout="",
                stderr=str(exc),
                execution_time_ms=0,
                error_message=f"Process execution failed: {str(exc)}",
            )

        duration_ms = int((time.perf_counter() - start_time) * 1000)

        # Classify outcome status
        if timed_out:
            status = ExecutionStatus.TIME_LIMIT_EXCEEDED
            err_msg = (
                f"Execution exceeded wall-clock timeout of {request.timeout_seconds}s."
            )
        elif consumer.limit_exceeded:
            status = ExecutionStatus.OUTPUT_LIMIT_EXCEEDED
            err_msg = f"Output exceeded maximum byte limit of {request.max_output_bytes} bytes."
        elif exit_code == 0:
            status = ExecutionStatus.COMPLETED
            err_msg = None
        else:
            status = ExecutionStatus.RUNTIME_ERROR
            err_msg = f"Process terminated with non-zero exit code {exit_code}."

        return ExecutionResult(
            status=status,
            exit_code=exit_code,
            stdout=consumer.get_full_stdout(),
            stderr=consumer.get_full_stderr(),
            execution_time_ms=duration_ms,
            error_message=err_msg,
        )

    async def stream_execute(
        self, request: ExecutionRequest
    ) -> AsyncGenerator[StreamChunk, None]:
        """Execute subprocess and stream stdout/stderr chunks in real time."""
        consumer = StreamConsumer(max_bytes=request.max_output_bytes)
        start_time = time.perf_counter()
        timed_out = False

        yield StreamChunk(
            event=StreamEventType.STATUS,
            data="Initializing execution process...",
        )

        cmd = [sys.executable, "-u", "-B", "-c", request.source_code]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE if request.stdin_data else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            if request.stdin_data and process.stdin:
                process.stdin.write(request.stdin_data.encode("utf-8"))
                await process.stdin.drain()
                process.stdin.close()

            async def read_stream(stream, is_stderr: bool):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    text_chunk = line.decode("utf-8", errors="replace")
                    if is_stderr:
                        chunk_obj = consumer.consume_stderr(text_chunk)
                    else:
                        chunk_obj = consumer.consume_stdout(text_chunk)
                    if chunk_obj:
                        yield chunk_obj
                    if consumer.limit_exceeded:
                        with contextlib.suppress(Exception):
                            process.kill()
                        break

            # Read stdout
            async for chunk in read_stream(process.stdout, is_stderr=False):
                yield chunk

            # Wait for process completion with timeout
            try:
                await asyncio.wait_for(process.wait(), timeout=request.timeout_seconds)
            except TimeoutError:
                timed_out = True
                try:
                    process.kill()
                    await process.wait()
                except Exception:
                    pass
                yield StreamChunk(
                    event=StreamEventType.ERROR,
                    data=f"\n[SYSTEM: Execution exceeded wall-clock timeout of {request.timeout_seconds}s.]",
                )

            # Read remaining stderr
            async for chunk in read_stream(process.stderr, is_stderr=True):
                yield chunk

            exit_code = process.returncode if not timed_out else -9
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            if timed_out:
                status = ExecutionStatus.TIME_LIMIT_EXCEEDED
            elif consumer.limit_exceeded:
                status = ExecutionStatus.OUTPUT_LIMIT_EXCEEDED
            elif exit_code == 0:
                status = ExecutionStatus.COMPLETED
            else:
                status = ExecutionStatus.RUNTIME_ERROR

            yield StreamChunk(
                event=StreamEventType.COMPLETE,
                data=json.dumps(
                    {
                        "status": status.value,
                        "exit_code": exit_code,
                        "duration_ms": duration_ms,
                    }
                ),
            )

        except Exception as exc:
            yield StreamChunk(
                event=StreamEventType.ERROR,
                data=f"[SYSTEM ERROR: Process execution failed: {str(exc)}]",
            )
