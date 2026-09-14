"""Base Language Strategy Interface for Polyglot Code Execution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseLanguageStrategy(ABC):
    """Abstract strategy defining compilation and execution semantics for a language."""

    @property
    @abstractmethod
    def language_id(self) -> str:
        """Unique language identifier (e.g., 'python', 'cpp', 'rust')."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable display name (e.g., 'Python 3.12', 'C++20 (GCC 14)')."""

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Source file extension (e.g., '.py', '.cpp', '.rs')."""

    @property
    @abstractmethod
    def is_compiled(self) -> bool:
        """Whether the language requires an ahead-of-time compilation phase."""

    @property
    def monaco_language_id(self) -> str:
        """Monaco Editor syntax identifier (e.g. 'python', 'cpp', 'rust', 'go', 'javascript')."""
        return self.language_id

    @abstractmethod
    def get_compile_command(
        self, source_path: Path, output_binary_path: Path
    ) -> list[str]:
        """Return command list for compilation phase, or empty list if interpreted."""

    @abstractmethod
    def get_execution_command(self, target_path: Path) -> list[str]:
        """Return command list for execution phase."""

    @abstractmethod
    def get_default_boilerplate(self) -> str:
        """Return default starter code template for the web IDE."""

    def get_seccomp_profile_name(self) -> str:
        """Return appropriate Seccomp-BPF profile filename."""
        return "seccomp-profile.json"
