# Requirements Specification
## Secure Real-Time Remote Code Execution Laboratory Platform

**Document Version:** 1.0.0  
**Status:** Approved Specification  
**Scope:** Core Platform & MVP (Version 1.0)  

---

## 1. Executive Summary & System Objectives

The **Secure Real-Time Remote Code Execution Laboratory Platform** is a distributed, multi-tenant computing system engineered to provide isolated, browser-accessible programming environments. It allows educational institutions, instructors, and students to compile, execute, and monitor arbitrary user-submitted code in real time without local toolchain installation.

The platform's primary engineering objective is solving the trilemma of **Multi-Tenant Arbitrary Code Execution**:
1. **Safety (Zero-Trust Sandboxing):** Eliminating host compromise, resource starvation, and lateral network traversal from untrusted payloads.
2. **Performance (Low Latency):** Achieving sub-second cold-start execution times and low-latency real-time standard I/O streaming.
3. **Scalability (Decoupled Concurrency):** Preventing web API thread starvation during submission deadlines through an asynchronous worker-broker topology.

---

## 2. Measurable Engineering Goals & Operational Limits

The following quantitative targets represent strict non-functional constraints enforced at the operating system, container runtime, network, and application layers:

| Metric | Target Value | Enforcement Mechanism | Failure Response / Status Code |
| :--- | :--- | :--- | :--- |
| **Execution Wall-Clock Timeout** | Default: **5.0 s**<br>Configurable Max: **15.0 s** | Worker watchdog timer + POSIX `SIGKILL` | `TIME_LIMIT_EXCEEDED` (TLE) |
| **CPU Time Quota** | **0.5 Core** (50,000 µs per 100,000 µs period) | Linux cgroups v2 (`cpu.max` CFS scheduler quota) | Throttling / `TIME_LIMIT_EXCEEDED` if wall-clock expires |
| **Memory Allocation Limit** | Hard Limit: **128 MB** (v1)<br>Configurable Max: **256 MB** | Linux cgroups v2 (`memory.max`), Swap disabled (`memory.swap.max = 0`) | Kernel OOM-Killer trigger $\rightarrow$ `MEMORY_LIMIT_EXCEEDED` (MLE) |
| **Process / Thread Limit** | Max **64 PIDs** per sandbox | Linux cgroups v2 (`pids.max`) | `Resource temporarily unavailable` (Prevents fork bombs) |
| **Standard Output (stdout/stderr) Limit** | Hard Cap: **1 MB** or **10,000 lines** | Worker stream consumer byte counter | Stream truncated $\rightarrow$ `OUTPUT_LIMIT_EXCEEDED` |
| **WebSocket Streaming Rate** | Maximum **50 KB/s** burst rate | Application-level token bucket rate limiter | Backpressure applied / Stream throttled |
| **Concurrent Active Sandbox Executions** | $\ge \mathbf{50}$ concurrent streams / worker node | Horizontal worker scaling via Celery / Redis | Queued in Redis FIFO buffer (`PENDING`) |
| **Sandbox Cold-Start Overhead** | $\le \mathbf{800\text{ ms}}$ (Target: $< 400\text{ ms}$) | Pre-pulled base images, minimal Alpine runtime | Tracked via Prometheus execution telemetry |

---

## 3. Minimum Viable Product (MVP) Scope — Version 1.0

To ensure rapid delivery of a robust, fully verifiable end-to-end architecture, Version 1.0 is constrained to the following functional core:

- **Language Support:**
  - **Python 3.11** execution only (interpreted runtime; simplifies compilation pipeline while exercising full sandbox and streaming machinery).
- **User Authentication & Authorization:**
  - Secure registration and login via JSON Web Tokens (JWT: Access + Refresh tokens).
  - Password hashing using Argon2id or bcrypt.
  - Role-based separation: `Student` (submit and view own history) and `Admin` (view global telemetry and node health).
- **Code Submission & In-Browser IDE:**
  - Web-based code editor (Monaco Editor) with Python syntax highlighting, line numbers, and error markers.
  - Standard input (`stdin`) configuration payload.
- **Sandboxed Execution Engine:**
  - Docker container running as non-root user (`uid=1001`, `gid=1001`).
  - Read-only root filesystem (`--read-only`) with writable memory-backed ephemeral mount (`tmpfs` on `/tmp`, max 16MB).
  - Total network isolation (`--net=none`).
  - Dropped Linux capabilities (`--cap-drop=ALL`).
  - Kernel-enforced cgroup limits for CPU, RAM, and PIDs.
- **Real-Time WebSocket Output Streaming:**
  - Full-duplex WebSocket connection per execution session.
  - Output chunks streamed directly from Worker via Redis Pub/Sub to FastAPI and rendered in an interactive web terminal.
- **Execution Telemetry & Persistence:**
  - Relational persistence in PostgreSQL: user records, submission source code, status codes, execution duration (ms), peak memory consumed (KB), and exit code.
  - Historical submission list and detail views.

---

## 4. Functional Requirements (FR)

### 4.1 Authentication & User Management
- **FR-AUTH-01:** System shall permit user registration with email, username, and password.
- **FR-AUTH-02:** System shall authenticate users and issue cryptographically signed JWT tokens with 15-minute access expiration and 7-day refresh expiration.
- **FR-AUTH-03:** All API endpoints processing code submission or history retrieval must require valid JWT Bearer authentication.

### 4.2 Code Submission & Management
- **FR-SUB-01:** Users shall be able to draft Python scripts within the Monaco Editor component.
- **FR-SUB-02:** Users shall be able to supply optional `stdin` input data prior to or during execution.
- **FR-SUB-03:** Client shall transmit code payloads over a secure REST API endpoint (`POST /api/v1/submissions`) or directly over an established WebSocket connection.
- **FR-SUB-04:** Backend shall validate code payload size (maximum 64 KB source code) and reject oversized submissions with HTTP 413.

### 4.3 Execution & Sandboxing
- **FR-EXEC-01:** System shall enqueue valid execution requests into a Redis broker queue with a distinct UUID v4 `submission_id`.
- **FR-EXEC-02:** Execution workers shall dequeue tasks and instantiate a containerized sandbox with pre-configured cgroup constraints.
- **FR-EXEC-03:** Sandbox shall execute code using the standard CPython interpreter (`python -u -B script.py`).
- **FR-EXEC-04:** Worker shall enforce a hard wall-clock timeout ($5.0\text{s}$) using an independent supervisor thread or signal timer.
- **FR-EXEC-05:** Sandboxes must be completely destroyed immediately upon process termination; no residual processes or filesystem artifacts shall persist.

### 4.4 Real-Time Streaming
- **FR-STRM-01:** Backend shall provide a WebSocket endpoint (`/ws/v1/submissions/{submission_id}`) accessible to the authenticated submitting user.
- **FR-STRM-02:** Worker shall capture `stdout` and `stderr` multiplexed streams and publish chunks to Redis Pub/Sub channel `exec:{submission_id}`.
- **FR-STRM-03:** Backend WebSocket handler shall subscribe to `exec:{submission_id}` and relay text frames to the client with sub-100ms transmission latency.
- **FR-STRM-04:** Terminal stream shall transmit status metadata events (e.g., `STARTING`, `RUNNING`, `STDOUT`, `STDERR`, `COMPLETED`, `FAILED`).

### 4.5 Persistence & Reporting
- **FR-HIST-01:** System shall store every submission in PostgreSQL with fields: `id`, `user_id`, `code`, `language`, `status`, `exit_code`, `execution_time_ms`, `peak_memory_bytes`, `created_at`.
- **FR-HIST-02:** Users shall be able to query paginated execution history (`GET /api/v1/submissions`).
- **FR-HIST-03:** Users shall be able to retrieve the full output log of past executions (`GET /api/v1/submissions/{id}`).

---

## 5. Non-Functional Requirements (NFR)

### 5.1 Security
- **NFR-SEC-01 (Least Privilege):** Code execution containers shall run with unprivileged user permissions (`uid=1001`, `gid=1001`) and drop all ambient Linux capabilities (`CAP_DROP ALL`).
- **NFR-SEC-02 (Network Isolation):** Containers must have no external or internal network connectivity (`--network none`); only loopback (`127.0.0.1`) shall be available.
- **NFR-SEC-03 (Filesystem Protection):** Root filesystem of the execution container must be mounted strictly read-only (`--read-only`). The only writable location shall be an ephemeral `tmpfs` RAM disk mounted at `/tmp` with `noexec,nosuid,nodev` flags and a 16 MB ceiling.
- **NFR-SEC-04 (Host Isolation):** Host Docker daemon socket (`/var/run/docker.sock`) must never be accessible inside execution containers.

### 5.2 Performance & Responsiveness
- **NFR-PERF-01:** The API Gateway response time for enqueuing submissions shall be $< 50\text{ ms}$ (95th percentile).
- **NFR-PERF-02:** The time from submission receipt to first streamed byte of output (for warm workers) shall be $< 1.0\text{ s}$.
- **NFR-PERF-03:** The frontend code editor and terminal shall maintain 60 FPS rendering under streaming rates up to 50 KB/s.

### 5.3 Reliability & Fault Tolerance
- **NFR-REL-01 (Idempotency & Clean Up):** If a worker terminates abnormally during execution, the container must be reaped by an independent garbage collection daemon within 60 seconds.
- **NFR-REL-02 (Worker Isolation):** Crash or hang of user code inside a sandbox container must not cause failure, slowdown, or memory leak in the host worker daemon.
- **NFR-REL-03 (Database Connection Resilience):** Database operations shall utilize connection pooling (`SQLAlchemy` / `asyncpg`) with automatic retry on transient connection drops.

### 5.4 Maintainability & Code Quality
- **NFR-MAINT-01:** 100% of API endpoints must be documented with OpenAPI v3 schemas.
- **NFR-MAINT-02:** Backend codebase must pass strict static type analysis (`mypy`) and PEP 8 linting (`ruff`).
- **NFR-MAINT-03:** Core execution sandbox and API routes must maintain $\ge 80\%$ automated unit and integration test coverage.
