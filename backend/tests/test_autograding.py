"""Tests for automated grading, oracle verification, and problem endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from worker.grading.harness import GradingHarness
from worker.grading.models import (
    ComparisonMode,
    EvaluationVerdict,
    TestCaseData,
)
from worker.grading.verifier import ResultVerifier


async def get_auth_headers(client: AsyncClient) -> dict[str, str]:
    """Helper to register and login a test user to acquire JWT authorization header."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "student_grader@test.edu",
            "username": "student_grader",
            "password": "SecurePassword123!",
            "role": "student",
        },
    )
    res = await client.post(
        "/api/v1/auth/login/json",
        json={
            "username_or_email": "student_grader",
            "password": "SecurePassword123!",
        },
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_result_verifier_normalized_mode():
    """Verify whitespace, CRLF, and trailing line normalization."""
    expected = "hello world\n42\n"
    actual = "hello world  \r\n42\r\n\r\n"
    is_match, diff, reason = ResultVerifier.verify(
        actual=actual, expected=expected, mode=ComparisonMode.NORMALIZED
    )
    assert is_match is True
    assert diff is None
    assert reason is None

    # Mismatched content
    bad_actual = "hello world\n43\n"
    is_match, diff, reason = ResultVerifier.verify(
        actual=bad_actual, expected=expected, mode=ComparisonMode.NORMALIZED
    )
    assert is_match is False
    assert diff is not None
    assert "Output mismatch" in reason


def test_result_verifier_strict_mode():
    """Verify strict byte-for-byte comparison."""
    expected = "hello\n"
    actual = "hello \n"
    is_match, _, _ = ResultVerifier.verify(
        actual=actual, expected=expected, mode=ComparisonMode.STRICT
    )
    assert is_match is False

    match_actual = "hello\n"
    is_match, _, _ = ResultVerifier.verify(
        actual=match_actual, expected=expected, mode=ComparisonMode.STRICT
    )
    assert is_match is True


def test_result_verifier_epsilon_mode():
    """Verify floating-point comparison with epsilon tolerance."""
    expected = "3.14159265 2.71828"
    actual_close = "3.14159266 2.71828001"
    is_match, _, _ = ResultVerifier.verify(
        actual=actual_close,
        expected=expected,
        mode=ComparisonMode.EPSILON,
        epsilon=1e-5,
    )
    assert is_match is True

    actual_divergent = "3.14159265 2.72"
    is_match, _, reason = ResultVerifier.verify(
        actual=actual_divergent,
        expected=expected,
        mode=ComparisonMode.EPSILON,
        epsilon=1e-5,
    )
    assert is_match is False
    assert "Floating point divergence" in reason


@pytest.mark.asyncio
async def test_grading_harness_evaluation_and_sanitization():
    """Verify multi-test evaluation and information hiding for hidden test cases."""
    code = """
import sys
input_data = sys.stdin.read().split()
if not input_data:
    sys.exit(0)
a = int(input_data[0])
b = int(input_data[1])
print(a + b)
"""
    test_cases = [
        TestCaseData(
            id="tc-1",
            input_data="3 5\n",
            expected_output="8",
            is_hidden=False,
            weight=30,
            order=1,
        ),
        TestCaseData(
            id="tc-2",
            input_data="10 20\n",
            expected_output="30",
            is_hidden=True,
            weight=70,
            order=2,
        ),
    ]

    summary = await GradingHarness.evaluate_submission(
        submission_id="sub-123",
        problem_id="prob-456",
        source_code=code,
        language="python",
        test_cases=test_cases,
        time_limit_ms=2000,
        memory_limit_mb=128,
        force_process=True,
    )

    assert summary.overall_status == EvaluationVerdict.ACCEPTED
    assert summary.total_score == 100
    assert summary.max_score == 100
    assert summary.passed_count == 2
    assert len(summary.test_case_results) == 2

    # Unsanitized summary retains hidden test case data
    assert summary.test_case_results[1].input_data == "10 20\n"

    # Sanitize for student: verifies information hiding
    sanitized = GradingHarness.sanitize_for_student(summary)
    assert sanitized.test_case_results[0].input_data == "3 5\n"
    assert sanitized.test_case_results[1].input_data == "[REDACTED: HIDDEN TEST CASE]"
    assert (
        sanitized.test_case_results[1].expected_output == "[REDACTED: HIDDEN TEST CASE]"
    )


@pytest.mark.asyncio
async def test_api_list_and_get_problems(async_client: AsyncClient):
    """Verify problem listing and detail endpoints with seeded data."""
    headers = await get_auth_headers(async_client)

    # List problems
    resp = await async_client.get("/api/v1/problems", headers=headers)
    assert resp.status_code == 200
    problems = resp.json()
    assert len(problems) >= 3

    slugs = [p["slug"] for p in problems]
    assert "two-sum" in slugs
    assert "valid-palindrome" in slugs
    assert "nth-fibonacci" in slugs

    # Get problem details
    detail_resp = await async_client.get("/api/v1/problems/two-sum", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["title"] == "Two Sum Problem"
    assert detail["total_test_cases"] == 4
    # Student only sees visible sample test cases (not hidden ones)
    assert len(detail["sample_test_cases"]) == 2
    for tc in detail["sample_test_cases"]:
        assert tc["is_hidden"] is False
        assert tc["input_data"] is not None


@pytest.mark.asyncio
async def test_api_submit_and_grade_problem(async_client: AsyncClient):
    """Verify submission and autograding evaluation endpoint."""
    headers = await get_auth_headers(async_client)

    two_sum_solution = """
import sys
content = sys.stdin.read().strip().split('\\n')
nums = list(map(int, content[0].split()))
target = int(content[1].strip())

seen = {}
for idx, num in enumerate(nums):
    complement = target - num
    if complement in seen:
        i1 = seen[complement]
        i2 = idx
        print(f"{min(i1, i2)} {max(i1, i2)}")
        break
    seen[num] = idx
"""
    payload = {
        "language": "python",
        "source_code": two_sum_solution,
    }

    resp = await async_client.post(
        "/api/v1/problems/two-sum/submit",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    scorecard = resp.json()

    assert scorecard["overall_status"] == "ACCEPTED"
    assert scorecard["total_score"] == 100
    assert scorecard["max_score"] == 100
    assert scorecard["passed_count"] == 4

    # Check information hiding on the scorecard
    results = scorecard["test_case_results"]
    assert len(results) == 4
    # Hidden test case (order 3 and 4) must be redacted
    hidden_tc = next(r for r in results if r["order"] == 3)
    assert hidden_tc["is_hidden"] is True
    assert hidden_tc["input_data"] == "[REDACTED: HIDDEN TEST CASE]"
    assert hidden_tc["expected_output"] == "[REDACTED: HIDDEN TEST CASE]"
