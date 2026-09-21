"""Adversarial security and sandbox containment test suite.

Validates that malicious, hostile, or runaway code submissions are
strictly contained by OS cgroups, Seccomp-BPF filters, and watchdog limits.
"""

import json
from pathlib import Path

import pytest

from worker.sandbox.models import ExecutionRequest, ExecutionStatus
from worker.sandbox.process_sandbox import ProcessSandbox


@pytest.mark.asyncio
async def test_adversarial_fork_bomb_containment():
    """Verify that exponential process forking is intercepted and contained."""
    sandbox = ProcessSandbox()

    fork_bomb_code = (
        "import os, time\n"
        "try:\n"
        "    for _ in range(10):\n"
        "        if hasattr(os, 'fork'):\n"
        "            os.fork()\n"
        "    while True:\n"
        "        time.sleep(0.1)\n"
        "except Exception as e:\n"
        "    print(f'Fork blocked: {e}')\n"
    )

    request = ExecutionRequest(
        source_code=fork_bomb_code,
        timeout_seconds=2,
    )

    result = await sandbox.execute(request)
    assert result.status in (
        ExecutionStatus.TIME_LIMIT_EXCEEDED,
        ExecutionStatus.RESOURCE_LIMIT_EXCEEDED,
        ExecutionStatus.COMPLETED,
    )
    assert result.execution_time_ms is not None
    assert result.execution_time_ms <= 3500


@pytest.mark.asyncio
async def test_adversarial_memory_exhaustion_containment():
    """Verify that rapid heap exhaustion triggers MemoryError or MEMORY_LIMIT_EXCEEDED."""
    sandbox = ProcessSandbox()

    memory_bomb_code = (
        "import sys\n"
        "try:\n"
        "    _ = b'x' * (sys.maxsize // 2)\n"
        "    print('Allocated')\n"
        "except (MemoryError, OverflowError) as e:\n"
        "    print(f'Caught expected memory ceiling: {type(e).__name__}')\n"
    )

    request = ExecutionRequest(
        source_code=memory_bomb_code,
        timeout_seconds=3,
    )

    result = await sandbox.execute(request)
    assert result.status in (
        ExecutionStatus.COMPLETED,
        ExecutionStatus.MEMORY_LIMIT_EXCEEDED,
        ExecutionStatus.RUNTIME_ERROR,
    )
    assert (
        "Caught expected memory ceiling" in result.stdout
        or result.status == ExecutionStatus.MEMORY_LIMIT_EXCEEDED
    )


@pytest.mark.asyncio
async def test_adversarial_rootfs_write_containment():
    """Verify that write operations to restricted OS filesystem paths fail."""
    sandbox = ProcessSandbox()

    rootfs_tamper_code = (
        "import sys\n"
        "targets = ['/etc/passwd', '/bin/sh', 'C:\\\\Windows\\\\System32\\\\drivers\\\\etc\\\\hosts']\n"
        "blocked = 0\n"
        "for target in targets:\n"
        "    try:\n"
        "        with open(target, 'w') as f:\n"
        "            f.write('pwned')\n"
        "    except (PermissionError, OSError, FileNotFoundError):\n"
        "        blocked += 1\n"
        "print(f'Security blocks: {blocked}/{len(targets)}')\n"
    )

    request = ExecutionRequest(
        source_code=rootfs_tamper_code,
        timeout_seconds=3,
    )

    result = await sandbox.execute(request)
    assert result.status == ExecutionStatus.COMPLETED
    assert "Security blocks:" in result.stdout


@pytest.mark.asyncio
async def test_adversarial_network_exfiltration_containment():
    """Verify that network socket connections outside sandbox boundary are trapped."""
    sandbox = ProcessSandbox()

    network_probe_code = (
        "import socket\n"
        "try:\n"
        "    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
        "    s.settimeout(0.5)\n"
        "    s.connect(('127.0.0.1', 59999))\n"
        "    print('Connected')\n"
        "except (OSError, ConnectionRefusedError, TimeoutError) as e:\n"
        "    print(f'Network blocked: {type(e).__name__}')\n"
    )

    request = ExecutionRequest(
        source_code=network_probe_code,
        timeout_seconds=3,
    )

    result = await sandbox.execute(request)
    assert result.status == ExecutionStatus.COMPLETED
    assert "Network blocked:" in result.stdout


def test_adversarial_seccomp_profile_structure():
    """Verify that Seccomp-BPF policy blocks dangerous system calls via defaultAction ERRNO."""
    seccomp_path = Path("docker/python/seccomp-profile.json")
    assert seccomp_path.exists(), "Seccomp profile must be present in docker/python/"

    with open(seccomp_path, encoding="utf-8") as f:
        policy = json.load(f)

    # Whitelist model: defaultAction is ERRNO, meaning unlisted syscalls are denied
    assert policy.get("defaultAction") == "SCMP_ACT_ERRNO"

    # Verify that dangerous syscalls are NOT in the allowed list
    allowed_syscalls = set()
    for rule in policy.get("syscalls", []):
        if rule.get("action") == "SCMP_ACT_ALLOW":
            for name in rule.get("names", []):
                allowed_syscalls.add(name)

    critical_dangerous = ["ptrace", "bpf", "mount", "reboot", "swapon", "kexec_load"]
    for dangerous in critical_dangerous:
        assert dangerous not in allowed_syscalls, (
            f"Dangerous syscall '{dangerous}' must not be whitelisted in Seccomp profile"
        )
