"""Submission ingestion, status tracking, and telemetry retrieval endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.logging import logger
from app.db.session import get_db
from app.models.user import User
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionListResponse,
    SubmissionResponse,
)
from app.services import submission_service

router = APIRouter()


async def get_redis_client():
    """Dependency for ephemeral Redis client."""
    client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


@router.post(
    "",
    response_model=SubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit code for sandboxed execution",
)
async def submit_code(
    sub_in: SubmissionCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis_client: Annotated[Redis, Depends(get_redis_client)],
) -> SubmissionResponse:
    """Ingest code submission, persist PENDING record, and enqueue to worker pool."""
    # Check supported language
    if sub_in.language.lower() != "python":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language runtime '{sub_in.language}'. Version 1.0 supports 'python' only.",
        )

    try:
        submission = await submission_service.create_submission(
            db=db,
            user_id=current_user.id,
            sub_in=sub_in,
            redis_client=redis_client,
        )
        logger.info(
            "Enqueued submission %s for user %s", submission.id, current_user.id
        )
        return submission
    except Exception as exc:
        logger.error("Failed to enqueue submission: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit execution job to broker.",
        ) from exc


@router.get(
    "",
    response_model=SubmissionListResponse,
    summary="List paginated historical submissions",
)
async def list_user_submissions(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> SubmissionListResponse:
    """Retrieve historical execution submissions for the current user."""
    items, total = await submission_service.list_submissions(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
    )
    return SubmissionListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{submission_id}",
    response_model=SubmissionResponse,
    summary="Get submission details and execution telemetry",
)
async def get_submission_details(
    submission_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SubmissionResponse:
    """Fetch single submission execution metrics and status."""
    submission = await submission_service.get_submission(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
    )
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Submission not found or access denied.",
        )
    return submission
