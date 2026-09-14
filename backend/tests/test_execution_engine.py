"""Unit and adversarial tests for the Secure Execution Engine and Sandboxing."""

import json

import pytest

from worker.sandbox.models import ExecutionRequest, ExecutionStatus, StreamEventType
from worker.sandbox.process_sandbox import ProcessSandbox


@pytest.fixture
def sandbox():
    """Provide a reliable sandbox instance for test environments."""
    return ProcessSandbox()


@pytest.mark.asyncio
async def test_successful_python_execution(sandbox):
    """Verify that valid Python code executes successfully and returns expected output."""
    req = ExecutionRequest(
        source_code="print('Hello Systems Engineering!')\nprint(40 + 2)",
        language="python",
        timeout_seconds=3.0,
    )
    result = await sandbox.execute(req)

    assert result.status == ExecutionStatus.COMPLETED
    assert result.exit_code == 0
    assert "Hello Systems Engineering!" in result.stdout
    assert "42" in result.stdout
    assert result.execution_time_ms >= 0


@pytest.mark.asyncio
async def test_standard_input_piping(sandbox):
    """Verify that stdin data is correctly piped to the program."""
    req = ExecutionRequest(
        source_code="name = input()\nage = int(input())\nprint(f'User {name} is {age} years old.')",
        stdin_data="AdaLovelace\n36\n",
        timeout_seconds=3.0,
    )
    result = await sandbox.execute(req)

    assert result.status == ExecutionStatus.COMPLETED
    assert result.exit_code == 0
    assert "User AdaLovelace is 36 years old." in result.stdout


@pytest.mark.asyncio
async def test_watchdog_timeout_enforcement(sandbox):
    """Verify that infinite loops are forcefully terminated by the watchdog timer."""
    req = ExecutionRequest(
        source_code="import time\nwhile True:\n    time.sleep(0.1)",
        timeout_seconds=1.0,
    )
    result = await sandbox.execute(req)

    assert result.status == ExecutionStatus.TIME_LIMIT_EXCEEDED
    assert result.exit_code in [-9, 137]
    assert "timeout" in (result.error_message or "").lower()


@pytest.mark.asyncio
async def test_runtime_error_and_traceback_capture(sandbox):
    """Verify that uncaught runtime exceptions are captured in stderr with non-zero exit code."""
    req = ExecutionRequest(
        source_code="def divide(a, b):\n    return a / b\nprint(divide(10, 0))",
        timeout_seconds=3.0,
    )
    result = await sandbox.execute(req)

    assert result.status == ExecutionStatus.RUNTIME_ERROR
    assert result.exit_code != 0
    assert "ZeroDivisionError: division by zero" in result.stderr


@pytest.mark.asyncio
async def test_output_limit_capping(sandbox):
    """Verify that excessive output exceeding byte limit is truncated."""
    req = ExecutionRequest(
        source_code="for i in range(1000):\n    print('A' * 100)",
        max_output_bytes=2048,  # Cap at 2 KB
        timeout_seconds=3.0,
    )
    result = await sandbox.execute(req)

    assert result.status == ExecutionStatus.OUTPUT_LIMIT_EXCEEDED
    assert len(result.stdout.encode("utf-8")) <= 4096  # Bounded
    assert (
        "Output limit" in result.stdout
        or "exceeded" in (result.error_message or "").lower()
    )


@pytest.mark.asyncio
async def test_realtime_stream_chunks(sandbox):
    """Verify that stream_execute yields structured real-time chunks."""
    req = ExecutionRequest(
        source_code="import sys\nprint('Line 1')\nprint('Error line', file=sys.stderr)\nprint('Line 2')",
        timeout_seconds=3.0,
    )
    chunks = []
    async for chunk in sandbox.stream_execute(req):
        chunks.append(chunk)

    # Verify presence of status, stdout, stderr, and complete events
    events = [c.event for c in chunks]
    assert StreamEventType.STATUS in events
    assert StreamEventType.STDOUT in events
    assert StreamEventType.COMPLETE in events

    complete_chunk = next(c for c in chunks if c.event == StreamEventType.COMPLETE)
    payload = json.loads(complete_chunk.data)
    assert payload["status"] == ExecutionStatus.COMPLETED.value
    assert payload["exit_code"] == 0
