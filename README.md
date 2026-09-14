# Secure Real-Time Remote Code Execution Laboratory Platform

[![CI Pipeline](https://github.com/farazrasul0-cmd/secure-remote-code-execution-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/farazrasul0-cmd/secure-remote-code-execution-lab/actions)
[![Security Scan](https://github.com/farazrasul0-cmd/secure-remote-code-execution-lab/actions/workflows/security-scan.yml/badge.svg)](https://github.com/farazrasul0-cmd/secure-remote-code-execution-lab/actions)
[![Release](https://img.shields.io/badge/release-v2.0.0-blue.svg)](https://github.com/farazrasul0-cmd/secure-remote-code-execution-lab/releases)
[![Tests](https://img.shields.io/badge/tests-88%20passed-brightgreen.svg)]()
[![Kubernetes](https://img.shields.io/badge/kubernetes-v1.30-326ce5.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)]()

A distributed, multi-tenant remote code execution platform and virtual computer lab engineered with operating system virtualization primitives, asynchronous task distribution, and low-latency real-time standard I/O streaming.

Graduated to **v2.0.0 Production Release** as a Master's portfolio project demonstrating graduate-level systems knowledge across **Operating Systems**, **Distributed Systems**, **Networking**, **Cybersecurity**, and **Cloud Infrastructure**.

---

## 1. Key Architectural Features

- **Polyglot Multi-Language Sandbox:** Pluggable execution engine supporting Python 3.12, C17 (GCC 14), C++20 (G++ 14), Rust 2021, Go 1.22, and Node.js 20 with hardened compiler sanitizers (`-fstack-protector-strong`, PIE, RELRO).
- **Interactive PTY Pseudo-Terminal:** Low-level POSIX PTY allocation with dynamic window resizing (`TIOCSWINSZ`), upstream keystroke streaming, and out-of-band `Ctrl+C` (`SIGINT`) signal handling.
- **Micro-VM & Hardware Virtualization Drivers:** Pluggable sandbox hierarchy (`ProcessSandbox`, `DockerSandbox`, `MicroVMSandbox`) with automated host KVM capability probing and benchmarking harness.
- **Automated Algorithmic Autograding:** Automated problem verification engine with floating-point epsilon matching, strict/token normalization, and cryptographically hidden oracle test vectors.
- **Collaborative Coding Rooms:** Multi-user collaborative pair-programming rooms with dual-channel WebSocket multiplexing (`rce:room:sync` for document deltas and `rce:room:exec` for live output broadcasts).
- **Distributed Observability:** OpenTelemetry W3C `traceparent` context propagation across Redis and Celery queues for end-to-end distributed tracing.
- **Cloud-Native Kubernetes & GitOps:** Production Helm chart (`helm/rce-platform/`) with PodSecurityStandards Restricted enforcement, Zero-Trust NetworkPolicies, Celery queue-depth HPA autoscaling, automated PostgreSQL disaster recovery backups, and Prometheus alerting rules.
- **GitHub Actions CI/CD Pipeline:** Multi-job automated verification enforcing Ruff linting, 100% Pytest pass rates, TypeScript typechecking, Trivy vulnerability scanning, and multi-service GHCR publishing.

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

## 3. Platform Evolution Milestones

- **v1.0.0 (MVP):** Single-tenant Python container runner, FastAPI gateway, and xterm.js streaming.
- **v1.1.0 (Polyglot):** 6-language compilation engine with defense-in-depth compiler hardening.
- **v1.2.0 (Autograding):** LeetCode-style autograding engine with hidden test cases and scorecards.
- **v1.3.0 (Interactive PTY):** True bidirectional PTY pseudo-terminal with signals and window geometry.
- **v1.4.0 (Kubernetes):** Helm charts, PodSecurityStandards Restricted, and Queue-Depth HPA.
- **v1.5.0 (Resilience & Micro-VM):** AWS Firecracker-style micro-VM drivers, OpenTelemetry tracing, collaborative rooms, and Chaos Engineering fault tolerance.
- **v2.0.0 (Production Release):** GitHub Actions CI/CD GitOps pipelines, Trivy security scanning, automated database disaster recovery backups, Prometheus declarative alerting, and GHCR container publishing.

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
