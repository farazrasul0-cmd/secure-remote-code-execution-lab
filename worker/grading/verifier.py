"""Output verifier and oracle comparator."""

from __future__ import annotations

import math

from worker.grading.models import ComparisonMode
from worker.grading.normalizer import OutputNormalizer


class ResultVerifier:
    """Verifies student program output against expected oracle output."""

    @classmethod
    def verify(
        cls,
        actual: str,
        expected: str,
        mode: ComparisonMode = ComparisonMode.NORMALIZED,
        epsilon: float = 1e-6,
    ) -> tuple[bool, str | None, str | None]:
        """Compare actual output with expected oracle output.

        Returns:
            Tuple of (is_correct, diff_string, failure_reason)
        """
        if mode == ComparisonMode.STRICT:
            if actual == expected:
                return True, None, None
            diff = OutputNormalizer.generate_diff(expected, actual)
            return False, diff, "Strict byte-for-byte mismatch"

        if mode == ComparisonMode.NORMALIZED:
            norm_actual = OutputNormalizer.normalize_text(actual)
            norm_expected = OutputNormalizer.normalize_text(expected)
            if norm_actual == norm_expected:
                return True, None, None
            diff = OutputNormalizer.generate_diff(norm_expected, norm_actual)
            return False, diff, "Output mismatch after whitespace normalization"

        if mode == ComparisonMode.TOKEN:
            tokens_actual = OutputNormalizer.tokenize(actual)
            tokens_expected = OutputNormalizer.tokenize(expected)
            if tokens_actual == tokens_expected:
                return True, None, None
            diff = OutputNormalizer.generate_diff(
                " ".join(tokens_expected), " ".join(tokens_actual)
            )
            reason = (
                f"Token count mismatch ({len(tokens_actual)} vs {len(tokens_expected)})"
                if len(tokens_actual) != len(tokens_expected)
                else "Token value mismatch"
            )
            return False, diff, reason

        if mode == ComparisonMode.EPSILON:
            tokens_actual = OutputNormalizer.tokenize(actual)
            tokens_expected = OutputNormalizer.tokenize(expected)
            if len(tokens_actual) != len(tokens_expected):
                diff = OutputNormalizer.generate_diff(
                    " ".join(tokens_expected), " ".join(tokens_actual)
                )
                return (
                    False,
                    diff,
                    f"Token count mismatch ({len(tokens_actual)} vs {len(tokens_expected)})",
                )

            for idx, (tok_act, tok_exp) in enumerate(
                zip(tokens_actual, tokens_expected, strict=False)
            ):
                try:
                    val_act = float(tok_act)
                    val_exp = float(tok_exp)
                    # Check absolute or relative difference
                    diff_val = abs(val_act - val_exp)
                    if not (
                        diff_val <= epsilon
                        or (
                            diff_val / max(1.0, abs(val_exp)) <= epsilon
                            and not math.isnan(diff_val)
                        )
                    ):
                        return (
                            False,
                            OutputNormalizer.generate_diff(expected, actual),
                            f"Floating point divergence at token index {idx}: {val_act} vs {val_exp} (diff={diff_val:.2e} > eps={epsilon})",
                        )
                except ValueError:
                    if tok_act != tok_exp:
                        return (
                            False,
                            OutputNormalizer.generate_diff(expected, actual),
                            f"String mismatch at token index {idx}: '{tok_act}' vs '{tok_exp}'",
                        )

            return True, None, None

        # Fallback default
        norm_actual = OutputNormalizer.normalize_text(actual)
        norm_expected = OutputNormalizer.normalize_text(expected)
        is_ok = norm_actual == norm_expected
        diff = (
            OutputNormalizer.generate_diff(norm_expected, norm_actual)
            if not is_ok
            else None
        )
        return is_ok, diff, None if is_ok else "Output mismatch"
