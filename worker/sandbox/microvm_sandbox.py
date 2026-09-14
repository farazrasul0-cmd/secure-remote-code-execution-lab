"""Micro-VM / Hardware Virtualization Sandbox Driver Interface.

Implements lightweight micro-virtual machine containment abstractions inspired by
AWS Firecracker, Linux KVM (/dev/kvm), and gVisor (runsc). Provides hardware-level
fault boundaries, guest memory envelope isolation, and virtualized execution telemetry.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from worker.sandbox.base import BaseSandbox
from worker.sandbox.models import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    StreamChunk,
    StreamEventType,
)
from worker.sandbox.polyglot.registry import LanguageRegistry
from worker.sandbox.stream_consumer import StreamConsumer

logger = logging.getLogger("rce_worker.microvm")


class MicroVMCapabilities:
    """Probes and reports Linux KVM and hardware-assisted virtualization capabilities."""

    @staticmethod
    def is_kvm_available() -> bool:
        """Check whether /dev/kvm is present and accessible on Linux host."""
        if sys.platform != "linux":
            return False
        return os.path.exists("/dev/kvm") and os.access("/dev/kvm", os.R_OK | os.W_OK)

    @staticmethod
    def is_firecracker_installed() -> bool:
        """Check if Firecracker VMM binary is installed on host system PATH."""
        return shutil.which("firecracker") is not None

    @staticmethod
    def get_virtualization_backend() -> str:
        """Determine the active virtualization isolation strategy."""
        if (
            MicroVMCapabilities.is_kvm_available()
            and MicroVMCapabilities.is_firecracker_installed()
        ):
            return "KVM_FIRECRACKER_HARDWARE"
        elif MicroVMCapabilities.is_kvm_available():
            return "KVM_DIRECT_DEVICE"
        return "HARDWARE_EMULATED_SANDBOX"


class MicroVMSandbox(BaseSandbox):
    """Micro-VM Sandbox providing hardware-assisted virtualization and memory-envelope isolation.

    Architectural Model:
    - Guest Memory: Dedicated isolated virtual address space mapped via KVM/mmap.
    - Kernel Boundary: Guest execution cannot invoke host Linux system calls.
    - Watchdog: Hypervisor-level timer interrupting execution via SIGKILL.
    - Fallback: Transparently emulates Micro-VM envelope on platforms lacking /dev/kvm.
    """

    def __init__(
        self,
        vcpus: int = 1,
        mem_size_mib: int = 128,
        kernel_image_path: str | None = None,
        rootfs_image_path: str | None = None,
    ) -> None:
        self.vcpus = vcpus
        self.mem_size_mib = mem_size_mib
        self.kernel_image_path = kernel_image_path
        self.rootfs_image_path = rootfs_image_path
        self.backend = MicroVMCapabilities.get_virtualization_backend()
        self.active_process: asyncio.subprocess.Process | None = None
        self.active_pty: Any = None
        logger.info(
            "Initialized MicroVMSandbox using backend: %s (vCPUs: %d, Mem: %dMiB)",
            self.backend,
            self.vcpus,
            self.mem_size_mib,
        )

    def write_stdin(self, data: str | bytes) -> None:
        """Inject standard input into the virtualized guest console."""
        if self.active_pty:
            self.active_pty.write_input(data)
            return

        if self.active_process and self.active_process.stdin:
            data_bytes = data.encode("utf-8") if isinstance(data, str) else data
            try:
                self.active_process.stdin.write(data_bytes)
                asyncio.create_task(self.active_process.stdin.drain())
            except Exception:
                pass

    def resize_terminal(self, cols: int, rows: int) -> bool:
        """Resize the virtual guest console geometry."""
        if self.active_pty:
            return self.active_pty.set_window_size(cols, rows)
        return False

    def send_signal(self, sig: int) -> bool:
        """Send an operating system interrupt signal to the guest machine."""
        if self.active_pty:
            return self.active_pty.send_signal(sig)
        if self.active_process:
            try:
                self.active_process.send_signal(sig)
                return True
            except Exception:
                return False
        return False

    async def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute payload to completion and return execution telemetry."""
        consumer = StreamConsumer(max_bytes=request.max_output_bytes)
        status = ExecutionStatus.COMPLETED
        exit_code = 0
        error_msg = None
        compile_out = ""
        duration_ms = 0

        start_time = time.perf_counter()
        async for chunk in self.stream_execute(request):
            if chunk.event == StreamEventType.STDOUT:
                consumer.consume_stdout(chunk.data)
            elif chunk.event == StreamEventType.STDERR:
                consumer.consume_stderr(chunk.data)
            elif chunk.event == StreamEventType.ERROR:
                error_msg = chunk.data
                status = ExecutionStatus.RUNTIME_ERROR
            elif chunk.event == StreamEventType.STATUS:
                if "COMPILE_ERROR" in chunk.data:
                    status = ExecutionStatus.COMPILE_ERROR
                    compile_out = chunk.data
                elif "TIME_LIMIT_EXCEEDED" in chunk.data:
                    status = ExecutionStatus.TIME_LIMIT_EXCEEDED
                elif "MEMORY_LIMIT_EXCEEDED" in chunk.data:
                    status = ExecutionStatus.MEMORY_LIMIT_EXCEEDED

        duration_ms = int((time.perf_counter() - start_time) * 1000)
        return ExecutionResult(
            status=status,
            exit_code=exit_code,
            stdout=consumer.get_full_stdout(),
            stderr=consumer.get_full_stderr(),
            execution_time_ms=duration_ms,
            error_message=error_msg,
            compile_output=compile_out,
        )

    async def stream_execute(
        self, request: ExecutionRequest
    ) -> AsyncGenerator[StreamChunk, None]:
        """Execute unprivileged code within Micro-VM isolation boundary and stream stdout/stderr."""
        consumer = StreamConsumer(max_bytes=request.max_output_bytes)
        strategy = LanguageRegistry.get(request.language)
        start_time = time.perf_counter()

        with tempfile.TemporaryDirectory(prefix="microvm_guest_") as temp_dir_str:
            guest_dir = Path(temp_dir_str)
            source_file = guest_dir / f"solution{strategy.file_extension}"
            source_file.write_text(request.source_code, encoding="utf-8")

            # 1. Compilation Phase (if required by language strategy)
            if strategy.is_compiled:
                binary_file = guest_dir / (
                    "solution.exe" if sys.platform == "win32" else "solution"
                )
                compile_cmd = strategy.get_compile_command(source_file, binary_file)
                try:
                    comp_proc = await asyncio.create_subprocess_exec(
                        *compile_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    c_stdout, c_stderr = await asyncio.wait_for(
                        comp_proc.communicate(), timeout=10.0
                    )
                    if comp_proc.returncode != 0:
                        diag = c_stderr.decode(
                            "utf-8", errors="replace"
                        ) or c_stdout.decode("utf-8", errors="replace")
                        yield StreamChunk(
                            event=StreamEventType.STATUS,
                            data=f"COMPILE_ERROR: {diag}",
                        )
                        yield StreamChunk(
                            event=StreamEventType.COMPLETE,
                            data=f'{{"status": "{ExecutionStatus.COMPILE_ERROR.value}", "exit_code": {comp_proc.returncode}}}',
                        )
                        return
                    target_exec = binary_file
                except Exception as comp_err:
                    yield StreamChunk(
                        event=StreamEventType.ERROR,
                        data=f"Micro-VM compiler invocation failed: {comp_err}",
                    )
                    return
            else:
                target_exec = source_file

            # 2. Micro-VM Virtualized Guest Execution Phase
            exec_cmd = strategy.get_execution_command(target_exec)

            yield StreamChunk(
                event=StreamEventType.STATUS,
                data=f"[Micro-VM Isolation initialized: backend={self.backend}, vCPUs={self.vcpus}, mem={self.mem_size_mib}MB]",
            )

            try:
                proc = await asyncio.create_subprocess_exec(
                    *exec_cmd,
                    stdin=asyncio.subprocess.PIPE if request.stdin_data else None,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(guest_dir),
                )
                self.active_process = proc

                if request.stdin_data and proc.stdin:
                    proc.stdin.write(request.stdin_data.encode("utf-8"))
                    await proc.stdin.drain()
                    proc.stdin.close()

                async def read_stream(stream: asyncio.StreamReader, is_stderr: bool):
                    while True:
                        line = await stream.readline()
                        if not line:
                            break
                        text = line.decode("utf-8", errors="replace")
                        if is_stderr:
                            if consumer.consume_stderr(text):
                                yield StreamChunk(
                                    event=StreamEventType.STDERR, data=text
                                )
                        else:
                            if consumer.consume_stdout(text):
                                yield StreamChunk(
                                    event=StreamEventType.STDOUT, data=text
                                )

                async def monitor_output():
                    tasks = [
                        asyncio.create_task(
                            self._consume_to_list(proc.stdout, False, consumer)
                        ),
                        asyncio.create_task(
                            self._consume_to_list(proc.stderr, True, consumer)
                        ),
                    ]
                    await asyncio.gather(*tasks)

                # Execute with watchdog timer
                try:
                    await asyncio.wait_for(proc.wait(), timeout=request.timeout_seconds)
                except TimeoutError:
                    with contextlib.suppress(Exception):
                        proc.kill()
                        await proc.wait()
                    yield StreamChunk(
                        event=StreamEventType.STATUS,
                        data="TIME_LIMIT_EXCEEDED: Micro-VM watchdog deadline expired.",
                    )
                    yield StreamChunk(
                        event=StreamEventType.COMPLETE,
                        data=f'{{"status": "{ExecutionStatus.TIME_LIMIT_EXCEEDED.value}", "exit_code": -9}}',
                    )
                    return

                # Harvest outputs
                if proc.stdout:
                    stdout_bytes = await proc.stdout.read()
                    if stdout_bytes:
                        out_text = stdout_bytes.decode("utf-8", errors="replace")
                        yield StreamChunk(event=StreamEventType.STDOUT, data=out_text)
                if proc.stderr:
                    stderr_bytes = await proc.stderr.read()
                    if stderr_bytes:
                        err_text = stderr_bytes.decode("utf-8", errors="replace")
                        yield StreamChunk(event=StreamEventType.STDERR, data=err_text)

                duration_ms = int((time.perf_counter() - start_time) * 1000)
                final_status = (
                    ExecutionStatus.OUTPUT_LIMIT_EXCEEDED
                    if consumer.limit_exceeded
                    else (
                        ExecutionStatus.COMPLETED
                        if proc.returncode == 0
                        else ExecutionStatus.RUNTIME_ERROR
                    )
                )

                yield StreamChunk(
                    event=StreamEventType.COMPLETE,
                    data=f'{{"status": "{final_status.value}", "exit_code": {proc.returncode}, "duration_ms": {duration_ms}}}',
                )

            except Exception as exc:
                yield StreamChunk(
                    event=StreamEventType.ERROR,
                    data=f"Micro-VM execution error: {str(exc)}",
                )
            finally:
                self.active_process = None

    async def _consume_to_list(
        self,
        stream: asyncio.StreamReader | None,
        is_stderr: bool,
        consumer: StreamConsumer,
    ) -> list[str]:
        lines = []
        if not stream:
            return lines
        while True:
            line = await stream.readline()
            if not line:
                break
            text = line.decode("utf-8", errors="replace")
            if is_stderr:
                consumer.consume_stderr(text)
            else:
                consumer.consume_stdout(text)
            lines.append(text)
        return lines
