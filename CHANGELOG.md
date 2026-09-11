# Changelog

All notable changes to the Secure Real-Time Remote Code Execution Laboratory Platform will be documented in this file.

## [0.5.0] - 2026-09-11
### Added
- **Distributed Redis Broker Client (`RedisBroker`)**: Created async and sync Redis client connection pool manager in `worker/broker/redis_client.py` for task queues and Pub/Sub channel management.
- **Stream Multiplexer (`StreamMultiplexer`)**: Engineered real-time stream broadcaster in `worker/streaming/multiplexer.py` assigning monotonic sequence numbers to stdout/stderr chunks and publishing to `rce:stream:<submission_id>`.
- **Stream Catch-up Buffer (`StreamBuffer`)**: Implemented Redis list buffer in `worker/streaming/buffer.py` with 60-second TTL to support seamless client reconnection and stream replay.
- **Asynchronous Worker Daemon (`AsyncWorkerDaemon`)**: Built standalone async queue consumer in `worker/daemon.py` using non-blocking Redis `BRPOP` loops with graceful shutdown handling.
- **Celery Worker & Task Definitions**: Configured Celery application in `worker/celery_app.py` with fair scheduling policies (`worker_prefetch_multiplier=1`, `task_acks_late=True`, `task_reject_on_worker_lost=True`) and implemented `execute_code` task in `worker/tasks/execution.py`.
- **Automated Container Janitor (`JanitorReaper`)**: Implemented background reaper daemon in `worker/janitor/reaper.py` scanning containers labeled `sandbox_type=isolated` and purging orphaned containers exceeding operational lease (30s).
- **Comprehensive Worker Test Suite**: Added 6 tests in `backend/tests/test_worker_streaming.py` validating sequence monotonicity, buffer replay, janitor safety, and end-to-end execution streaming (14/14 tests passing across full test suite).

## [0.4.0] - 2026-09-11
### Added
- **Core Execution Models & Enums**: Defined `ExecutionStatus` (`COMPLETED`, `TIME_LIMIT_EXCEEDED`, `MEMORY_LIMIT_EXCEEDED`, `OUTPUT_LIMIT_EXCEEDED`, `RUNTIME_ERROR`, `RESOURCE_LIMIT_EXCEEDED`), `ExecutionRequest`, `ExecutionResult`, and `StreamChunk` with Pydantic v2.
- **Base Sandbox Interface (`BaseSandbox`)**: Implemented abstract contract supporting both batch execution (`execute`) and real-time streaming (`stream_execute`).
- **Hardened Docker Sandbox (`DockerSandbox`)**: Implemented production OCI container runner enforcing cgroups v2 (`cpu_quota=50000`, `mem_limit=128m`, `memswap_limit=128m`, `pids_limit=64`), dropped capabilities (`CAP_DROP ALL`), read-only rootfs, in-memory `tmpfs` RAM disk (`/tmp`, 16MB), and zero network connectivity (`--net=none`).
- **Subprocess Sandbox (`ProcessSandbox`)**: Created isolated testing and fallback sandbox with non-blocking async execution, stdin piping, and watchdog supervision.
- **Dynamic Sandbox Factory (`SandboxFactory`)**: Factory pattern dynamically selecting `DockerSandbox` when Docker daemon is reachable and falling back to `ProcessSandbox` for environments without running Docker daemon.
- **Stream Consumer & Output Capper (`StreamConsumer`)**: Enforced maximum byte ceiling (1MB hard cap) with real-time stream truncation, preventing buffer flooding and memory exhaustion.
- **Watchdog Timer Supervisor**: Implemented hard timeout enforcement ($5.0\text{s}$ wall-clock limit) issuing POSIX `SIGKILL` on infinite loop detection.
- **Comprehensive Unit & Adversarial Test Suite**: Added 6 tests in `backend/tests/test_execution_engine.py` verifying standard execution, stdin piping, infinite loop timeouts, runtime exceptions, output capping, and real-time streaming chunks (100% test pass rate).

## [0.3.0] - 2026-09-11
### Added
- **Monorepo Directory Structure**: Scaffolded unified monorepo modules (`backend/`, `worker/`, `frontend/`, `docker/`, `database/`, `deployment/`).
- **Local Infrastructure (Docker Compose)**: Configured `docker-compose.dev.yml` provisioning PostgreSQL 15 and Redis 7 with persistent volumes and healthchecks.
- **Environment Configuration**: Created `.env.example` defining database, broker, security, and execution limit parameters.
- **FastAPI Backend Skeleton**: Created ASGI application with lifespan management, CORS middleware, structured logging, and central v1 API router.
- **System Health Endpoint**: Implemented `GET /api/v1/health` verifying API readiness, PostgreSQL connectivity, and Redis broker ping.
- **Asynchronous Database Foundation**: Implemented SQLAlchemy 2.0 `create_async_engine`, async sessionmaker, and `get_db` FastAPI dependency; established Alembic async migration setup (`alembic.ini`, `env.py`).
- **Execution Worker Skeleton**: Scaffolded Celery/async worker service with requirements, task definitions, and Dockerfile.
- **Docker Sandbox Runtime**: Created minimal Alpine Python 3.11 Dockerfile (`uid=1001`) and custom Seccomp-BPF policy.
- **Frontend Skeleton**: Scaffolded React 18 + TypeScript SPA with Vite, Monaco Editor, and xterm.js dependencies.
- **Developer Tooling**: Configured `ruff.toml` for Python 3.11 linting/formatting, `.pre-commit-config.yaml`, `.editorconfig`, and automated pytest test suite (`test_health.py` with 100% pass rate).

## [0.2.0] - 2026-09-11
### Added
- Created `documentation/13_REQUIREMENTS_SPECIFICATION.md` defining functional, non-functional, MVP, and measurable engineering requirements.
- Created `documentation/14_ARCHITECTURE_DECISION_RECORDS.md` documenting ADR-001 through ADR-005 (Docker vs gVisor vs Firecracker, WebSockets vs SSE, Redis Pub/Sub decoupling, PostgreSQL JSONB, tmpfs RAM mounts).
- Created `documentation/15_DEVELOPMENT_SETUP.md` with developer onboarding guide, prerequisites, step-by-step setup, and security validation tests.
- Created `documentation/16_USER_GUIDE.md` detailing user roles (Student, Instructor, Admin), execution outcomes (TLE, MLE, OLE, Runtime Error), and interface workflows.
- Created `documentation/17_RESEARCH_AND_EVALUATION_PLAN.md` detailing academic research questions (RQ1-RQ3), empirical benchmark metrics, and load testing methodology.
- Created `documentation/18_THREAT_MODEL.md` specifying STRIDE threat modeling, attack vector matrix, and Linux kernel defense-in-depth mitigations.
- Created `documentation/19_SYSTEM_DESIGN_DECISIONS.md` explaining producer-consumer decoupling, stream multiplexing protocol, stateless gateway topology, and ephemeral sandbox lifecycles.
- Created root `SYSTEM_ARCHITECTURE.md` mirroring updated architectural diagrams and measurable goals.

### Changed
- Updated project definition to **"Secure Real-Time Remote Code Execution Laboratory Platform"**.
- Restructured `README.md` and `PROJECT_ROADMAP.md` to reflect the Systems-First development order (Foundation $\rightarrow$ Sandbox Core $\rightarrow$ Worker/Broker $\rightarrow$ Backend Gateway $\rightarrow$ Frontend $\rightarrow$ Hardening $\rightarrow$ Cloud Deployment).
- Updated `documentation/01_PROJECT_OVERVIEW.md` and `documentation/02_SYSTEM_ARCHITECTURE.md` with detailed Mermaid sequence diagrams and decoupled Pub/Sub streaming architecture.
- Formally established MVP Scope (Version 1.0) and quantitative engineering limits (5.0s timeout, 128MB RAM, 0.5 CPU core, 64 PIDs, 1MB output cap, 50 concurrent streams).

## [0.1.0] - Initial
- Initial project documentation and architecture planning.
