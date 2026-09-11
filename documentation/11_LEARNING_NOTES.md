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

