"""Isolated Subprocess Sandbox Implementation supporting Polyglot Execution."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import shutil
import signal
import sys
import tempfile
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

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


def _terminate_subprocess(process: asyncio.subprocess.Process) -> None:
    """Terminate child process and its entire process group on POSIX systems."""
    if sys.platform != "win32" and process.pid:
        with contextlib.suppress(Exception):
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    with contextlib.suppress(Exception):
        process.kill()


class ProcessSandbox(BaseSandbox):
    """Subprocess sandbox executing unprivileged code with watchdog timers and polyglot strategies."""

    def __init__(self) -> None:
        self.active_process: asyncio.subprocess.Process | None = None
        self.active_pty: Any = None

    @staticmethod
    def _adapt_compile_command_for_platform(cmd: list[str]) -> list[str]:
        if sys.platform != "win32":
            return cmd
        filtered = []
        skip_next = False
        for arg in cmd:
            if skip_next:
                skip_next = False
                continue
            if arg == "-std=c17":
                filtered.append("-std=c11")
            elif arg == "-std=c++20":
                filtered.append("-std=c++14")
            elif arg in ["-pie", "-fPIE", "-Wl,-z,relro,-z,now"]:
                continue
            elif arg == "-z":
                skip_next = True
                continue
            else:
                filtered.append(arg)

        if filtered and filtered[0] == "rustc" and not shutil.which("rustc"):
            cargo_rustc = Path.home() / ".cargo" / "bin" / "rustc.exe"
            if cargo_rustc.exists():
                filtered[0] = str(cargo_rustc)

        if filtered and filtered[0] == "go" and not shutil.which("go"):
            for candidate in [
                Path("C:/Program Files/Go/bin/go.exe"),
                Path("C:/Go/bin/go.exe"),
                Path.home() / "go" / "bin" / "go.exe",
            ]:
                if candidate.exists():
                    filtered[0] = str(candidate)
                    break

        return filtered

    def write_stdin(self, data: str | bytes) -> None:
        """Inject interactive user input into active process or PTY."""
        if self.active_pty:
            self.active_pty.write_input(data)
            return

        if self.active_process and self.active_process.stdin:
            data_str = (
                data.decode("utf-8", errors="replace")
                if isinstance(data, bytes)
                else data
            )
            # Normalize carriage returns for raw pipes (xterm sends \r, but console pipes expect \n)
            data_str = data_str.replace("\r\n", "\n").replace("\r", "\n")
            data_bytes = data_str.encode("utf-8")
            try:
                self.active_process.stdin.write(data_bytes)
                asyncio.create_task(self.active_process.stdin.drain())
            except Exception:
                pass

    def resize_terminal(self, cols: int, rows: int) -> bool:
        """Update terminal dimensions and dispatch SIGWINCH if supported."""
        if self.active_pty:
            return self.active_pty.set_window_size(cols, rows)
        return False

    def send_signal(self, sig: int) -> bool:
        """Deliver an operating system signal (e.g. SIGINT) to the active sandbox process."""
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
        """Execute request across compilation and runtime phases."""
        consumer = StreamConsumer(max_bytes=request.max_output_bytes)
        start_time = time.perf_counter()
        timed_out = False
        exit_code = None

        strategy = LanguageRegistry.get(request.language)
        temp_dir_obj = tempfile.TemporaryDirectory()

        try:
            temp_dir = Path(temp_dir_obj.name)
            source_file = temp_dir / f"solution{strategy.file_extension}"
            source_file.write_text(request.source_code, encoding="utf-8")

            # 1. Compilation Phase (if ahead-of-time compiled)
            if strategy.is_compiled:
                binary_file = temp_dir / (
                    "solution.exe" if sys.platform == "win32" else "solution"
                )
                compile_cmd = self._adapt_compile_command_for_platform(
                    strategy.get_compile_command(source_file, binary_file)
                )

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
                        err_text = c_stderr.decode(
                            "utf-8", errors="replace"
                        ) or c_stdout.decode("utf-8", errors="replace")
                        duration_ms = int((time.perf_counter() - start_time) * 1000)
                        return ExecutionResult(
                            status=ExecutionStatus.COMPILE_ERROR,
                            exit_code=comp_proc.returncode,
                            stdout="",
                            stderr=err_text,
                            compile_output=err_text,
                            execution_time_ms=duration_ms,
                            error_message="Compilation failed. See stderr for compiler diagnostics.",
                        )
                    target_exec = binary_file
                except FileNotFoundError as fnf:
                    return ExecutionResult(
                        status=ExecutionStatus.COMPILE_ERROR,
                        exit_code=127,
                        stdout="",
                        stderr=f"Compiler '{compile_cmd[0]}' not installed on host: {fnf}",
                        compile_output=f"Compiler '{compile_cmd[0]}' not found.",
                        execution_time_ms=0,
                        error_message=f"Compiler '{compile_cmd[0]}' is not available.",
                    )
                except TimeoutError:
                    return ExecutionResult(
                        status=ExecutionStatus.COMPILE_ERROR,
                        exit_code=-9,
                        stdout="",
                        stderr="Compilation exceeded 10.0s time limit (possible macro/template recursion bomb).",
                        compile_output="Compilation timed out.",
                        execution_time_ms=10000,
                        error_message="Compilation time limit exceeded.",
                    )
            else:
                target_exec = source_file

            # 2. Execution Phase
            cmd = strategy.get_execution_command(target_exec)

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
                with contextlib.suppress(Exception):
                    process.kill()
                    await process.wait()
                exit_code = -9

        except Exception as exc:
            return ExecutionResult(
                status=ExecutionStatus.SYSTEM_ERROR,
                stdout="",
                stderr=str(exc),
                execution_time_ms=0,
                error_message=f"Process execution failed: {str(exc)}",
            )
        finally:
            with contextlib.suppress(Exception):
                temp_dir_obj.cleanup()

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
        """Execute process and stream stdout/stderr chunks in real time."""
        consumer = StreamConsumer(max_bytes=request.max_output_bytes)
        start_time = time.perf_counter()
        timed_out = False

        strategy = LanguageRegistry.get(request.language)
        temp_dir_obj = tempfile.TemporaryDirectory()

        try:
            temp_dir = Path(temp_dir_obj.name)
            source_file = temp_dir / f"solution{strategy.file_extension}"
            source_file.write_text(request.source_code, encoding="utf-8")

            # 1. Compilation Phase
            if strategy.is_compiled:
                yield StreamChunk(
                    event=StreamEventType.STATUS,
                    data=f"Compiling {strategy.display_name} source code...",
                )
                binary_file = temp_dir / (
                    "solution.exe" if sys.platform == "win32" else "solution"
                )
                compile_cmd = self._adapt_compile_command_for_platform(
                    strategy.get_compile_command(source_file, binary_file)
                )

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
                        err_text = c_stderr.decode(
                            "utf-8", errors="replace"
                        ) or c_stdout.decode("utf-8", errors="replace")
                        yield StreamChunk(event=StreamEventType.ERROR, data=err_text)
                        duration_ms = int((time.perf_counter() - start_time) * 1000)
                        complete_payload = {
                            "status": ExecutionStatus.COMPILE_ERROR.value,
                            "exit_code": comp_proc.returncode,
                            "duration_ms": duration_ms,
                            "oom_killed": False,
                            "compile_output": err_text,
                        }
                        yield StreamChunk(
                            event=StreamEventType.COMPLETE,
                            data=json.dumps(complete_payload),
                        )
                        return
                except FileNotFoundError as fnf:
                    err_msg = (
                        f"Compiler '{compile_cmd[0]}' not installed on host: {fnf}\n"
                    )
                    yield StreamChunk(event=StreamEventType.ERROR, data=err_msg)
                    complete_payload = {
                        "status": ExecutionStatus.COMPILE_ERROR.value,
                        "exit_code": 127,
                        "duration_ms": 0,
                        "oom_killed": False,
                        "compile_output": err_msg,
                    }
                    yield StreamChunk(
                        event=StreamEventType.COMPLETE,
                        data=json.dumps(complete_payload),
                    )
                    return
                except TimeoutError:
                    err_msg = "[SYSTEM: Compilation timed out after 10.0s]\n"
                    yield StreamChunk(event=StreamEventType.ERROR, data=err_msg)
                    complete_payload = {
                        "status": ExecutionStatus.COMPILE_ERROR.value,
                        "exit_code": -9,
                        "duration_ms": 10000,
                        "oom_killed": False,
                        "compile_output": err_msg,
                    }
                    yield StreamChunk(
                        event=StreamEventType.COMPLETE,
                        data=json.dumps(complete_payload),
                    )
                    return

                target_exec = binary_file
                yield StreamChunk(
                    event=StreamEventType.STATUS,
                    data="Compilation successful. Initializing execution sandbox...",
                )
            else:
                target_exec = source_file
                yield StreamChunk(
                    event=StreamEventType.STATUS,
                    data=f"Initializing {strategy.display_name} execution runtime...",
                )

            # 2. Execution Phase
            cmd = strategy.get_execution_command(target_exec)

            spawn_kwargs: dict[str, Any] = {}
            if sys.platform != "win32":
                spawn_kwargs["start_new_session"] = True

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **spawn_kwargs,
            )
            self.active_process = process

            if request.stdin_data and process.stdin:
                process.stdin.write(request.stdin_data.encode("utf-8"))
                await process.stdin.drain()
                # User supplied batch input via the Stdin drawer / autograder.
                # Send EOF so readers reading until EOF don't hang.
                with contextlib.suppress(AttributeError, NotImplementedError, OSError):
                    process.stdin.write_eof()
                with contextlib.suppress(Exception):
                    process.stdin.close()

            chunk_queue: asyncio.Queue[StreamChunk | None] = asyncio.Queue()
            pumps_done = 0

            async def pump(stream, is_stderr: bool):
                nonlocal pumps_done
                try:
                    while True:
                        data = await stream.read(1024)
                        if not data:
                            break
                        text_chunk = data.decode("utf-8", errors="replace")
                        chunk_obj = (
                            consumer.consume_stderr(text_chunk)
                            if is_stderr
                            else consumer.consume_stdout(text_chunk)
                        )
                        if chunk_obj:
                            await chunk_queue.put(chunk_obj)
                        if consumer.limit_exceeded:
                            _terminate_subprocess(process)
                            break
                except Exception:
                    pass
                finally:
                    pumps_done += 1
                    if pumps_done >= 2:
                        await chunk_queue.put(None)

            pump_stdout = asyncio.create_task(pump(process.stdout, False))
            pump_stderr = asyncio.create_task(pump(process.stderr, True))

            # Stream chunks as they arrive from stdout/stderr concurrently
            while True:
                remaining = max(
                    0.01, request.timeout_seconds - (time.perf_counter() - start_time)
                )
                try:
                    item = await asyncio.wait_for(chunk_queue.get(), timeout=remaining)
                    if item is None:
                        break
                    yield item
                except TimeoutError:
                    timed_out = True
                    _terminate_subprocess(process)
                    with contextlib.suppress(Exception):
                        await process.wait()
                    yield StreamChunk(
                        event=StreamEventType.ERROR,
                        data=f"\n[SYSTEM: Execution exceeded wall-clock timeout of {request.timeout_seconds}s.]",
                    )
                    break

            with contextlib.suppress(Exception):
                await asyncio.wait_for(process.wait(), timeout=2.0)
            with contextlib.suppress(Exception):
                pump_stdout.cancel()
                pump_stderr.cancel()

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

            complete_payload = {
                "status": status.value,
                "exit_code": exit_code,
                "duration_ms": duration_ms,
                "oom_killed": False,
            }
            yield StreamChunk(
                event=StreamEventType.COMPLETE,
                data=json.dumps(complete_payload),
            )

        except Exception as exc:
            yield StreamChunk(
                event=StreamEventType.ERROR,
                data=f"\n[SYSTEM: Fatal execution failure: {str(exc)}]",
            )
            complete_payload = {
                "status": ExecutionStatus.SYSTEM_ERROR.value,
                "exit_code": None,
                "duration_ms": 0,
                "oom_killed": False,
            }
            yield StreamChunk(
                event=StreamEventType.COMPLETE,
                data=json.dumps(complete_payload),
            )
        finally:
            self.active_process = None
            with contextlib.suppress(Exception):
                temp_dir_obj.cleanup()
