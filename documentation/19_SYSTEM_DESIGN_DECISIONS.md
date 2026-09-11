# System Design Decisions & Technical Architecture
## Secure Real-Time Remote Code Execution Laboratory Platform

**Document Version:** 1.0.0  
**Scope:** Architectural Patterns, Component Interaction, and Design Rationale  

---

## 1. Decoupling of Ingestion and Execution

```
[ Client ] ──(HTTP POST)──> [ FastAPI Gateway ] ──(LPUSH)──> [ Redis Queue ]
                                                                   │
                                                                   ▼ (BRPOP)
                                                         [ Worker Daemon ]
                                                                   │
                                                                   ▼ (docker run)
                                                         [ Sandboxed Container ]
```

### 1.1 The Web Thread Starvation Problem
In naive web architectures, code execution requests are processed synchronously within the web server's request-response lifecycle. For an RCE platform, this approach has fatal architectural consequences:
- **Event Loop Blocking:** Code execution is long-running (100ms to 15,000ms). Holding an ASGI worker thread blocks concurrent I/O operations.
- **Cascading Failure:** During class assignment submission deadlines, 200 simultaneous submissions immediately exhaust available web worker threads, driving HTTP 504 Gateway Timeouts for all users.
- **Resource Contention:** Heavy compilation and execution directly compete with the web server for CPU cycles and memory.

### 1.2 The Producer-Consumer Solution
We implement an asynchronous **Producer-Consumer Architecture** mediated by Redis:
1. **The Ingress Producer (FastAPI):** Accepts the HTTP/WebSocket submission, verifies authentication, validates the payload schema (max 64KB), writes a `PENDING` record to PostgreSQL, pushes a message onto a Redis list (`queue:submissions`), and immediately returns HTTP 202 (Accepted) with the `submission_id`.
2. **The Buffer (Redis Queue):** Serves as a shock absorber for burst traffic. Jobs wait safely in memory without consuming CPU compute resources.
3. **The Consumer (Worker Pool):** Autonomous worker processes pull jobs from the queue via non-blocking or blocking reads (`BRPOP`). Workers scale horizontally across independent nodes based on queue depth metrics.

---

## 2. Real-Time Stream Multiplexing Architecture

Providing a desktop-grade IDE experience requires live terminal streaming rather than delayed batch returns.

```
┌────────────────────────────────────────────────────────────────────────┐
│                              Worker Node                               │
│  [ Sandbox stdout/stderr ] ──> [ Stream Consumer ] ──(Publish Chunk)──┐│
└───────────────────────────────────────────────────────────────────────┼┘
                                                                        ▼
                                                       [ Redis Pub/Sub: exec:{id} ]
                                                                        │
┌───────────────────────────────────────────────────────────────────────┼┐
│                           FastAPI Gateway                             ││
│  [ Client Terminal (xterm.js) ] <──(WebSocket Frame)── [ Subscriber ] ◄┘│
└────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Stream Pipeline Design
1. **Container I/O Capture:** The worker process attaches to the container's standard output and standard error streams using non-blocking I/O pipes.
2. **Chunk Framing:** The worker reads byte chunks (buffer size: 1024 bytes) and wraps them in a structured JSON payload:
   ```json
   {
     "event": "stdout",
     "data": "Hello World\n",
     "timestamp": 1726054800123
   }
   ```
3. **Pub/Sub Brokerage:** The worker publishes the frame to a dynamic Redis Pub/Sub channel: `exec:<submission_id>`.
4. **WebSocket Fan-Out:** The FastAPI gateway, maintaining an active WebSocket session with the client, is subscribed to `exec:<submission_id>`. It immediately relays received frames across the WebSocket connection without persistent storage overhead.
5. **Client Terminal Emulation:** The browser frontend pipes received text chunks directly into an `xterm.js` instance, which interprets ANSI formatting, colors, and carriage returns in real time.

### 2.2 Control Signal Protocol
The streaming protocol defines explicit control events:
- `SYSTEM_INIT`: Worker initialized sandbox environment.
- `STDOUT`: Standard output chunk.
- `STDERR`: Standard error chunk.
- `EXECUTION_COMPLETE`: Program terminated; payload includes exit code, duration (ms), and peak memory (bytes).
- `EXECUTION_ERROR`: Kernel or sandbox abort (e.g., TLE, MLE, OLE).

---

## 3. Stateless Gateway & Connection Topology

### 3.1 Eliminating Server Affinity (Sticky Sessions)
In distributed cloud deployments, client connections may be routed to any healthy FastAPI gateway instance behind an Application Load Balancer (ALB).
- By utilizing **Redis Pub/Sub** as an intermediary message bus, any API instance can service the WebSocket connection regardless of which physical worker node is executing the sandbox container.
- Neither the API gateway nor the worker requires local state about the other. All correlation is decoupled through the unique `submission_id`.

### 3.2 Reconnection & Stream Resilience
If a transient network disconnect interrupts the client's WebSocket connection:
1. Output chunks are concurrently appended to a bounded Redis list (`stream_buffer:<submission_id>`) with a 60-second Time-To-Live (TTL).
2. Upon reconnecting, the client supplies the last received chunk sequence number.
3. The gateway flushes missed chunks from the buffer before resuming the live Pub/Sub stream, guaranteeing zero lost output.

---

## 4. Sandbox Lifecycle & Ephemeral Cleanliness

```
[ Uninitialized ]
       │
       ▼ (docker create + cgroups)
  [ CREATED ]
       │
       ▼ (docker start + tmpfs mount)
  [ RUNNING ] ───(Watchdog Timer / OOM Trigger)───┐
       │                                          │
       ▼ (Process Exit / SIGTERM)                 ▼ (SIGKILL)
  [ TERMINATED ]                            [ ABORTED ]
       │                                          │
       └──────────────────┬───────────────────────┘
                          │
                          ▼ (docker rm -v --force)
                      [ PURGED ]
```

### 4.1 Zero Disk Persistence Principle
To prevent data contamination, disk exhaustion, or cross-tenant information leakage:
- Containers run with an immutable, read-only root filesystem (`--read-only`).
- User source code is written to an in-memory `tmpfs` RAM disk mounted at `/tmp`.
- No files are ever written to the host server's physical drive.
- When the container terminates, the `tmpfs` mount and all its contents are instantly dissolved from host RAM.

### 4.2 The Orphan Reaper / Janitor Daemon
In distributed architectures, worker nodes may fail, power off, or be forcefully restarted while sandbox containers are active. To prevent "zombie" containers from leaking host resources:
- Every container is spawned with an explicit metadata label: `created_at=<timestamp>` and `max_lease_seconds=30`.
- An autonomous supervisor daemon (`JanitorDaemon`) executes every 30 seconds:
  ```bash
  docker ps --filter "label=sandbox_type=isolated"
  ```
  Any container whose active duration exceeds its `max_lease_seconds` is forcefully killed (`SIGKILL`) and pruned (`docker rm -f`).

---

## 5. Database Schema & High-Write Optimization

### 5.1 Relational Schema Architecture (PostgreSQL)

```sql
-- Core User Identity & Role
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'student',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Submission Records & Execution Metadata
CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    language VARCHAR(30) NOT NULL,
    source_code TEXT NOT NULL,
    stdin_data TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    exit_code INTEGER,
    execution_time_ms INTEGER,
    peak_memory_bytes BIGINT,
    telemetry JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Indexing Strategy
CREATE INDEX idx_submissions_user_created ON submissions(user_id, created_at DESC);
CREATE INDEX idx_submissions_status ON submissions(status);
CREATE INDEX idx_submissions_telemetry_gin ON submissions USING GIN (telemetry);
```

### 5.2 Write Separation: Telemetry vs. Terminal Logs
A common pitfall is storing streaming terminal output line-by-line as database rows. This generates thousands of database writes per execution, locking tables and exhausting database connection pools.
- **Architectural Separation:**
  - Real-time terminal output is streamed via **Redis Pub/Sub** and stored temporarily in an in-memory Redis buffer with a short TTL.
  - PostgreSQL only receives **one single row insert** (`PENDING`) upon submission and **one row update** upon execution completion (recording final status, wall-clock runtime, memory usage, and truncated output summary).
  - This preserves database throughput and scales linearly with user load.
