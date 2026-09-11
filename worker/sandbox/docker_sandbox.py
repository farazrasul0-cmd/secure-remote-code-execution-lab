"""Production Docker OCI Container Sandbox Implementation."""

import asyncio
import contextlib
import json
import os
import time
from collections.abc import AsyncGenerator

from docker.errors import DockerException

import docker
from worker.sandbox.base import BaseSandbox
from worker.sandbox.models import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    StreamChunk,
    StreamEventType,
)
from worker.sandbox.stream_consumer import StreamConsumer


class DockerSandbox(BaseSandbox):
    """Hardened Docker sandbox enforcing Linux cgroups v2, namespaces, and seccomp."""

    def __init__(self, seccomp_profile_path: str | None = None):
        self.client = docker.from_env()
        self.seccomp_profile = None
        if seccomp_profile_path and os.path.exists(seccomp_profile_path):
            with open(seccomp_profile_path, encoding="utf-8") as f:
                self.seccomp_profile = json.load(f)

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute request and accumulate stream into single result."""
        consumer = StreamConsumer(max_bytes=request.max_output_bytes)
        final_result = None

        async for chunk in self.stream_execute(request):
            if chunk.event == StreamEventType.STDOUT:
                consumer.consume_stdout(chunk.data)
            elif chunk.event == StreamEventType.STDERR:
                consumer.consume_stderr(chunk.data)

        # Fallback if streaming ended
        return final_result or ExecutionResult(
            status=ExecutionStatus.COMPLETED
            if not consumer.limit_exceeded
            else ExecutionStatus.OUTPUT_LIMIT_EXCEEDED,
            stdout=consumer.get_full_stdout(),
            stderr=consumer.get_full_stderr(),
            execution_time_ms=0,
        )

    async def stream_execute(
        self, request: ExecutionRequest
    ) -> AsyncGenerator[StreamChunk, None]:
        """Execute container and stream standard output/error chunks in real time."""
        consumer = StreamConsumer(max_bytes=request.max_output_bytes)
        container = None
        start_time = time.perf_counter()
        timed_out = False

        # Prepare security and isolation options
        security_opt = ["no-new-privileges:true"]
        if self.seccomp_profile:
            security_opt.append(f"seccomp={json.dumps(self.seccomp_profile)}")

        yield StreamChunk(
            event=StreamEventType.STATUS,
            data="Initializing isolated sandbox container...",
        )

        try:
            # Create isolated container
            container = self.client.containers.create(
                image=f"lab-sandbox-{request.language}:3.11",
                command=["python3", "-u", "-B", "-c", request.source_code],
                stdin_open=bool(request.stdin_data),
                network_mode="none",
                read_only=True,
                tmpfs={"/tmp": "rw,noexec,nosuid,size=16m"},
                user="1001:1001",
                cap_drop=["ALL"],
                security_opt=security_opt,
                mem_limit=request.memory_limit,
                memswap_limit=request.memory_limit,
                cpu_period=100000,
                cpu_quota=request.cpu_quota,
                pids_limit=request.max_pids,
                labels={"sandbox_type": "isolated", "managed_by": "rce_worker"},
                environment={"PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1"},
            )

            # Start container
            container.start()

            # Pipe standard input if provided
            if request.stdin_data:
                socket = container.attach_socket(params={"stdin": 1, "stream": 1})
                socket._sock.sendall(request.stdin_data.encode("utf-8"))
                socket.close()

            # Monitor execution with timeout watchdog
            async def read_logs():
                for log_chunk in container.logs(
                    stdout=True, stderr=True, stream=True, follow=True
                ):
                    text_chunk = log_chunk.decode("utf-8", errors="replace")
                    chunk_obj = consumer.consume_stdout(text_chunk)
                    if chunk_obj:
                        yield chunk_obj
                    if consumer.limit_exceeded:
                        break

            try:
                async with asyncio.timeout(request.timeout_seconds):
                    # In asyncio, wrap the blocking logs generator
                    loop = asyncio.get_running_loop()
                    log_stream = await loop.run_in_executor(
                        None,
                        lambda: container.logs(
                            stdout=True, stderr=True, stream=True, follow=True
                        ),
                    )
                    for log_chunk in log_stream:
                        text_chunk = log_chunk.decode("utf-8", errors="replace")
                        chunk_obj = consumer.consume_stdout(text_chunk)
                        if chunk_obj:
                            yield chunk_obj
                        if consumer.limit_exceeded:
                            break
            except TimeoutError:
                timed_out = True
                with contextlib.suppress(Exception):
                    container.kill(signal="SIGKILL")
                yield StreamChunk(
                    event=StreamEventType.ERROR,
                    data=f"\n[SYSTEM: Execution exceeded wall-clock timeout of {request.timeout_seconds}s.]",
                )

            # Collect final container inspect state
            container.reload()
            state = container.attrs.get("State", {})
            exit_code = state.get("ExitCode", -1)
            oom_killed = state.get("OOMKilled", False)
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            # Determine final status
            if timed_out:
                status = ExecutionStatus.TIME_LIMIT_EXCEEDED
            elif oom_killed or exit_code == 137 and not timed_out:
                status = ExecutionStatus.MEMORY_LIMIT_EXCEEDED
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
                        "oom_killed": oom_killed,
                    }
                ),
            )

        except DockerException as dex:
            yield StreamChunk(
                event=StreamEventType.ERROR,
                data=f"[SYSTEM ERROR: Docker daemon failure: {str(dex)}]",
            )
        finally:
            if container:
                with contextlib.suppress(Exception):
                    container.remove(force=True, v=True)
