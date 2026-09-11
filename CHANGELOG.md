# Changelog

All notable changes to the Secure Real-Time Remote Code Execution Laboratory Platform will be documented in this file.

## [0.7.0] - 2026-09-12
### Added
- **Interactive Cloud IDE Architecture (`App.tsx`)**: Built modern split-pane workstation layout in React 18 and TypeScript with Tailwind CSS, coordinating the code editor, terminal, telemetry dashboard, and execution drawer.
- **Monaco Editor Component (`CodeEditor.tsx`)**: Integrated `@monaco-editor/react` with Python 3.11 syntax highlighting, `vs-dark` theme, execution lockouts (`readOnly: isRunning`), and `Ctrl+Enter` shortcut execution command.
- **Virtual Terminal Emulator (`TerminalView.tsx`)**: Integrated `xterm.js` with `FitAddon` and `ResizeObserver` supporting ANSI colors, carriage return handling (`convertEol: true`), custom dark theme palette, buffer copying, and 5000-line memory-capped scrollback.
- **Custom WebSocket Stream Hook (`useExecutionStream.ts`)**: Implemented React hook managing connection lifecycles (`CONNECTING`, `STREAMING`, `FINISHED`, `ERROR`), deduplicating stream frames with monotonic sequence checks, and providing exponential backoff auto-reconnect.
- **Execution Telemetry Dashboard (`TelemetryPanel.tsx`)**: Built real-time telemetry component displaying execution duration, peak RAM consumption, process exit codes, and Linux kernel sandbox isolation specifications (cgroups v2, Seccomp-BPF, `--net=none`).
- **Standard Input Drawer (`StdinDrawer.tsx`)**: Built collapsible drawer allowing users to pipe custom multi-line input payloads into `sys.stdin` at container launch.
- **Audit Log & History Drawer (`SubmissionHistory.tsx`)**: Implemented audit log panel querying `/api/v1/submissions` with code restoration into Monaco Editor.
- **Authentication Modal & Context (`AuthModal.tsx`, `AuthContext.tsx`)**: Implemented modal supporting user registration, OAuth2 JWT login, and session persistence across page reloads.

## [0.6.0] - 2026-09-12
### Added
- **Authentication & Cryptography Subsystem**: Implemented JWT access token generation, cryptographically signed token verification, and 72-byte safe salted password hashing using C-accelerated `bcrypt` in `backend/app/core/security.py`.
- **Relational Domain Models & Alembic Migration**: Implemented SQLAlchemy 2.0 ORM entities `User` and `Submission` with PostgreSQL native UUID primary keys, automatic ISO timestamps, and cascading relationships; authored Alembic migration `001_initial_schema.py`.
- **FastAPI Authentication Routes (`/api/v1/auth`)**: Implemented `/register`, OAuth2-compatible `/login`, and `/me` endpoints in `backend/app/api/v1/endpoints/auth.py` with Pydantic v2 schemas and validation.
- **Submission Ingestion & Queue Dispatch (`/api/v1/submissions`)**: Built `POST /api/v1/submissions` creating database records in `PENDING` state and dispatching task payloads onto the Redis broker queue (`rce:submissions`) for worker consumption.
- **Submission History & Detail Queries**: Built `GET /api/v1/submissions` with cursor/page pagination and `GET /api/v1/submissions/{id}` with user-isolated access controls.
- **Full-Duplex WebSocket Streaming Gateway (`/ws/v1/submissions/{id}`)**: Built WebSocket endpoint with query-token authentication, Redis buffer replay (`StreamBuffer`), and real-time Pub/Sub subscriber relay to client terminals.
- **End-to-End Integration Test Suite**: Added 4 integration tests in `backend/tests/test_auth_and_submissions.py` and `backend/tests/test_websocket.py` verifying full auth lifecycle, submission dispatch, unauthorized access rejection, and WebSocket security (18/18 tests passing with 76% codebase coverage).

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
