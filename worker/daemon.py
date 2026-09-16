"""Standalone Asynchronous Worker Daemon using Direct Redis Queue Consumption."""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Ensure backend package is in python path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.submission import Submission
from worker.config import worker_settings
from worker.grading.harness import GradingHarness
from worker.grading.models import ComparisonMode, TestCaseData
from worker.sandbox.models import ExecutionRequest
from worker.tasks.execution import _stream_and_collect

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | worker.daemon - %(message)s",
)
logger = logging.getLogger("rce_worker.daemon")

# Initialize database engine for worker result persistence
db_engine = create_async_engine(
    worker_settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
)
WorkerSessionLocal = async_sessionmaker(
    bind=db_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def _persist_submission_result(
    submission_id: str,
    status: str,
    exit_code: int | None = None,
    duration_ms: int | None = None,
    output_summary: str | None = None,
    score: int | None = None,
    max_score: int | None = None,
    grading_status: str | None = None,
) -> None:
    """Update submission record in PostgreSQL database upon completion."""
    try:
        import uuid

        sub_uuid = uuid.UUID(submission_id)
        async with WorkerSessionLocal() as session:
            stmt = (
                update(Submission)
                .where(Submission.id == sub_uuid)
                .values(
                    status=status,
                    exit_code=exit_code,
                    execution_time_ms=duration_ms,
                    output_summary=output_summary,
                    score=score,
                    max_score=max_score,
                    grading_status=grading_status,
                )
            )
            await session.execute(stmt)
            await session.commit()
            logger.info("Persisted database status '%s' for submission %s", status, submission_id)
    except Exception as db_err:
        logger.error("Failed to persist submission %s to database: %s", submission_id, db_err)


class AsyncWorkerDaemon:
    """Consumes execution jobs directly from Redis queue and executes asynchronously."""

    def __init__(
        self,
        redis_url: str = worker_settings.REDIS_URL,
        queue_name: str = worker_settings.QUEUE_NAME,
    ):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self.running = False
        self._redis: Redis | None = None

    async def start(self) -> None:
        """Start the consumer loop."""
        self.running = True
        self._redis = Redis.from_url(self.redis_url, decode_responses=True)
        logger.info(
            "Async Worker Daemon started. Listening on queue '%s'...", self.queue_name
        )

        while self.running:
            try:
                # Blocking pop with 2-second timeout to allow graceful shutdown
                item = await self._redis.brpop(self.queue_name, timeout=2)
                if not item:
                    continue

                _, raw_payload = item
                task_data = json.loads(raw_payload)
                submission_id = task_data.get("submission_id")

                if not submission_id:
                    logger.error(
                        "Received invalid task payload without submission_id: %s",
                        raw_payload,
                    )
                    continue

                logger.info("Dequeued job for submission: %s", submission_id)

                if task_data.get("action") == "grade" or "test_cases" in task_data:
                    # Execute autograding job
                    raw_cases = task_data.get("test_cases", [])
                    tc_objects = [TestCaseData(**tc) for tc in raw_cases]
                    mode_str = task_data.get("mode", "NORMALIZED")
                    comp_mode = (
                        ComparisonMode(mode_str)
                        if mode_str in ComparisonMode.__members__
                        else ComparisonMode.NORMALIZED
                    )

                    summary = await GradingHarness.evaluate_submission(
                        submission_id=submission_id,
                        problem_id=task_data.get("problem_id", ""),
                        source_code=task_data.get("source_code", ""),
                        language=task_data.get("language", "python"),
                        test_cases=tc_objects,
                        time_limit_ms=int(task_data.get("time_limit_ms", 2000)),
                        memory_limit_mb=int(task_data.get("memory_limit_mb", 128)),
                        mode=comp_mode,
                    )

                    # Persist grading result to Redis for quick retrieval
                    await self._redis.set(
                        f"rce:grading:{submission_id}",
                        summary.model_dump_json(),
                        ex=86400,
                    )
                    await _persist_submission_result(
                        submission_id=submission_id,
                        status=summary.overall_status.value,
                        score=summary.total_score,
                        max_score=summary.max_score,
                        grading_status=summary.overall_status.value,
                    )
                    logger.info(
                        "Finished grading job for submission %s: Status=%s, Score=%d/%d",
                        submission_id,
                        summary.overall_status.value,
                        summary.total_score,
                        summary.max_score,
                    )
                else:
                    request = ExecutionRequest(
                        source_code=task_data.get("source_code", ""),
                        language=task_data.get("language", "python"),
                        stdin_data=task_data.get("stdin_data"),
                        timeout_seconds=float(task_data.get("timeout_seconds", 5.0)),
                        memory_limit=task_data.get("memory_limit", "128m"),
                        cpu_quota=int(task_data.get("cpu_quota", 50000)),
                        max_pids=int(task_data.get("max_pids", 64)),
                        max_output_bytes=int(
                            task_data.get("max_output_bytes", 1048576)
                        ),
                    )

                    # Execute sandbox and publish stream chunks
                    result = await _stream_and_collect(submission_id, request)
                    await _persist_submission_result(
                        submission_id=submission_id,
                        status=result.get("status", "COMPLETED"),
                        exit_code=result.get("exit_code"),
                        duration_ms=result.get("duration_ms"),
                        output_summary=result.get("stdout") or result.get("stderr"),
                    )
                    logger.info(
                        "Finished job for submission: %s (Status: %s)",
                        submission_id,
                        result["status"],
                    )

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error in worker daemon loop: %s", exc)
                await asyncio.sleep(1)

        if self._redis:
            await self._redis.aclose()
        logger.info("Async Worker Daemon terminated cleanly.")

    def stop(self) -> None:
        """Signal daemon to gracefully stop after finishing active job."""
        logger.info("Stopping worker daemon...")
        self.running = False


if __name__ == "__main__":
    daemon = AsyncWorkerDaemon()

    def handle_signal():
        daemon.stop()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(daemon.start())
    except KeyboardInterrupt:
        daemon.stop()
