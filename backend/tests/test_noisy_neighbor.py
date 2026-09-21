"""Noisy-neighbor stress test validating multi-tenant isolation under concurrent load."""

import asyncio
import time

import pytest

from worker.sandbox.models import ExecutionRequest, ExecutionStatus
from worker.sandbox.process_sandbox import ProcessSandbox


@pytest.mark.asyncio
async def test_noisy_neighbor_concurrent_isolation():
    """Verify that a rogue runaway workload cannot starve adjacent concurrent executions."""
    sandbox_rogue = ProcessSandbox()
    sandbox_normal = ProcessSandbox()

    # Rogue tenant attempts 100% CPU hog in tight loop
    rogue_code = "import time\nwhile True:\n    _ = [x * x for x in range(1000)]\n"

    # Well-behaved tenant performs bounded computation
    normal_code = (
        "total = sum(i * i for i in range(10000))\nprint(f'Computed total: {total}')\n"
    )

    req_rogue = ExecutionRequest(source_code=rogue_code, timeout_seconds=2)
    req_normal = ExecutionRequest(source_code=normal_code, timeout_seconds=3)

    start_time = time.perf_counter()

    # Dispatch both simultaneously
    res_rogue, res_normal = await asyncio.gather(
        sandbox_rogue.execute(req_rogue),
        sandbox_normal.execute(req_normal),
    )

    total_duration = time.perf_counter() - start_time

    # Assert rogue tenant was terminated at timeout
    assert res_rogue.status == ExecutionStatus.TIME_LIMIT_EXCEEDED
    assert res_rogue.execution_time_ms is not None
    assert res_rogue.execution_time_ms >= 1900

    # Assert normal tenant completed cleanly without starvation
    assert res_normal.status == ExecutionStatus.COMPLETED
    assert "Computed total: 333283335000" in res_normal.stdout

    # Total duration should be dominated by the 2s timeout of the rogue task, not serialized (2s + 1s = 3s)
    assert total_duration < 6.0
