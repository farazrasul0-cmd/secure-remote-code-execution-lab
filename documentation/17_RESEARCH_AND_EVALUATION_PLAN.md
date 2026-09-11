# Academic Research & Empirical Evaluation Plan
## Secure Real-Time Remote Code Execution Laboratory Platform

**Author:** Lead Developer & Graduate Candidate  
**Context:** Master's Selection Portfolio & Systems Research Evaluation  
**Research Focus:** Operating Systems, Distributed Systems, Cloud-Native Virtualization, and Multi-Tenant Security  

---

## 1. Research Motivation & Core Problems

In cloud-native multi-tenant computing, safely executing arbitrary user-submitted code presents an inherent engineering conflict between **isolation depth** and **execution latency**:
- Heavyweight isolation (hardware virtualization / traditional VMs) provides robust security boundaries but incurs substantial memory overhead and multi-second boot latencies.
- Lightweight process sandboxes (`nsjail`, Linux containers) achieve sub-second execution speeds but share the host operating system kernel, expanding the attack surface.

This research evaluation analyzes the performance characteristics, resource containment precision, and concurrency scalability of our decoupled containerized architecture.

---

## 2. Research Questions (RQ)

- **RQ1 (Startup Latency & Pooling):**  
  *What is the quantitative latency overhead of cold-start container initialization versus a pre-warmed container pooling strategy across varying concurrent submission loads?*
- **RQ2 (Resource Containment Precision):**  
  *How effectively do Linux cgroups v2 controllers enforce CPU CFS quotas and memory ceilings against deliberately adversarial payloads (e.g., recursive memory allocators, CPU-bound spinning), and what is the latency penalty of kernel OOM-killer interventions?*
- **RQ3 (Stream Multiplexing Performance):**  
  *What is the end-to-end latency distribution (from standard output generation in the sandbox to client terminal rendering) across Redis Pub/Sub and WebSocket streaming pipelines under network backpressure?*

---

## 3. Evaluation Metrics & Instrumentation

The platform will collect granular metrics across four primary evaluation axes:

| Metric Category | Specific Indicator | Target / Unit | Measurement Instrument |
| :--- | :--- | :--- | :--- |
| **Latency** | Cold-Start Container Latency | $\le 800\text{ ms}$ | High-resolution worker timestamps (`time.perf_counter_ns`) |
| | Warm-Pool Retrieval Latency | $\le 50\text{ ms}$ | In-memory pool queue dequeue timestamp |
| | Time-to-First-Byte (TTFB) | $\le 1000\text{ ms}$ | WebSocket client message reception timestamp |
| | Stream Chunk Transit Delay | $\le 25\text{ ms}$ | Delta between worker publication and WebSocket delivery |
| **Throughput** | Maximum Sustainable Throughput | $\ge 20\text{ jobs/sec/node}$ | Locust load testing benchmark |
| | Concurrent Active Streams | $\ge 50\text{ concurrent}$ | Active WebSocket connection gauge |
| **Resource Isolation** | Memory Limit Enforcement Accuracy | $\pm 1\%$ of 128 MB | Linux cgroup v2 `memory.current` vs allocated array size |
| | CPU Quota Adherence | $\pm 2\%$ of 50% CPU | Linux cgroup v2 `cpu.stat` (throttled time vs total runtime) |
| **Security Containment** | Malicious Payload Neutralization | **100.0%** (0 escapes) | Automated adversarial test suite |

---

## 4. Empirical Benchmark Methodology

```
┌─────────────────────────────────────────────────────────────┐
│                 Load Generator (Locust / k6)                │
└──────────────┬───────────────────────────────▲──────────────┘
               │ Submit Code Payloads          │ Track Latency / TTFB
               ▼                               │
┌───────────────────────────────┐   ┌──────────┴──────────────┐
│       FastAPI Gateway         │   │   WebSocket Receiver    │
└──────────────┬────────────────┘   └──────────▲──────────────┘
               │ Redis Queue                   │ Redis Pub/Sub
               ▼                               │
┌───────────────────────────────┐   ┌──────────┴──────────────┐
│     Worker Pool (Celery)      ├───┤ Ephemeral Sandbox Node  │
└───────────────────────────────┘   └─────────────────────────┘
```

### 4.1 Workload Profiles
1. **Benign Educational Workload (Typical Labs):**
   - Short computational tasks (sorting algorithms, basic string parsing, Fibonacci computations).
   - Execution duration: 100ms – 1500ms.
   - Output volume: 1 KB – 20 KB.
2. **Adversarial / Stress Workload:**
   - **Fork Bomb:** Recursive process spawning attempting to exhaust host PID space.
   - **Memory Allocator:** Rapid sequential `malloc` / string multiplications exceeding 128 MB.
   - **CPU Burner:** Unbounded matrix multiplication / infinite busy-wait loops.
   - **File Descriptor Leak:** Opening thousands of files on `/tmp` to trigger kernel `EMFILE`.
   - **Socket / Network Scanner:** Probing internal network ranges (`10.0.0.0/8`, `192.168.0.0/16`) to test network namespace isolation.

### 4.2 Benchmark Stages
- **Phase A: Single-Tenant Baseline:**  
  Measure baseline execution speed, memory footprint, and cold-start overhead with zero background load ($N=1$).
- **Phase B: Concurrency Scalability:**  
  Step-load testing using Locust: ramping from 1 to 100 concurrent users submitting jobs at 5-second intervals. Measure P50, P95, and P99 latency degradation.
- **Phase C: Adversarial Stress Test:**  
  Inject adversarial scripts simultaneously with benign scripts to verify whether malicious resource hogging affects adjacent student jobs (noisy-neighbor verification).

---

## 5. Comparative Architectural Analysis

As part of the academic evaluation, our Docker-based cgroups v2 sandbox will be benchmarked against alternative sandboxing architectures:

| Isolation Architecture | Security Boundary | Cold Start Latency | Memory Overhead | Portability |
| :--- | :--- | :--- | :--- | :--- |
| **Docker + cgroups v2 (Current)** | Linux Namespaces + cgroups | ~400–800 ms | ~15–30 MB | Universal (Linux/macOS/Windows) |
| **Google gVisor (`runsc`)** | User-space virtualized kernel | ~500–900 ms | ~40–60 MB | Linux host required |
| **AWS Firecracker MicroVM** | Hardware KVM Hypervisor | ~50–150 ms | ~5 MB | Bare-metal Linux with `/dev/kvm` |
| **Linux `nsjail`** | Process namespaces + seccomp | ~5–20 ms | < 2 MB | Native Linux only |

---

## 6. Presentation of Results for Master's Portfolio

The final research evaluation will be synthesized into:
1. **Quantitative Performance Graphs:**
   - Cumulative Distribution Function (CDF) of cold vs warm start latencies.
   - Latency vs Concurrency throughput saturation curves.
   - cgroup CPU throttling over time graphs generated from `cpu.stat`.
2. **Academic Publication / Technical Paper Format:**
   - Title: *Design and Evaluation of a Low-Latency, Multi-Tenant Sandboxed Remote Execution Engine for Systems Education*.
   - Sections: Abstract, Introduction, Threat Model, System Architecture, Experimental Evaluation, Related Work, and Conclusion.
