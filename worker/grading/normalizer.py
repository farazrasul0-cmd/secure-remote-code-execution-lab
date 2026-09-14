"""Output normalization and diffing utilities for automated grading."""

from __future__ import annotations

import difflib


class OutputNormalizer:
    """Utilities to normalize program output and generate visual diffs."""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalize line endings to LF, strip trailing spaces per line, and strip trailing newlines."""
        if not text:
            return ""
        # Convert CRLF to LF
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Strip trailing whitespace on each line
        lines = [line.rstrip() for line in text.split("\n")]
        # Remove trailing empty lines
        while lines and lines[-1] == "":
            lines.pop()
        return "\n".join(lines)

    @staticmethod
    def tokenize(text: str) -> list[str]:
        """Split text into whitespace-delimited tokens."""
        return text.split()

    @staticmethod
    def generate_diff(expected: str, actual: str, max_lines: int = 20) -> str:
        """Generate a concise unified diff between expected and actual outputs."""
        norm_expected = OutputNormalizer.normalize_text(expected).splitlines(
            keepends=True
        )
        norm_actual = OutputNormalizer.normalize_text(actual).splitlines(keepends=True)

        diff = list(
            difflib.unified_diff(
                norm_expected,
                norm_actual,
                fromfile="expected_output",
                tofile="actual_output",
                lineterm="",
            )
        )

        if not diff:
            return ""

        if len(diff) > max_lines:
            truncated = diff[:max_lines]
            truncated.append(f"... ({len(diff) - max_lines} more diff lines truncated)")
            return "\n".join(truncated)

        return "\n".join(diff)
