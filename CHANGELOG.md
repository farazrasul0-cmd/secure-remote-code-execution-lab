# Changelog

All notable changes to the Secure Real-Time Remote Code Execution Laboratory Platform will be documented in this file.

## [1.5.0] - 2026-09-15
### Added
- **Micro-VM Hardware Virtualization Driver (`worker/sandbox/microvm_sandbox.py`)**: Implemented `MicroVMSandbox` supporting hardware-assisted fault boundaries, guest memory envelope isolation, POSIX signal propagation, and watchdog timeout supervisors inspired by AWS Firecracker and Linux KVM (`/dev/kvm`).
- **Pluggable Sandbox Driver Hierarchy & Capability Factory (`worker/sandbox/factory.py`, `models.py`)**: Formalized `SandboxDriverType` enum (`PROCESS`, `DOCKER`, `MICROVM`, `AUTO`) and upgraded `SandboxFactory` with capability discovery; dynamically checks host `/dev/kvm` and Docker daemon availability to automatically deploy the highest security driver supported by the underlying hardware.
- **Automated Sandbox Benchmarking Harness (`worker/sandbox/benchmark/harness.py`)**: Created empirical benchmark suite quantitatively measuring cold startup initialization latency (ms), execution throughput, and estimated memory overhead across all available isolation drivers.
- **Sandbox Drivers Test Suite (`backend/tests/test_sandbox_drivers.py`)**: Authored 14 unit and integration tests verifying driver instantiation, fallback negotiation, output streaming, timeout termination, KVM probe detection, and comparative benchmark execution (expanding test suite to 75/75 passing tests).
- **OpenTelemetry Subsystem & W3C TraceContext (`backend/app/core/telemetry.py`)**: Engineered vendor-neutral distributed tracing architecture with global TracerProvider initialization, W3C `traceparent` carrier injection/extraction, and child span inheritance across asynchronous queue boundaries.
- **Asynchronous Trace Propagation Across Redis & Celery (`submission_service.py`, `execution.py`)**: Integrated W3C TraceContext metadata headers into Redis queue submissions and re-linked them within Celery worker coroutines as child spans (`rce.worker.sandbox_execution`) tagged with semantic conventions (`rce.submission_id`, `rce.language`, `rce.status`, `rce.exit_code`).
- **Distributed Tracing Test Suite (`backend/tests/test_distributed_tracing.py`)**: Authored 4 unit and integration tests verifying global TracerProvider setup, W3C traceparent formatting, carrier extraction, and end-to-end worker span creation (expanding test suite to 79/79 passing tests).

## [1.4.0] - 2026-09-14
### Added
- **Enterprise Helm Chart (`helm/rce-platform/`)**: Packaged the complete platform into a production-grade Helm chart with 17 parameterized templates, centralized `values.yaml` configuration, and Go template helpers for consistent labeling and security context injection.
- **PodSecurityStandards Restricted Enforcement (`namespace.yaml`)**: Configured namespace-level admission with `pod-security.kubernetes.io/enforce: restricted`, enforcing non-root UIDs (`10001`), dropped ALL capabilities, read-only root filesystems, and Seccomp `RuntimeDefault` profiles across all workloads.
- **Zero-Trust NetworkPolicy Suite (`networkpolicies.yaml`)**: Implemented default-deny-all ingress and egress baseline with microsegmented label-selector whitelists: frontend accepts only Ingress Controller traffic; backend connects to PostgreSQL and Redis; workers connect only to Redis; databases accept only authorized pods.
- **Queue-Depth HPA Autoscaling (`hpa-worker.yaml`)**: Configured HPA v2 scaling Celery worker replicas on custom Prometheus metric `rce_worker_queue_depth` (Little's Law: target 5 submissions per worker) with aggressive scale-up (0s stabilization) and conservative scale-down (300s window).
- **Backend CPU/Memory HPA (`hpa-backend.yaml`)**: Configured HPA v2 scaling API gateway replicas on CPU (70%) and memory (80%) utilization with stabilization policies.
- **PostgreSQL 16 StatefulSet (`statefulset-postgres.yaml`)**: Deployed PostgreSQL with 10Gi PersistentVolumeClaim, headless service for DNS, `pg_isready` health probes, and secret-backed password injection.
- **Redis 7 StatefulSet (`statefulset-redis.yaml`)**: Deployed Redis with AOF persistence (`--appendonly yes`), 2Gi PVC, read-only root filesystem, and `redis-cli ping` health probes.
- **Ingress with WebSocket Support (`ingress.yaml`)**: Configured path-based routing (`/api` and `/ws` to backend, `/` to frontend) with 3600s proxy read/send timeout annotations for long-running interactive terminal sessions.
- **Kubernetes Manifest Validation Test Suite (`test_kubernetes_manifests.py`)**: Authored 14 unit tests verifying chart structure, PSS compliance, NetworkPolicy rules, HPA metrics, StatefulSet storage, and Ingress routing (expanding test suite to 61/61 passing tests).

## [1.3.0] - 2026-09-14
### Added
- **Bidirectional Interactive Pseudo-Terminal (PTY) (`worker/sandbox/pty_session.py`)**: Implemented low-level POSIX PTY allocation using `pty.openpty()`, non-blocking I/O (`os.O_NONBLOCK`), newline line discipline translation (`termios.ONLCR`), cross-platform non-POSIX fallback, and dynamic terminal window sizing via `TIOCSWINSZ` ioctl.
- **Upstream Input & Control Consumer (`worker/tasks/execution.py`)**: Engineered asynchronous subscriber task listening to Redis Pub/Sub channel `rce:input:<submission_id>`, dynamically routing upstream `stdin` keystrokes, `resize` events, and `signal` dispatches (`SIGINT`) directly to active sandbox processes and PTY sessions.
- **Full-Duplex Bidirectional WebSocket Gateway (`backend/app/api/v1/endpoints/websocket.py`)**: Refactored WebSocket handler into concurrent `downstream_pump` and `upstream_pump` coroutines, streaming live terminal outputs to the browser while concurrently accepting user keystrokes, viewport geometry adjustments, and out-of-band interrupt requests.
- **Interactive Terminal UI & Keystroke Capture (`TerminalView.tsx`, `useExecutionStream.ts`, `App.tsx`)**: Upgraded `xterm.js` terminal view with interactive cursor blinking, `onData` keystroke piping, `onResize` geometry propagation, upstream input dispatch methods (`sendInput`, `sendResize`, `sendSignal`), and an interactive `Ctrl+C` interrupt button for aborting runaway executions.
- **Interactive PTY Test Suite (`test_interactive_terminal.py`)**: Authored 7 comprehensive unit and integration tests verifying PTY allocation, non-POSIX fallbacks, window size ioctl packing, upstream Redis message routing, full-duplex WebSocket framing, and process signal delivery (expanding the test suite to 47/47 passing tests).

## [1.2.0] - 2026-09-14
### Added
- **Automated Autograding & Problem Verification Engine (`worker/grading/`)**: Implemented deterministic oracle evaluation harness (`GradingHarness`), output normalizer (`OutputNormalizer`), and multi-mode result verifier (`ResultVerifier`) supporting `NORMALIZED`, `STRICT`, `TOKEN`, and `EPSILON` floating-point tolerance ($\le 10^{-6}$).
- **Information Hiding & Oracle Protection (`GradingHarness.sanitize_for_student`)**: Enforced server-side test vector sanitization; private system test inputs and expected outputs are cryptographically scrubbed to `[REDACTED: HIDDEN TEST CASE]` before serialization, preventing hardcoded cheat submissions.
- **Problem & TestCase Database Schemas & Migrations (`backend/app/models/problem.py`, `002_autograding_problems_and_test_cases.py`)**: Added `Problem` and `TestCase` entities with difficulty ratings, time/memory constraints, test point weights, and visibility flags; added `score`, `max_score`, and `grading_status` to `submissions`.
- **Problem Autograding APIs (`backend/app/api/v1/endpoints/problems.py`)**: Implemented REST endpoints for problem catalog discovery, detailed problem retrieval with visible sample test cases, admin problem creation, code submission autograding, and scorecard retrieval.
- **Seed Algorithmic Problems**: Seeded standard introductory challenges (Two Sum, Valid Palindrome, Nth Fibonacci) with mixed visible sample and hidden grading test cases.
- **Frontend Problem Catalog & Autograding Scorecard UI (`ProblemPanel.tsx`, `GradingScorecard.tsx`, `App.tsx`)**: Created catalog browser with difficulty tags, markdown specifications, sample I/O viewers, "Submit for Grading" triggers, and comprehensive scorecard modals with per-test runtime metrics and padlock icons for hidden vectors.
- **Autograding Pytest Suite (`test_autograding.py`)**: Authored 6 unit and integration tests verifying output normalization modes, floating-point divergence detection, test harness score aggregation, information hiding sanitization, and API submission grading (growing test suite to 40/40 passing tests).

## [1.1.0] - 2026-09-14
### Added
- **Polyglot Strategy Engine (`worker/sandbox/polyglot/`)**: Implemented the Strategy Design Pattern for multi-language execution runtimes, introducing `BaseLanguageStrategy`, `LanguageRegistry`, and dedicated strategies for Python 3.12, C17 (GCC 14), C++20 (G++ 14), Rust 2021, Go 1.22, and JavaScript (Node.js 20).
- **Two-Phase Compilation & Execution Engine (`process_sandbox.py`, `models.py`)**: Engineered asymmetric two-phase sandbox lifecycle decoupling compiler analysis (Stage 1) from binary execution (Stage 2); added `COMPILE_ERROR` status with full diagnostic traceback capture without consuming runtime timeout limits.
- **Defensive Binary Compiler Hardening**: Configured C/C++ compilation with stack canaries (`-fstack-protector-strong`), Position Independent Executables (`-fPIE -pie`), Full RELRO (`-Wl,-z,relro,-z,now`), non-executable stack (`-z noexecstack`), memory bounds fortification (`-D_FORTIFY_SOURCE=2`), and template recursion caps (`-ftemplate-depth=128`).
- **Language Exposition API (`/api/v1/languages`)**: Added REST endpoint serving supported runtimes, file extensions, and starter code templates.
- **Frontend Polyglot IDE Support (`CodeEditor.tsx`, `App.tsx`, `types/index.ts`)**: Integrated multi-language dropdown in Monaco Editor, with syntax highlighting and pre-populated starter templates for all 6 supported languages.
- **Polyglot Test Suite (`test_polyglot.py`)**: Added 5 unit and integration tests verifying strategy dispatch, compiler flag enforcement, compilation error capture, and languages API exposition (growing test suite to 34/34 passing tests).

## [1.0.0] - 2026-09-14
### Added
- **Production Multi-Stage Containerization (`frontend/Dockerfile`, `backend/Dockerfile`, `worker/Dockerfile`)**: Implemented multi-stage Docker builds reducing image sizes by >85% (purging compilation toolchains, npm devDependencies, and pip caches); enforced non-root execution (`UID 10001:GID 10001`) and integrated container `HEALTHCHECK` probes on all services.
- **Production Docker Compose Orchestration (`deployment/docker-compose.prod.yml`)**: Designed production deployment manifest featuring dual-network segregation (`rce_public_network` for Nginx ingress, `rce_internal_network` for private microservices), `no-new-privileges: true`, resource limits (CPU quotas, RAM ceilings), and persistent volume mappings for PostgreSQL 16 and Redis 7 (AOF enabled).
- **High-Performance Ingress Reverse Proxy (`deployment/nginx.conf`, `frontend/nginx.conf`)**: Configured Nginx with gzip asset compression, upstream keep-alive pooling, WebSocket upgrade headers, and OWASP security headers (`X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`).
- **Distributed Load Testing Suite (`benchmarks/load_test_k6.js`)**: Developed k6 performance test ramping from 1 to 25 virtual users simulating realistic student code submissions, measuring latency percentiles ($p50, p95, p99$) and validating Redis sliding window rate limiting.
- **Automated Systems Benchmarking Engine (`benchmarks/benchmark_engine.py`)**: Built automated empirical evaluation harness measuring bare-metal vs. sandbox virtualization overhead (RQ1), Little's Law queueing throughput (RQ2), and 100% adversarial threat containment (RQ3); generated `benchmark_report.json` and `benchmark_report.md`.
- **Academic Research & Systems Defense Documentation (`documentation/22_RESEARCH_VALUE.md`, `documentation/21_ARCHITECTURE_DECISIONS.md`, `documentation/18_DEPLOYMENT_ARCHITECTURE.md`, `documentation/04_TECHNOLOGY_STACK.md`)**: Synthesized comprehensive research findings answering three formal Research Questions with empirical data tables, architectural trade-off defenses, and Master's thesis interview talking points.

## [0.8.0] - 2026-09-14
### Added
- **Adversarial Exploitation Test Suite (`test_adversarial.py`)**: Authored comprehensive security test suite verifying fork bomb mitigation (`pids_limit=64`), OOM memory exhaustion traps, restricted root filesystem write prevention, network exfiltration containment, and Seccomp-BPF default-deny syscall filters.
- **Distributed Sliding Window Rate Limiter (`RateLimiter`)**: Engineered Redis Sorted Set (`ZSET`) sliding window rate limiter in `backend/app/core/rate_limiter.py` enforcing per-user submission quotas (`15/min`) with high-availability fail-open resilience and automated `Retry-After` header issuance.
- **Prometheus Metrics & Telemetry Exporter (`metrics.py`, `endpoints/metrics.py`)**: Instrumented Prometheus telemetry collecting submission counts, wall-clock execution latency histograms, peak RAM histograms, active sandbox gauges, broker queue depths, and rate-limiting rejection counters; exposed at `/metrics` and `/api/v1/metrics`.
- **Noisy-Neighbor Multi-Tenant Stress Benchmark (`test_noisy_neighbor.py`)**: Built stress test executing simultaneous rogue CPU-hog computations alongside interactive workloads, demonstrating zero starvation and strict CPU quota isolation via cgroups v2 (`cpu.max=50000 100000`).
- **Shared Async Redis Dependency Module (`backend/app/core/redis.py`)**: Centralized Redis dependency injection to eliminate circular imports between API endpoints and rate limiting middleware.
- **Expanded Pytest Test Suite**: Grew test coverage from 18 to 29 tests (100% pass rate, 79% codebase coverage).

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
