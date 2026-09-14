"""Problem and Autograding business logic service."""

from __future__ import annotations

import logging
import uuid

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.problem import Problem, TestCase
from app.models.submission import Submission
from app.models.user import User
from app.schemas.problem import (
    GradingResultRead,
    GradingSubmissionCreate,
    ProblemCreate,
    ProblemDetailRead,
    ProblemRead,
    TestCaseRead,
)
from worker.grading.harness import GradingHarness
from worker.grading.models import (
    ComparisonMode,
    GradingSummary,
    TestCaseData,
)

logger = logging.getLogger("rce.services.problem")


async def list_problems(
    db: AsyncSession,
    difficulty: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> list[ProblemRead]:
    """Retrieve list of active problems with test case counts."""
    query = (
        select(Problem)
        .options(selectinload(Problem.test_cases))
        .where(Problem.is_published.is_(True))
    )
    if difficulty:
        query = query.where(Problem.difficulty == difficulty.upper())

    query = query.order_by(Problem.created_at.asc()).offset(skip).limit(limit)
    result = await db.execute(query)
    problems = result.scalars().all()

    items: list[ProblemRead] = []
    for prob in problems:
        total_tc = len(prob.test_cases)
        sample_tc = sum(1 for tc in prob.test_cases if not tc.is_hidden)
        items.append(
            ProblemRead(
                id=prob.id,
                title=prob.title,
                slug=prob.slug,
                description=prob.description,
                difficulty=prob.difficulty,
                time_limit_ms=prob.time_limit_ms,
                memory_limit_mb=prob.memory_limit_mb,
                is_published=prob.is_published,
                created_at=prob.created_at,
                test_case_count=total_tc,
                sample_cases_count=sample_tc,
            )
        )
    return items


async def get_problem_by_id_or_slug(
    db: AsyncSession,
    identifier: str,
    include_hidden: bool = False,
) -> ProblemDetailRead | None:
    """Fetch problem details by UUID or unique slug, censoring hidden test cases if unprivileged."""
    query = select(Problem).options(selectinload(Problem.test_cases))
    try:
        val_uuid = uuid.UUID(identifier)
        query = query.where(Problem.id == val_uuid)
    except ValueError:
        query = query.where(Problem.slug == identifier)

    result = await db.execute(query)
    prob = result.scalar_one_or_none()
    if not prob:
        return None

    total_tc = len(prob.test_cases)
    total_points = sum(tc.weight for tc in prob.test_cases)

    # Filter and censor test cases
    sample_cases: list[TestCaseRead] = []
    for tc in prob.test_cases:
        if not tc.is_hidden or include_hidden:
            sample_cases.append(
                TestCaseRead(
                    id=tc.id,
                    is_hidden=tc.is_hidden,
                    weight=tc.weight,
                    order=tc.order,
                    explanation=tc.explanation,
                    input_data=tc.input_data,
                    expected_output=tc.expected_output,
                )
            )

    return ProblemDetailRead(
        id=prob.id,
        title=prob.title,
        slug=prob.slug,
        description=prob.description,
        difficulty=prob.difficulty,
        time_limit_ms=prob.time_limit_ms,
        memory_limit_mb=prob.memory_limit_mb,
        is_published=prob.is_published,
        created_at=prob.created_at,
        sample_test_cases=sample_cases,
        total_test_cases=total_tc,
        total_points=total_points,
    )


async def create_problem(
    db: AsyncSession,
    prob_in: ProblemCreate,
) -> Problem:
    """Create a new problem with initial test cases (admin only)."""
    prob = Problem(
        title=prob_in.title,
        slug=prob_in.slug,
        description=prob_in.description,
        difficulty=prob_in.difficulty,
        time_limit_ms=prob_in.time_limit_ms,
        memory_limit_mb=prob_in.memory_limit_mb,
        is_published=prob_in.is_published,
    )
    db.add(prob)
    await db.flush()

    for idx, tc_in in enumerate(prob_in.test_cases):
        tc = TestCase(
            problem_id=prob.id,
            input_data=tc_in.input_data,
            expected_output=tc_in.expected_output,
            is_hidden=tc_in.is_hidden,
            weight=tc_in.weight,
            order=tc_in.order or (idx + 1),
            explanation=tc_in.explanation,
        )
        db.add(tc)

    await db.commit()
    await db.refresh(prob)
    return prob


async def submit_and_grade_problem(
    db: AsyncSession,
    user_id: uuid.UUID,
    problem_identifier: str,
    submission_in: GradingSubmissionCreate,
    redis_client: Redis | None = None,
    is_admin: bool = False,
) -> tuple[Submission, GradingResultRead]:
    """Evaluate submission against problem test cases, update database, and return scorecard."""
    # Find problem
    query = select(Problem).options(selectinload(Problem.test_cases))
    try:
        val_uuid = uuid.UUID(problem_identifier)
        query = query.where(Problem.id == val_uuid)
    except ValueError:
        query = query.where(Problem.slug == problem_identifier)

    result = await db.execute(query)
    problem = result.scalar_one_or_none()
    if not problem:
        raise ValueError(f"Problem '{problem_identifier}' not found.")

    if not problem.test_cases:
        raise ValueError(f"Problem '{problem.title}' has no test cases configured.")

    # Create submission record
    submission = Submission(
        user_id=user_id,
        problem_id=problem.id,
        language=submission_in.language,
        source_code=submission_in.source_code,
        status="GRADING",
        telemetry={},
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # Convert test cases to worker format
    tc_data_list = [
        TestCaseData(
            id=str(tc.id),
            input_data=tc.input_data,
            expected_output=tc.expected_output,
            is_hidden=tc.is_hidden,
            weight=tc.weight,
            order=tc.order,
            explanation=tc.explanation,
        )
        for tc in sorted(problem.test_cases, key=lambda x: x.order)
    ]

    # Run grading harness (force_process=True allows testing and standalone operation without host docker socket)
    summary: GradingSummary = await GradingHarness.evaluate_submission(
        submission_id=str(submission.id),
        problem_id=str(problem.id),
        source_code=submission_in.source_code,
        language=submission_in.language,
        test_cases=tc_data_list,
        time_limit_ms=problem.time_limit_ms,
        memory_limit_mb=problem.memory_limit_mb,
        mode=ComparisonMode.NORMALIZED,
        force_process=True,
    )

    # Persist results in DB
    submission.score = summary.total_score
    submission.max_score = summary.max_score
    submission.grading_status = summary.overall_status.value
    submission.status = "COMPLETED"
    submission.execution_time_ms = summary.execution_time_ms
    submission.peak_memory_bytes = summary.peak_memory_bytes
    submission.telemetry = summary.model_dump()

    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # If not admin, sanitize hidden test cases to enforce Information Hiding
    if not is_admin:
        sanitized_summary = GradingHarness.sanitize_for_student(summary)
    else:
        sanitized_summary = summary

    grading_read = GradingResultRead.model_validate(sanitized_summary.model_dump())
    return submission, grading_read


async def get_grading_scorecard(
    db: AsyncSession,
    submission_id: uuid.UUID,
    current_user: User,
) -> GradingResultRead | None:
    """Retrieve autograding scorecard for a submission, ensuring tenant isolation and information hiding."""
    query = select(Submission).where(Submission.id == submission_id)
    if current_user.role != "admin":
        query = query.where(Submission.user_id == current_user.id)

    result = await db.execute(query)
    sub = result.scalar_one_or_none()
    if not sub or not sub.telemetry or "test_case_results" not in sub.telemetry:
        return None

    raw_summary = GradingSummary(**sub.telemetry)
    if current_user.role != "admin":
        raw_summary = GradingHarness.sanitize_for_student(raw_summary)

    return GradingResultRead.model_validate(raw_summary.model_dump())


async def seed_default_problems_if_empty(db: AsyncSession) -> None:
    """Seed introductory algorithmic problems if database has 0 problems."""
    count_query = select(func.count(Problem.id))
    result = await db.execute(count_query)
    count = result.scalar_one()
    if count > 0:
        return

    logger.info("Seeding default algorithmic problems and test cases...")

    # Problem 1: Two Sum
    two_sum = Problem(
        title="Two Sum Problem",
        slug="two-sum",
        description="""### Problem Statement
Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`.

### Input Format
- Line 1: Space-separated integers representing `nums`
- Line 2: An integer `target`

### Output Format
- Print the two 0-indexed indices separated by a space in ascending order.

### Example
**Input:**
```
2 7 11 15
9
```
**Output:**
```
0 1
```
""",
        difficulty="EASY",
        time_limit_ms=2000,
        memory_limit_mb=128,
        is_published=True,
    )
    db.add(two_sum)
    await db.flush()

    db.add_all(
        [
            TestCase(
                problem_id=two_sum.id,
                input_data="2 7 11 15\n9",
                expected_output="0 1",
                is_hidden=False,
                weight=25,
                order=1,
                explanation="nums[0] + nums[1] = 2 + 7 = 9",
            ),
            TestCase(
                problem_id=two_sum.id,
                input_data="3 2 4\n6",
                expected_output="1 2",
                is_hidden=False,
                weight=25,
                order=2,
                explanation="nums[1] + nums[2] = 2 + 4 = 6",
            ),
            TestCase(
                problem_id=two_sum.id,
                input_data="3 3\n6",
                expected_output="0 1",
                is_hidden=True,
                weight=25,
                order=3,
            ),
            TestCase(
                problem_id=two_sum.id,
                input_data="-1 -2 -3 -4 -5\n-8",
                expected_output="2 4",
                is_hidden=True,
                weight=25,
                order=4,
            ),
        ]
    )

    # Problem 2: Palindrome String
    palindrome = Problem(
        title="Valid Palindrome",
        slug="valid-palindrome",
        description="""### Problem Statement
Given a string `s`, determine if it is a palindrome, considering only alphanumeric characters and ignoring cases.

### Input Format
- Line 1: A string `s`

### Output Format
- Print `true` if `s` is a palindrome, or `false` otherwise.

### Example
**Input:**
```
racecar
```
**Output:**
```
true
```
""",
        difficulty="EASY",
        time_limit_ms=2000,
        memory_limit_mb=128,
        is_published=True,
    )
    db.add(palindrome)
    await db.flush()

    db.add_all(
        [
            TestCase(
                problem_id=palindrome.id,
                input_data="racecar",
                expected_output="true",
                is_hidden=False,
                weight=30,
                order=1,
            ),
            TestCase(
                problem_id=palindrome.id,
                input_data="hello",
                expected_output="false",
                is_hidden=False,
                weight=30,
                order=2,
            ),
            TestCase(
                problem_id=palindrome.id,
                input_data="A man a plan a canal Panama",
                expected_output="true",
                is_hidden=True,
                weight=40,
                order=3,
            ),
        ]
    )

    # Problem 3: Fibonacci Number
    fib = Problem(
        title="Nth Fibonacci Number",
        slug="nth-fibonacci",
        description=r"""### Problem Statement
Compute the `n`-th Fibonacci number $F(n)$ modulo $10^9 + 7$, where $F(0) = 0$ and $F(1) = 1$.

### Input Format
- Line 1: An integer `n` ($0 \le n \le 10^5$)

### Output Format
- Print the single integer $F(n) \pmod{10^9 + 7}$.
""",
        difficulty="MEDIUM",
        time_limit_ms=2000,
        memory_limit_mb=128,
        is_published=True,
    )
    db.add(fib)
    await db.flush()

    db.add_all(
        [
            TestCase(
                problem_id=fib.id,
                input_data="2",
                expected_output="1",
                is_hidden=False,
                weight=20,
                order=1,
            ),
            TestCase(
                problem_id=fib.id,
                input_data="10",
                expected_output="55",
                is_hidden=False,
                weight=30,
                order=2,
            ),
            TestCase(
                problem_id=fib.id,
                input_data="50",
                expected_output="586268941",
                is_hidden=True,
                weight=50,
                order=3,
            ),
        ]
    )

    await db.commit()
    logger.info("Default problems seeded successfully.")
