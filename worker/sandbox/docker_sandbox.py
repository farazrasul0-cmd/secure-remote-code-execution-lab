"""Production Docker OCI Container Sandbox Implementation."""

import asyncio
import contextlib
import json
import os
import queue
import threading
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
        self.active_container = None
        self.stdin_socket = None
        if seccomp_profile_path and os.path.exists(seccomp_profile_path):
            with open(seccomp_profile_path, encoding="utf-8") as f:
                self.seccomp_profile = json.load(f)

    def write_stdin(self, data: str | bytes) -> None:
        """Inject interactive user input into active container stdin socket."""
        if self.stdin_socket:
            try:
                data_str = data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data
                data_str = data_str.replace("\r\n", "\n").replace("\r", "\n")
                data_bytes = data_str.encode("utf-8")
                if hasattr(self.stdin_socket, "_sock"):
                    self.stdin_socket._sock.sendall(data_bytes)
                else:
                    self.stdin_socket.sendall(data_bytes)
            except Exception as e:
                import logging
                logging.getLogger("rce_worker.sandbox").error("Failed to write to stdin_socket: %s", e)
        else:
            import logging
            logging.getLogger("rce_worker.sandbox").warning("write_stdin called but stdin_socket is None!")

    def send_signal(self, sig: int) -> bool:
        """Deliver an operating system signal (e.g. SIGINT) to the active container process."""
        if self.active_container:
            try:
                self.active_container.kill(signal=sig)
                return True
            except Exception as e:
                import logging
                logging.getLogger("rce_worker.sandbox").error("Failed to kill container with signal %s: %s", sig, e)
                return False
        return False

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute request and accumulate stream into single result."""
        if request.language.lower() != "python":
            from worker.sandbox.process_sandbox import ProcessSandbox
            return await ProcessSandbox().execute(request)

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

        # For polyglot languages without custom docker container, delegate to ProcessSandbox
        if request.language.lower() != "python":
            from worker.sandbox.process_sandbox import ProcessSandbox
            fallback = ProcessSandbox()
            self.active_container = None
            async for chunk in fallback.stream_execute(request):
                yield chunk
            return

        # Prepare security and isolation options
        security_opt = ["no-new-privileges:true"]
        if self.seccomp_profile:
            security_opt.append(f"seccomp={json.dumps(self.seccomp_profile)}")

        yield StreamChunk(
            event=StreamEventType.STATUS,
            data="Initializing isolated sandbox container...",
        )

        try:
            # Create isolated container with stdin and tty enabled for interactive PTY sessions
            container = self.client.containers.create(
                image=f"lab-sandbox-{request.language}:3.11",
                command=["python3", "-u", "-B", "-c", request.source_code],
                stdin_open=True,
                tty=True,
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
            self.active_container = container

            # Attach full-duplex interactive stream socket (stdin, stdout, stderr)
            self.stdin_socket = container.attach_socket(
                params={"stdin": 1, "stdout": 1, "stderr": 1, "stream": 1}
            )

            # Start container with transient netns retry
            for attempt in range(3):
                try:
                    container.start()
                    break
                except DockerException as start_err:
                    if "netns" in str(start_err).lower() and attempt < 2:
                        await asyncio.sleep(0.2)
                        continue
                    raise

            # Pipe initial standard input if provided
            if request.stdin_data:
                # Ensure input has terminal line break and append \x04 (EOT / Ctrl+D) to signal EOF to PTY
                payload = request.stdin_data
                if not payload.endswith("\n"):
                    payload += "\n"
                payload += "\x04"
                self.write_stdin(payload)

            # Monitor execution with nonblocking thread+queue log reader and timeout watchdog
            log_queue: queue.Queue[bytes | None] = queue.Queue()
            stop_reader = threading.Event()
            raw_sock = self.stdin_socket._sock if hasattr(self.stdin_socket, "_sock") else self.stdin_socket

            def log_worker():
                try:
                    while not stop_reader.is_set():
                        chunk = raw_sock.recv(4096)
                        if not chunk:
                            break
                        log_queue.put(chunk)
                except Exception:
                    pass
                finally:
                    log_queue.put(None)

            reader_thread = threading.Thread(target=log_worker, daemon=True)
            reader_thread.start()

            # Poll queue and enforce timeout limit
            while True:
                elapsed = time.perf_counter() - start_time
                if elapsed >= request.timeout_seconds:
                    timed_out = True
                    with contextlib.suppress(Exception):
                        container.kill(signal="SIGKILL")
                    stop_reader.set()
                    break

                # Drain available chunks
                drained_any = False
                while not log_queue.empty():
                    item = log_queue.get_nowait()
                    if item is None:
                        break
                    drained_any = True
                    text_chunk = item.decode("utf-8", errors="replace")
                    chunk_obj = consumer.consume_stdout(text_chunk)
                    if chunk_obj:
                        yield chunk_obj
                    if consumer.limit_exceeded:
                        break

                if consumer.limit_exceeded:
                    with contextlib.suppress(Exception):
                        container.kill(signal="SIGKILL")
                    stop_reader.set()
                    break

                # Check if container has exited cleanly
                with contextlib.suppress(Exception):
                    container.reload()
                    if not container.attrs.get("State", {}).get("Running", True) and log_queue.empty():
                        break

                await asyncio.sleep(0.05)

            stop_reader.set()
            with contextlib.suppress(Exception):
                reader_thread.join(timeout=0.5)

            while not log_queue.empty():
                item = log_queue.get_nowait()
                if item:
                    text_chunk = item.decode("utf-8", errors="replace")
                    chunk_obj = consumer.consume_stdout(text_chunk)
                    if chunk_obj:
                        yield chunk_obj

            if timed_out:
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
            if self.stdin_socket:
                with contextlib.suppress(Exception):
                    self.stdin_socket.close()
                self.stdin_socket = None
            self.active_container = None
            if container:
                with contextlib.suppress(Exception):
                    container.remove(force=True, v=True)
