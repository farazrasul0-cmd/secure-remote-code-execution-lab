"""Rust Language Compilation and Execution Strategy."""

from __future__ import annotations

from pathlib import Path

from worker.sandbox.polyglot.base import BaseLanguageStrategy


class RustStrategy(BaseLanguageStrategy):
    """Compilation and execution strategy for Rust (rustc)."""

    @property
    def language_id(self) -> str:
        return "rust"

    @property
    def display_name(self) -> str:
        return "Rust (rustc 1.79+)"

    @property
    def file_extension(self) -> str:
        return ".rs"

    @property
    def is_compiled(self) -> bool:
        return True

    def get_compile_command(
        self, source_path: Path, output_binary_path: Path
    ) -> list[str]:
        # -O: Optimization level
        # --crate-type bin: Build standalone executable binary
        # -C overflow-checks=on: Ensure integer overflow causes runtime panics
        return [
            "rustc",
            "-O",
            "--crate-type",
            "bin",
            "-C",
            "overflow-checks=on",
            str(source_path),
            "-o",
            str(output_binary_path),
        ]

    def get_execution_command(self, target_path: Path) -> list[str]:
        return [str(target_path)]

    def get_default_boilerplate(self) -> str:
        return (
            "// Secure Remote Execution Laboratory\n"
            "// Language: Rust 2021 Edition\n\n"
            "fn main() {\n"
            '    println!("Hello from the memory-safe Rust sandbox!");\n'
            "}\n"
        )
