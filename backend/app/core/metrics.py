"""Prometheus telemetry and instrumentation metrics."""

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# Platform Metrics Registry
REGISTRY = CollectorRegistry(auto_describe=True)

# Submissions counter partitioned by language and execution status
SUBMISSIONS_TOTAL = Counter(
    "rce_submissions_total",
    "Total code submissions processed by the platform.",
    ["language", "status"],
    registry=REGISTRY,
)

# Execution wall-clock latency histogram
EXECUTION_DURATION_SECONDS = Histogram(
    "rce_execution_duration_seconds",
    "Execution wall-clock duration in seconds.",
    ["language"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.5, 5.0, 10.0),
    registry=REGISTRY,
)

# Peak memory usage histogram
PEAK_MEMORY_BYTES = Histogram(
    "rce_memory_peak_bytes",
    "Peak memory consumed by sandboxed containers in bytes.",
    ["language"],
    buckets=(
        1_000_000,
        5_000_000,
        10_000_000,
        25_000_000,
        50_000_000,
        100_000_000,
        134_217_728,
    ),
    registry=REGISTRY,
)

# Active executing sandboxes gauge
ACTIVE_SANDBOXES = Gauge(
    "rce_active_sandboxes",
    "Number of sandboxes currently executing user code.",
    ["sandbox_type"],
    registry=REGISTRY,
)

# Worker queue depth gauge
QUEUE_DEPTH = Gauge(
    "rce_queue_depth",
    "Current number of pending execution tasks in the broker queue.",
    ["queue_name"],
    registry=REGISTRY,
)

# Rate limiting rejection counter
RATE_LIMIT_HITS_TOTAL = Counter(
    "rce_rate_limit_hits_total",
    "Total number of requests rejected by rate limiting.",
    ["endpoint"],
    registry=REGISTRY,
)


def get_metrics_response() -> tuple[bytes, str]:
    """Generate Prometheus formatted metrics text and media type."""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
