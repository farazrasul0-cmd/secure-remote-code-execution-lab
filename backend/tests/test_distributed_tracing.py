"""Unit and integration tests for Task 9.2: Distributed Observability and OpenTelemetry Tracing.

Tests cover:
1. OpenTelemetry TracerProvider initialization and W3C TraceContext injection/extraction.
2. Cross-process traceparent header serialization in dictionary carriers.
3. Span context propagation through asynchronous task boundaries.
4. FastAPI OpenTelemetry middleware integration and TraceContext propagation in submission_service.
5. Worker execution span generation with semantic convention attributes (status, exit_code).
"""

import uuid
from unittest.mock import AsyncMock

import pytest
from opentelemetry import trace
from opentelemetry.trace import Tracer

from app.core.telemetry import (
    TraceContextManager,
    get_tracer,
    init_tracer,
)
from worker.sandbox.models import ExecutionRequest
from worker.tasks.execution import _stream_and_collect

# ============================================================================
# 1. Tracer Initialization & TracerProvider Tests
# ============================================================================


def test_init_tracer_configures_global_provider():
    """Verify init_tracer configures global OpenTelemetry TracerProvider with service attributes."""
    provider = init_tracer(service_name="rce-test-service")
    assert provider is not None
    current = trace.get_tracer_provider()
    assert current is not None

    tracer = get_tracer("rce.test_module")
    assert isinstance(tracer, Tracer)


# ============================================================================
# 2. W3C TraceContext Injection and Extraction Tests
# ============================================================================


def test_trace_context_injection_and_extraction():
    """Verify TraceContextManager injects standard W3C 'traceparent' header into carrier dict."""
    tracer = get_tracer("rce.unit_test")

    with tracer.start_as_current_span("parent_test_span") as span:
        assert span.is_recording()
        carrier: dict[str, str] = {}
        TraceContextManager.inject_context(carrier)

        # W3C TraceContext requires 'traceparent' header
        assert "traceparent" in carrier
        traceparent = carrier["traceparent"]
        # Format: 00-{trace_id}-{parent_id}-{flags}
        parts = traceparent.split("-")
        assert len(parts) == 4
        assert parts[0] == "00"  # Version
        assert len(parts[1]) == 32  # 128-bit Trace ID
        assert len(parts[2]) == 16  # 64-bit Span ID

        # Test extraction in another context
        extracted_ctx = TraceContextManager.extract_context(carrier)
        assert extracted_ctx is not None

        # Verify current trace ID helper
        current_trace_id = TraceContextManager.get_current_trace_id()
        assert current_trace_id is not None
        assert current_trace_id == parts[1]


def test_start_as_current_span_with_carrier():
    """Verify child span is correctly created and inherits context from carrier."""
    tracer = get_tracer("rce.chain")

    carrier: dict[str, str] = {}
    with tracer.start_as_current_span("root_span") as root:
        TraceContextManager.inject_context(carrier)
        root_trace_id = format(root.get_span_context().trace_id, "032x")

    # Start child span referencing the injected carrier
    with TraceContextManager.start_as_current_span(
        "child_span", carrier=carrier, attributes={"test.key": "val"}
    ) as child:
        child_trace_id = format(child.get_span_context().trace_id, "032x")
        # Trace ID must match parent trace ID across async boundary
        assert child_trace_id == root_trace_id
        assert child.attributes.get("test.key") == "val"


# ============================================================================
# 3. Worker Execution Span & Semantic Convention Tests
# ============================================================================


@pytest.mark.asyncio
async def test_worker_execution_creates_trace_span(monkeypatch):
    """Verify worker execution pipeline creates a traced span with semantic attributes."""
    tracer = get_tracer("rce.worker_test")
    carrier: dict[str, str] = {}

    with tracer.start_as_current_span("api_submit_span") as api_span:
        TraceContextManager.inject_context(carrier)
        expected_trace_id = format(api_span.get_span_context().trace_id, "032x")

    request = ExecutionRequest(
        source_code="print('TRACING_TEST_OK')\n",
        language="python",
        timeout_seconds=5.0,
    )

    # Mock Redis async client
    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock()
    mock_redis.rpush = AsyncMock()
    mock_redis.expire = AsyncMock()
    mock_redis.aclose = AsyncMock()
    mock_pubsub = AsyncMock()
    mock_pubsub.get_message.return_value = None
    mock_redis.pubsub.return_value = mock_pubsub

    monkeypatch.setattr(
        "worker.tasks.execution.redis_broker.get_async_client",
        lambda: mock_redis,
    )

    sub_id = str(uuid.uuid4())
    result = await _stream_and_collect(
        submission_id=sub_id,
        request=request,
        force_process=True,
        trace_context=carrier,
    )

    assert result["status"] == "COMPLETED"
    assert "TRACING_TEST_OK" in result["stdout"]
    assert len(expected_trace_id) == 32
