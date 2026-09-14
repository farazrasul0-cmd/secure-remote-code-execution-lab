# System Architecture Decisions & Technical Defense
## Secure Real-Time Remote Code Execution Laboratory Platform

**Document Version:** 1.0.0  
**Target:** Master's Admission Defense & Technical Architecture Review  

---

## 1. Executive Summary

This document formalizes the principal architectural decisions made across the entire platform lifecycle. Each decision is structured according to the standard Architecture Decision Record (ADR) format: **Context**, **Decision**, **Alternatives Evaluated**, **Trade-offs**, and **Interview Defense Strategy**.

---

## Decision 1: Multi-Stage Containerization & Non-Root Execution

### Context
In containerized cloud deployments, container images frequently suffer from bloat, containing compilation toolchains (`gcc`, `npm`, `make`), package managers, and development header files. Furthermore, containers running as root (`UID 0`) introduce catastrophic privilege escalation vulnerabilities to the host operating system.

### Decision
Adopt **Multi-Stage Docker Builds** across all services (Frontend, Backend, Worker):
1. **Frontend:** Stage 1 (`node:20-alpine`) compiles TypeScript and bundles assets; Stage 2 (`nginx:alpine`) serves static files with zero Node.js runtime.
2. **Backend & Worker:** Stage 1 (`python:3.12-slim`) builds wheel archives; Stage 2 installs pre-compiled wheels, strips compilers, and executes under a dedicated system user (`UID 10001:GID 10001`).

### Alternatives Evaluated
* *Single-stage build with `apt-get purge`:* Flawed because layer history preserves deleted binaries and build caches, yielding large image sizes ($> 1\text{ GB}$).
* *Mounting source code dynamically in production:* Violates container immutability, introduces host filesystem permission conflicts, and degrades I/O performance.

### Trade-offs
* *Con:* Slightly longer initial CI build times when building wheels from source.
* *Pro:* Over 85% image size reduction (from 1.2GB down to ~150MB), sub-second cold-start downloads, and complete eradication of compiler-assisted remote exploits.

### Defense Formulation
> *"We enforced the Principle of Least Functionality through multi-stage containerization. By segregating the compilation toolchain from the execution environment, we eliminated package managers and compilers from our production images, preventing attackers from synthesizing kernel exploit binaries in memory. Enforcing non-root UID 10001 guarantees that in the event of an isolation breach, the adversary acquires no administrative privileges on the host kernel."*

---

## Decision 2: Decoupled Ingress Reverse Proxy & Dual-Network Segmentation

### Context
Allowing direct external internet access to internal databases (PostgreSQL) and in-memory caches (Redis) exposes the system to port scanning, brute force authentication attacks, and remote denial-of-service.

### Decision
Segregate the infrastructure into two isolated Docker bridge networks:
1. `rce_public_network`: Only ports 80/443 on the Nginx reverse proxy are bound to the host interface.
2. `rce_internal_network`: An internal, private bridge connecting Nginx, Frontend, Backend, Worker, Redis, and PostgreSQL. PostgreSQL (5432) and Redis (6379) are unreachable from the outside world.

### Alternatives Evaluated
* *Single flat Docker network:* All containers communicate without barriers; exposing ports directly to the host for administrative convenience. Highly insecure.
* *Kubernetes Network Policies / Calico CNI:* Enterprise-grade but introduces significant configuration overhead and infrastructure costs for standalone laboratory deployments.

### Trade-offs
* *Con:* Requires internal DNS resolution and Nginx configuration for all upstream routing.
* *Pro:* Complete network air-gapping of critical data stores; zero exposed attack surface outside port 80/443.

### Defense Formulation
> *"We implemented network micro-segmentation using dual Docker bridge networks. Only the Nginx reverse proxy binds to the public host interface, enforcing TLS termination, rate limits, and OWASP security headers. The PostgreSQL and Redis instances reside entirely within an unexposed internal bridge, rendering them mathematically unreachable from external network scans."*

---

## Decision 3: Distributed Rate Limiting via Redis Sorted Sets (`ZSET`)

### Context
Unrestricted submission endpoints allow denial-of-service attacks, queue saturation, and compute starvation. Fixed-window rate limiters (e.g., reset count every 60s) suffer from the *boundary burst flaw*, permitting twice the quota across window boundaries.

### Decision
Implement the **Sliding Window Log algorithm** using Redis Sorted Sets (`ZSET`) in an atomic transaction pipeline (`client.pipeline()`). Timestamps are scored and pruned within rolling 60-second intervals. If the count exceeds the limit, the gateway rejects the request with `HTTP 429 Too Many Requests` and a calculated `Retry-After` header.

### Alternatives Evaluated
* *Fixed Window Counter:* Prone to 2x boundary bursts.
* *Token Bucket with In-Memory Dict:* Fails across horizontally scaled API replicas because state is not shared.
* *Leaky Bucket via Celery:* Adds latency to legitimate burst traffic.

### Trade-offs
* *Con:* Higher memory consumption in Redis compared to a simple counter, since each request timestamp is stored.
* *Pro:* Mathematically precise sliding window enforcement, zero boundary bursts, and 100% thread-safe atomic execution across horizontally load-balanced API nodes.

### Defense Formulation
> *"Traditional fixed-window rate limiters suffer from boundary burst vulnerabilities. We implemented a sliding window log utilizing Redis Sorted Sets executed within an atomic pipeline. By scoring timestamps and pruning expired entries in a single round-trip, our rate limiter prevents multi-replica race conditions and provides exact `Retry-After` headers compliant with RFC 6585."*

---

## Decision 4: Asynchronous Redis Pub/Sub Streaming Bus for WebSockets

### Context
When user code executes inside transient containers, terminal stdout/stderr chunks must be transmitted in real time to the browser. In a distributed multi-instance deployment, the container may execute on Worker Host B while the user's WebSocket is connected to API Gateway Instance A.

### Decision
Decouple compute execution from API gateway ingress using **Redis Pub/Sub channels** (`rce:stream:<submission_id>`). The Celery worker pipes container output directly into Redis Pub/Sub. The API gateway subscribes to the channel and pumps frames into the client's WebSocket connection.

### Alternatives Evaluated
* *Direct TCP Socket from Worker to Frontend:* Bypasses the API gateway, requiring workers to handle public SSL and client authentication, creating an operational nightmare.
* *Database Polling (`SELECT FROM execution_logs WHERE ...`):* Generates excessive read I/O on PostgreSQL and introduces multi-second polling latency.

### Trade-offs
* *Con:* Redis Pub/Sub provides *at-most-once* delivery semantics without message persistence.
* *Pro:* Sub-millisecond latency, zero database load, and complete horizontal decoupling of the compute tier from the client connection tier. We compensated for at-most-once delivery by adding a secondary 60-second Redis list buffer (`rce:buffer:<id>`) for reconnection reconciliation.

### Defense Formulation
> *"We decoupled compute workers from client connections using Redis Pub/Sub as an asynchronous message backplane. This adheres to the Competing Consumers and Reactor patterns. Any API gateway replica can service any user's WebSocket stream regardless of which worker node is hosting the transient Docker container."*

---

## Decision 5: Virtual Terminal Emulation & Monotonic Sequence Reconciliation

### Context
Browser `<textarea>` and `<pre>` elements cannot render ANSI color codes (`\x1b[32m`) or handle cursor repositioning. Furthermore, packet reordering or network reconnection during WebSocket streaming can cause duplicate or interleaved output.

### Decision
1. Integrate `xterm.js` with `xterm-addon-fit` for virtual VT100 / ECMA-48 terminal emulation.
2. Implement monotonic integer sequence numbers ($0, 1, 2, \dots$) on all backend stream chunks. The frontend client compares incoming sequences against the highest recorded sequence, discarding duplicates.
3. Configure a bounded 5,000-line circular ring buffer in `xterm.js` to eliminate browser DOM memory leaks under infinite print loops.

### Alternatives Evaluated
* *Raw HTML `<pre>` tags:* Produces unreadable ANSI escape garbage on console errors and crashes the browser tab on large outputs.
* *Server-side complete buffer push on completion:* Completely eliminates real-time terminal interactivity, rendering long-running or interactive scripts unusable.

### Trade-offs
* *Con:* Monaco and xterm.js add ~480KB (gzipped) to the frontend JavaScript bundle.
* *Pro:* Genuine IDE/terminal developer experience with sub-millisecond character rendering, robust reconnection recovery, and bounded client-side RAM usage.

### Defense Formulation
> *"Displaying streaming process output requires genuine terminal emulation. We integrated xterm.js backed by monotonic frame sequencing and a bounded circular ring buffer. This provides full ANSI color parsing, prevents DOM exhaustion under adversarial infinite print loops, and ensures stream deduplication across erratic network handoffs."*

---

## Decision 6: Multi-Layered Defense-in-Depth Sandbox Isolation

### Context
Executing arbitrary, untrusted user code on shared host infrastructure introduces extreme security threats: kernel exploitation, fork bombs, memory starvation, network exfiltration, and local privilege escalation. A single layer of defense (e.g. process sandboxing or pure containerization) is susceptible to single-point-of-failure vulnerabilities.

### Decision
Implement an asymmetric, defense-in-depth isolation harness combining Linux kernel primitives:
1. **Linux Cgroups v2:** Hard bounds on CPU quotas (`cpu.max`), memory ceiling (`memory.max = 128MB`), swap suppression (`memory.swap.max = 0`), and strict PID exhaustion limits (`pids.max = 64`) to neutralize fork bombs.
2. **Seccomp-BPF Syscall Whitelisting:** Kernel-level filtering restricting invocations to safe computational syscalls (`read`, `write`, `exit`, `mmap`, `brk`), explicitly trapping and rejecting high-risk operations (`clone`, `fork`, `execve`, `socket`, `ptrace`, `chroot`).
3. **Read-Only Rootfs & Ephemeral Mounts:** Mount the root filesystem as read-only (`--read-only`), providing only an ephemeral in-memory tmpfs for `/tmp` with `noexec` and `nosuid` flags where applicable.
4. **Network Air-Gapping:** Isolate student execution containers from the network (`--network none`) to prevent exfiltration, port scanning, and command-and-control callbacks.

### Alternatives Evaluated
* *Pure Process-Level Sandboxing (`subprocess.Popen` with resource limits):* Susceptible to kernel privilege escalation and shared OS namespace side-channels.
* *Full Hardware Virtualization (QEMU/KVM):* Guarantees hypervisor isolation, but cold-start latencies of 1.5s–3.0s make it unsuitable for interactive, responsive student labs.
* *MicroVMs (AWS Firecracker / gVisor):* Excellent security boundary, but requires nested virtualization (`/dev/kvm`) and Linux kernel support not universally available on developer desktop machines without hypervisor access.

### Trade-offs
* *Con:* Requires cgroup v2-enabled Linux host for full hardware enforcement; requires fine-tuned seccomp profiles per language runtime.
* *Pro:* Near-instant container startup (<120ms), zero host network exposure, deterministic memory ceiling enforcement with instant OOM reaping, and full resilience against local fork bombs.

### Defense Formulation
> *"We adhered to the Principle of Least Privilege and Defense-in-Depth. Untrusted execution does not rely on a single defensive boundary. We combine Linux cgroups v2 for deterministic resource containment (memory ceiling, zero swap, strict PID caps) with Seccomp-BPF syscall whitelisting to block dangerous kernel vectors like socket creation and process cloning. Root filesystems are mounted read-only with ephemeral tmpfs volumes, and container networks are air-gapped, ensuring total blast-radius containment."*

---

## Decision 7: Polyglot Strategy Pattern & Two-Phase Compiler Sandboxing

### Context
A robust educational and testing platform must support diverse programming paradigms: interpreted languages (Python, Node.js) and compiled languages (C, C++, Rust, Go). Compiled languages present unique systems engineering challenges:
1. Compilers (`gcc`, `g++`, `rustc`, `go build`) require significantly higher CPU, memory, and filesystem headroom (512MB–1GB RAM, multiple threads, disk write access for AST synthesis and linking) than the runtime sandbox allows (128MB RAM, single CPU, read-only rootfs).
2. Compilation failure (syntax errors, template instantiation failures, missing types) must be caught deterministically prior to runtime, classified as `COMPILE_ERROR`, and returned with precise diagnostics without consuming runtime compute quotas or triggering false execution timeouts.
3. Adding new languages must adhere to the Open/Closed Principle without mutating existing sandbox or orchestrator logic.

### Decision
1. **Strategy Design Pattern:** Define an abstract `BaseLanguageStrategy` declaring `compile()`, `get_execute_command()`, `source_filename`, `is_compiled`, and security compilation flags. Specialized strategies (`PythonStrategy`, `CStrategy`, `CppStrategy`, `RustStrategy`, `GoStrategy`, `NodeStrategy`) encapsulate language-specific toolchain invocation.
2. **Central Registry:** Implement `LanguageRegistry` with O(1) lookup and alias resolution (`py` $\to$ `python`, `rs` $\to$ `rust`, `golang` $\to$ `go`, `js` $\to$ `node`).
3. **Asymmetric Two-Phase Lifecycle:** Decouple execution into:
   - **Phase 1 (Compilation):** Granted higher compilation resource quotas (10s compilation timeout, 1024MB RAM). Employs hardening flags: `-O2`, `-fstack-protector-strong`, `-D_FORTIFY_SOURCE=2`, `-fPIE`, `-Wl,-z,relro,-z,now`, and `-z noexecstack`. If compilation exits non-zero, capture stderr and return `ExecutionStatus.COMPILE_ERROR` immediately.
   - **Phase 2 (Execution):** The resulting stripped ELF binary or interpreted script is executed under strict student cgroup limits (128MB RAM, 0.5 CPU, 5s timeout, air-gapped network).

### Alternatives Evaluated
* *Single-Phase Compilation inside Student Sandbox:* Running `rustc` or `g++` inside a 128MB cgroup immediately triggers out-of-memory kernel reaping (`SIGKILL 137`), preventing legitimate C++ or Rust programs from compiling.
* *Monolithic Sandbox If-Else Dispatch:* Hardcoding language commands inside `process_sandbox.py` violates the Single Responsibility and Open/Closed principles, resulting in unmaintainable spaghetti code when adding new language toolchains.

### Trade-offs
* *Con:* Compiled submissions incur two sequential process invocations (compilation followed by execution), slightly increasing total turn-around latency (~300ms–800ms compilation overhead).
* *Pro:* Total isolation between compiler resource profiles and runtime security bounds; elegant extensibility where new languages are added simply by registering a new strategy; clean client diagnostics separating syntax/compilation issues from runtime faults.

### Defense Formulation
> *"We engineered a Polyglot Execution Pipeline utilizing the Strategy Pattern coupled with an asymmetric two-phase lifecycle. Compilers inherently exhibit high resource requirements for AST generation, template expansion, and LLVM linking, whereas untrusted student execution requires draconian containment. Decoupling compilation from execution allowed us to apply strict compiler hardening flags (stack canaries, ASLR PIE, RELRO, non-executable stack) in the compilation stage, while confining the generated binary to strict cgroup quotas. Syntax errors immediately short-circuit as `COMPILE_ERROR`, avoiding false timeouts and preserving compute resources."*

---

## Decision 8: Autograding Engine, Deterministic Oracle Verification & Information Hiding

### Context
Automated programming problem verification requires running untrusted student code against a comprehensive suite of input/output test vectors. This introduces three critical challenges:
1. **Information Leakage:** If test vectors (inputs and expected outputs) are exposed to client-side code, students can trivially hardcode responses (`if input == X return Y`) without solving the underlying computational problem.
2. **Execution Flakiness & Contamination:** If subsequent test cases run within the same container or shared memory context, lingering background threads, memory leaks, or unclosed file descriptors cause non-deterministic cascading failures.
3. **Format & Precision Fragility:** Strict byte-for-byte matching causes false rejections due to cross-platform line ending differences (`\r\n` vs `\n`), trailing whitespace, or IEEE 754 floating-point rounding divergence.

### Decision
1. **Deterministic Oracle Harness:** Implement an isolated evaluation pipeline in `worker/grading/harness.py`. Each test vector runs with fresh stdin piping and reset CPU/memory watchdog timers. Early compilation errors short-circuit all subsequent test executions immediately.
2. **Architectural Information Hiding:** Partition test cases into public sample vectors (`is_hidden = False`) and private grading vectors (`is_hidden = True`). Enforce sanitization at the API serialization boundary (`GradingHarness.sanitize_for_student`): for all hidden test vectors, input data and expected answers are permanently scrubbed to `[REDACTED: HIDDEN TEST CASE]` before returning JSON responses to unprivileged students.
3. **Multi-Mode Verification Comparator:** Implement an extensible output comparator supporting:
   - `NORMALIZED`: CRLF-to-LF conversion, trailing whitespace stripping, and trailing newline pruning.
   - `STRICT`: Byte-for-byte exact equality.
   - `EPSILON`: Token-based floating-point comparison enforcing $\frac{|y_{\text{act}} - y_{\text{exp}}|}{\max(1.0, |y_{\text{exp}}|)} \le 10^{-6}$.
4. **Weighted Scoring Model:** Calculate aggregate submission score as:
   $$\text{Score} = \frac{\sum_{i \in \text{passed}} \text{Weight}_i}{\sum_{i \in \text{total}} \text{Weight}_i} \times 100$$
   Assigning discrete verdicts (`ACCEPTED`, `PARTIAL`, `WRONG_ANSWER`, `TIME_LIMIT_EXCEEDED`, `MEMORY_LIMIT_EXCEEDED`, `COMPILE_ERROR`).

### Alternatives Evaluated
* *Client-Side Test Case Verification:* Sending test cases to the frontend and checking stdout in JavaScript. Catastrophic security flaw allowing total oracle extraction via DevTools.
* *Monolithic Shell Script Grading Harness:* Running bash scripts inside the container to diff files. Inflexible, prone to shell injection, and cannot provide structured JSON telemetry.
* *Binary All-or-Nothing Scoring:* Rejecting students without partial credit. Discourages learning and fails to reward correct logic on subsets of test cases.

### Trade-offs
* *Con:* Evaluating $N$ test cases requires $N$ process invocations, scaling execution latency linearly with test suite size ($T_{\text{total}} = \sum t_i$).
* *Pro:* Total isolation between test vectors; complete prevention of hardcoded oracle cheats; robust, platform-agnostic output verification; and fine-grained partial credit feedback.

### Defense Formulation
> *"We implemented an autograding verification architecture founded on the Principle of Information Hiding and formal oracle verification. To eliminate oracle extraction attacks and hardcoded cheat solutions, private test vectors are cryptographically scrubbed at the serialization gateway, ensuring students receive deterministic runtime metrics without revealing underlying proprietary test data. Our multi-mode verifier normalizes line endings and applies IEEE 754 $\epsilon$-tolerance, preventing false negatives while maintaining rigorous algorithmic standards."*

---

## Decision 9: Bidirectional Interactive Pseudo-Terminal (PTY) & Redis Input Channel Architecture

### Context
Standard remote code execution systems pipe static standard input into a process and stream standard output back to the user upon execution. However, realistic computer laboratory instruction requires interactive computing:
1. **Interactive REPLs & Prompts:** Dynamic languages (Python `input()`, Node.js REPL) and tools expect an interactive terminal session where users type inputs in response to runtime prompts.
2. **Terminal Discipline & ANSI Control:** Standard pipes disable TTY line discipline, breaking ANSI color formatting, carriage-return cursor resets, and interactive terminal features.
3. **Viewport Geometry & Resizing:** When a user resizes their browser window or changes font sizes, terminal programs with dynamic line wrapping must adjust their internal viewport dimensions or risk garbled rendering.
4. **Out-of-Band Control & Cancellation:** Long-running loops or unresponsive scripts require an immediate interrupt mechanism (`SIGINT` / `Ctrl+C`) to restore user control without terminating the entire worker node.
5. **Decoupled Gateway-to-Worker Routing:** Directly binding WebSocket connections to worker host sockets breaks horizontal scaling and load balancer autonomy.

### Decision
1. **Linux Pseudo-Terminal Allocation:** Implement `PTYSession` in `worker/sandbox/pty_session.py` using POSIX `pty.openpty()`. The child execution process connects its file descriptors to the PTY slave, while the worker asynchronous loop manages the PTY master. Line discipline translation (`termios.ONLCR`) is enabled to automatically translate newlines into carriage-return + newline pairs.
2. **Cross-Platform Host Compatibility Fallback:** Non-POSIX development environments (e.g. Windows hosts) automatically utilize asynchronous queue-backed pipe emulation, ensuring tests and local development execute without missing POSIX module errors.
3. **Decoupled Dual-Channel Redis Event Bus:**
   - **Downstream Channel (`rce:stream:<submission_id>`):** Pipes execution output chunks from worker multiplexers to WebSocket clients, backed by an in-memory Redis list buffer (`rce:buffer:<submission_id>`) for catch-up replay.
   - **Upstream Channel (`rce:input:<submission_id>`):** Transmits structured JSON frames (`stdin`, `resize`, `signal`) from WebSocket endpoints to worker listener tasks (`_consume_upstream_inputs`).
4. **Dynamic Viewport Synchronization (`TIOCSWINSZ`):** Terminal resize frames from `xterm.js` are packed into C `struct winsize` (`struct.pack("HHHH", rows, cols, 0, 0)`) and applied to the PTY master via `fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)`, causing the Linux kernel to dispatch `SIGWINCH` to the child process group.
5. **Asynchronous Signal Propagation (`SIGINT`):** Interactive interrupt requests (`Ctrl+C` or UI interrupt button) dispatch operating system signals directly to the child process PID (`os.kill(child_pid, signal.SIGINT)`), allowing graceful exception raising (`KeyboardInterrupt`) without worker corruption.

### Alternatives Evaluated
* *Direct WebSocket-to-Worker TCP Socket Binding:* Opening direct TCP connections between API gateways and Celery workers. Strongly rejected: couples gateway instances to specific worker pods, prevents horizontal auto-scaling, and fails when worker pods restart or migrate across nodes.
* *Standard Anonymous Pipes with Polling:* Simulating interactive input using standard `asyncio.subprocess.PIPE`. Rejected: cannot allocate real TTYs; programs detect `!isatty()` and disable interactive buffering and readline; cannot deliver `SIGWINCH` resize signals.
* *SSH Daemon Per Container:* Running an OpenSSH server inside every student container. Rejected: introduces extreme resource overhead (cryptographic handshakes, SSH key provisioning), high initialization latency (>1500ms), and massive attack surface.

### Trade-offs
* *Con:* Maintaining bidirectional Redis Pub/Sub channels incurs small pub/sub memory overhead and requires concurrent reader/writer task coordination in both API gateways and worker nodes.
* *Pro:* Total architectural decoupling between web gateways and execution workers; true POSIX TTY semantics for interactive REPLs; zero SSH overhead; sub-5ms keystroke latency; and resilient signal propagation.

### Defense Formulation
* > *"We designed our interactive terminal architecture around Linux PTY master/slave virtual character devices decoupled from the web tier via a full-duplex Redis Pub/Sub backplane. Rather than coupling browser WebSockets directly to worker processes or incurring the heavyweight latency of per-container SSH daemons, our system separates downstream terminal streaming from upstream control framing. Window resize ioctls (`TIOCSWINSZ`) propagate dynamically across the network to emit kernel `SIGWINCH` signals, while `SIGINT` events allow users to halt infinite loops with zero worker host contamination."*

---

## Decision 10: Cloud-Native Kubernetes Orchestration, Helm Packaging & Queue-Depth Autoscaling

### Context
Deploying a multi-service distributed platform (frontend, backend API, Celery workers, PostgreSQL, Redis) to production requires solving several infrastructure challenges:
1. **Reproducible Deployments:** Static YAML manifests with hardcoded values break across environments (dev, staging, production). Image tags, replica counts, secrets, and resource limits must be parameterized.
2. **Stateful Data Persistence:** PostgreSQL and Redis require persistent storage that survives pod eviction, node failure, and rolling upgrades without data loss.
3. **Lateral Movement Prevention:** If untrusted student code achieves sandbox escape, the attacker must be prevented from reaching databases, cloud metadata endpoints, or other student workloads via the flat Kubernetes network.
4. **Elastic Capacity Under Burst Load:** CPU-based autoscaling fails for I/O-bound Celery workers (sleeping tasks consume 0% CPU while queue backlog grows unbounded). Autoscaling must be driven by queue depth.
5. **Container Privilege Minimization:** Every workload must enforce the Principle of Least Privilege at the Linux kernel level to prevent privilege escalation attacks.

### Decision
1. **Helm Chart Packaging:** Package the entire platform into a parameterized Helm chart (`helm/rce-platform/`) with 17 Go-templated manifests, centralized `values.yaml`, and reusable helper templates (`_helpers.tpl`).
2. **StatefulSets for Data Services:** Deploy PostgreSQL 16 and Redis 7 as StatefulSets with dedicated PersistentVolumeClaim templates (10Gi and 2Gi respectively), headless services for stable DNS, and health probe commands (`pg_isready`, `redis-cli ping`).
3. **PodSecurityStandards Restricted:** Enforce namespace-level `pod-security.kubernetes.io/enforce: restricted` requiring non-root UIDs (10001), dropped ALL capabilities, `allowPrivilegeEscalation: false`, `readOnlyRootFilesystem: true`, and `seccompProfile: RuntimeDefault` across all workloads.
4. **Zero-Trust NetworkPolicy Suite:** Deploy 6 NetworkPolicies: default-deny-all baseline, then microsegmented whitelists allowing only exact inter-service communication paths (frontend→backend, backend→postgres/redis, worker→redis). Workers receive zero ingress.
5. **Queue-Depth HPA v2 Autoscaling:** Scale worker Deployments on custom Prometheus metric `rce_worker_queue_depth` (target: 5 pending submissions per worker, max: 20 replicas) with aggressive scale-up (0s stabilization) and conservative scale-down (300s stabilization). Backend API scales on CPU/memory utilization.
6. **Ingress with WebSocket Upgrade:** Configure `ingress-nginx` with path-based routing (`/api`→backend, `/ws`→backend, `/`→frontend) and 3600-second proxy timeout annotations for long-running interactive PTY sessions.

### Alternatives Evaluated
* *Raw Kubernetes YAML without Helm:* Hardcoded manifests are non-portable across environments and require manual find-and-replace for every configuration change. Rejected for maintainability.
* *Docker Compose in Production:* Lacks pod-level security enforcement, NetworkPolicies, PersistentVolumeClaims, health-based rescheduling, and horizontal autoscaling. Suitable only for local development.
* *CPU-Based Worker HPA:* Celery workers executing short `sleep()` or I/O-bound tasks report near-zero CPU utilization. HPA never triggers, causing unbounded queue growth and student wait times. Rejected in favor of queue-depth scaling.
* *Default Kubernetes Network (No Policies):* Every pod can reach every other pod. A sandbox-escaped process can port-scan PostgreSQL (5432), exfiltrate data, or query `169.254.169.254` for cloud credentials. Rejected for zero-trust microsegmentation.

### Trade-offs
* *Con:* Helm templating adds syntactic complexity and requires Helm CLI tooling. NetworkPolicies require a CNI plugin that supports them (e.g., Cilium, Calico). Custom metrics HPA requires Prometheus Adapter or KEDA installation.
* *Pro:* One-command reproducible deployments; namespace-level security enforcement; zero lateral movement; elastic capacity under burst load; and persistent, crash-safe data services.

### Defense Formulation
> *"We engineered a cloud-native deployment architecture using Helm-parameterized Kubernetes manifests enforcing PodSecurityStandards Restricted at the namespace admission level. Zero-trust NetworkPolicies implement default-deny-all with microsegmented label-selector whitelists, preventing lateral movement from compromised sandbox pods. Worker autoscaling applies Little's Law ($L = \lambda W$) via HPA v2 custom metrics, scaling on Redis queue depth rather than CPU utilization—eliminating the blind spot where I/O-bound workers report 0% CPU while thousands of tasks queue. StatefulSets with dedicated PVCs guarantee crash-consistent data persistence for PostgreSQL WAL files and Redis AOF journals."*

---

## Decision 11: Pluggable Sandbox Driver Hierarchy & Micro-VM Virtualization

### Context
Previous platform iterations relied primarily on Docker container sandboxing with fallback to native subprocess execution. However, scaling a secure multi-tenant execution platform across enterprise clouds and local developer environments presents architectural constraints:
1. **Container Escape Risks:** All Linux containers share the host operating system kernel. A zero-day privilege escalation or syscall flaw can compromise the entire node.
2. **Heterogeneous Host Environments:** Developer laptops (Windows/macOS), standard Kubernetes nodes, and bare-metal KVM instances have vastly different virtualization capabilities. Forcing Docker on environments without daemon access or ignoring KVM when hardware virtualization is present is sub-optimal.
3. **Hardware Isolation Guarantees:** Enterprise and academic multi-tenant workloads executing hostile or untrusted student submissions require defense-in-depth isolation that guarantees memory boundaries at the hardware hypervisor level.

### Decision
1. **Abstract Driver Hierarchy:** Formalize the `BaseSandbox` interface across three specialized runtime drivers:
   - **`ProcessSandbox`:** Lightweight, zero-overhead subprocess execution for local development and rapid test cycles.
   - **`DockerSandbox`:** Containerized execution with cgroups v2 resource ceilings, Seccomp-BPF filters, and read-only root filesystems.
   - **`MicroVMSandbox`:** Hardware-assisted virtualization driver providing guest memory envelope isolation, watchdog supervision, and KVM hypervisor integration.
2. **Dynamic Capability Negotiation:** Implement `SandboxFactory.create_sandbox(driver_type=AUTO)` which dynamically probes host capabilities (`MicroVMCapabilities.is_kvm_available()`, Docker daemon socket reachability) to automatically deploy the highest-security containment driver supported by the underlying hardware.
3. **Automated Driver Benchmarking Harness:** Create `SandboxBenchmarkHarness` to quantitatively measure cold startup latency, execution duration, and memory overhead across all available isolation drivers.

### Alternatives Evaluated
* *Hardcoding Docker as the Sole Execution Driver:* Fails in environments without nested virtualization or Docker daemon permissions (e.g., restricted Kubernetes pods or Windows developer workstations without Docker Desktop).
* *Full-Blown QEMU System Emulation:* Emulating full PC hardware (BIOS, PCI buses, ACPI) incurs severe cold-start latency (>1500ms) and high memory footprint (>128MB per instance), making it unusable for real-time sub-second code execution.
* *gVisor-only (runsc):* Requires specialized Linux kernel configurations and suffers from high syscall translation overhead for I/O-intensive code.

### Trade-offs
* *Con:* Maintaining three distinct drivers increases codebase surface area and test matrix complexity.
* *Pro:* Total architectural flexibility; hardware-level fault boundaries when KVM is present; seamless developer experience on laptops; and clear enterprise migration path to Firecracker/Kata Containers.

### Defense Formulation
> *"We transitioned our execution tier from a monolithic container runner to a pluggable driver architecture supporting native subprocesses, OCI containers, and hardware-virtualized Micro-VMs. By implementing dynamic capability negotiation, the platform automatically detects `/dev/kvm` to engage hardware-assisted guest memory envelopes with hypervisor-enforced fault boundaries, while falling back gracefully to hardened Docker cgroups v2 or local process sandboxes. Our benchmarking harness empirically verifies that micro-VM isolation provides hardware-level tenant isolation with single-digit millisecond startup overhead."*





