"""Pydantic schemas for Problems, TestCases, and Autograding verification."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TestCaseBase(BaseModel):
    """Base schema for test case."""

    input_data: str
    expected_output: str
    is_hidden: bool = False
    weight: int = 10
    order: int = 1
    explanation: str | None = None


class TestCaseCreate(TestCaseBase):
    """Schema for creating a new test case."""

    pass


class TestCaseRead(BaseModel):
    """Public test case schema with information hiding for hidden test vectors."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_hidden: bool
    weight: int
    order: int
    explanation: str | None = None
    input_data: str | None = None
    expected_output: str | None = None


class ProblemBase(BaseModel):
    """Base problem attributes."""

    title: str = Field(..., max_length=200)
    slug: str = Field(..., max_length=220)
    description: str
    difficulty: str = Field("EASY", pattern="^(EASY|MEDIUM|HARD)$")
    time_limit_ms: int = Field(2000, ge=100, le=15000)
    memory_limit_mb: int = Field(128, ge=16, le=1024)
    is_published: bool = True


class ProblemCreate(ProblemBase):
    """Schema for problem creation including initial test cases."""

    test_cases: list[TestCaseCreate] = Field(default_factory=list)


class ProblemRead(ProblemBase):
    """Summary schema for problem listings."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    test_case_count: int = 0
    sample_cases_count: int = 0


class ProblemDetailRead(ProblemBase):
    """Detailed problem schema with visible sample cases."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    sample_test_cases: list[TestCaseRead] = Field(default_factory=list)
    total_test_cases: int = 0
    total_points: int = 0


class GradingSubmissionCreate(BaseModel):
    """Payload to submit code for problem autograding."""

    language: str = Field("python", max_length=30)
    source_code: str = Field(..., min_length=1)


class TestCaseResultRead(BaseModel):
    """Individual test case evaluation result."""

    test_case_id: str
    order: int
    status: str
    passed: bool
    duration_ms: int = 0
    memory_bytes: int = 0
    is_hidden: bool = False
    weight: int = 10
    earned_points: int = 0
    input_data: str | None = None
    expected_output: str | None = None
    actual_output: str | None = None
    diff: str | None = None
    error_message: str | None = None


class GradingResultRead(BaseModel):
    """Grading scorecard and summary evaluation."""

    submission_id: str
    problem_id: str
    overall_status: str
    total_score: int
    max_score: int
    percentage: float
    passed_count: int
    total_test_cases: int
    execution_time_ms: int = 0
    peak_memory_bytes: int = 0
    compile_error: str | None = None
    test_case_results: list[TestCaseResultRead] = Field(default_factory=list)
