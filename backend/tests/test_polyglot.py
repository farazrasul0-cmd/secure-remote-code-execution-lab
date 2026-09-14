"""Unit and Integration Tests for Polyglot Language Execution Engine."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from worker.sandbox.models import ExecutionRequest, ExecutionStatus
from worker.sandbox.polyglot.c import CStrategy
from worker.sandbox.polyglot.cpp import CppStrategy
from worker.sandbox.polyglot.go import GoStrategy
from worker.sandbox.polyglot.node import NodeStrategy
from worker.sandbox.polyglot.python import PythonStrategy
from worker.sandbox.polyglot.registry import LanguageRegistry
from worker.sandbox.polyglot.rust import RustStrategy
from worker.sandbox.process_sandbox import ProcessSandbox


def test_language_registry_strategy_dispatch():
    """Verify strategy registry retrieval and alias resolution."""
    # Direct retrieval
    assert isinstance(LanguageRegistry.get("python"), PythonStrategy)
    assert isinstance(LanguageRegistry.get("c"), CStrategy)
    assert isinstance(LanguageRegistry.get("cpp"), CppStrategy)
    assert isinstance(LanguageRegistry.get("rust"), RustStrategy)
    assert isinstance(LanguageRegistry.get("go"), GoStrategy)
    assert isinstance(LanguageRegistry.get("javascript"), NodeStrategy)

    # Alias resolution
    assert LanguageRegistry.get("py").language_id == "python"
    assert LanguageRegistry.get("python3").language_id == "python"
    assert LanguageRegistry.get("c++").language_id == "cpp"
    assert LanguageRegistry.get("rs").language_id == "rust"
    assert LanguageRegistry.get("golang").language_id == "go"
    assert LanguageRegistry.get("js").language_id == "javascript"
    assert LanguageRegistry.get("node").language_id == "javascript"

    # Unsupported language rejection
    assert not LanguageRegistry.is_supported("brainfuck")
    with pytest.raises(ValueError, match="Unsupported programming language"):
        LanguageRegistry.get("ruby_on_rails")


def test_compiler_hardening_flags():
    """Verify that C and C++ strategies enforce defensive binary hardening flags."""
    c_strat = CStrategy()
    cpp_strat = CppStrategy()

    from pathlib import Path

    src = Path("test.c")
    out = Path("test.out")

    c_cmd = c_strat.get_compile_command(src, out)
    assert "-fstack-protector-strong" in c_cmd
    assert "-D_FORTIFY_SOURCE=2" in c_cmd
    assert "-fPIE" in c_cmd
    assert "-Wl,-z,relro,-z,now" in c_cmd
    assert "noexecstack" in c_cmd

    cpp_cmd = cpp_strat.get_compile_command(Path("test.cpp"), out)
    assert "-std=c++20" in cpp_cmd
    assert "-ftemplate-depth=128" in cpp_cmd
    assert "-fstack-protector-strong" in cpp_cmd


@pytest.mark.asyncio
async def test_python_execution_in_polyglot_sandbox():
    """Verify Python execution through the polyglot sandbox pipeline."""
    sandbox = ProcessSandbox()
    req = ExecutionRequest(
        source_code="print('Polyglot Python Test')",
        language="python",
        timeout_seconds=3,
    )
    result = await sandbox.execute(req)
    assert result.status == ExecutionStatus.COMPLETED
    assert "Polyglot Python Test" in result.stdout


@pytest.mark.asyncio
async def test_cpp_compilation_error_capture():
    """Verify that invalid C++ syntax produces COMPILE_ERROR with diagnostic text."""
    sandbox = ProcessSandbox()
    invalid_cpp = """
    #include <iostream>
    int main() {
        this_is_an_invalid_syntax_error_without_semicolon
        return 0;
    }
    """
    req = ExecutionRequest(
        source_code=invalid_cpp,
        language="cpp",
        timeout_seconds=5,
    )
    result = await sandbox.execute(req)
    # Either COMPILE_ERROR (if g++ is installed and failed) or compiler not found (which also reports COMPILE_ERROR)
    assert result.status == ExecutionStatus.COMPILE_ERROR
    assert len(result.stderr) > 0
    assert result.compile_output != ""


@pytest.mark.asyncio
async def test_api_languages_endpoint():
    """Verify that GET /api/v1/languages returns all supported runtimes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/api/v1/languages")
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 6
        lang_ids = [item["id"] for item in data]
        assert "python" in lang_ids
        assert "c" in lang_ids
        assert "cpp" in lang_ids
        assert "rust" in lang_ids
        assert "go" in lang_ids
        assert "javascript" in lang_ids

        # Check boilerplate template structure
        for lang in data:
            assert "boilerplate" in lang
            assert "extension" in lang
            assert "is_compiled" in lang
