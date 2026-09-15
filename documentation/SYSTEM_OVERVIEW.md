# System Overview & Architecture Topology
## Secure Real-Time Remote Code Execution Laboratory Platform

**Document Version:** 2.0.0  
**Domain:** Distributed Systems, Cloud Architecture & OS Sandboxing  
**Academic Target:** Master's Portfolio Systems Overview  

---

## 1. Abstract & Problem Statement

Modern computer science education and technical assessments demand interactive code execution in a web browser. However, providing multi-tenant access to execute arbitrary user-submitted code creates an acute security and systems challenge:
1. **Adversarial Exploitation:** Untrusted code may attempt fork bombs (`while(1) fork()`), memory exhaustion bombs, local privilege escalation, network scanning (SSRF), or persistent host file tampering.
2. **Interactive Low-Latency Requirement:** Users require sub-second terminal feedback, bidirectional keystrokes (`stdin`), window resizing (`TIOCSWINSZ`), and POSIX signal handling (`SIGINT` on `Ctrl+C`).
3. **Bursty Concurrency:** Classrooms and examinations introduce massive, synchronized submission spikes that can easily exhaust server thread pools and induce cascading outages.

The **Secure Real-Time Remote Code Execution Laboratory Platform** resolves these tensions by combining low-level Linux operating system virtualization primitives, an asynchronous decoupled distributed broker architecture, full-duplex WebSockets, and cloud-native Kubernetes orchestration.

---

## 2. High-Level System Topology

The platform decomposes into five distinct, horizontally decoupled subsystems:

```
[ In-Browser Client ]
(React 18 + Monaco Editor + xterm.js + TypeScript)
        │ ▲
   REST │ │ WebSockets (RFC 6455 Full-Duplex)
        ▼ │
┌─────────────────────────────────────────────────────────────────┐
│ Ingress & API Gateway Layer (FastAPI ASGI + Uvicorn)            │
│ • JWT Authentication (Argon2id) & Role-Based Access Control     │
│ • Sliding Window Rate Limiting via Redis Sorted Sets (ZSET)     │
│ • Submission Ingestion & Validation (Pydantic v2)               │
│ • Distributed Tracing Injection (W3C traceparent header)        │
└───────────────┬─────────────────────────────────▲───────────────┘
                │                                 │
     Task Push  │ (Async Celery Queue)            │ Subscribes (rce:stream:<id>)
                ▼                                 │ Broadcasts (rce:room:exec)
┌─────────────────────────────────────────────────┴───────────────┐
│ Distributed Message Backplane & Cache (Redis 7)                 │
│ • FIFO Task Queue (submissions_queue)                           │
│ • Real-Time Pub/Sub Streaming Bus (stdout/stderr chunks)        │
│ • Circular Replay Buffer (60s TTL, Monotonic Sequence IDs)      │
│ • Collaborative Delta Channels (rce:room:sync:<room_id>)        │
└───────────────┬─────────────────────────────────────────────────┘
                │
     Task Pull  │ (Worker Concurrency: Little's Law)
                ▼
┌─────────────────────────────────────────────────────────────────┐
│ Compute Execution Worker Tier (Celery + Async Worker Daemon)   │
│ • Watchdog Supervisor Timer (POSIX SIGKILL timeout)             │
│ • Two-Phase Polyglot Compiler (Compile vs. Execute isolation)   │
│ • Upstream Input Consumer (stdin keystrokes, resize, signals)   │
│ • Stream Multiplexer with Output Capping (1 MB / 10,000 lines)  │
└───────────────┬─────────────────────────────────────────────────┘
                │
                ├───────────────────────┬─────────────────────────┐
                ▼                       ▼                         ▼
    ┌───────────────────────┐ ┌───────────────────┐ ┌───────────────────┐
    │ Docker Container      │ │ Micro-VM (KVM)    │ │ Local Process     │
    │ Sandbox               │ │ Sandbox           │ │ Sandbox           │
    │ • cgroups v2 quotas   │ │ • Hardware hyper- │ │ • POSIX PTY pipe  │
    │ • Seccomp-BPF filters │ │   visor boundary  │ │ • Non-POSIX fall- │
    │ • net=none isolation  │ │ • Sub-5ms boot    │ │   back            │
    │ • tmpfs RAM disk      │ │ • Ring -1 isolat. │ │ • Unit test mock  │
    └───────────────────────┘ └───────────────────┘ └───────────────────┘
```

---

## 3. Subsystem Descriptions

### 3.1 Frontend Web IDE (`frontend/`)
- **Monaco Editor Integration:** Embedded VS Code editor engine supporting syntax highlighting, error squiggles, and pre-populated starter templates for 6 programming languages (Python 3.12, C17, C++20, Rust 2021, Go 1.22, Node.js 20).
- **Interactive xterm.js Terminal:** Hardware-accelerated ANSI terminal emulator supporting bidirectional standard I/O, cursor blinking, VT100 control codes, dynamic window geometry negotiation, and out-of-band `Ctrl+C` interrupt signals.
- **Algorithmic Problem Catalog & Scorecard:** LeetCode-style challenge interface displaying problem descriptions, difficulty ratings, sample test cases, and multi-test execution scorecards.
- **Collaborative Coding UI:** Multi-user collaborative pair programming with real-time peer cursor indicators, shared code editing, and simultaneous terminal execution streaming.

### 3.2 API Gateway & Orchestration Layer (`backend/`)
- **FastAPI ASGI Framework:** Fully asynchronous event loop capable of maintaining tens of thousands of idle and streaming WebSocket connections with negligible thread overhead.
- **Relational Persistence (PostgreSQL 16):** Database models for users, submissions, execution logs, problems, test cases, and collaborative rooms with Alembic async migrations.
- **Distributed Rate Limiting:** Atomic sliding-window rate limiting implemented with Redis Sorted Sets (`ZSET`) to eliminate boundary burst attacks.
- **Dual-Channel WebSocket Hub:** Concurrent downstream/upstream multiplexing forwarding live execution logs to clients while routing interactive keystrokes to compute workers.

### 3.3 Asynchronous Queue & Distributed Backplane (`Redis 7`)
- **Decoupled Job Queue:** Buffers burst submissions during peak traffic hours, protecting compute workers from resource exhaustion and thrashing.
- **Pub/Sub Real-Time Bus:** Zero-overhead, sub-millisecond message transport connecting compute workers to API WebSocket instances across distributed Kubernetes nodes.
- **Circular Replay Buffers:** In-memory Redis list structures storing monotonic sequence frames with 60-second TTLs, allowing reconnecting clients to replay dropped frames without data loss.

### 3.4 Worker Execution Engine (`worker/`)
- **Pluggable Sandbox Abstraction:** Unified `BaseSandbox` interface instantiated dynamically via `SandboxFactory` with runtime capability negotiation (`ProcessSandbox`, `DockerSandbox`, `MicroVMSandbox`).
- **Two-Phase Compilation Engine:** Asymmetric compilation model that separates compiler diagnostics (Stage 1) from binary execution (Stage 2), capturing compiler errors without consuming runtime timeout allowances.
- **Interactive PTY Session Manager:** Low-level POSIX pseudo-terminal allocation (`pty.openpty()`) with non-blocking I/O, terminal line discipline (`termios.ONLCR`), dynamic window geometry packing (`TIOCSWINSZ`), and signal dispatching (`SIGINT`).
- **Autograding Verification Engine:** Algorithmic verification harness with multi-mode comparison (`NORMALIZED`, `STRICT`, `TOKEN`, `EPSILON`), timing constraints, and cryptographically scrubbed hidden test vectors.

---

## 4. Key Performance & Operational Envelope

| Dimension | Standard Specification | Enforcement Mechanism |
| :--- | :--- | :--- |
| **Max Wall-Clock Duration** | 5.0 seconds (configurable) | Asynchronous watchdog supervisor + POSIX `SIGKILL` |
| **CPU Bandwidth** | 0.5 Cores (50% CFS quota) | Linux cgroups v2 (`cpu.max="50000 100000"`) |
| **Memory Ceiling** | 128 MB (Swap suppressed) | Linux cgroups v2 (`memory.max="128m"`, `memory.swap.max=0`) |
| **Process / Thread Cap** | 64 Tasks | Linux cgroups v2 (`pids.max=64`) |
| **Network Egress** | Zero bytes (Air-gapped) | Linux Network Namespace (`--net=none`) + K8s NetworkPolicies |
| **Output Buffer Cap** | 1 MB / 10,000 lines | Worker stream consumer byte counter |
| **Worker Autoscaling** | 2 to 20 replicas | Kubernetes HPA v2 scaled on custom metric `rce_worker_queue_depth` |
