# Architecture Walkthrough & Request Lifecycle
## Secure Real-Time Remote Code Execution Laboratory Platform

**Document Version:** 2.0.0  
**Domain:** Asynchronous Request Pipelines, Full-Duplex WebSockets & Compute Scheduling  
**Academic Target:** Systems Engineering & Codebase Walkthrough  

---

## 1. End-to-End Execution Lifecycle

When a user submits code for execution from the web browser, the system executes an asynchronous, decoupled 10-step sequence:

```
Browser               FastAPI Gateway          Redis Queue            Celery Worker         Docker/Micro-VM Sandbox
   │                         │                      │                       │                           │
   │─── 1. POST /submission ─▶│                      │                       │                           │
   │    (code, lang, stdin)  │                      │                       │                           │
   │                         │─── 2. Validate & ───▶│                       │                           │
   │                         │    Push Job (ZSET)   │                       │                           │
   │◀── 3. 202 Accepted ─────│                      │                       │                           │
   │    (submission_id)      │                      │                       │                           │
   │                         │                      │                       │                           │
   │─── 4. Open WebSocket ──▶│                      │                       │                           │
   │    /ws/v1/submissions   │                      │                       │                           │
   │                         │── 5. Subscribe ─────▶│                       │                           │
   │                         │   rce:stream:<id>    │                       │                           │
   │                         │                      │                       │                           │
   │                         │                      │◀─── 6. Dequeue Job ───│                           │
   │                         │                      │                       │─── 7. Initialize ────────▶│
   │                         │                      │                       │    Sandbox & Watchdog     │
   │                         │                      │                       │                           │
   │                         │                      │◀── 8. Stream Chunk ───│◀── Stdout/Stderr ─────────│
   │                         │◀── 9. Pub/Sub Frame ─│   (Monotonic Seq)     │    (Watchdog Guarded)     │
   │◀── 10. WebSocket Frame ─│                      │                       │                           │
   │    (Render in xterm.js) │                      │                       │─── 11. Cleanup & Reaping ─▶│
```

---

## 2. Deep Dive: Architectural Subsystems

### 2.1 Ingestion & Distributed Rate Limiting
- **Endpoint:** `POST /api/v1/submissions`
- **Component:** `backend/app/api/v1/endpoints/submissions.py` & `backend/app/services/rate_limiter.py`
- **Mechanism:**
  1. The incoming JSON payload is validated using Pydantic v2 schemas (`SubmissionCreate`).
  2. The user's JWT identity is extracted and verified.
  3. The request passes through an atomic **Sliding Window Log Rate Limiter** implemented in Redis (`ZSET`). Expired timestamps older than 60 seconds are purged with `ZREMRANGEBYSCORE`, and the current count is evaluated in a single round-trip pipeline. If the quota is exceeded, the request immediately terminates with `HTTP 429 Too Many Requests` and a compliant `Retry-After` header.
  4. A new record is persisted in PostgreSQL with status `PENDING`.
  5. The task payload—injected with W3C `traceparent` distributed tracing headers—is enqueued onto Celery's Redis broker. The API immediately responds with `HTTP 202 Accepted` and the generated `submission_id`.

### 2.2 Full-Duplex Bidirectional WebSocket Hub
- **Endpoint:** `/ws/v1/submissions/{submission_id}`
- **Component:** `backend/app/api/v1/endpoints/websocket.py`
- **Mechanism:**
  1. The client establishes a persistent WebSocket connection authenticated via JWT query parameter or header.
  2. The endpoint initializes two concurrent asynchronous coroutines:
     - **`downstream_pump`**: Subscribes to Redis Pub/Sub channel `rce:stream:<submission_id>` and checks the circular replay buffer (`rce:buffer:<submission_id>`). Any frames emitted while the client was handshaking are replayed gaplessly before streaming live worker output to the client.
     - **`upstream_pump`**: Concurrently listens for client WebSocket messages (`input` keystrokes, `resize` events with rows/cols, and `signal` interruptions like `SIGINT`). Upstream payloads are published to Redis channel `rce:input:<submission_id>`.

### 2.3 Worker Dequeue & Pluggable Sandbox Instantiation
- **Component:** `worker/tasks/execution.py` & `worker/sandbox/factory.py`
- **Mechanism:**
  1. The Celery worker pulls the task from the Redis FIFO queue.
  2. The worker extracts the W3C `traceparent` carrier and creates an OpenTelemetry child span (`rce.worker.sandbox_execution`).
  3. The `SandboxFactory` evaluates available system drivers (`SandboxDriverType.AUTO`):
     - Checks if `/dev/kvm` exists and is writable $\rightarrow$ Selects `MicroVMSandbox`.
     - Checks if the Docker daemon socket is responsive $\rightarrow$ Selects `DockerSandbox`.
     - Otherwise $\rightarrow$ Gracefully falls back to `ProcessSandbox`.
  4. The code and input files are written into a transient sandbox directory.

### 2.4 Execution, Multiplexing & Watchdog Supervisor
- **Component:** `worker/streaming/multiplexer.py` & `worker/sandbox/pty_session.py`
- **Mechanism:**
  1. A background watchdog timer starts with the configured execution timeout (default: 5.0 seconds).
  2. If the runtime is polyglot (C, C++, Rust, Go), the worker executes **Stage 1 (Compilation)** inside the sandbox with defensive flags (`-fstack-protector-strong`, `-fPIE -pie`, `-Wl,-z,relro,-z,now`). Compilation diagnostics are streamed directly.
  3. The worker begins **Stage 2 (Execution)**:
     - In interactive mode, a POSIX PTY session (`pty.openpty()`) is attached to capture terminal line discipline (`ONLCR`) and forward window resize events (`TIOCSWINSZ`).
     - In standard mode, stdout and stderr streams are consumed asynchronously.
  4. Every stream chunk is wrapped in a structured JSON envelope, assigned a strictly monotonic sequence number (`seq`), and published to Redis Pub/Sub while simultaneously appending to the 60s circular buffer.
  5. If total output exceeds **1 MB** or **10,000 lines**, the multiplexer truncates the stream and emits `OUTPUT_LIMIT_EXCEEDED` (OLE).
  6. If the execution exceeds 5.0 seconds, the watchdog fires `SIGKILL` on the container or guest VM, categorizing the result as `TIME_LIMIT_EXCEEDED` (TLE).

### 2.5 Teardown, Database Finalization & Janitor Reaper
- **Component:** `worker/daemon.py`
- **Mechanism:**
  1. The sandbox container or Micro-VM is stopped and unmounted.
  2. The worker inspects the exit code and memory metrics. If `OOMKilled == True`, the status is finalized as `MEMORY_LIMIT_EXCEEDED` (MLE).
  3. Final execution metrics (execution duration in milliseconds, memory in kilobytes, exit code, and final status) are committed to PostgreSQL.
  4. An independent background `JanitorDaemon` periodically scans Docker Engine for any orphan containers surviving worker crashes older than 300 seconds, issuing force-reap commands (`docker rm -f`) to prevent resource leaks.
