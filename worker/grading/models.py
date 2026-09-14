"""Data models and enums for problem verification and autograding."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class EvaluationVerdict(StrEnum):
    """Evaluation verdict for test cases and overall submissions."""

    ACCEPTED = "ACCEPTED"
    PARTIAL = "PARTIAL"
    WRONG_ANSWER = "WRONG_ANSWER"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    COMPILE_ERROR = "COMPILE_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    PENDING = "PENDING"


class ComparisonMode(StrEnum):
    """Output comparison verification mode."""

    NORMALIZED = "NORMALIZED"
    STRICT = "STRICT"
    TOKEN = "TOKEN"
    EPSILON = "EPSILON"


class TestCaseData(BaseModel):
    """Data transfer representation of a test case oracle."""

    id: str
    input_data: str
    expected_output: str
    is_hidden: bool = False
    weight: int = 10
    order: int = 1
    explanation: str | None = None


class TestCaseVerdict(BaseModel):
    """Evaluation verdict for an individual test case."""

    test_case_id: str
    order: int
    status: EvaluationVerdict
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


class GradingSummary(BaseModel):
    """Complete autograding evaluation summary for a submission."""

    submission_id: str
    problem_id: str
    overall_status: EvaluationVerdict
    total_score: int
    max_score: int
    percentage: float
    passed_count: int
    total_test_cases: int
    execution_time_ms: int = 0
    peak_memory_bytes: int = 0
    compile_error: str | None = None
    test_case_results: list[TestCaseVerdict] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
