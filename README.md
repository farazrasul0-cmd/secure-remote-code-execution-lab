# Secure Real-Time Remote Code Execution Laboratory Platform

[![CI Pipeline](https://github.com/farazrasul0-cmd/secure-remote-code-execution-lab/actions/workflows/ci.yml/badge.svg)](https://github.com/farazrasul0-cmd/secure-remote-code-execution-lab/actions)
[![Security Scan](https://github.com/farazrasul0-cmd/secure-remote-code-execution-lab/actions/workflows/security-scan.yml/badge.svg)](https://github.com/farazrasul0-cmd/secure-remote-code-execution-lab/actions)
[![Release](https://img.shields.io/badge/release-v2.0.0-blue.svg)](https://github.com/farazrasul0-cmd/secure-remote-code-execution-lab/releases)
[![Tests](https://img.shields.io/badge/tests-88%20passed-brightgreen.svg)]()
[![Kubernetes](https://img.shields.io/badge/kubernetes-v1.30-326ce5.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)]()
[![Code Style](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

A distributed, multi-tenant remote code execution platform and virtual computer lab engineered with operating system virtualization primitives, asynchronous task distribution, and low-latency real-time standard I/O streaming.

Graduated to **v2.0.0 Production Release** as a Master's portfolio project demonstrating graduate-level systems knowledge across **Operating Systems**, **Distributed Systems**, **Networking**, **Cybersecurity**, and **Cloud Infrastructure**.

---

## 🌟 Key Highlights & Systems Innovations

- **🛡️ 6-Layer Concentric Security Perimeter:** Combines Linux cgroups v2 resource quotas (`cpu.max`, `memory.max`, `pids.max=64`), unprivileged user namespaces (`uid=1001`), read-only root filesystems, air-gapped network namespaces (`--net=none`), and custom Seccomp-BPF filters blocking ~350 dangerous syscalls.
- **⚡ Pluggable Hardware-Assisted Micro-VMs:** AWS Firecracker-style `MicroVMSandbox` leveraging Linux KVM (`/dev/kvm`) to execute untrusted code inside a hardware-isolated guest kernel with **sub-5ms cold startup latency** (50x faster than traditional containers).
- **🖥️ Bidirectional Interactive Pseudo-Terminal (PTY):** Low-level POSIX PTY allocation (`pty.openpty()`) integrated with `xterm.js` and Monaco Editor, supporting character-by-character standard input, dynamic terminal window resizing (`TIOCSWINSZ`), and out-of-band `Ctrl+C` (`SIGINT`) signal handling.
- **🔄 Decoupled Asynchronous Backplane:** FastAPI ASGI gateway buffers execution requests into Redis FIFO queues, decoupling compute workloads from web I/O. Real-time stdout/stderr frames stream back via Redis Pub/Sub with a 60-second circular buffer for gapless reconnection recovery.
- **👥 Real-Time Multi-User Collaborative Rooms:** Dual-channel WebSocket multiplexing over Redis Pub/Sub (`rce:room:sync` for document deltas and `rce:room:exec` for live execution streaming) enabling synchronized pair programming without database write thrashing.
- **📊 Algorithmic Autograding Engine:** LeetCode-style problem verification oracle supporting floating-point epsilon tolerance ($\le 10^{-6}$), strict/token normalization, and cryptographic information hiding that scrubs private test cases before serialization.
- **🔭 Distributed Observability:** End-to-end W3C TraceContext propagation (`traceparent`) linking FastAPI requests to Celery execution spans across Redis message brokers via OpenTelemetry.
- **☸️ Cloud-Native Kubernetes GitOps:** Production Helm chart with PodSecurityStandards Restricted enforcement, queue-depth HPA autoscaling (Little's Law: target 5 tasks/worker), automated daily PostgreSQL backups, and declarative Prometheus alerting rules.

---

## 📐 System Architecture

```
[ In-Browser Client: React 18 + Monaco Editor + xterm.js ]
                 │ ▲
    REST (HTTP)  │ │ WebSockets (RFC 6455 Full-Duplex Live I/O)
                 ▼ │
┌──────────────────────────────────────────────────────────────┐
│ Ingress & API Gateway: FastAPI (ASGI Async Event Loop)       │
│ • JWT Authentication (Argon2id) & Role-Based Access Control  │
│ • Sliding Window Rate Limiting (Redis Sorted Sets ZSET)      │
│ • Distributed Tracing Injection (W3C traceparent header)     │
└───────────────┬──────────────────────────────▲───────────────┘
                │                              │
     Task Push  │ (Async Celery Queue)         │ Subscribes (rce:stream:<id>)
                ▼                              │ Broadcasts (rce:room:exec)
┌──────────────────────────────────────────────┴───────────────┐
│ Distributed Message Backplane: Redis 7                       │
│ • FIFO Job Queue (task_submissions)                          │
│ • Pub/Sub Real-Time Streaming Bus                            │
│ • Circular Replay Buffer (60s TTL, Monotonic Sequence IDs)   │
└───────────────┬──────────────────────────────────────────────┘
                │
     Task Pull  │ (Worker Prefetch = 1)
                ▼
┌──────────────────────────────────────────────────────────────┐
│ Compute Execution Workers: Celery Fleet + Watchdog Timer     │
│ • POSIX SIGKILL Watchdog Timer (5.0s Wall-Clock Limit)       │
│ • Stream Multiplexer with Output Cap (1 MB / 10,000 lines)   │
│ • Interactive PTY Session Manager (pty.openpty, TIOCSWINSZ)  │
└───────────────┬──────────────────────────────────────────────┘
                │
                ├──────────────────────┬───────────────────────┐
                ▼                      ▼                       ▼
    ┌──────────────────────┐ ┌───────────────────┐ ┌───────────────────┐
    │ Docker Container     │ │ Micro-VM (KVM)    │ │ Local Process     │
    │ Sandbox              │ │ Sandbox           │ │ Sandbox           │
    │ • cgroups v2 quotas  │ │ • Ring -1 hyper-  │ │ • POSIX PTY pipe  │
    │ • Seccomp-BPF filter │ │   visor boundary  │ │ • Test mock       │
    │ • net=none isolation │ │ • Sub-5ms boot    │ │ • Subprocess caps │
    │ • tmpfs RAM disk     │ │ • Guest kernel    │ │ • Byte capper     │
    └──────────────────────┘ └───────────────────┘ └───────────────────┘
```

---

## 📊 Measurable Operational Limits & Containment

| Parameter | Operational Limit | Enforcement Mechanism | Failure Status Code |
| :--- | :--- | :--- | :--- |
| **Execution Wall-Clock Timeout** | **5.0 s** (configurable max 15.0s) | Worker watchdog timer + POSIX `SIGKILL` | `TIME_LIMIT_EXCEEDED` (TLE) |
| **CPU Allocation Quota** | **0.5 Core** (50% CFS scheduler quota) | Linux cgroups v2 (`cpu.max="50000 100000"`) | Throttled / `TIME_LIMIT_EXCEEDED` |
| **Memory Allocation Ceiling** | **128 MB** (Swap strictly disabled) | Linux cgroups v2 (`memory.max="128m"`, `swap=0`) | Kernel OOM Killer $\rightarrow$ `MEMORY_LIMIT_EXCEEDED` |
| **Process / Thread Limit** | **64 Tasks** per sandbox | Linux cgroups v2 (`pids.max=64`) | Prevents Fork Bombs (`EAGAIN`) |
| **Output Buffer Ceiling** | **1 MB** (or 10,000 lines) | Worker stream consumer byte counter | `OUTPUT_LIMIT_EXCEEDED` (OLE) |
| **Streaming Rate Limit** | Max **50 KB/s** burst rate | Token bucket rate limiter | Stream throttled / Backpressure |
| **Network Egress** | **0 Bytes** (Air-gapped) | Network Namespace (`--net=none`) + K8s Policy | `Network is unreachable` |

---

## ⚡ Comparative Benchmark Results

| Driver Type | Isolation Boundary | Cold Startup Latency (ms) | Memory Baseline (MB) | Containment Rate (5 Attack Suites) |
| :--- | :--- | :--- | :--- | :--- |
| **`ProcessSandbox`** | OS Process Table | **1.2 ms** ($\pm 0.3$) | ~4 MB | Fallback only |
| **`DockerSandbox`** | Namespaces + cgroups + Seccomp | **242.6 ms** ($\pm 18.4$) | ~22 MB | **100% (20/20 per suite)** |
| **`MicroVMSandbox`** | Hardware Virtualization (KVM) | **4.8 ms** ($\pm 0.9$) | ~12 MB | **100% (20/20 per suite)** |

---

## 🛠️ Supported Polyglot Languages

| Language | Compiler / Runtime | Optimization & Defensive Hardening Flags |
| :--- | :--- | :--- |
| **Python** | Python 3.12 (CPython) | Unbuffered I/O, isolated system site-packages |
| **C** | GCC 14 (C17 Standard) | `-O2 -fstack-protector-strong -fPIE -pie -Wl,-z,relro,-z,now` |
| **C++** | G++ 14 (C++20 Standard) | `-O2 -fstack-protector-strong -fPIE -pie -Wl,-z,relro,-z,now` |
| **Rust** | Rustc 1.78 (2021 Edition) | `--edition 2021 -C opt-level=2 -C overflow-checks=on` |
| **Go** | Go 1.22 | `go build -buildmode=pie -trimpath` |
| **JavaScript** | Node.js 20 LTS (V8) | `--max-old-space-size=64 --no-deprecation` |

---

## 🚀 Quickstart & Installation

### Option 1: Full Docker Compose Development Environment
```bash
# 1. Clone repository
git clone https://github.com/farazrasul0-cmd/secure-remote-code-execution-lab.git
cd secure-remote-code-execution-lab

# 2. Configure environment
cp .env.example .env

# 3. Start PostgreSQL and Redis
docker compose -f docker-compose.dev.yml up -d

# 4. Initialize backend virtualenv
python -m venv backend/venv
source backend/venv/bin/activate # Or .\backend\venv\Scripts\activate on Windows
pip install -r backend/requirements.txt
alembic -c backend/alembic.ini upgrade head

# 5. Run test suite (All 88 tests must pass)
pytest backend/tests/ -v

# 6. Start API Gateway
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --reload

# 7. Start Celery Worker Daemon
celery -A worker.tasks.execution worker --loglevel=info --concurrency=2
```

### Option 2: Production Kubernetes Deployment via Helm
```bash
# 1. Inspect and lint Helm chart
helm lint helm/rce-platform/

# 2. Deploy to Kubernetes cluster
helm upgrade --install rce-platform helm/rce-platform/ \
  --namespace rce-platform \
  --create-namespace \
  --values helm/rce-platform/values.yaml

# 3. Verify PodSecurityStandards Restricted workloads
kubectl get pods -n rce-platform
```

---

## 📚 Master's Portfolio Documentation Suite

Comprehensive systems specifications, designs, and academic defense documents:

- **Academic & Research:**
  - 📄 [Research Paper (PDF/MD)](documentation/RESEARCH_PAPER.md) — Formal publication-style report on architecture, security, and performance.
  - 🎓 [Research Contributions](documentation/RESEARCH_CONTRIBUTION.md) — Novelties, academic questions, and trade-off analysis.
  - 🎙️ [Master's Interview Preparation](MASTER_INTERVIEW_PREPARATION.md) — Multi-tiered (Short, Technical, Deep) answers for 10 challenging professor questions.
  - 📋 [CV & Statement of Purpose Descriptions](CV_PROJECT_DESCRIPTION.md) — Tailored application and resume blurbs.
- **Systems Architecture & Security:**
  - 🏛️ [System Overview](documentation/SYSTEM_OVERVIEW.md) — Architectural vision, operational limits, and component hierarchy.
  - 🔍 [Architecture Walkthrough](documentation/ARCHITECTURE_WALKTHROUGH.md) — 11-step end-to-end request lifecycle and subsystem breakdown.
  - 🛡️ [Security Model & STRIDE Analysis](documentation/SECURITY_MODEL.md) — 6-layer defense-in-depth perimeter and kernel containment mechanics.
  - 🌐 [Distributed Systems Design](documentation/DISTRIBUTED_SYSTEM_DESIGN.md) — Decoupled queuing, sequence replay buffers, and Little's Law autoscaling.
  - 📈 [Performance Evaluation & Benchmarks](documentation/PERFORMANCE_EVALUATION.md) — Empirical experiments, cold-boot profiles, and CFS quota tests.
  - 📊 [Complete System Diagrams](documentation/SYSTEM_DIAGRAMS.md) — 6 Mermaid diagrams covering topology, security, sequence, K8s, CI/CD, and tracing.
  - 📜 [Architecture Decision Records (ADRs)](documentation/21_ARCHITECTURE_DECISIONS.md) — 15 ADRs detailing technical trade-offs and interview defense strategies.
  - 🧠 [Learning Notes & CS Foundations](documentation/11_LEARNING_NOTES.md) — 20 deep-dive sections on operating systems, distributed algorithms, and networking.

---

## 🤝 Open Source & Governance

- [Contributing Guidelines](CONTRIBUTING.md) — Code style, GitFlow workflow, and testing rules.
- [Security Policy](SECURITY.md) — Responsible vulnerability disclosure and containment guarantees.
- [Code of Conduct](CODE_OF_CONDUCT.md) — Contributor Covenant v2.1.
- [Final Release Checklist](FINAL_RELEASE_CHECKLIST.md) — Production audit verification record.

---

## 📄 License & Citation

Distributed under the MIT License. If you utilize this platform or its benchmarks in academic research, please cite:

```bibtex
@software{zain2026securerce,
  author = {Syed Faraz Zain},
  title = {Secure Real-Time Remote Code Execution Laboratory Platform: Architecture, Security Design and Performance Evaluation},
  year = {2026},
  version = {2.0.0},
  url = {https://github.com/farazrasul0-cmd/secure-remote-code-execution-lab}
}
```
