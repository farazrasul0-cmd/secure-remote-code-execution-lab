"""API endpoints for Problems and Autograding evaluation."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin_user, get_current_user
from app.core.redis import get_redis_client
from app.db.session import get_db
from app.models.user import User
from app.schemas.problem import (
    GradingResultRead,
    GradingSubmissionCreate,
    ProblemCreate,
    ProblemDetailRead,
    ProblemRead,
)
from app.services import problem_service

router = APIRouter()


@router.get("", response_model=list[ProblemRead])
async def list_problems(
    difficulty: Annotated[
        str | None, Query(description="Filter by EASY, MEDIUM, HARD")
    ] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ProblemRead]:
    """List all available algorithmic problems with metadata and test case statistics."""
    # Ensure standard problems are seeded
    await problem_service.seed_default_problems_if_empty(db)
    return await problem_service.list_problems(
        db=db, difficulty=difficulty, skip=skip, limit=limit
    )


@router.get("/{identifier}", response_model=ProblemDetailRead)
async def get_problem(
    identifier: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProblemDetailRead:
    """Retrieve problem details by UUID or slug with sample test cases."""
    # Ensure standard problems are seeded
    await problem_service.seed_default_problems_if_empty(db)
    is_admin = current_user.role == "admin"
    problem = await problem_service.get_problem_by_id_or_slug(
        db=db, identifier=identifier, include_hidden=is_admin
    )
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem '{identifier}' not found",
        )
    return problem


@router.post("", response_model=ProblemDetailRead, status_code=status.HTTP_201_CREATED)
async def create_problem(
    problem_in: ProblemCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user),
) -> ProblemDetailRead:
    """Create a new problem with test cases (administrator privilege required)."""
    existing = await problem_service.get_problem_by_id_or_slug(
        db=db, identifier=problem_in.slug, include_hidden=True
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Problem with slug '{problem_in.slug}' already exists.",
        )

    prob = await problem_service.create_problem(db=db, prob_in=problem_in)
    result = await problem_service.get_problem_by_id_or_slug(
        db=db, identifier=str(prob.id), include_hidden=True
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve created problem",
        )
    return result


@router.post("/{identifier}/submit", response_model=GradingResultRead)
async def submit_for_grading(
    identifier: str,
    submission_in: GradingSubmissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    redis_client: Redis = Depends(get_redis_client),
) -> GradingResultRead:
    """Submit code solution to be evaluated against problem test suite."""
    await problem_service.seed_default_problems_if_empty(db)
    is_admin = current_user.role == "admin"
    try:
        _, scorecard = await problem_service.submit_and_grade_problem(
            db=db,
            user_id=current_user.id,
            problem_identifier=identifier,
            submission_in=submission_in,
            redis_client=redis_client,
            is_admin=is_admin,
        )
        return scorecard
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get("/submissions/{submission_id}/grading", response_model=GradingResultRead)
async def get_grading_result(
    submission_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GradingResultRead:
    """Retrieve autograding scorecard and test case verdicts for a submission."""
    scorecard = await problem_service.get_grading_scorecard(
        db=db,
        submission_id=submission_id,
        current_user=current_user,
    )
    if not scorecard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grading scorecard for submission '{submission_id}' not found.",
        )
    return scorecard
