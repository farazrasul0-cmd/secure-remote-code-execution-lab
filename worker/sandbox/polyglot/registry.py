"""Central Language Registry and Strategy Dispatcher."""

from __future__ import annotations

from typing import Any

from worker.sandbox.polyglot.base import BaseLanguageStrategy
from worker.sandbox.polyglot.c import CStrategy
from worker.sandbox.polyglot.cpp import CppStrategy
from worker.sandbox.polyglot.go import GoStrategy
from worker.sandbox.polyglot.node import NodeStrategy
from worker.sandbox.polyglot.python import PythonStrategy
from worker.sandbox.polyglot.rust import RustStrategy


class LanguageRegistry:
    """Registry maintaining active language compilation and execution strategies."""

    _strategies: dict[str, BaseLanguageStrategy] = {}
    _aliases: dict[str, str] = {
        "py": "python",
        "python3": "python",
        "c++": "cpp",
        "cplusplus": "cpp",
        "rs": "rust",
        "golang": "go",
        "js": "javascript",
        "node": "javascript",
        "nodejs": "javascript",
    }

    @classmethod
    def initialize(cls) -> None:
        """Register all supported language strategies."""
        cls.register(PythonStrategy())
        cls.register(CStrategy())
        cls.register(CppStrategy())
        cls.register(RustStrategy())
        cls.register(GoStrategy())
        cls.register(NodeStrategy())

    @classmethod
    def register(cls, strategy: BaseLanguageStrategy) -> None:
        """Register a new language strategy instance."""
        cls._strategies[strategy.language_id.lower()] = strategy

    @classmethod
    def get(cls, language_id: str) -> BaseLanguageStrategy:
        """Retrieve strategy for given language, resolving aliases."""
        if not cls._strategies:
            cls.initialize()

        norm = language_id.strip().lower()
        resolved = cls._aliases.get(norm, norm)

        if resolved not in cls._strategies:
            supported = ", ".join(cls._strategies.keys())
            raise ValueError(
                f"Unsupported programming language '{language_id}'. "
                f"Supported runtimes: {supported}"
            )
        return cls._strategies[resolved]

    @classmethod
    def is_supported(cls, language_id: str) -> bool:
        """Check if language or alias is supported."""
        if not cls._strategies:
            cls.initialize()
        norm = language_id.strip().lower()
        resolved = cls._aliases.get(norm, norm)
        return resolved in cls._strategies

    @classmethod
    def list_supported(cls) -> list[dict[str, Any]]:
        """Return metadata list of all supported languages for API exposition."""
        if not cls._strategies:
            cls.initialize()
        return [
            {
                "id": s.language_id,
                "name": s.display_name,
                "extension": s.file_extension,
                "is_compiled": s.is_compiled,
                "monaco_id": s.monaco_language_id,
                "boilerplate": s.get_default_boilerplate(),
            }
            for s in cls._strategies.values()
        ]


# Automatically initialize registry on import
LanguageRegistry.initialize()
