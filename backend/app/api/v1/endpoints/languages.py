"""Supported Programming Languages and Runtimes Endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from worker.sandbox.polyglot.registry import LanguageRegistry

router = APIRouter()


@router.get("", response_model=list[dict[str, Any]])
async def list_supported_languages() -> list[dict[str, Any]]:
    """Return all active language runtimes, file extensions, and starter boilerplates."""
    return LanguageRegistry.list_supported()
