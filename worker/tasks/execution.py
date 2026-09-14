"""Celery Execution Tasks for Distributed Sandbox Execution and Streaming."""

import asyncio
import contextlib
import json
import logging
import signal
from typing import Any

from worker.broker.redis_client import redis_broker
from worker.celery_app import celery_app
from worker.grading.harness import GradingHarness
from worker.grading.models import ComparisonMode, TestCaseData
from worker.janitor.reaper import JanitorReaper
from worker.sandbox.factory import SandboxFactory
from worker.sandbox.models import (
    ExecutionRequest,
    ExecutionStatus,
    StreamChunk,
    StreamEventType,
)
from worker.streaming.multiplexer import StreamMultiplexer

logger = logging.getLogger("rce_worker.tasks")


async def _consume_upstream_inputs(
    sandbox: Any,
    redis_client: Any,
    input_channel: str,
) -> None:
    """Subscribe to upstream input channel and forward keystrokes/signals to active sandbox."""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(input_channel)
    try:
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.2)
            if msg and msg.get("type") == "message":
                raw_data = msg.get("data")
                if raw_data:
                    try:
                        frame = json.loads(raw_data)
                        frame_type = frame.get("type")
                        if frame_type == "stdin":
                            sandbox.write_stdin(frame.get("data", ""))
                        elif frame_type == "resize":
                            cols = int(frame.get("cols", 80))
                            rows = int(frame.get("rows", 24))
                            sandbox.resize_terminal(cols, rows)
                        elif frame_type == "signal":
                            sig_name = frame.get("signal", "SIGINT")
                            sig_val = getattr(signal, sig_name, signal.SIGINT)
                            sandbox.send_signal(sig_val)
                    except Exception as err:
                        logger.debug("Error processing upstream input frame: %s", err)
            await asyncio.sleep(0.01)
    except asyncio.CancelledError:
        pass
    finally:
        with contextlib.suppress(Exception):
            await pubsub.unsubscribe(input_channel)
            await pubsub.aclose()


async def _stream_and_collect(
    submission_id: str,
    request: ExecutionRequest,
    force_process: bool = False,
    trace_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Asynchronous core running sandbox, multiplexing streams to Redis, and gathering metrics."""
    sandbox = SandboxFactory.create_sandbox(force_process=force_process)
    multiplexer = StreamMultiplexer(submission_id)
    redis_client = redis_broker.get_async_client()

    input_channel = f"rce:input:{submission_id}"
    input_task = asyncio.create_task(
        _consume_upstream_inputs(sandbox, redis_client, input_channel)
    )

    stdout_parts = []
    stderr_parts = []
    final_payload = {
        "status": ExecutionStatus.SYSTEM_ERROR.value,
        "exit_code": None,
        "duration_ms": 0,
        "oom_killed": False,
    }

    try:
        from app.core.telemetry import TraceContextManager

        span_ctx = TraceContextManager.start_as_current_span(
            "rce.worker.sandbox_execution",
            carrier=trace_context,
            attributes={
                "rce.submission_id": submission_id,
                "rce.language": request.language,
                "rce.timeout_seconds": request.timeout_seconds,
            },
        )
    except Exception:
        span_ctx = contextlib.nullcontext()

    with span_ctx as span:
        try:
            async for chunk in sandbox.stream_execute(request):
                # 1. Publish to Redis Pub/Sub and buffer in Redis list
                await multiplexer.publish_chunk_async(redis_client, chunk)

                # 2. Accumulate logs for final return
                if chunk.event == StreamEventType.STDOUT:
                    stdout_parts.append(chunk.data)
                elif chunk.event == StreamEventType.STDERR:
                    stderr_parts.append(chunk.data)
                elif chunk.event == StreamEventType.COMPLETE:
                    with contextlib.suppress(Exception):
                        final_payload = json.loads(chunk.data)

            if span and hasattr(span, "set_attribute"):
                span.set_attribute(
                    "rce.status",
                    final_payload.get("status", ExecutionStatus.COMPLETED.value),
                )
                if final_payload.get("exit_code") is not None:
                    span.set_attribute("rce.exit_code", final_payload.get("exit_code"))

        except Exception as exc:
            logger.error(
                "Exception during execution of submission %s: %s",
                submission_id,
                exc,
            )
            err_chunk = StreamChunk(
                event=StreamEventType.ERROR,
                data=f"[SYSTEM ERROR: {str(exc)}]",
            )
            await multiplexer.publish_chunk_async(redis_client, err_chunk)
            final_payload["status"] = ExecutionStatus.SYSTEM_ERROR.value
            final_payload["error_message"] = str(exc)
            if span and hasattr(span, "record_exception"):
                span.record_exception(exc)

        finally:
            input_task.cancel()
            with contextlib.suppress(Exception):
                await input_task
            await redis_client.aclose()

    return {
        "submission_id": submission_id,
        "status": final_payload.get("status", ExecutionStatus.COMPLETED.value),
        "exit_code": final_payload.get("exit_code"),
        "duration_ms": final_payload.get("duration_ms", 0),
        "oom_killed": final_payload.get("oom_killed", False),
        "stdout": "".join(stdout_parts),
        "stderr": "".join(stderr_parts),
    }


@celery_app.task(bind=True, name="worker.tasks.execution.execute_code")
def execute_code(
    self,
    submission_id: str,
    source_code: str,
    language: str = "python",
    stdin_data: str | None = None,
    timeout_seconds: float = 5.0,
    memory_limit: str = "128m",
    cpu_quota: int = 50000,
    max_pids: int = 64,
    max_output_bytes: int = 1048576,
    force_process: bool = False,
    trace_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute code payload in isolated sandbox and stream output chunks via Redis Pub/Sub."""
    logger.info("Starting execution task for submission: %s", submission_id)

    request = ExecutionRequest(
        source_code=source_code,
        language=language,
        stdin_data=stdin_data,
        timeout_seconds=timeout_seconds,
        memory_limit=memory_limit,
        cpu_quota=cpu_quota,
        max_pids=max_pids,
        max_output_bytes=max_output_bytes,
    )

    # Execute async pipeline within synchronous Celery task
    result = asyncio.run(
        _stream_and_collect(
            submission_id,
            request,
            force_process=force_process,
            trace_context=trace_context,
        )
    )
    logger.info(
        "Completed execution task for submission: %s (Status: %s)",
        submission_id,
        result["status"],
    )
    return result


@celery_app.task(bind=True, name="worker.tasks.execution.grade_code")
def grade_code(
    self,
    submission_id: str,
    problem_id: str,
    source_code: str,
    language: str = "python",
    test_cases: list[dict] | None = None,
    time_limit_ms: int = 2000,
    memory_limit_mb: int = 128,
    mode: str = "NORMALIZED",
    force_process: bool = False,
) -> dict[str, Any]:
    """Execute code against problem test cases, compute score, and produce evaluation summary."""
    logger.info(
        "Starting grading task for submission: %s (Problem: %s)",
        submission_id,
        problem_id,
    )
    tc_objects = [TestCaseData(**tc) for tc in (test_cases or [])]
    comp_mode = (
        ComparisonMode(mode)
        if mode in ComparisonMode.__members__
        else ComparisonMode.NORMALIZED
    )

    summary = asyncio.run(
        GradingHarness.evaluate_submission(
            submission_id=submission_id,
            problem_id=problem_id,
            source_code=source_code,
            language=language,
            test_cases=tc_objects,
            time_limit_ms=time_limit_ms,
            memory_limit_mb=memory_limit_mb,
            mode=comp_mode,
            force_process=force_process,
        )
    )
    logger.info(
        "Grading complete for submission %s: Status=%s, Score=%d/%d (%0.1f%%)",
        submission_id,
        summary.overall_status.value,
        summary.total_score,
        summary.max_score,
        summary.percentage,
    )
    return summary.model_dump()


@celery_app.task(name="worker.tasks.execution.reap_orphan_containers")
def reap_orphan_containers() -> dict[str, Any]:
    """Periodic task executed by Celery Beat to purge orphaned sandbox containers."""
    reaper = JanitorReaper()
    reaped = reaper.reap_stale_containers()
    return {"reaped_count": len(reaped), "reaped_ids": reaped}
