# ==============================================================================
# Multi-Stage Production Dockerfile for Backend API Gateway (FastAPI + ASGI)
# ==============================================================================

# --- Stage 1: Wheel Builder ---
FROM python:3.12-slim AS builder

WORKDIR /build

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install compiler dependencies required for C-extensions (psycopg2/asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Build pre-compiled wheels for fast, clean, compiler-free installation
RUN pip install --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /build/wheels -r requirements.txt

# --- Stage 2: Hardened Runtime ---
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PATH="/home/appuser/.local/bin:${PATH}"

# Install minimal runtime shared libraries only (no compiler toolchain)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Security: Create dedicated unprivileged system user and group (UID/GID 10001)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Copy pre-compiled binary wheels from builder
COPY --from=builder /build/wheels /wheels
RUN pip install --upgrade pip && \
    pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels

# Copy application source code with non-root ownership
COPY --chown=appuser:appgroup . /app

# Switch execution context to non-root user
USER appuser

# Expose API Gateway port
EXPOSE 8000

# Production Health Check Probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Launch ASGI production cluster with multiple worker processes
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
