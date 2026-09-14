"""OpenTelemetry Distributed Tracing & W3C TraceContext Propagation Subsystem.

Provides centralized tracer provider setup, W3C TraceContext injection and extraction
helpers across asynchronous boundaries (Redis queue, Celery task metadata, and Pub/Sub).
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from opentelemetry import trace
from opentelemetry.propagate import extract, inject
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from opentelemetry.trace import Span, Tracer

logger = logging.getLogger("rce.telemetry")

_TRACER_INITIALIZED = False


def init_tracer(
    service_name: str = "rce-backend-api", debug_console: bool = False
) -> TracerProvider:
    """Initialize and configure global OpenTelemetry TracerProvider with W3C standards."""
    global _TRACER_INITIALIZED

    current_provider = trace.get_tracer_provider()
    if isinstance(current_provider, TracerProvider) and _TRACER_INITIALIZED:
        return current_provider

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.namespace": "rce-laboratory",
            "service.version": "1.5.0",
        }
    )

    provider = TracerProvider(resource=resource)

    if debug_console:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _TRACER_INITIALIZED = True
    logger.info(
        "OpenTelemetry TracerProvider initialized for service: %s", service_name
    )
    return provider


def get_tracer(module_name: str = "rce.core") -> Tracer:
    """Obtain a tracer instance scoped to the specified module."""
    if not _TRACER_INITIALIZED:
        init_tracer()
    return trace.get_tracer(module_name)


class TraceContextManager:
    """Helpers to serialize and deserialize W3C TraceContext (traceparent) across queues."""

    @staticmethod
    def inject_context(carrier: dict[str, Any] | None = None) -> dict[str, Any]:
        """Inject active span's W3C traceparent into dictionary carrier for RPC/task metadata."""
        if carrier is None:
            carrier = {}
        inject(carrier)
        return carrier

    @staticmethod
    def extract_context(carrier: dict[str, Any]) -> Any:
        """Extract W3C TraceContext from carrier dictionary to re-link parent-child spans."""
        return extract(carrier)

    @staticmethod
    @contextmanager
    def start_as_current_span(
        name: str,
        carrier: dict[str, Any] | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> Generator[Span, None, None]:
        """Context manager creating a new span, optionally linked to an extracted parent context."""
        tracer = get_tracer("rce.context")
        parent_context = (
            TraceContextManager.extract_context(carrier) if carrier else None
        )

        with tracer.start_as_current_span(
            name, context=parent_context, attributes=attributes or {}
        ) as span:
            yield span

    @staticmethod
    def get_current_trace_id() -> str | None:
        """Return current 32-character hex trace ID if span is active, otherwise None."""
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().trace_id, "032x")
        return None
