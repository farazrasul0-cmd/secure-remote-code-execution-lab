"""C++ Language Compilation and Execution Strategy."""

from __future__ import annotations

from pathlib import Path

from worker.sandbox.polyglot.base import BaseLanguageStrategy


class CppStrategy(BaseLanguageStrategy):
    """Hardened compilation and execution strategy for C++20 (G++)."""

    @property
    def language_id(self) -> str:
        return "cpp"

    @property
    def display_name(self) -> str:
        return "C++20 (G++ 14)"

    @property
    def file_extension(self) -> str:
        return ".cpp"

    @property
    def is_compiled(self) -> bool:
        return True

    def get_compile_command(
        self, source_path: Path, output_binary_path: Path
    ) -> list[str]:
        # Defensive Hardening Flags:
        # -std=c++20: Modern C++ specification
        # -O2: Optimization level 2
        # -Wall: Enable all compiler warnings
        # -fstack-protector-strong: Stack canaries
        # -D_FORTIFY_SOURCE=2: Memory bounds checking
        # -fPIE -pie: ASLR randomization
        # -Wl,-z,relro,-z,now: Full RELRO protection
        # -z noexecstack: DEP/NX bit protection
        # -ftemplate-depth=128: Cap template metaprogramming recursion depth to prevent compiler OOM bombs
        return [
            "g++",
            "-std=c++20",
            "-O2",
            "-Wall",
            "-fstack-protector-strong",
            "-D_FORTIFY_SOURCE=2",
            "-fPIE",
            "-pie",
            "-Wl,-z,relro,-z,now",
            "-z",
            "noexecstack",
            "-ftemplate-depth=128",
            str(source_path),
            "-o",
            str(output_binary_path),
        ]

    def get_execution_command(self, target_path: Path) -> list[str]:
        return [str(target_path)]

    def get_default_boilerplate(self) -> str:
        return (
            "// Secure Remote Execution Laboratory\n"
            "// Language: C++20 (G++ Hardened)\n\n"
            "#include <iostream>\n"
            "#include <vector>\n"
            "#include <string>\n\n"
            "int main() {\n"
            '    std::cout << "Hello from the hardened C++ sandbox!" << std::endl;\n'
            "    return 0;\n"
            "}\n"
        )
