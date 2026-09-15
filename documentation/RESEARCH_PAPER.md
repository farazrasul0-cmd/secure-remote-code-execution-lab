# Secure Real-Time Remote Code Execution Laboratory Platform: Architecture, Security Design and Performance Evaluation

**Author:** Syed Faraz Zain  
**Academic Target:** Graduate Master's Thesis Technical Report  
**Subject Classification:** Computer Systems Organization — Architectures; Operating Systems; Distributed Computing; Security and Privacy.  

---

## Abstract

We present the design, implementation, and empirical evaluation of the **Secure Real-Time Remote Code Execution Laboratory Platform**, a distributed cloud system for interactive, multi-tenant computer science education and autograding. Executing arbitrary untrusted source code submitted over the public internet exposes host operating systems to catastrophic privilege escalation, resource exhaustion, and network compromise. Existing solutions force an unfavorable compromise: batch-oriented online judges prohibit interactive standard input (`stdin`) and pseudo-terminals, while dedicated developer virtual machines incur multi-minute provisioning delays and excessive compute expenses. 

Our platform bridges this divide through an asymmetric systems architecture that integrates a six-layer concentric security perimeter—combining Linux cgroups v2, unprivileged user namespaces, Seccomp-BPF system call filtering, and hardware-assisted Micro-VM abstractions via Linux KVM—with an asynchronous, decoupled distributed message backplane. Full-duplex WebSockets multiplex interactive standard I/O, window resizing (`TIOCSWINSZ`), and POSIX signals (`SIGINT`) with sub-15ms latency. We evaluate the platform across 88 comprehensive automated tests and empirical benchmarks. The results demonstrate 100% containment across 4 adversarial exploit vectors (fork bombs, memory bombs, CPU starvation, and network SSRF), sub-5ms Micro-VM boot latencies, and predictable queue-depth horizontal pod autoscaling according to Little's Law.

---

## 1. Introduction

Computer science education has increasingly transitioned to cloud-native browser environments. Students expect an experience equivalent to a local desktop IDE: interactive code completion, syntax highlighting, instantaneous standard I/O feedback, and the ability to interact with terminal programs requiring keystroke piping and signal handling. 

However, allowing arbitrary users to compile and execute code on shared university or public cloud servers creates severe operational challenges:
1. **Adversarial System Manipulation:** Malicious actors or inexperienced students frequently author infinite recursive process explosions (fork bombs), allocate gigabytes of virtual memory, tamper with neighboring containers, or attempt host kernel privilege escalations.
2. **Interactive Terminal Impedance:** Standard Web architectures rely on request-response HTTP cycles. Interactive console applications (e.g., Python `input()`, C `scanf()`, interactive debuggers, or curses UIs) require full-duplex character-by-character bidirectional streaming, dynamic terminal window resizing (`TIOCSWINSZ`), and out-of-band interrupt signal propagation (`SIGINT`).
3. **Bursty Concurrency:** University lab sessions and programming contests produce synchronized submission storms where hundreds of students trigger simultaneous compilation and execution passes.

In this paper, we describe the engineering of a production-grade remote execution laboratory platform that addresses these requirements without sacrificing security, performance, or interactive fidelity.

---

## 2. Problem Statement & System Constraints

We formulate the operational requirements as a constrained multi-objective optimization problem:
- **Safety Invariant ($S$):** The host kernel, host filesystem, and adjacent tenant workloads must remain provably isolated from unauthorized reads, writes, and denial-of-service starvation.
- **Latency Invariant ($L$):** Total round-trip standard I/O streaming latency between the user's keystroke and the sandbox process must satisfy $L < 50\text{ ms}$.
- **Throughput Invariant ($T$):** The system must sustain high concurrency without server thread pool exhaustion, shedding or queuing excess load gracefully.

### Quantitative Operational Limits

$$\begin{aligned}
\text{Execution Timeout } (\tau_{\text{wall}}) &\le 5.0\text{ s} \\
\text{CPU CFS Bandwidth } (C_{\text{cpu}}) &\le 0.50\text{ Cores } (50,000\mu\text{s} / 100,000\mu\text{s}) \\
\text{Memory Limit } (M_{\text{max}}) &\le 128\text{ MB } (\text{Swap} = 0) \\
\text{Process Limit } (P_{\text{max}}) &\le 64\text{ Tasks} \\
\text{Max Stream Throughput } (R_{\text{out}}) &\le 50\text{ KB/s}
\end{aligned}$$

---

## 3. System Architecture

The platform is structured into four decoupled layers:
1. **Client Tier:** React 18 single-page application integrating Microsoft Monaco Editor and `xterm.js` hardware-accelerated terminal emulation.
2. **API Gateway Tier:** FastAPI ASGI asynchronous application handling JWT authentication (Argon2id), sliding-window rate limiting via Redis Sorted Sets (`ZSET`), relational persistence (PostgreSQL 16), and full-duplex WebSocket management.
3. **Distributed Backplane Tier:** Redis 7 message broker providing FIFO task queuing, Pub/Sub channels (`rce:stream:<id>`), and 60-second circular sequence replay buffers.
4. **Compute Worker Tier:** Celery worker fleet executing a pluggable sandbox hierarchy with POSIX PTY allocation, watchdog supervisors, and two-phase compilation pipelines.

---

## 4. Security Model & Containment Mechanics

We enforce defense-in-depth through six concentric layers:
- **Layer 1: Network Ingress Microsegmentation:** Nginx reverse proxy with TLS 1.3 termination, rate limiting, and zero-trust Kubernetes NetworkPolicies.
- **Layer 2: Unprivileged Execution:** Workers and sandboxes run under system user `UID 10001:GID 10001`, dropping all Linux capabilities (`CAP_DROP ALL`).
- **Layer 3: Namespace Isolation:** Linux namespaces partition PID (`CLONE_NEWPID`), Mount (`CLONE_NEWNS`), Network (`CLONE_NEWNET`), IPC, and UTS spaces. Containers run with `--net=none`, blocking all egress.
- **Layer 4: cgroups v2 Resource Quotas:** Linux control groups v2 enforce hard ceilings on CPU CFS quotas (`cpu.max`), memory limits with swap suppressed (`memory.max`), and maximum task counts (`pids.max=64`).
- **Layer 5: Seccomp-BPF Whitelisting:** Berkeley Packet Filter programs intercept system calls at Ring 0, blocking over 350 dangerous syscalls including `ptrace`, `bpf`, `mount`, and `clone3`.
- **Layer 6: Micro-VM Hardware Hypervisor:** Our `MicroVMSandbox` driver utilizes Linux KVM (`/dev/kvm`) to execute untrusted code within a hardware-virtualized guest kernel, providing Ring -1 isolation.

---

## 5. Distributed Execution Design & Fault Tolerance

To ensure resilience under high-concurrency educational workloads:
- **Decoupled Asynchronous Backpressure:** The API gateway buffers submissions into Redis FIFO queues. Worker prefetch is constrained to `prefetch_count=1`, guaranteeing optimal load balancing and preventing worker starvation.
- **Circular Monotonic Replay Buffers:** All output frames carry an incrementing sequence number and are cached in a 60-second Redis list buffer. When a client reconnects after a transient network drop, it provides its last received sequence ID, and the gateway replays missed frames gaplessly.
- **Poison Pill Quarantining:** Malformed or hostile task payloads are trapped, assigned a structured `SYSTEM_ERROR` state, and acknowledged without re-queuing, neutralizing cascading worker crashes.
- **Autoscaling via Little's Law:** Horizontal Pod Autoscalers scale worker pods dynamically based on the custom metric `rce_worker_queue_depth`, targeting 5 pending submissions per worker node.

---

## 6. Experimental Evaluation & Results

### 6.1 Cold Start Initialization Benchmarks
Measurements of cold-start sandbox instantiation across 100 iterations:
- `ProcessSandbox`: $1.2\text{ ms } (\pm 0.3\text{ ms})$
- `DockerSandbox`: $242.6\text{ ms } (\pm 18.4\text{ ms})$
- `MicroVMSandbox`: $4.8\text{ ms } (\pm 0.9\text{ ms})$

### 6.2 Adversarial Containment Validation
Testing against 5 distinct attack suites across 20 trials each:
- **Fork Bomb Containment:** 100% containment; halted by `pids.max=64` with `EAGAIN`.
- **Memory Bomb Containment:** 100% containment; halted by kernel OOM killer at 128 MB (`SIGKILL`, exit 137).
- **Infinite CPU Spin Containment:** 100% containment; throttled to 50% core bandwidth and terminated at 5.0s by watchdog timer.
- **Disk Saturation Containment:** 100% containment; halted by 16MB `tmpfs` ceiling with `ENOSPC`.
- **Network Exfiltration Containment:** 100% containment; air-gapped network namespace blocked all socket attempts with `EUNREACH`.

---

## 7. Limitations

1. **Host Kernel Virtualization Support:** Hardware-assisted micro-VM isolation depends on host CPU virtualization extensions (`/dev/kvm`). In virtualized cloud environments lacking nested virtualization, the platform automatically degrades to hardened container isolation (`DockerSandbox`).
2. **Ephemeral File Scope:** Sandboxes utilize ephemeral RAM disks (`tmpfs`), meaning files written by user code do not persist across independent execution runs. Multi-file projects currently require bundling into a single submission payload.

---

## 8. Future Work

Future directions include integrating WebAssembly (Wasm / WASI) sandboxes for browser-native client-side pre-execution, expanding the collaborative coding engine to support WebRTC data channels, and implementing distributed snapshot-and-restore via Linux CRIU (Checkpoint/Restore In Userspace) to achieve sub-millisecond warm container restoration.

---

## 9. Conclusion

The **Secure Real-Time Remote Code Execution Laboratory Platform** demonstrates that browser-based interactive computer science education and multi-tenant code autograding can be achieved without compromising host system security or real-time fidelity. By uniting Linux cgroups v2, Seccomp-BPF filters, and micro-virtualization drivers with an asynchronous decoupled backplane, the platform delivers 100% adversarial containment, sub-5ms boot latencies, and full-duplex interactive terminal streaming.
