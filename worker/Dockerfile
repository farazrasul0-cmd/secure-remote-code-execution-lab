# ==============================================================================
# Multi-Stage Production Dockerfile for Execution Worker (Celery + Docker SDK)
# ==============================================================================

# --- Stage 1: Wheel Builder ---
FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# --- Stage 2: Hardened Runtime ---
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/home/appuser/.local/bin:${PATH}"

# Install minimal runtime dependencies: libpq5, curl, docker CLI for engine communication
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Security: Create dedicated unprivileged system user and grant Docker socket group access
RUN groupadd -g 10001 appgroup && \
    groupadd -g 999 docker && \
    useradd -u 10001 -g appgroup -G docker -s /bin/bash -m appuser

COPY --from=builder /build/wheels /wheels
RUN pip install --upgrade pip && \
    pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels

COPY --chown=appuser:appgroup . /app

USER appuser

# Celery Worker Health Check Probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD celery -A tasks.worker inspect ping -d celery@$HOSTNAME || exit 1

# Launch Celery worker daemon with bounded concurrency
CMD ["celery", "-A", "tasks.worker", "worker", "--loglevel=info", "--concurrency=4"]
