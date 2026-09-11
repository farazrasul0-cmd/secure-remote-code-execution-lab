# Secure Real-Time Remote Code Execution Laboratory Platform

A distributed, multi-tenant remote code execution platform and virtual computer lab engineered with operating system virtualization primitives, asynchronous task distribution, and low-latency real-time standard I/O streaming.

Developed as a Master's portfolio project demonstrating graduate-level systems knowledge across **Operating Systems**, **Distributed Systems**, **Networking**, **Cybersecurity**, and **Cloud Infrastructure**.

---

## 1. Key Architectural Features

- **In-Browser IDE & Terminal:** Interactive code editor (Monaco Editor) paired with an ANSI terminal (xterm.js) delivering desktop-grade editing and terminal output.
- **Full-Duplex Real-Time Streaming:** Sub-second output streaming using WebSockets multiplexed over a high-throughput Redis Pub/Sub bus.
- **Decoupled Asynchronous Processing:** FastAPI gateway buffers execution requests into Redis queues, completely isolating web threads from compute workloads.
- **Zero-Trust Hardened Sandbox:** Docker containers hardened with Linux cgroups v2 resource controllers, unprivileged user namespaces (`uid=1001`), read-only root filesystems, dropped capabilities (`CAP_DROP ALL`), restricted Seccomp syscall profiles, and strict network isolation (`--net=none`).
- **Telemetry & Historical Persistence:** PostgreSQL database recording execution runtimes, peak memory usage, exit codes, and audit logs.

---

## 2. Measurable Engineering Goals & Operational Limits

| Parameter | Target Limit | Enforcement Mechanism | Failure Status Code |
| :--- | :--- | :--- | :--- |
| **Execution Timeout** | **5.0 seconds** (configurable max 15.0s) | Worker watchdog timer + POSIX `SIGKILL` | `TIME_LIMIT_EXCEEDED` (TLE) |
| **CPU Allocation** | **0.5 CPU Core** (50% CFS scheduler quota) | Linux cgroups v2 (`cpu.max`) | Throttled / `TIME_LIMIT_EXCEEDED` |
| **Memory Ceiling** | **128 MB** (v1 hard limit, swap disabled) | Linux cgroups v2 (`memory.max`) | Kernel OOM Killer $\rightarrow$ `MEMORY_LIMIT_EXCEEDED` (MLE) |
| **Process / Thread Limit** | **64 PIDs** per sandbox | Linux cgroups v2 (`pids.max`) | Prevents Fork Bombs (`EAGAIN`) |
| **Output Buffer Cap** | **1 MB** (or 10,000 lines) | Worker stream consumer byte counter | `OUTPUT_LIMIT_EXCEEDED` (OLE) |
| **Streaming Rate** | Max **50 KB/s** burst rate | Token bucket rate limiter | Stream throttled / Backpressure |
| **Concurrency Target** | $\ge \mathbf{50}$ concurrent active streams / node | Horizontal worker scaling via Celery | FIFO queued in Redis buffer |

---

## 3. Minimum Viable Product (MVP) Scope — Version 1.0

The Version 1.0 milestone delivers a complete, verifiable end-to-end implementation:
- **Language Support:** **Python 3.11** execution only.
- **User Authentication:** JWT access & refresh tokens (Argon2id password hashing) with Role-Based Access Control (`Student`, `Admin`).
- **Code Submission:** Web-based submission interface with Monaco Editor and optional standard input (`stdin`) configuration.
- **Sandbox Execution:** Hardened, unprivileged ephemeral Docker container with cgroup v2 limits, read-only rootfs, and memory-backed `tmpfs`.
- **WebSocket Output:** Real-time bi-directional streaming from worker to browser via Redis Pub/Sub and FastAPI WebSockets.
- **Execution History:** PostgreSQL persistence of past submissions, execution metrics (duration, memory, exit code), and execution logs.

---

## 4. High-Level Architecture

```
[ Client: React + Monaco + xterm.js ]
                │ ▲
   HTTP (REST)  │ │ WebSockets (Live I/O)
                ▼ │
    [ API Gateway: FastAPI ]
          │             ▲
 Enqueues │             │ Subscribes (Pub/Sub Stream)
          ▼             │
 [ Broker: Redis Queue ]│
          │             │
Pulls Job │             │
          ▼             │
  [ Worker: Celery / Daemon ]
          │             │
   Spawns │             │ Streams stdout/stderr
          ▼             │
 [ Sandbox Container (cgroups v2, seccomp, net=none, tmpfs) ]
```

---

## 5. Technology Stack

- **Frontend:** React 18, TypeScript, Monaco Editor, xterm.js, TailwindCSS, Vite.
- **Backend API:** FastAPI (Python 3.11, ASGI, Pydantic v2, SQLAlchemy 2.0 async).
- **Database:** PostgreSQL 15+ (with native JSONB telemetry and Alembic migrations).
- **Queue & Real-Time Bus:** Redis 7+ (FIFO task queue + Pub/Sub streaming channel).
- **Execution Workers:** Celery / Async Python Worker Daemon.
- **Sandbox Isolation:** Docker Engine (OCI Runtime, cgroups v2, Seccomp-BPF filters, Linux Namespaces).

---

## 6. Comprehensive Documentation Index

All architectural specifications, designs, and setup guides are available in the [`documentation/`](documentation/) directory:

- [01. Project Overview](documentation/01_PROJECT_OVERVIEW.md)
- [02. System Architecture](documentation/02_SYSTEM_ARCHITECTURE.md)
- [03. File Structure](documentation/03_FILE_STRUCTURE.md)
- [04. Database Design](documentation/04_DATABASE_DESIGN.md)
- [05. API Documentation](documentation/05_API_DOCUMENTATION.md)
- [06. Security Design](documentation/06_SECURITY_DESIGN.md)
- [07. Execution Engine](documentation/07_EXECUTION_ENGINE.md)
- [08. Distributed System Design](documentation/08_DISTRIBUTED_SYSTEM_DESIGN.md)
- [09. Deployment Guide](documentation/09_DEPLOYMENT_GUIDE.md)
- [10. Testing Strategy](documentation/10_TESTING_STRATEGY.md)
- [11. Learning Notes](documentation/11_LEARNING_NOTES.md)
- [12. Future Improvements](documentation/12_FUTURE_IMPROVEMENTS.md)
- [13. Requirements Specification](documentation/13_REQUIREMENTS_SPECIFICATION.md)
- [14. Architecture Decision Records (ADRs)](documentation/14_ARCHITECTURE_DECISION_RECORDS.md)
- [15. Development Setup Guide](documentation/15_DEVELOPMENT_SETUP.md)
- [16. User & Operational Guide](documentation/16_USER_GUIDE.md)
- [17. Research & Evaluation Plan](documentation/17_RESEARCH_AND_EVALUATION_PLAN.md)
- [18. Security Threat Model (STRIDE)](documentation/18_THREAT_MODEL.md)
- [19. System Design Decisions](documentation/19_SYSTEM_DESIGN_DECISIONS.md)
