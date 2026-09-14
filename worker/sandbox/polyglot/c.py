"""C Language Compilation and Execution Strategy."""

from __future__ import annotations

from pathlib import Path

from worker.sandbox.polyglot.base import BaseLanguageStrategy


class CStrategy(BaseLanguageStrategy):
    """Hardened compilation and execution strategy for C17 (GCC)."""

    @property
    def language_id(self) -> str:
        return "c"

    @property
    def display_name(self) -> str:
        return "C (GCC 14 / C17)"

    @property
    def file_extension(self) -> str:
        return ".c"

    @property
    def is_compiled(self) -> bool:
        return True

    def get_compile_command(
        self, source_path: Path, output_binary_path: Path
    ) -> list[str]:
        # Defensive Hardening Flags:
        # -O2: Optimization level 2
        # -Wall: Enable all standard compiler warnings
        # -fstack-protector-strong: Stack canaries against buffer overflows
        # -D_FORTIFY_SOURCE=2: Bounds checking on string/memory functions
        # -fPIE -pie: Position Independent Executable (ASLR)
        # -Wl,-z,relro,-z,now: Full RELRO (read-only GOT)
        # -z noexecstack: Non-executable stack (DEP/NX)
        return [
            "gcc",
            "-std=c17",
            "-O2",
            "-Wall",
            "-fstack-protector-strong",
            "-D_FORTIFY_SOURCE=2",
            "-fPIE",
            "-pie",
            "-Wl,-z,relro,-z,now",
            "-z",
            "noexecstack",
            str(source_path),
            "-o",
            str(output_binary_path),
        ]

    def get_execution_command(self, target_path: Path) -> list[str]:
        return [str(target_path)]

    def get_default_boilerplate(self) -> str:
        return (
            "// Secure Remote Execution Laboratory\n"
            "// Language: C17 (GCC Hardened)\n\n"
            "#include <stdio.h>\n\n"
            "int main(void) {\n"
            '    printf("Hello from the hardened C sandbox!\\n");\n'
            "    return 0;\n"
            "}\n"
        )
