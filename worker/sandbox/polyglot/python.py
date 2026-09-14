"""Python Language Execution Strategy."""

from __future__ import annotations

import sys
from pathlib import Path

from worker.sandbox.polyglot.base import BaseLanguageStrategy


class PythonStrategy(BaseLanguageStrategy):
    """Execution strategy for Python 3."""

    @property
    def language_id(self) -> str:
        return "python"

    @property
    def display_name(self) -> str:
        return "Python 3.12"

    @property
    def file_extension(self) -> str:
        return ".py"

    @property
    def is_compiled(self) -> bool:
        return False

    def get_compile_command(
        self, source_path: Path, output_binary_path: Path
    ) -> list[str]:
        return []

    def get_execution_command(self, target_path: Path) -> list[str]:
        return [sys.executable, "-u", "-B", str(target_path)]

    def get_default_boilerplate(self) -> str:
        return (
            "# Secure Remote Execution Laboratory\n"
            "# Language: Python 3.12\n\n"
            "def main():\n"
            "    print('Hello from the secure Python sandbox!')\n\n"
            "if __name__ == '__main__':\n"
            "    main()\n"
        )
