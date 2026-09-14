"""Autograding evaluation harness executing code against test case suites."""

from __future__ import annotations

import logging

from worker.grading.models import (
    ComparisonMode,
    EvaluationVerdict,
    GradingSummary,
    TestCaseData,
    TestCaseVerdict,
)
from worker.grading.verifier import ResultVerifier
from worker.sandbox.factory import SandboxFactory
from worker.sandbox.models import ExecutionRequest, ExecutionStatus

logger = logging.getLogger("rce_worker.grading")


class GradingHarness:
    """Orchestrates test case execution, score aggregation, and information hiding."""

    @classmethod
    async def evaluate_submission(
        cls,
        submission_id: str,
        problem_id: str,
        source_code: str,
        language: str,
        test_cases: list[TestCaseData],
        time_limit_ms: int = 2000,
        memory_limit_mb: int = 128,
        mode: ComparisonMode = ComparisonMode.NORMALIZED,
        force_process: bool = False,
    ) -> GradingSummary:
        """Run submission against all test cases and compute evaluation summary."""
        sandbox = SandboxFactory.create_sandbox(force_process=force_process)
        test_case_results: list[TestCaseVerdict] = []

        total_score = 0
        max_score = sum(tc.weight for tc in test_cases)
        passed_count = 0
        peak_memory = 0
        total_exec_time = 0
        compile_error_output: str | None = None

        timeout_sec = max(0.5, time_limit_ms / 1000.0)
        memory_limit_str = f"{memory_limit_mb}m"

        for idx, tc in enumerate(test_cases):
            request = ExecutionRequest(
                source_code=source_code,
                language=language,
                stdin_data=tc.input_data,
                timeout_seconds=timeout_sec,
                memory_limit=memory_limit_str,
            )

            try:
                exec_result = await sandbox.execute(request)
            except Exception as exc:
                logger.error("Sandbox failure on test case %s: %s", tc.id, exc)
                test_case_results.append(
                    TestCaseVerdict(
                        test_case_id=tc.id,
                        order=tc.order,
                        status=EvaluationVerdict.SYSTEM_ERROR,
                        passed=False,
                        is_hidden=tc.is_hidden,
                        weight=tc.weight,
                        earned_points=0,
                        input_data=tc.input_data,
                        expected_output=tc.expected_output,
                        error_message=f"System error: {exc}",
                    )
                )
                continue

            exec_time = exec_result.execution_time_ms or 0
            mem_bytes = exec_result.peak_memory_bytes or 0
            total_exec_time += exec_time
            if mem_bytes > peak_memory:
                peak_memory = mem_bytes

            # Check for Compilation Error
            if exec_result.status == ExecutionStatus.COMPILE_ERROR:
                compile_error_output = exec_result.compile_output or exec_result.stderr
                test_case_results.append(
                    TestCaseVerdict(
                        test_case_id=tc.id,
                        order=tc.order,
                        status=EvaluationVerdict.COMPILE_ERROR,
                        passed=False,
                        duration_ms=exec_time,
                        memory_bytes=mem_bytes,
                        is_hidden=tc.is_hidden,
                        weight=tc.weight,
                        earned_points=0,
                        input_data=tc.input_data,
                        expected_output=tc.expected_output,
                        error_message="Compilation failed",
                    )
                )
                # Short-circuit remaining test cases on compile error
                for remaining_tc in test_cases[idx + 1 :]:
                    test_case_results.append(
                        TestCaseVerdict(
                            test_case_id=remaining_tc.id,
                            order=remaining_tc.order,
                            status=EvaluationVerdict.COMPILE_ERROR,
                            passed=False,
                            is_hidden=remaining_tc.is_hidden,
                            weight=remaining_tc.weight,
                            earned_points=0,
                            input_data=remaining_tc.input_data,
                            expected_output=remaining_tc.expected_output,
                            error_message="Compilation failed",
                        )
                    )
                break

            # Check for Time Limit Exceeded
            if (
                exec_result.status == ExecutionStatus.TIME_LIMIT_EXCEEDED
                or exec_time > time_limit_ms
            ):
                test_case_results.append(
                    TestCaseVerdict(
                        test_case_id=tc.id,
                        order=tc.order,
                        status=EvaluationVerdict.TIME_LIMIT_EXCEEDED,
                        passed=False,
                        duration_ms=exec_time,
                        memory_bytes=mem_bytes,
                        is_hidden=tc.is_hidden,
                        weight=tc.weight,
                        earned_points=0,
                        input_data=tc.input_data,
                        expected_output=tc.expected_output,
                        actual_output=exec_result.stdout,
                        error_message=f"Time limit of {time_limit_ms}ms exceeded",
                    )
                )
                continue

            # Check for Memory Limit Exceeded / OOM
            if exec_result.status == ExecutionStatus.MEMORY_LIMIT_EXCEEDED or (
                mem_bytes > (memory_limit_mb * 1024 * 1024) > 0
            ):
                test_case_results.append(
                    TestCaseVerdict(
                        test_case_id=tc.id,
                        order=tc.order,
                        status=EvaluationVerdict.MEMORY_LIMIT_EXCEEDED,
                        passed=False,
                        duration_ms=exec_time,
                        memory_bytes=mem_bytes,
                        is_hidden=tc.is_hidden,
                        weight=tc.weight,
                        earned_points=0,
                        input_data=tc.input_data,
                        expected_output=tc.expected_output,
                        actual_output=exec_result.stdout,
                        error_message=f"Memory limit of {memory_limit_mb}MB exceeded",
                    )
                )
                continue

            # Check for Runtime Error
            if exec_result.status == ExecutionStatus.RUNTIME_ERROR or (
                exec_result.exit_code is not None and exec_result.exit_code != 0
            ):
                test_case_results.append(
                    TestCaseVerdict(
                        test_case_id=tc.id,
                        order=tc.order,
                        status=EvaluationVerdict.RUNTIME_ERROR,
                        passed=False,
                        duration_ms=exec_time,
                        memory_bytes=mem_bytes,
                        is_hidden=tc.is_hidden,
                        weight=tc.weight,
                        earned_points=0,
                        input_data=tc.input_data,
                        expected_output=tc.expected_output,
                        actual_output=exec_result.stdout,
                        error_message=exec_result.stderr
                        or f"Process exited with non-zero code {exec_result.exit_code}",
                    )
                )
                continue

            # Normal Output Verification
            is_match, diff, reason = ResultVerifier.verify(
                actual=exec_result.stdout,
                expected=tc.expected_output,
                mode=mode,
            )

            if is_match:
                passed_count += 1
                total_score += tc.weight
                test_case_results.append(
                    TestCaseVerdict(
                        test_case_id=tc.id,
                        order=tc.order,
                        status=EvaluationVerdict.ACCEPTED,
                        passed=True,
                        duration_ms=exec_time,
                        memory_bytes=mem_bytes,
                        is_hidden=tc.is_hidden,
                        weight=tc.weight,
                        earned_points=tc.weight,
                        input_data=tc.input_data,
                        expected_output=tc.expected_output,
                        actual_output=exec_result.stdout,
                    )
                )
            else:
                test_case_results.append(
                    TestCaseVerdict(
                        test_case_id=tc.id,
                        order=tc.order,
                        status=EvaluationVerdict.WRONG_ANSWER,
                        passed=False,
                        duration_ms=exec_time,
                        memory_bytes=mem_bytes,
                        is_hidden=tc.is_hidden,
                        weight=tc.weight,
                        earned_points=0,
                        input_data=tc.input_data,
                        expected_output=tc.expected_output,
                        actual_output=exec_result.stdout,
                        diff=diff,
                        error_message=reason or "Output mismatch",
                    )
                )

        # Compute Overall Status
        overall_status = cls._determine_overall_status(
            test_case_results, compile_error_output
        )
        percentage = (
            round((total_score / max_score) * 100.0, 1) if max_score > 0 else 0.0
        )

        return GradingSummary(
            submission_id=submission_id,
            problem_id=problem_id,
            overall_status=overall_status,
            total_score=total_score,
            max_score=max_score,
            percentage=percentage,
            passed_count=passed_count,
            total_test_cases=len(test_cases),
            execution_time_ms=total_exec_time,
            peak_memory_bytes=peak_memory,
            compile_error=compile_error_output,
            test_case_results=test_case_results,
        )

    @staticmethod
    def _determine_overall_status(
        results: list[TestCaseVerdict], compile_error: str | None
    ) -> EvaluationVerdict:
        """Determine aggregate verdict from individual test results."""
        if compile_error:
            return EvaluationVerdict.COMPILE_ERROR

        if not results:
            return EvaluationVerdict.ACCEPTED

        all_passed = all(r.passed for r in results)
        if all_passed:
            return EvaluationVerdict.ACCEPTED

        passed_any = any(r.passed for r in results)
        if passed_any:
            return EvaluationVerdict.PARTIAL

        # If none passed, take the verdict of the first failure
        for r in results:
            if not r.passed:
                return r.status

        return EvaluationVerdict.WRONG_ANSWER

    @classmethod
    def sanitize_for_student(cls, summary: GradingSummary) -> GradingSummary:
        """Strip sensitive input/output oracle data from hidden test cases for unprivileged users."""
        sanitized_results: list[TestCaseVerdict] = []
        for res in summary.test_case_results:
            if res.is_hidden:
                sanitized_results.append(
                    TestCaseVerdict(
                        test_case_id=res.test_case_id,
                        order=res.order,
                        status=res.status,
                        passed=res.passed,
                        duration_ms=res.duration_ms,
                        memory_bytes=res.memory_bytes,
                        is_hidden=True,
                        weight=res.weight,
                        earned_points=res.earned_points,
                        input_data="[REDACTED: HIDDEN TEST CASE]",
                        expected_output="[REDACTED: HIDDEN TEST CASE]",
                        actual_output=None,
                        diff=None,
                        error_message=None if res.passed else res.status.value,
                    )
                )
            else:
                sanitized_results.append(res)

        return summary.model_copy(update={"test_case_results": sanitized_results})
