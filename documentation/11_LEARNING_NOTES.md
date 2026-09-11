# Learning Notes & Computer Science Foundations
## Secure Real-Time Remote Code Execution Laboratory Platform

**Document Version:** 1.0.0  
**Domain:** Core Systems Computer Science Concepts  

---

## 1. Operating Systems: Process Isolation & Resource Control

### 1.1 Linux Namespaces
Linux namespaces partition kernel resources such that one set of processes sees one set of resources while another set of processes sees a completely different set:
- **PID Namespace (`CLONE_NEWPID`):** Isolates the process ID space. The target process inside the sandbox becomes PID 1, completely blind to host processes and other containers.
- **Mount Namespace (`CLONE_NEWNS`):** Isolates the filesystem mount points. Combined with `pivot_root` and `--read-only`, untrusted code cannot view or modify the host VFS.
- **Network Namespace (`CLONE_NEWNET`):** Provides independent network device stacks, routing tables, and firewall rules. When initialized with `--net=none`, only a disconnected loopback device exists.
- **IPC Namespace (`CLONE_NEWIPC`):** Isolates System V IPC and POSIX message queues, preventing inter-process memory sharing or synchronization with host processes.
- **UTS Namespace (`CLONE_NEWUTS`):** Isolates hostname and domain name.
- **User Namespace (`CLONE_NEWUSER`):** Maps a container-internal `root` (UID 0) to an unprivileged user (e.g., UID 10001) on the host. In our platform, we enforce unprivileged execution directly (`uid=1001`), providing layered security.

### 1.2 Control Groups v2 (cgroups v2)
Unlike cgroups v1 which had fragmented hierarchies per controller, cgroups v2 provides a unified single-hierarchy resource distribution model:
- **CPU Controller (`cpu.max`):** Enforces bandwidth allocation using the Completely Fair Scheduler (CFS) quota. We configure `"50000 100000"`, which grants the process $50,000\mu\text{s}$ of CPU time every $100,000\mu\text{s}$ period (strictly limiting the container to 0.5 CPU core regardless of host core count).
- **Memory Controller (`memory.max`):** Sets a hard ceiling on total memory consumption (anonymous pages, page cache, swap). When memory usage hits this limit, the Linux kernel invokes the Out-Of-Memory (OOM) killer to terminate processes within the cgroup. We set `memory.swap.max = 0` to prevent swap-thrashing attacks.
- **PID Controller (`pids.max`):** Restricts the number of tasks (processes and threads) inside the cgroup. Setting `pids.max = 64` neutralizes fork bombs by forcing the `fork()` or `clone()` syscall to fail with `EAGAIN` (`Resource temporarily unavailable`).

### 1.3 Seccomp-BPF (System Call Interception)
Secure Computing Mode with Berkeley Packet Filter (Seccomp-BPF) inspects system call numbers and parameters before allowing the CPU to transition into kernel space (`ring 0`):
- Untrusted user programs only require a tiny fraction of the Linux kernel's ~450 system calls (e.g., `read`, `write`, `exit_group`, `mmap`, `brk`).
- Prohibiting dangerous calls (`ptrace`, `bpf`, `mount`, `chroot`, `clone3`, `sys_admin`) eliminates the principal vectors used for container breakout and kernel exploitation.

---

## 2. Distributed Systems: Decoupling & Concurrency

### 2.1 Producer-Consumer & Backpressure
- **The Fallacy of Synchronous Processing:** In synchronous web applications, request rate directly dictates execution concurrency. Under spiky loads (e.g., 200 students submitting simultaneously), unbuffered concurrency results in resource thrashing, CPU cache invalidation, and cascading OOM failures.
- **Asynchronous Buffering:** By placing Redis as a FIFO message queue between FastAPI (producer) and worker nodes (consumers), the system throttles execution concurrency to the exact capacity of the worker pool. Submissions beyond capacity safely wait in memory without crashing the cluster.

### 2.2 At-Least-Once Delivery vs. Idempotency
- In distributed task execution, workers may crash during code execution. 
- Message brokers use acknowledgments (`ACK`). If an ACK is not received before visibility timeout expires, the job is re-delivered.
- Because executing code causes side effects (e.g., streaming output, database writes), tasks are designed with unique UUIDs (`submission_id`). Execution status checks ensure that duplicate job delivery does not corrupt historical telemetry.

---

## 3. Computer Networks: Streaming Protocols & Sockets

### 3.1 HTTP Polling vs. Server-Sent Events (SSE) vs. WebSockets
- **HTTP Polling:** High overhead due to repeated TCP 3-way handshakes, TLS negotiation, and voluminous HTTP header transmission (500–1000 bytes header overhead for 50 bytes of data).
- **SSE:** Efficient unidirectional server-to-client streaming, but cannot send client keystrokes / interactive `stdin` upstream over the same channel.
- **WebSockets (`RFC 6455`):** Starts with an HTTP Upgrade handshake, then switches to a persistent, full-duplex TCP framing protocol. Frames have minimal overhead (2 to 10 bytes per frame), enabling sub-millisecond bidirectional transmission of terminal keystrokes and stdout chunks.

---

## 4. Cybersecurity: Defense-in-Depth for Untrusted Code

| Security Layer | Technology | Attack Vector Neutralized |
| :--- | :--- | :--- |
| **Network Boundary** | `--net=none` (Network Namespace) | SSRF, LAN port scanning, botnet/DDoS participation, crypto mining. |
| **Filesystem Boundary** | Read-Only Rootfs + in-memory `tmpfs` | Host filesystem alteration, persistent malware storage, disk filling. |
| **Resource Boundary** | cgroups v2 (`cpu`, `memory`, `pids`) | Infinite busy loops, RAM exhaustion bombs, fork bombs. |
| **Privilege Boundary** | Non-root user + `CAP_DROP ALL` | Setuid privilege escalation, root directory tampering. |
| **Kernel Syscall Boundary**| Seccomp-BPF | Container breakout, kernel 0-day exploitation, process snooping (`ptrace`). |
| **Application Boundary** | Worker output counter + token bucket | Terminal buffer exhaustion, WebSocket network saturation. |

---

## 5. Software Architecture: Monorepo Foundations & ASGI Lifecycles

### 5.1 Monorepo vs. Polyrepo Architecture
- **Coordinated Atomicity:** In distributed systems containing tightly coupled interfaces (FastAPI backend schemas, Celery worker payloads, frontend WebSocket frames), a polyrepo introduces synchronization friction and schema drift.
- **Unified CI/CD & Tooling:** Maintaining `backend/`, `worker/`, `frontend/`, and `docker/` within a single repository enables unified linting, synchronized database migrations, and atomic feature branch testing.

### 5.2 Asynchronous Server Gateway Interface (ASGI) vs. WSGI
- **WSGI Limitations:** The traditional Web Server Gateway Interface (PEP 3333) is fundamentally synchronous and request-response driven. Each HTTP connection occupies a dedicated worker thread or OS process, making it impossible to scale persistent WebSocket streams without exhausting operating system thread limits.
- **ASGI Concurrency:** ASGI decouples connection handling from execution using Python's `asyncio` event loop. A single OS process running Uvicorn can concurrently manage tens of thousands of idle or streaming WebSocket connections using asynchronous non-blocking multiplexing.

### 5.3 Asynchronous Database Connection Pooling (`asyncpg` + SQLAlchemy 2.0)
- **Non-Blocking I/O:** Traditional database drivers (like `psycopg2`) block the calling thread during query execution over TCP. `asyncpg` implements the PostgreSQL wire protocol directly over asyncio streams, allowing the web server to handle other incoming requests while waiting for PostgreSQL query responses.
- **Connection Pre-Ping & Leak Prevention:** Our pool configuration (`pool_pre_ping=True`, `pool_size=10`, `max_overflow=20`) proactively tests connections before issuing queries, preventing stale socket errors, while the scoped `get_db` async generator ensures that sessions are reliably rolled back and closed upon completion.

---

## 6. Execution Engine & Operating System Kernel Primitives

### 6.1 CPU Bandwidth Throttling via Completely Fair Scheduler (CFS) Quotas
- **Concept Learned:** Linux cgroups v2 CPU bandwidth controller (`cpu.max`).
- **Simple Explanation:** Rather than allocating an entire CPU core to a process, the Linux kernel slices time into periods (typically $100,000\mu\text{s} = 100\text{ms}$). The quota specifies how many microseconds within that period the process is allowed to run on the CPU.
- **Why It Matters:** Without CPU quotas, an untrusted script with an infinite loop (`while True: pass`) or spinning threads monopolizes 100% of the host CPU core, starving adjacent user jobs and driving CPU fan/power limits.
- **Where It Is Used in This Project:** In `DockerSandbox` configuration: `cpu_period=100000` and `cpu_quota=50000`. This guarantees untrusted code can consume at most 50% of one core ($0.5\text{ CPU}$), even if it spawns multiple worker threads.
- **Real-World Examples:** Kubernetes CPU limits (`resources.limits.cpu: "500m"`), AWS Lambda vCPU scheduling, LeetCode online judge CPU time limits.

### 6.2 The Linux Out-Of-Memory (OOM) Killer & Swap Suppression
- **Concept Learned:** Kernel memory cgroups (`memory.max`) and swap disablement (`memory.swap.max = 0`).
- **Simple Explanation:** When memory usage inside a cgroup hits `memory.max`, the Linux kernel triggers the Out-Of-Memory (OOM) killer. It assigns an `oom_score` to processes in the cgroup and terminates the offending process with signal 9 (`SIGKILL`, resulting in Linux exit code 137).
- **Why It Matters:** If swap is enabled, a malicious program allocating gigabytes of memory forces the host operating system to continuously swap memory pages to disk, causing extreme disk I/O thrashing ("swap death") that freezes the entire host machine. Disabling swap forces an instantaneous kill.
- **Where It Is Used in This Project:** In `DockerSandbox` parameters: `mem_limit="128m"` and `memswap_limit="128m"`. Container inspect state checks `OOMKilled == True` to accurately categorize the failure as `MEMORY_LIMIT_EXCEEDED` rather than a generic crash.
- **Real-World Examples:** Docker container memory limits (`--memory=128m --memory-swap=128m`), Google Cloud Run container memory ceilings.

### 6.3 Fork Bomb Neutralization via Process ID Controllers
- **Concept Learned:** Linux cgroups v2 PID controller (`pids.max`).
- **Simple Explanation:** Sets a hard ceiling on the number of processes and threads that can exist concurrently within the cgroup hierarchy.
- **Why It Matters:** In Unix, the global PID space is finite (default `/proc/sys/kernel/pid_max` is typically 32,768 or 4,194,304). A fork bomb (`while True: os.fork()`) rapidly exhausts the host kernel's PID table. Once exhausted, the host OS cannot execute basic administrative commands (`ps`, `kill`, `ssh`), causing total system paralysis.
- **Where It Is Used in This Project:** Configured in `DockerSandbox`: `pids_limit=64`. Spawning the 65th process or thread fails immediately with error code `EAGAIN` (`Resource temporarily unavailable`).
- **Real-World Examples:** Systemd `TasksMax` configuration, AWS Fargate task process limits.

### 6.4 System Call Filtering via Seccomp-BPF
- **Concept Learned:** Secure Computing Mode with Berkeley Packet Filters (Seccomp-BPF).
- **Simple Explanation:** A programmable firewall for Linux system calls. When a user program issues a syscall (e.g. `syscall(SYS_ptrace)`), the kernel runs a BPF bytecode filter in `ring 0`. If the syscall is not on the whitelist, the kernel immediately rejects it with `EPERM` or terminates the thread.
- **Why It Matters:** Container isolation relies on the shared host Linux kernel. Most container breakout exploits (e.g., Dirty COW, Dirty Pipe) exploit obscure kernel vulnerabilities in rarely used system calls. Dropping dangerous syscalls eliminates over 80% of potential kernel attack surfaces.
- **Where It Is Used in This Project:** In `docker/python/seccomp-profile.json` loaded by `DockerSandbox`. Prohibits `ptrace` (process debugging/tampering), `bpf` (kernel bytecode injection), `mount`/`chroot` (filesystem escape), and `reboot`.
- **Real-World Examples:** Docker's default Seccomp profile, Google Chromium browser sandbox, Cloudflare Workers sandbox.

### 6.5 POSIX Signals & The Watchdog Pattern
- **Concept Learned:** Difference between maskable signals (`SIGTERM` = 15) and unmaskable signals (`SIGKILL` = 9).
- **Simple Explanation:** A process can intercept, block, or completely ignore `SIGTERM` by registering a custom signal handler (`signal.signal(signal.SIGTERM, handler)`). However, `SIGKILL` cannot be caught, handled, or ignored—the Linux kernel scheduler instantly removes the process from the run queue.
- **Why It Matters:** Malicious student code might catch `SIGTERM` to prevent timeout termination. An execution watchdog must always use `SIGKILL` to guarantee that rogue infinite loops are annihilated.
- **Where It Is Used in This Project:** In `DockerSandbox` and `ProcessSandbox`: watchdog supervisors fire when `timeout_seconds` is reached, issuing `container.kill(signal="SIGKILL")` or `process.kill()`.
- **Real-World Examples:** Kubernetes pod eviction (sends `SIGTERM`, waits grace period, then issues `SIGKILL`), high-frequency trading watchdog daemons.

### 6.6 Volatile RAM Disks (`tmpfs`) & Read-Only Root Filesystems
- **Concept Learned:** In-memory Virtual Filesystem (`tmpfs`) mounts combined with `--read-only` rootfs.
- **Simple Explanation:** The container's root filesystem is mounted strictly read-only. The only writable location is `/tmp`, which is backed entirely by system RAM, capped at 16MB, and configured with `noexec,nosuid,nodev`.
- **Why It Matters:** Prevents malicious scripts from filling physical host hard drives, altering system binaries, or leaving residual malware files on the server. When the container terminates, the memory is instantly reclaimed by the kernel.
- **Where It Is Used in This Project:** In `DockerSandbox`: `read_only=True` and `tmpfs={"/tmp": "rw,noexec,nosuid,size=16m"}`.
- **Real-World Examples:** AWS Lambda ephemeral storage (`/tmp`), ephemeral CI/CD test runners.


