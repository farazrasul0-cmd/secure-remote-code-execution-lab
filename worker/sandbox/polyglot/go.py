"""Go Language Compilation and Execution Strategy."""

from __future__ import annotations

from pathlib import Path

from worker.sandbox.polyglot.base import BaseLanguageStrategy


class GoStrategy(BaseLanguageStrategy):
    """Compilation and execution strategy for Go (gc 1.22+)."""

    @property
    def language_id(self) -> str:
        return "go"

    @property
    def display_name(self) -> str:
        return "Go (1.22+)"

    @property
    def file_extension(self) -> str:
        return ".go"

    @property
    def is_compiled(self) -> bool:
        return True

    def get_compile_command(
        self, source_path: Path, output_binary_path: Path
    ) -> list[str]:
        # -ldflags "-s -w": Strip symbol table and debug info to minimize binary footprint
        return [
            "go",
            "build",
            "-ldflags",
            "-s -w",
            "-o",
            str(output_binary_path),
            str(source_path),
        ]

    def get_execution_command(self, target_path: Path) -> list[str]:
        return [str(target_path)]

    def get_default_boilerplate(self) -> str:
        return (
            "// Secure Remote Execution Laboratory\n"
            "// Language: Go 1.22+\n\n"
            "package main\n\n"
            'import "fmt"\n\n'
            "func main() {\n"
            '    fmt.Println("Hello from the concurrent Go sandbox!")\n'
            "}\n"
        )
