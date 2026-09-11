# Project Overview
## Secure Real-Time Remote Code Execution Laboratory Platform

**Document Version:** 1.0.0  
**Status:** Active  

---

## 1. Project Vision

The **Secure Real-Time Remote Code Execution Laboratory Platform** is a distributed, multi-tenant computing system engineered to provide isolated, browser-accessible programming environments. It allows educational institutions, instructors, and students to compile, execute, and monitor arbitrary user-submitted code in real time without local toolchain installation.

The platform is designed specifically as a graduate-level portfolio project demonstrating mastery of:
- **Operating Systems:** Process lifecycle management, Linux namespaces, cgroups v2 resource controllers, and Seccomp syscall filtering.
- **Distributed Systems:** Asynchronous message queue decoupling, horizontal worker scaling, and low-latency stream multiplexing.
- **Networking:** Full-duplex WebSocket connections, stream chunk framing, and network namespace isolation (`--net=none`).
- **Cybersecurity:** Zero-trust defense-in-depth, least-privilege containerization, and STRIDE threat mitigation.
- **Backend Engineering:** Asynchronous ASGI web architecture (FastAPI), connection pooling, and ACID-compliant relational persistence (PostgreSQL).

---

## 2. Minimum Viable Product (MVP) Scope — Version 1.0

- **Language Runtime:** Python 3.11 execution only.
- **User Authentication:** JWT Bearer authentication with role-based access control (`Student`, `Admin`).
- **Code Submission:** Web-based code editor (Monaco Editor) with standard input (`stdin`) configuration.
- **Sandbox Execution:** Hardened, unprivileged ephemeral Docker container with cgroup v2 limits, read-only rootfs, and memory-backed `tmpfs`.
- **WebSocket Output:** Real-time bi-directional streaming from worker to browser via Redis Pub/Sub and FastAPI WebSockets.
- **Execution History:** PostgreSQL persistence of past submissions, execution metrics (duration, memory, exit code), and execution logs.

---

## 3. Measurable Engineering Goals & Operational Limits

| Parameter | Target Limit | Enforcement Mechanism | Failure Status Code |
| :--- | :--- | :--- | :--- |
| **Execution Timeout** | **5.0 seconds** (configurable max 15.0s) | Worker watchdog timer + POSIX `SIGKILL` | `TIME_LIMIT_EXCEEDED` (TLE) |
| **CPU Allocation** | **0.5 CPU Core** (50% CFS scheduler quota) | Linux cgroups v2 (`cpu.max`) | Throttled / `TIME_LIMIT_EXCEEDED` |
| **Memory Ceiling** | **128 MB** (v1 hard limit, swap disabled) | Linux cgroups v2 (`memory.max`) | Kernel OOM Killer $\rightarrow$ `MEMORY_LIMIT_EXCEEDED` (MLE) |
| **Process / Thread Limit** | **64 PIDs** per sandbox | Linux cgroups v2 (`pids.max`) | Prevents Fork Bombs (`EAGAIN`) |
| **Output Buffer Cap** | **1 MB** (or 10,000 lines) | Worker stream consumer byte counter | `OUTPUT_LIMIT_EXCEEDED` (OLE) |
| **Streaming Rate** | Max **50 KB/s** burst rate | Token bucket rate limiter | Stream throttled / Backpressure |
| **Concurrency Target** | $\ge \mathbf{50}$ concurrent active streams / node | Horizontal worker scaling via Celery | FIFO queued in Redis buffer |
