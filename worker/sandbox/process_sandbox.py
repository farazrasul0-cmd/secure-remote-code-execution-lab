"""Isolated Subprocess Sandbox Implementation supporting Polyglot Execution."""

from __future__ import annotations

import asyncio
import contextlib
import json
import sys
import tempfile
import time
from collections.abc import AsyncGenerator
from pathlib import Path

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


class ProcessSandbox(BaseSandbox):
    """Subprocess sandbox executing unprivileged code with watchdog timers and polyglot strategies."""

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
                    chunk_obj = (
                        consumer.consume_stderr(text_chunk)
                        if is_stderr
                        else consumer.consume_stdout(text_chunk)
                    )
                    if chunk_obj:
                        yield chunk_obj
                    if consumer.limit_exceeded:
                        with contextlib.suppress(Exception):
                            process.kill()
                        break

            # Read stdout
            async for chunk in read_stream(process.stdout, is_stderr=False):
                yield chunk

            # Wait for completion with timeout
            try:
                await asyncio.wait_for(process.wait(), timeout=request.timeout_seconds)
            except TimeoutError:
                timed_out = True
                with contextlib.suppress(Exception):
                    process.kill()
                    await process.wait()
                yield StreamChunk(
                    event=StreamEventType.ERROR,
                    data=f"\n[SYSTEM: Execution exceeded wall-clock timeout of {request.timeout_seconds}s.]",
                )

            # Read stderr
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
            with contextlib.suppress(Exception):
                temp_dir_obj.cleanup()
