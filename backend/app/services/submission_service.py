"""Submission persistence and queue dispatch business logic."""

import json
import uuid

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.submission import Submission
from app.models.user import User
from app.schemas.submission import SubmissionCreate


async def create_submission(
    db: AsyncSession,
    user_id: uuid.UUID,
    sub_in: SubmissionCreate,
    redis_client: Redis | None = None,
) -> Submission:
    """Persist new submission record and push job payload to Redis queue."""
    submission = Submission(
        user_id=user_id,
        language=sub_in.language,
        source_code=sub_in.source_code,
        stdin_data=sub_in.stdin_data,
        status="PENDING",
        telemetry={},
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # Dispatch to Redis task queue
    if redis_client:
        task_payload = {
            "submission_id": str(submission.id),
            "user_id": str(user_id),
            "source_code": submission.source_code,
            "language": submission.language,
            "stdin_data": submission.stdin_data,
            "timeout_seconds": settings.EXECUTION_TIMEOUT_SECONDS,
            "memory_limit": settings.SANDBOX_MEMORY_LIMIT,
            "cpu_quota": settings.SANDBOX_CPU_QUOTA,
            "max_pids": settings.SANDBOX_MAX_PIDS,
            "max_output_bytes": settings.SANDBOX_MAX_OUTPUT_BYTES,
        }
        await redis_client.lpush("rce:submissions", json.dumps(task_payload))

    return submission


async def get_submission(
    db: AsyncSession,
    submission_id: uuid.UUID,
    current_user: User,
) -> Submission | None:
    """Fetch single submission ensuring tenant ownership or admin access."""
    query = select(Submission).where(Submission.id == submission_id)
    if current_user.role != "admin":
        query = query.where(Submission.user_id == current_user.id)

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def list_submissions(
    db: AsyncSession,
    current_user: User,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Submission], int]:
    """Retrieve paginated submissions for the authenticated user or all if admin."""
    base_query = select(Submission)
    count_query = select(func.count(Submission.id))

    if current_user.role != "admin":
        base_query = base_query.where(Submission.user_id == current_user.id)
        count_query = count_query.where(Submission.user_id == current_user.id)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    items_query = (
        base_query.order_by(Submission.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items_result = await db.execute(items_query)
    items = list(items_result.scalars().all())

    return items, total
