"""Unit and integration tests for Task 9.1: Next-Gen Sandbox Drivers and Micro-VM Virtualization.

Tests verify:
1. SandboxDriverType enum coverage and string parsing.
2. SandboxFactory dynamic driver instantiation and capability fallback negotiation.
3. MicroVMSandbox execution lifecycle, output streaming, and timeout watchdog.
4. MicroVMCapabilities probe methods and virtualization backend detection.
5. SandboxBenchmarkHarness execution and comparative telemetry reporting.
"""

import signal
from unittest.mock import MagicMock

import pytest

from worker.sandbox.benchmark.harness import (
    DriverBenchmarkResult,
    SandboxBenchmarkHarness,
)
from worker.sandbox.factory import SandboxFactory
from worker.sandbox.microvm_sandbox import MicroVMCapabilities, MicroVMSandbox
from worker.sandbox.models import (
    ExecutionRequest,
    ExecutionStatus,
    SandboxDriverType,
    StreamEventType,
)
from worker.sandbox.process_sandbox import ProcessSandbox

# ============================================================================
# 1. Driver Type Enum & Factory Selection Tests
# ============================================================================


def test_sandbox_driver_type_enum():
    """Verify SandboxDriverType enum values and conversions."""
    assert SandboxDriverType.PROCESS == "process"
    assert SandboxDriverType.DOCKER == "docker"
    assert SandboxDriverType.MICROVM == "microvm"
    assert SandboxDriverType.AUTO == "auto"


def test_factory_explicit_process_driver():
    """Verify SandboxFactory instantiates ProcessSandbox when requested."""
    sandbox = SandboxFactory.create_sandbox(driver_type=SandboxDriverType.PROCESS)
    assert isinstance(sandbox, ProcessSandbox)

    # String parameter check
    sandbox_str = SandboxFactory.create_sandbox(driver_type="process")
    assert isinstance(sandbox_str, ProcessSandbox)


def test_factory_explicit_microvm_driver():
    """Verify SandboxFactory instantiates MicroVMSandbox when requested."""
    sandbox = SandboxFactory.create_sandbox(
        driver_type=SandboxDriverType.MICROVM, vcpus=2, mem_size_mib=256
    )
    assert isinstance(sandbox, MicroVMSandbox)
    assert sandbox.vcpus == 2
    assert sandbox.mem_size_mib == 256


def test_factory_docker_fallback_when_daemon_unavailable(monkeypatch):
    """Verify SandboxFactory falls back to ProcessSandbox if Docker daemon ping fails."""
    mock_docker = MagicMock()
    mock_docker.from_env.side_effect = Exception("Docker daemon connection refused")
    monkeypatch.setattr("worker.sandbox.factory.docker", mock_docker)

    sandbox = SandboxFactory.create_sandbox(driver_type=SandboxDriverType.DOCKER)
    assert isinstance(sandbox, ProcessSandbox)


def test_factory_auto_mode_kvm_selection(monkeypatch):
    """Verify AUTO mode selects MicroVMSandbox when KVM is present."""
    monkeypatch.setattr(
        "worker.sandbox.microvm_sandbox.MicroVMCapabilities.is_kvm_available",
        lambda: True,
    )
    sandbox = SandboxFactory.create_sandbox(driver_type=SandboxDriverType.AUTO)
    assert isinstance(sandbox, MicroVMSandbox)


def test_factory_auto_mode_process_fallback(monkeypatch):
    """Verify AUTO mode falls back to ProcessSandbox when KVM and Docker are unavailable."""
    monkeypatch.setattr(
        "worker.sandbox.microvm_sandbox.MicroVMCapabilities.is_kvm_available",
        lambda: False,
    )
    mock_docker = MagicMock()
    mock_docker.from_env.side_effect = Exception("No Docker")
    monkeypatch.setattr("worker.sandbox.factory.docker", mock_docker)

    sandbox = SandboxFactory.create_sandbox(driver_type=SandboxDriverType.AUTO)
    assert isinstance(sandbox, ProcessSandbox)


# ============================================================================
# 2. MicroVMCapabilities Probe Tests
# ============================================================================


def test_microvm_capabilities_probe_non_linux(monkeypatch):
    """Verify MicroVMCapabilities correctly detects lack of /dev/kvm on non-Linux OS."""
    monkeypatch.setattr("sys.platform", "win32")
    assert MicroVMCapabilities.is_kvm_available() is False
    assert (
        MicroVMCapabilities.get_virtualization_backend() == "HARDWARE_EMULATED_SANDBOX"
    )


def test_microvm_capabilities_probe_linux_kvm(monkeypatch):
    """Verify KVM capability detection when /dev/kvm is simulated on Linux."""
    monkeypatch.setattr("sys.platform", "linux")
    monkeypatch.setattr("os.path.exists", lambda p: p == "/dev/kvm")
    monkeypatch.setattr("os.access", lambda p, m: True)
    monkeypatch.setattr("shutil.which", lambda cmd: None)

    assert MicroVMCapabilities.is_kvm_available() is True
    assert MicroVMCapabilities.get_virtualization_backend() == "KVM_DIRECT_DEVICE"


# ============================================================================
# 3. MicroVMSandbox Execution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_microvm_sandbox_python_execution():
    """Verify MicroVMSandbox executes Python code and yields formatted stream chunks."""
    sandbox = MicroVMSandbox(vcpus=1, mem_size_mib=128)
    request = ExecutionRequest(
        source_code="print('HELLO_FROM_MICROVM')\n",
        language="python",
        timeout_seconds=5.0,
    )

    chunks = []
    async for chunk in sandbox.stream_execute(request):
        chunks.append(chunk)

    events = [c.event for c in chunks]
    assert StreamEventType.STATUS in events
    assert StreamEventType.STDOUT in events
    assert StreamEventType.COMPLETE in events

    stdout_text = "".join(c.data for c in chunks if c.event == StreamEventType.STDOUT)
    assert "HELLO_FROM_MICROVM" in stdout_text


@pytest.mark.asyncio
async def test_microvm_sandbox_execute_to_completion():
    """Verify MicroVMSandbox.execute() produces complete ExecutionResult telemetry."""
    sandbox = MicroVMSandbox(vcpus=1, mem_size_mib=128)
    request = ExecutionRequest(
        source_code="x = 10 * 10\nprint(f'RESULT={x}')\n",
        language="python",
        timeout_seconds=5.0,
    )

    result = await sandbox.execute(request)
    assert result.status == ExecutionStatus.COMPLETED
    assert "RESULT=100" in result.stdout
    assert result.execution_time_ms >= 0


@pytest.mark.asyncio
async def test_microvm_sandbox_timeout_watchdog():
    """Verify MicroVMSandbox watchdog terminates long-running code with TIME_LIMIT_EXCEEDED."""
    sandbox = MicroVMSandbox(vcpus=1, mem_size_mib=128)
    request = ExecutionRequest(
        source_code="import time\ntime.sleep(5)\n",
        language="python",
        timeout_seconds=0.5,
    )

    result = await sandbox.execute(request)
    assert result.status == ExecutionStatus.TIME_LIMIT_EXCEEDED


def test_microvm_sandbox_interactive_methods():
    """Verify MicroVMSandbox stdin, resize, and signal forwarding."""
    sandbox = MicroVMSandbox()

    # Without active process, calls should safely no-op
    sandbox.write_stdin("hello")
    assert sandbox.resize_terminal(80, 24) is False
    assert sandbox.send_signal(signal.SIGINT) is False

    # Attach mock PTY
    mock_pty = MagicMock()
    mock_pty.set_window_size.return_value = True
    mock_pty.send_signal.return_value = True
    sandbox.active_pty = mock_pty

    sandbox.write_stdin("input_cmd\n")
    mock_pty.write_input.assert_called_once_with("input_cmd\n")

    assert sandbox.resize_terminal(100, 30) is True
    mock_pty.set_window_size.assert_called_once_with(100, 30)

    assert sandbox.send_signal(signal.SIGINT) is True
    mock_pty.send_signal.assert_called_once_with(signal.SIGINT)


# ============================================================================
# 4. Benchmark Harness Tests
# ============================================================================


@pytest.mark.asyncio
async def test_benchmark_harness_single_driver():
    """Verify SandboxBenchmarkHarness accurately profiles a driver."""
    bench = await SandboxBenchmarkHarness.benchmark_driver(
        SandboxDriverType.PROCESS, iterations=1
    )
    assert isinstance(bench, DriverBenchmarkResult)
    assert bench.driver_type == "process"
    assert bench.startup_latency_ms >= 0
    assert bench.execution_duration_ms >= 0
    assert "BENCHMARK_OK" in bench.stdout


@pytest.mark.asyncio
async def test_benchmark_harness_comparative_suite():
    """Verify comparative suite generates structured comparative telemetry across drivers."""
    results = await SandboxBenchmarkHarness.run_comparative_suite()
    assert len(results) >= 2
    types = [r.get("driver_type") for r in results]
    assert "process" in types
    assert "microvm" in types
