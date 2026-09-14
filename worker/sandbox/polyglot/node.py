"""JavaScript / Node.js Language Execution Strategy."""

from __future__ import annotations

from pathlib import Path

from worker.sandbox.polyglot.base import BaseLanguageStrategy


class NodeStrategy(BaseLanguageStrategy):
    """Execution strategy for JavaScript (Node.js 20+)."""

    @property
    def language_id(self) -> str:
        return "javascript"

    @property
    def display_name(self) -> str:
        return "JavaScript (Node.js 20 LTS)"

    @property
    def file_extension(self) -> str:
        return ".js"

    @property
    def is_compiled(self) -> bool:
        return False

    def get_compile_command(
        self, source_path: Path, output_binary_path: Path
    ) -> list[str]:
        return []

    def get_execution_command(self, target_path: Path) -> list[str]:
        # --max-old-space-size=128: Cap V8 heap memory to 128MB matching cgroup limits
        # --no-warnings: Suppress process warning noise in student stdout
        return [
            "node",
            "--max-old-space-size=128",
            "--no-warnings",
            str(target_path),
        ]

    def get_default_boilerplate(self) -> str:
        return (
            "// Secure Remote Execution Laboratory\n"
            "// Language: JavaScript (Node.js 20)\n\n"
            "function main() {\n"
            '    console.log("Hello from the asynchronous Node.js sandbox!");\n'
            "}\n\n"
            "main();\n"
        )
