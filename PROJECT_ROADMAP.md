# Project Roadmap & Master Execution Plan
## Secure Real-Time Remote Code Execution Laboratory Platform

**Document Version:** 1.0.0  
**Project Vision:** Build a production-style, multi-tenant remote code execution platform where users write, execute, and monitor code securely in real time through an in-browser IDE.  
**Academic Objective:** Master's portfolio project demonstrating rigorous understanding of:
- **Operating Systems:** Linux cgroups v2, namespaces, process lifecycle, signal handling, and Seccomp-BPF filters.
- **Distributed Systems:** Decoupled producer-consumer pipelines, asynchronous task queuing, at-least-once delivery, and backpressure.
- **Networking:** Full-duplex WebSocket framing (`RFC 6455`), multiplexed standard streams, and network namespace isolation (`--net=none`).
- **Cybersecurity:** Defense-in-depth, zero-trust container sandboxing, capability dropping (`CAP_DROP ALL`), and STRIDE threat mitigation.
- **Backend & Cloud Architecture:** ASGI async event loops, connection pooling, and horizontal worker scalability.

---

## 1. Measurable Engineering Goals & Operational Limits

| Parameter | Target Limit | Enforcement Mechanism | Failure Status Code |
| :--- | :--- | :--- | :--- |
| **Execution Wall-Clock Timeout** | **5.0 s** (configurable max 15.0s) | Worker watchdog timer + POSIX `SIGKILL` | `TIME_LIMIT_EXCEEDED` (TLE) |
| **CPU Time Quota** | **0.5 Core** (50% CFS scheduler bandwidth) | Linux cgroups v2 (`cpu.max`) | Throttled / `TIME_LIMIT_EXCEEDED` |
| **Memory Allocation Limit** | **128 MB** (v1 hard limit, swap disabled) | Linux cgroups v2 (`memory.max`) | Kernel OOM-Killer $\rightarrow$ `MEMORY_LIMIT_EXCEEDED` (MLE) |
| **Process / Thread Limit** | **64 PIDs** per sandbox | Linux cgroups v2 (`pids.max`) | Prevents Fork Bombs (`EAGAIN`) |
| **Standard Output (stdout/stderr) Limit** | **1 MB** (or 10,000 lines) | Worker stream consumer byte counter | `OUTPUT_LIMIT_EXCEEDED` (OLE) |
| **WebSocket Streaming Rate** | Maximum **50 KB/s** burst rate | Token bucket rate limiter | Backpressure applied / Stream throttled |
| **Concurrent Active Executions** | $\ge \mathbf{50}$ concurrent streams / worker node | Horizontal worker scaling via Celery / Redis | Queued in Redis FIFO buffer (`PENDING`) |

---

## 2. Minimum Viable Product (MVP) Scope — Version 1.0

- **Language Runtime:** Python 3.11 only.
- **User Authentication:** JWT Bearer authentication (access & refresh tokens) with bcrypt/Argon2id password hashing.
- **Code Submission:** Web-based Monaco code editor interface with optional `stdin` input.
- **Sandbox Execution:** Hardened, unprivileged ephemeral Docker container with cgroup v2 limits, read-only rootfs, and memory-backed `tmpfs`.
- **WebSocket Output:** Real-time bi-directional streaming from worker to browser via Redis Pub/Sub and FastAPI WebSockets.
- **Execution History:** PostgreSQL persistence of past submissions, execution metrics (duration, memory, exit code), and execution logs.

---

## 3. Systems-First Development Roadmap

### Phase 1: Project Foundation & Infrastructure Setup (Completed)
- [x] Task 1.1: Initialize unified monorepo directory layout (`backend/`, `worker/`, `frontend/`, `docker/`, `database/`, `deployment/`).
- [x] Task 1.2: Configure `.env.example` and environment variable management.
- [x] Task 1.3: Define `docker-compose.dev.yml` for local infrastructure (PostgreSQL 15+ and Redis 7+).
- [x] Task 1.4: Establish Git repository standards, pre-commit linting (`ruff`, `.editorconfig`), and testing framework.

### Phase 2: Secure Execution Engine & Sandbox Core (Completed)
- [x] Task 2.1: Author hardened unprivileged Python 3.11 Dockerfile (`uid=1001`, minimal Alpine base).
- [x] Task 2.2: Define Seccomp-BPF JSON profile blocking dangerous system calls (`ptrace`, `bpf`, `mount`).
- [x] Task 2.3: Implement standalone Python sandbox runner using Docker SDK with strict cgroups v2 (`cpu.max`, `memory.max`, `pids.max`).
- [x] Task 2.4: Implement memory-backed `tmpfs` RAM disk mount (`--read-only` rootfs, 16MB tmpfs).
- [x] Task 2.5: Implement worker watchdog supervisor with POSIX `SIGKILL` timeout enforcement.
- [x] Task 2.6: Write unit tests verifying containment of fork bombs, memory bombs, and infinite loops.

### Phase 3: Distributed Worker Architecture & Real-Time Streaming (Completed)
- [x] Task 3.1: Configure Redis as message broker and streaming pub/sub bus.
- [x] Task 3.2: Implement asynchronous Celery worker / consumer daemon for task dispatch.
- [x] Task 3.3: Implement stream multiplexer piping container stdout/stderr chunks to Redis Pub/Sub (`exec:<id>`).
- [x] Task 3.4: Implement stream buffer with 60s TTL in Redis for reconnection resilience.
- [x] Task 3.5: Implement automated orphan container cleanup daemon (`JanitorDaemon`).

### Phase 4: Backend API Gateway, Authentication & Persistence (Completed)
- [x] Task 4.1: Initialize FastAPI application with ASGI asynchronous architecture.
- [x] Task 4.2: Design PostgreSQL schema (Users, Submissions, ExecutionLogs) and Alembic migrations.
- [x] Task 4.3: Implement JWT authentication routes (`/api/v1/auth/register`, `/api/v1/auth/login`).
- [x] Task 4.4: Implement submission ingestion endpoint (`POST /api/v1/submissions`) with payload validation.
- [x] Task 4.5: Implement full-duplex WebSocket endpoint (`/ws/v1/submissions/{id}`) subscribing to Redis Pub/Sub.
- [x] Task 4.6: Implement submission history and telemetry endpoints (`GET /api/v1/submissions`).

### Phase 5: Interactive Web Application (Frontend) (Completed)
- [x] Task 5.1: Initialize React 18 + TypeScript application using Vite.
- [x] Task 5.2: Integrate Monaco Editor with Python 3.11 syntax highlighting, shortcuts, and themes.
- [x] Task 5.3: Integrate `xterm.js` terminal emulator with ANSI color and stream rendering.
- [x] Task 5.4: Build custom React WebSocket hook with auto-reconnection and buffering.
- [x] Task 5.5: Build execution history dashboard with telemetry metrics (runtime, memory, status badges).

### Phase 6: System Hardening, Adversarial Testing & Telemetry (Completed)
- [x] Task 6.1: Execute comprehensive adversarial test suite (fork bombs, OOM, disk filling, network scanning).
- [x] Task 6.2: Implement distributed rate limiting on submission endpoints (Token Bucket / Redis).
- [x] Task 6.3: Instrument Prometheus metrics (submission latency, worker queue depth, container count).
- [x] Task 6.4: Validate 100% containment under noisy-neighbor stress benchmarks.

### Phase 7: Production Cloud Deployment, Benchmarking & Portfolio Defense (Completed)
- [x] Task 7.1: Configure production multi-stage Dockerfiles and production Docker Compose / Kubernetes manifests.
- [x] Task 7.2: Run Locust / k6 load testing suite measuring cold-start vs. warm-pool latencies.
- [x] Task 7.3: Synthesize empirical evaluation graphs and publish research findings in `documentation/`.
- [x] Task 7.4: Conduct final Master's technical portfolio review and defense preparation.

### Phase 8: Advanced Systems Architecture (In Progress)
- [x] Task 8.1: Polyglot Execution Pipeline (C/C++, Rust, Go, Node.js, Strategy Pattern & Two-Phase Compiler Sandboxing).
- [ ] Task 8.2: Automated Autograding & Problem Verification Engine (Hidden test cases, memory & time limits, grading scorecard UI).
- [ ] Task 8.3: Bidirectional Interactive Pseudo-Terminal (PTY, termios, signal multiplexing, interactive REPL).
- [ ] Task 8.4: Cloud-Native Kubernetes Orchestration & HPA (Helm charts, PodSecurityStandards, Prometheus queue-depth autoscaling).


