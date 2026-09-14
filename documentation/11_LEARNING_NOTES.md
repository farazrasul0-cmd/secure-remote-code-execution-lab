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

---

## 7. Distributed Systems: Worker Queuing, Stream Multiplexing & Fault Tolerance

### 7.1 Redis Queue (Lists) vs. Redis Pub/Sub
- **Concept Learned:** Decoupling task dispatch (storage/queuing) from real-time messaging (fan-out/broadcast).
- **Simple Explanation:** A Redis List (`LPUSH` / `BRPOP`) is a persistent FIFO queue that stores tasks until an available consumer dequeues them. Redis Pub/Sub (`PUBLISH` / `SUBSCRIBE`) is an ephemeral broadcast bus that delivers messages to currently active subscribers without retaining them.
- **Why It Matters:** Task dispatch requires durability and load leveling—if all workers are busy, submissions must wait safely in the queue. Stream chunks, by contrast, are ephemeral telemetry meant for an active WebSocket client; storing millions of transient stream chunks inside persistent database tables would destroy write throughput.
- **Where It Is Used in This Project:** Task dispatch uses Redis lists (`rce:submissions`), while real-time stdout/stderr frames are broadcast over Redis Pub/Sub channels (`rce:stream:<submission_id>`).
- **Real-World Examples:** Apache Kafka vs. RabbitMQ vs. WebSockets, live chat applications, continuous integration build log streaming (e.g. GitHub Actions).

### 7.2 Monotonic Sequence Numbering & Reconnection Replay
- **Concept Learned:** Monotonic sequence vectors in distributed stream delivery.
- **Simple Explanation:** Every output chunk generated by a sandbox is assigned an incremental integer sequence ($0, 1, 2, \dots$) by the `StreamMultiplexer`, and concurrently written to an in-memory Redis list buffer with a 60-second TTL.
- **Why It Matters:** In real-world networks, client WebSocket connections frequently drop (e.g., student switching Wi-Fi networks). Without sequence numbers, a reconnecting client either loses missed output or receives duplicates. With monotonic sequence numbers, the client simply asks: *"Give me chunks starting from sequence 42."*
- **Where It Is Used in This Project:** Implemented in `StreamMultiplexer` ([`worker/streaming/multiplexer.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/streaming/multiplexer.py)) and `StreamBuffer` ([`worker/streaming/buffer.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/streaming/buffer.py)).
- **Real-World Examples:** TCP packet sequence numbers (`SYN`/`ACK`), Kafka partition offsets, Raft consensus log indexes.

### 7.3 Fair Scheduling & The Prefetch Multiplier
- **Concept Learned:** Consumer prefetching and head-of-line blocking prevention in task workers.
- **Simple Explanation:** By default, task queue consumers (like Celery) prefetch batches of tasks (default `prefetch_multiplier = 4`) into local memory to minimize network roundtrips.
- **Why It Matters:** When tasks have wildly variable execution durations (e.g., Task A takes 100ms, Task B takes 15,000ms), prefetching causes severe head-of-line blocking. If Worker 1 prefetches 4 tasks that happen to be 15-second infinite loops, the remaining 3 tasks sit idle inside Worker 1's memory buffer while Worker 2 sits completely idle.
- **Where It Is Used in This Project:** In `worker/celery_app.py`, configured `worker_prefetch_multiplier = 1`. Each worker thread pulls exactly 1 job at a time and only requests another upon full completion, guaranteeing optimal load balancing across compute nodes.
- **Real-World Examples:** RabbitMQ `basic.qos(prefetch_count=1)`, AWS SQS message visibility batch tuning.

### 7.4 At-Least-Once Delivery & Late Acknowledgments (`task_acks_late`)
- **Concept Learned:** Message acknowledgment timing and worker failure recovery.
- **Simple Explanation:** In standard queuing, a worker sends an acknowledgment (`ACK`) to the broker the moment it receives a job, removing it from the queue. With *late acknowledgments*, the worker only sends the `ACK` after the task finishes executing.
- **Why It Matters:** If a worker host suffers a power outage, OOM crash, or kernel panic while executing user code, an early-ACK system loses the user's submission forever. With late acknowledgments (`task_acks_late=True` and `task_reject_on_worker_lost=True`), the broker detects the worker disconnect and automatically re-queues the submission for another healthy node.
- **Where It Is Used in This Project:** Enforced in `worker/celery_app.py`.
- **Real-World Examples:** Celery production best practices, SQS Dead-Letter Queues (DLQ), gRPC at-least-once streaming.

### 7.5 The Janitor Pattern: Distributed Resource Lease Reaping
- **Concept Learned:** Ephemeral resource lease expiration and automated garbage collection.
- **Simple Explanation:** Every resource spawned in a distributed system (like a Docker container) is tagged with metadata: creation timestamp and maximum lease duration (e.g. 30s). An independent background daemon periodically inspects all active resources and forcefully purges any resource that has outlived its lease.
- **Why It Matters:** If a worker process is killed abruptly (e.g. `kill -9` or node reboot), its in-flight Docker containers become "orphans," running indefinitely on the host and permanently consuming CPU, RAM, and network namespaces.
- **Where It Is Used in This Project:** In `JanitorReaper` ([`worker/janitor/reaper.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/janitor/reaper.py)), running periodically every 30 seconds via Celery Beat or asyncio background tasks.
- **Real-World Examples:** Kubernetes garbage collection (terminating orphaned pods and dangling volume attachments), AWS CloudFormation stack rollbacks, HashiCorp Nomad job reaper.

---

## 8. Backend API Gateway, Authentication & Asynchronous Persistence

### 8.1 Cryptographic Password Hashing: Bcrypt, Work Factors & Key Truncation
- **Concept Learned:** Adaptive password hashing algorithms, cryptographic salting, and key size constraints of the Blowfish cipher.
- **Simple Explanation:** Standard hash functions (like SHA-256 or MD5) are fast mathematical algorithms designed for data integrity. If used for passwords, attackers can calculate billions of guesses per second using GPUs or precomputed rainbow tables. Bcrypt incorporates a random 128-bit salt and an exponential "cost factor" ($2^{12} = 4096$ iterations) to make brute-force attacks computationally prohibitive.
- **Why It Matters:** In the event of a database compromise or SQL dump leak, salted bcrypt hashes prevent offline cracking. Furthermore, Bcrypt is based on the Blowfish block cipher, which has a strict architectural limit of 72 bytes on input keys. Unhandled long passwords either trigger runtime exceptions or are silently truncated; in our platform, passwords are explicitly clamped to 72 bytes before feeding into the native C-accelerated `bcrypt` library.
- **Where It Is Used in This Project:** Implemented in [`backend/app/core/security.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/backend/app/core/security.py) using `bcrypt.gensalt(rounds=12)` and `bcrypt.checkpw()`.
- **Real-World Examples:** NIST Special Publication 800-63B guidelines, Argon2id in modern password hashing standards, Linux `/etc/shadow` password storage.

### 8.2 Stateless Authentication: JSON Web Tokens (JWT) & Signature Verification
- **Concept Learned:** Stateless vs. stateful session management, symmetric cryptographic signing (HMAC-SHA256).
- **Simple Explanation:** A JSON Web Token consists of three base64url-encoded parts separated by periods: `Header.Payload.Signature`. The server cryptographically signs the header and payload using a server-side secret key (`HS256`). When a client presents the token in an `Authorization: Bearer <token>` header, any backend server can verify the signature and trust the payload (`user_id`, `exp`) without querying the database for a session row.
- **Why It Matters:** In high-throughput distributed systems, querying a central database for every single HTTP request and WebSocket handshake to validate user identity introduces massive database contention and latency. JWTs make the API gateway completely stateless, enabling horizontal scaling behind a round-robin load balancer.
- **Where It Is Used in This Project:** Built in [`backend/app/core/security.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/backend/app/core/security.py) and enforced via FastAPI dependency injection in [`backend/app/api/deps.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/backend/app/api/deps.py).
- **Real-World Examples:** OAuth2 / OpenID Connect (OIDC), Google Cloud Identity tokens, microservice authentication meshes.

### 8.3 Network Protocols: HTTP/1.1 Request-Response vs. WebSocket (RFC 6455) Full-Duplex Streaming
- **Concept Learned:** Protocol upgrade handshakes, framing, and persistent bidirectional TCP socket connections.
- **Simple Explanation:** HTTP is inherently half-duplex and request-driven: a client sends a request and waits for the server's response. For real-time terminal output, polling HTTP endpoints produces excessive latency and overhead (repeated TCP handshakes, TLS negotiation, and HTTP headers). WebSockets start with an HTTP `Upgrade: websocket` handshake and transition the underlying TCP socket into a bi-directional, framed, full-duplex communication channel.
- **Why It Matters:** A running terminal application in the sandbox (e.g. `for i in range(100): print(i); sleep(0.1)`) generates chunks incrementally. WebSockets allow the backend to push individual chunks to the browser with sub-millisecond network framing latency without requiring the browser to poll.
- **Where It Is Used in This Project:** In [`backend/app/api/v1/endpoints/websocket.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/backend/app/api/v1/endpoints/websocket.py), handling `/ws/v1/submissions/{id}` connections.
- **Real-World Examples:** Cloud IDE terminals (GitHub Codespaces, AWS Cloud9), multiplayer games, live trading platforms.

### 8.4 Event-Driven API Gateways: Decoupled WebSockets with Redis Pub/Sub
- **Concept Learned:** Pub/Sub backplane routing in multi-instance API gateways.
- **Simple Explanation:** When a user opens a WebSocket connection to the API gateway, the container executing their code might be running on a different physical worker node. The WebSocket server cannot directly read from the container's standard output. Instead, the API gateway subscribes to a Redis Pub/Sub channel (`rce:stream:<submission_id>`) and pumps received messages directly over the client's WebSocket connection.
- **Why It Matters:** This design decouples the API gateway tier from the worker execution tier entirely. If the API cluster has 5 instances and the worker cluster has 20 nodes, any API instance can service any user's WebSocket stream because Redis acts as the unified distributed message backplane.
- **Where It Is Used in This Project:** In [`backend/app/api/v1/endpoints/websocket.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/backend/app/api/v1/endpoints/websocket.py) with async Redis `pubsub.listen()`.
- **Real-World Examples:** Socket.io Redis Adapter, AWS API Gateway WebSocket integration with SQS/SNS, Slack messaging architecture.

### 8.5 Asynchronous Data Access: Non-Blocking I/O & Connection Pooling
- **Concept Learned:** Asynchronous database drivers (`asyncpg`), event loop concurrency, and session lifecycles.
- **Simple Explanation:** In traditional synchronous database programming (e.g. standard `psycopg2`), when a thread executes `SELECT * FROM submissions`, that thread is blocked while waiting for the network round-trip and disk read from PostgreSQL. In an asynchronous event loop (`asyncio`), `await db.execute(...)` yields execution back to the loop, allowing the server to handle thousands of concurrent requests on a single OS thread.
- **Why It Matters:** Synchronous blocking database calls quickly exhaust worker thread pools (e.g. 50 threads = 50 concurrent requests maximum). With async I/O (`asyncpg` + SQLAlchemy 2.0 async session), a single API process can comfortably handle thousands of simultaneous active connections with minimal memory footprint.
- **Where It Is Used in This Project:** In [`backend/app/db/session.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/backend/app/db/session.py) using `AsyncEngine` and `async_sessionmaker`, and throughout services with `AsyncSession`.
- **Real-World Examples:** High-concurrency financial trading engines, modern FastAPI / Go / Node.js web architectures.

---

## 9. Interactive Web Application: Terminal Emulation, Monaco & Stream Reconciliation

### 9.1 Virtual Terminal Emulation & ANSI Escape Sequences (ECMA-48 / VT100)
- **Concept Learned:** Pseudo-terminal interfaces, character cell grids, and in-band control sequences.
- **Simple Explanation:** Operating system kernels emit stdout/stderr as raw byte streams. When formatted for human consoles, programs emit ANSI escape sequences (`\x1b[31m` for red, `\x1b[0m` for reset, `\r` for carriage return). A virtual terminal emulator (like `xterm.js`) is an in-memory 2D character matrix parser that translates these escape codes into colored glyphs, handles cursor positioning, and scrolls active viewports.
- **Why It Matters:** Raw HTML tags like `<pre>` or `<textarea>` do not interpret ANSI control sequences. If a Python script outputs a traceback or progress bar, displaying it in `<pre>` produces unreadable escape garbage (e.g., `[31mError[0m`) and broken line feeds. With `xterm.js` and `convertEol: true`, the browser renders a genuine Linux terminal interface.
- **Where It Is Used in This Project:** Implemented in [`frontend/src/components/TerminalView.tsx`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/frontend/src/components/TerminalView.tsx) using `xterm.js` and `xterm-addon-fit`.
- **Real-World Examples:** Visual Studio Code integrated terminal, GitHub Codespaces, Hyper terminal, Alacritty, iTerm2.

### 9.2 Background Web Workers & Abstract Syntax Tree Tokenization (Monaco Editor)
- **Concept Learned:** Browser main thread offloading and asynchronous tokenization pipelines.
- **Simple Explanation:** Parsing code into an Abstract Syntax Tree (AST) for syntax highlighting, scope matching, and autocomplete is CPU-heavy. If executed on the browser's main JavaScript UI thread, user typing produces noticeable lag and dropped animation frames.
- **Why It Matters:** Monaco Editor runs its language service parsers inside isolated Web Workers. The main thread remains unblocked to render DOM updates at 60 FPS, providing a responsive development environment even when editing complex multi-line algorithms.
- **Where It Is Used in This Project:** Implemented in [`frontend/src/components/CodeEditor.tsx`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/frontend/src/components/CodeEditor.tsx) using `@monaco-editor/react`.
- **Real-World Examples:** Visual Studio Code, TypeScript Playground, CodeSandbox, Replit.

### 9.3 Stream Reconciliation, Monotonic Sequence Numbers & Jitter Buffering
- **Concept Learned:** Frame deduplication and sequence reconstruction in distributed network streams.
- **Simple Explanation:** In unpredictable network environments (mobile networks, Wi-Fi reconnection), WebSocket frames can be delayed, duplicated, or dropped. The backend tags each frame with an incremental integer sequence ($0, 1, 2, \dots$). The frontend stream consumer compares each incoming sequence against its highest recorded sequence. If `chunk.sequence <= highestSequence`, the chunk is discarded as a duplicate; if greater, it is appended to the terminal buffer.
- **Why It Matters:** Prevents duplicate print statements and corrupted terminal output during connection flushes or Redis buffer replays when a client reconnects.
- **Where It Is Used in This Project:** Enforced in [`frontend/src/hooks/useExecutionStream.ts`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/frontend/src/hooks/useExecutionStream.ts).
- **Real-World Examples:** Video streaming protocols (RTP / WebRTC packet sequencing), TCP packet reconstruction, TCP Reno/Cubic sliding windows.

### 9.4 Client-Side Terminal Buffer Management & Memory Leak Prevention
- **Concept Learned:** Bounded circular buffers vs. unbounded DOM growth.
- **Simple Explanation:** If an infinite loop prints 100,000 lines of output before being terminated by the watchdog timer, appending all 100,000 lines to the browser DOM consumes hundreds of megabytes of RAM, causing the browser tab to crash or become unresponsive.
- **Why It Matters:** By configuring `xterm.js` with `scrollback: 5000`, the terminal acts as a fixed-size ring buffer: new incoming lines displace the oldest lines once the 5,000-line limit is reached. Combined with the backend's 1MB output ceiling, this ensures zero client-side memory leakage under adversarial code submissions.
- **Where It Is Used in This Project:** Configured in [`frontend/src/components/TerminalView.tsx`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/frontend/src/components/TerminalView.tsx).
- **Real-World Examples:** Linux kernel `dmesg` circular ring buffer, log rotation daemons (`logrotate`), production server monitoring consoles.

---

## 10. System Hardening, Adversarial Testing & Observability

### 10.1 Adversarial Sandbox Testing: Fork Bombs, OOM Killers & Seccomp-BPF Whitelisting
- **Concept Learned:** Defensive kernel-level isolation against denial-of-service, exhaustion attacks, and privilege escalation.
- **Simple Explanation:** When running arbitrary user code, adversaries attempt attacks such as:
  1. *Process Table Exhaustion (Fork Bomb)*: An exponential process creation loop (`while True: os.fork()`) attempts to starve the host OS process table (`PID_MAX`), causing system panic. Linux cgroups `pids.max` strictly limits the container to 64 PIDs, returning `EAGAIN` (Resource temporarily unavailable) to rogue processes.
  2. *Memory Over-allocation (OOM Killer)*: Attempting to allocate unbounded memory (`bytearray(10**9)`). Linux cgroups `memory.max` constrains the container to 128MB. If exceeded, the Linux Out-Of-Memory (OOM) killer immediately terminates the process with `SIGKILL` (Exit 137).
  3. *Root Filesystem Mutation*: Writing to system directories (`/etc`, `/bin`, `/usr`) to install malware or compromise subsequent runs. Mounting the root filesystem `read_only: true` with a bounded volatile `tmpfs` at `/tmp` guarantees strict container immutability.
  4. *Network Ingress/Egress Tampering*: Attempting to connect to command-and-control servers, crypto miners, or local cloud metadata services (`169.254.169.254`). Setting `network_mode: "none"` disables the container's network stack entirely, preventing all TCP/UDP socket creation.
  5. *Kernel System Call Filtering (Seccomp-BPF)*: Unrestricted system calls expose the host kernel to zero-day vulnerabilities (e.g., `ptrace`, `bpf`, `mount`, `reboot`). A default-deny BPF filter (`SCMP_ACT_ERRNO`) blocks dangerous syscalls at the hardware/kernel boundary before code execution.
- **Why It Matters:** In a multi-tenant compute laboratory, user code cannot be trusted. Application-layer filters (e.g. checking code with regex) are easily bypassed by obfuscation (`__import__('o' + 's')`). True isolation must be enforced by the Linux kernel hardware boundary.
- **Where It Is Used in This Project:** Enforced in [`worker/app/core/sandbox.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/app/core/sandbox.py), configured in [`docker/python/seccomp-profile.json`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/docker/python/seccomp-profile.json), and verified in [`backend/tests/test_adversarial.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/backend/tests/test_adversarial.py).
- **Real-World Examples:** Google Cloud Run sandbox (gVisor), AWS Lambda Firecracker microVMs, Judge0, LeetCode submission engines.

### 10.2 Distributed Rate Limiting: Sliding Window Log vs. Fixed Window in Redis
- **Concept Learned:** Distributed sliding-window algorithm using Redis Sorted Sets (`ZSET`), atomic pipelining, and HTTP 429 throttling.
- **Simple Explanation:** Standard fixed-window counters (e.g., reset counter every 60 seconds) suffer from the *boundary burst problem*: a user can send 15 requests at 00:59 and another 15 requests at 01:01, resulting in 30 requests within 2 seconds without violating the 15 req/min limit. The Sliding Window Log algorithm stores each request timestamp as an element and score in a Redis Sorted Set (`ZSET`). For each incoming request:
  1. Remove expired timestamps older than `now - window_seconds` via `ZREMRANGEBYSCORE`.
  2. Count surviving timestamps via `ZCARD`.
  3. If count $\ge$ limit, calculate `retry_after` based on the oldest record and reject with HTTP 429.
  4. Otherwise, add the current timestamp via `ZADD`, set key expiration via `EXPIRE`, and permit the request.
- **Why It Matters:** All four operations execute inside an atomic Redis pipeline (`client.pipeline()`), eliminating race conditions across multiple load-balanced API gateway replicas without requiring distributed locks.
- **Where It Is Used in This Project:** Built in [`backend/app/core/rate_limiter.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/backend/app/core/rate_limiter.py) and applied to `POST /api/v1/submissions` in [`backend/app/api/v1/endpoints/submissions.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/backend/app/api/v1/endpoints/submissions.py).
- **Real-World Examples:** Stripe API rate limiting, Cloudflare DDoS protection, GitHub REST API rate headers (`X-RateLimit-*`, `Retry-After`).

### 10.3 Systems Observability: Prometheus Instrumentation & The Four Golden Signals
- **Concept Learned:** Metric types (Counters, Gauges, Histograms), Prometheus exposition format, and site reliability telemetry.
- **Simple Explanation:** Effective production operations require visibility into the Google SRE "Four Golden Signals": Latency, Traffic, Errors, and Saturation. We instrumented:
  - *Counter (`rce_submissions_total`)*: Monotonically increasing count tracking total submissions segmented by language (`python`) and status (`COMPLETED`, `FAILED`, `TIMEOUT`, `OOM_KILLED`).
  - *Histogram (`rce_execution_duration_seconds`)*: Bucketed distribution ($0.1s$ to $30.0s$) measuring sandbox runtime latency to compute $p50, p90, p99$ percentiles.
  - *Histogram (`rce_peak_memory_bytes`)*: Peak memory consumption across sandboxes to detect container memory bloat.
  - *Gauge (`rce_active_sandboxes`, `rce_queue_depth`)*: Real-time gauges indicating saturation and concurrency bottlenecks.
  - *Counter (`rce_rate_limit_hits_total`)*: Tracking throttling rejections per endpoint.
- **Why It Matters:** Metrics allow automated alerting (e.g. queue depth spiking, high error ratios) and horizontal autoscaling (HPA) of worker nodes before latency degrades user experience.
- **Where It Is Used in This Project:** Implemented in [`backend/app/core/metrics.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/backend/app/core/metrics.py), exposed via [`backend/app/api/v1/endpoints/metrics.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/backend/app/api/v1/endpoints/metrics.py), and verified in [`backend/tests/test_metrics.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/backend/tests/test_metrics.py).
- **Real-World Examples:** Prometheus & Grafana cloud monitoring, Datadog APM, AWS CloudWatch Metrics.

### 10.4 Multi-Tenant Fair Scheduling: Noisy-Neighbor Mitigation with Linux Cgroups v2
- **Concept Learned:** CFS (Completely Fair Scheduler) bandwidth control, CPU quotas (`cpu.cfs_quota_us`), and multi-tenant resource isolation.
- **Simple Explanation:** In a multi-tenant cloud environment, a "noisy neighbor" is a workload that monopolizes shared hardware resources (e.g., spinning on a tight loop `while True: pass`), starving neighboring concurrent workloads of CPU cycles. Linux cgroups enforce CFS bandwidth limits: by allocating `nano_cpus = 500,000,000` ($0.5$ CPU core), the kernel restricts the container's execution time to $50ms$ per $100ms$ scheduler period.
- **Why It Matters:** Even if a malicious or poorly written script consumes $100\%$ of its allocated CPU slice, the host Linux kernel CFS strictly deschedules it when its quota expires, guaranteeing predictable execution time and zero starvation for concurrent user submissions.
- **Where It Is Used in This Project:** Configured in [`worker/app/core/sandbox.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/app/core/sandbox.py) and benchmarked in [`backend/tests/test_noisy_neighbor.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/backend/tests/test_noisy_neighbor.py).
- **Real-World Examples:** Kubernetes pod CPU limits (`resources.limits.cpu`), AWS ECS task definitions, multi-tenant databases (Amazon Aurora Serverless).

---

## 11. Production Cloud Deployment, Benchmarking & Empirical Evaluation

### 11.1 Production Containerization: Multi-Stage Builds & Non-Root Execution
- **Concept Learned:** Multi-stage compilation pipelines, image size optimization, and unprivileged container security (`USER appuser`).
- **Simple Explanation:** Development containers contain compiler toolchains (`gcc`, `libpq-dev`), package managers (`npm`), and source code, resulting in images exceeding 1.2GB. Multi-stage builds compile artifacts in temporary builder stages and copy only runtime wheels and compiled static files to minimal base images (`python:3.12-slim`, `nginx:alpine`), reducing image footprint by 85%. Enforcing non-root execution (`UID 10001`) prevents root container breakout exploits.
- **Why It Matters:** Smaller images pull across cloud clusters in seconds rather than minutes, while the absence of compilers prevents attackers from compiling local rootkits in memory.
- **Where It Is Used in This Project:** Implemented in [`frontend/Dockerfile`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/frontend/Dockerfile), [`backend/Dockerfile`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/backend/Dockerfile), and [`worker/Dockerfile`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/Dockerfile).
- **Real-World Examples:** Google Distroless containers, Kubernetes Pod Security Standards (Restricted profile).

### 11.2 Micro-Segmentation: Dual-Network Isolation & Reverse Proxy Ingress
- **Concept Learned:** Zero-trust network segmentation and gateway reverse proxy architecture.
- **Simple Explanation:** In a cloud deployment, databases (PostgreSQL) and message brokers (Redis) should never be exposed to public internet interfaces. By partitioning containers into `rce_public_network` (only Nginx ports 80/443 exposed) and `rce_internal_network` (isolated bridge with zero host ports), internal backing services become completely unreachable from external network scans.
- **Why It Matters:** Eliminates external brute-force attacks, port probing, and unauthorized direct access to student submission records.
- **Where It Is Used in This Project:** Configured in [`deployment/docker-compose.prod.yml`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/deployment/docker-compose.prod.yml) and [`deployment/nginx.conf`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/deployment/nginx.conf).
- **Real-World Examples:** AWS VPC private subnets, Kubernetes network policies with Calico/Cilium.

### 11.3 High-Concurrency Load Testing & Little's Law Capacity Modeling
- **Concept Learned:** Synthetic load generation (k6), queueing theory, and Little's Law ($L = \lambda W$).
- **Simple Explanation:** In queueing systems, capacity is governed by Little's Law: $L = \lambda W$, where $L$ is concurrency, $\lambda$ is sustainable throughput, and $W$ is execution duration. Because compute execution (~170ms) is slower than API ingestion (~20ms), decoupled message queues absorb traffic surges without dropping tasks or deadlocking the API gateway.
- **Why It Matters:** Provides the mathematical basis for capacity planning, ensuring university lab clusters are sized correctly to avoid queue overflow.
- **Where It Is Used in This Project:** Scripted in [`benchmarks/load_test_k6.js`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/benchmarks/load_test_k6.js) and analyzed in [`benchmarks/benchmark_engine.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/benchmarks/benchmark_engine.py).
- **Real-World Examples:** Cloud capacity sizing, Black Friday e-commerce stress testing, SRE queue reliability engineering.

### 11.4 Academic Evaluation Methodology & Research Defense
- **Concept Learned:** Scientific method in systems software: Research Questions (RQs), empirical percentile distributions, and controlled testbeds.
- **Simple Explanation:** Rather than treating a project as a simple software application, research methodology evaluates trade-offs scientifically. We formulated RQ1 (Isolation Overhead), RQ2 (Worker Scaling), and RQ3 (Adversarial Robustness), collecting empirical metrics across multiple iterations to prove security and performance objectively.
- **Why It Matters:** This bridges professional software engineering with academic rigor, creating a defensible body of work for Master's thesis examinations and systems conference submissions.
- **Where It Is Used in This Project:** Documented in [`documentation/22_RESEARCH_VALUE.md`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/documentation/22_RESEARCH_VALUE.md) and [`benchmarks/results/benchmark_report.md`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/benchmarks/results/benchmark_report.md).
- **Real-World Examples:** USENIX OSDI / ACM SOSP research publications on container virtualization (gVisor, Firecracker).

---

## 12. Polyglot Execution Pipelines & Compiler Systems

### 12.1 Ahead-of-Time Compilation vs. Interpretation in Multi-Tenant Sandboxes
- **Concept Learned:** Decoupling language translation from native machine execution.
- **Simple Explanation:** Interpreted languages (Python, JavaScript) execute source code or bytecode directly within a managed VM runtime process. Ahead-of-Time (AOT) compiled languages (C, C++, Rust, Go) require a separate compilation and linking phase that produces an Architecture-specific ELF binary before any code can run.
- **Why It Matters:** Single-stage sandboxes fail for compiled languages because syntax errors and type mismatches must be captured during the compilation phase, reporting `COMPILE_ERROR` immediately rather than consuming execution time limits or reporting runtime crashes.
- **Where It Is Used in This Project:** Built into [`worker/sandbox/process_sandbox.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/sandbox/process_sandbox.py) and [`worker/sandbox/polyglot/`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/sandbox/polyglot/).
- **Real-World Examples:** Online judges (LeetCode, Codeforces, HackerRank), CI/CD pipelines (GitHub Actions, GitLab CI).

### 12.2 Asymmetric Two-Phase Sandbox Lifecycle: Compiler Quotas vs. Runtime Quotas
- **Concept Learned:** Resource asymmetry between compilation and execution.
- **Simple Explanation:** Compilers (`g++`, `rustc`) require high peak memory (512MB--1GB) and multi-core CPU power to parse ASTs, instantiate templates, and run optimization passes. In contrast, the student's compiled binary needs tight, restrictive memory limits (128MB) and 0.5 CPU core with no network access. Applying a single uniform cgroup quota introduces an impossible trade-off: either the compiler runs out of memory, or the untrusted runtime is over-provisioned.
- **Why It Matters:** By introducing an asymmetric two-phase sandbox lifecycle, the system provisions generous resources to the compiler while strictly constraining the resulting binary.
- **Where It Is Used in This Project:** Enforced in `ProcessSandbox.execute()` and `ProcessSandbox.stream_execute()`.
- **Real-World Examples:** Google Bazel hermetic build actions, Linux Kbuild system.

### 12.3 Binary Hardening: Stack Canaries, ASLR, Full RELRO & Template Caps
- **Concept Learned:** Compiler exploit mitigation flags and defensive compilation.
- **Simple Explanation:** Compilers can inject runtime defenses directly into machine code:
  - `-fstack-protector-strong`: Injects stack canaries to terminate on buffer overflows.
  - `-fPIE -pie`: Produces Position Independent Executables to enable kernel ASLR.
  - `-Wl,-z,relro,-z,now`: Full RELRO makes the Global Offset Table (GOT) read-only at launch.
  - `-z noexecstack`: Marks stack pages as non-executable (DEP/NX).
  - `-ftemplate-depth=128`: Caps C++ template metaprogramming recursion to prevent compiler OOM denial-of-service bombs.
- **Why It Matters:** Even if student code contains memory corruption bugs, these flags force deterministic crashes (`SIGSEGV`, `__stack_chk_fail`) instead of enabling arbitrary shellcode execution.
- **Where It Is Used in This Project:** Configured in [`worker/sandbox/polyglot/c.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/sandbox/polyglot/c.py) and [`worker/sandbox/polyglot/cpp.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/sandbox/polyglot/cpp.py).
- **Real-World Examples:** Debian Hardening Build Flags, Microsoft Visual C++ `/GS` and `/guard:cf`.

### 12.4 Strategy Design Pattern for Polyglot Extensibility (SOLID Principles)
- **Concept Learned:** Behavioral Strategy Pattern, factory registration, and Open/Closed Principle.
- **Simple Explanation:** Rather than using brittle `if/elif` statements inside the execution worker to handle different languages, the Strategy pattern encapsulates language-specific compilation and execution commands inside interchangeable classes inheriting from `BaseLanguageStrategy`.
- **Why It Matters:** The execution engine depends only on the abstract interface. Supporting a new language requires zero modifications to existing sandbox, scheduling, or streaming code.
- **Where It Is Used in This Project:** Implemented in [`worker/sandbox/polyglot/base.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/sandbox/polyglot/base.py) and registered in [`worker/sandbox/polyglot/registry.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/sandbox/polyglot/registry.py).
- **Real-World Examples:** VS Code Language Server Protocol (LSP), LLVM target architecture backends.

---

## 13. Automated Autograding, Oracle Verification & Information Hiding

### 13.1 Oracle-Based Verification & Deterministic Test Harnesses
- **Concept Learned:** Formal specification checking using deterministic test oracles.
- **Simple Explanation:** An Oracle represents ground-truth output corresponding to a given input tuple. An automated grading harness pipes input vectors into the student's isolated process, gathers standard output, and checks it against the Oracle.
- **Why It Matters:** Eliminates evaluation non-determinism. Each test case runs in a freshly initialized sandbox environment, ensuring that file descriptors, memory leaks, or lingering threads from previous test cases do not contaminate subsequent evaluations.
- **Where It Is Used in This Project:** Implemented in [`worker/grading/harness.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/grading/harness.py) and [`worker/grading/verifier.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/grading/verifier.py).
- **Real-World Examples:** Competitive programming platforms (LeetCode, Codeforces, HackerRank, Kattis).

### 13.2 Information Hiding & Security Isolation in Grading
- **Concept Learned:** Cryptographic/architectural separation of public sample vectors from private system test cases.
- **Simple Explanation:** If students can see all test vectors, they can easily hardcode answers (`if input == X: print(Y)`) rather than solving the algorithmic problem. By strictly partitioning test cases into visible samples and hidden grading suites, and scrubbing private vectors before serializing JSON to the client, the platform protects evaluation integrity.
- **Why It Matters:** Prevents data poisoning, oracle extraction attacks, and test cheating. Even if an adversary inspects network payloads via browser developer tools, hidden inputs and expected answers are scrubbed server-side.
- **Where It Is Used in This Project:** Enforced in `GradingHarness.sanitize_for_student()` and FastAPI endpoint schemas in [`backend/app/schemas/problem.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/backend/app/schemas/problem.py).
- **Real-World Examples:** ACM ICPC International Collegiate Programming Contest, University CS autograders (Autolab, Gradescope).

### 13.3 Per-Test Resource Accounting: Time Limit Exceeded (TLE) vs. Memory Limit Exceeded (MLE)
- **Concept Learned:** Asymptotic complexity enforcement via dual-layer kernel and application-level watchdog timers.
- **Simple Explanation:** Algorithms that have improper asymptotic time complexity (e.g., $O(N^2)$ instead of $O(N \log N)$) exceed CPU wall-clock thresholds (TLE). Solutions that allocate unbounded data structures or recursion depth trigger physical memory cgroup caps (MLE) or kernel OOM reaping.
- **Why It Matters:** Granular classification allows students to distinguish between algorithmic scaling bottlenecks (TLE) versus programmatic defects (Runtime Error / Segmentation Fault).
- **Where It Is Used in This Project:** Measured per test vector in [`worker/grading/harness.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/grading/harness.py).
- **Real-World Examples:** Google Code Jam, Meta Hacker Cup, TopCoder SRM.

### 13.4 Output Normalization & Diffing Strategies
- **Concept Learned:** Tolerant equivalence verification across platform line-endings and IEEE 754 precision artifacts.
- **Simple Explanation:** Direct byte-for-byte matching is brittle: CRLF (`\r\n`) vs LF (`\n`) differences or trailing line spaces can cause correct algorithms to fail. Furthermore, floating-point math incurs rounding errors. The platform implements output normalization (CRLF unification, trailing whitespace pruning) and $\epsilon$-relative error tolerance ($\frac{|a - b|}{\max(1.0, |b|)} \le 10^{-6}$) for numeric problems.
- **Why It Matters:** Prevents frustrating false-negative rejections while upholding rigorous algorithmic correctness.
- **Where It Is Used in This Project:** Built into [`worker/grading/normalizer.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/grading/normalizer.py) and [`worker/grading/verifier.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/grading/verifier.py).
- **Real-World Examples:** Codeforces `testlib.h` special judge checkers, Kattis problem verification suite.

---

## 14. Bidirectional Pseudo-Terminal (PTY) Architecture & Interactive Terminal Emulation

### 14.1 Linux PTY Architecture & Master/Slave Virtual Character Devices
- **Concept Learned:** Decoupling interactive user I/O from program execution using virtual character device pairs (`/dev/ptmx` and `/dev/pts/N`).
- **Simple Explanation:** Standard pipes (`pipe(2)`) are dumb unidirectional byte streams with no terminal semantics—processes connected to pipes automatically disable interactive features (line editing, terminal coloring, raw keystrokes). A Pseudo-Terminal (PTY) provides a bidirectional software terminal: the emulator (worker/server) holds the **master FD**, while the child process connects its `stdin`, `stdout`, and `stderr` to the **slave FD**. The child process believes it is attached to a real hardware teletype terminal (`isatty(3) == 1`).
- **Why It Matters:** Enables full interactive REPLs (Python interactive prompt, Bash, GDB, Node REPL) and full-screen TUI programs (vim, htop) to run seamlessly inside remote sandboxes.
- **Where It Is Used in This Project:** Built in [`worker/sandbox/pty_session.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/sandbox/pty_session.py) using `pty.openpty()`.
- **Real-World Examples:** SSH daemon (`sshd`), `tmux`, `screen`, Docker exec (`docker exec -it`), Visual Studio Code integrated terminal.
- **Master's Interview Explanation:** "Standard UNIX pipes provide half-duplex stream buffering without terminal discipline. A PTY is a bidirectional IPC channel implemented as a pair of virtual character devices. The master endpoint acts as the display server and keyboard driver, while the slave endpoint implements the POSIX line discipline (`termios`). Subprocesses spawned on the slave endpoint perceive an interactive TTY, allowing runtime libraries like libc and Python's readline to activate unbuffered interactive sessions."

### 14.2 Termios Line Discipline, Raw Mode vs. Cooked Mode, and ONLCR Translation
- **Concept Learned:** Kernel-level terminal line discipline manipulation via `termios`.
- **Simple Explanation:** In **cooked (canonical) mode**, the kernel line discipline buffers input line-by-line until the user presses Enter, handling backspace and line editing in the kernel. In **raw mode**, keystrokes are passed immediately to the program byte-by-byte as they are typed. Furthermore, UNIX systems use `\n` for newlines while physical terminals require `\r\n` (Carriage Return + Line Feed). The `ONLCR` output flag configures the slave terminal to automatically map `\n` to `\r\n`.
- **Why It Matters:** Without `ONLCR`, terminal output exhibits the "staircase effect" where each line prints further to the right without returning to the first column. Without raw mode capture on the client, interactive auto-completion and arrow-key navigation cannot function.
- **Where It Is Used in This Project:** Configured in [`worker/sandbox/pty_session.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/sandbox/pty_session.py) via `termios.tcgetattr` and `termios.tcsetattr`.
- **Real-World Examples:** Linux serial console drivers, `stty raw -echo`, SSH client terminal negotiation.

### 14.3 Terminal Geometry, Dynamic Resizing & SIGWINCH Signal Handling
- **Concept Learned:** Terminal viewport synchronization using `TIOCSWINSZ` ioctl and `SIGWINCH` kernel signals.
- **Simple Explanation:** The master terminal and child process must agree on columns (width) and rows (height). When a user resizes their browser window or changes font size, `xterm.js` emits a resize event. The backend forwards `{type: "resize", cols: N, rows: M}` through WebSocket and Redis to the worker. The worker packs dimensions into `struct winsize { unsigned short ws_row, ws_col, ws_xpixel, ws_ypixel; }` via `struct.pack("HHHH", ...)` and issues `fcntl.ioctl(master_fd, termios.TIOCSWINSZ, winsize)`. The kernel then delivers `SIGWINCH` (Window Size Changed) to the child process group.
- **Why It Matters:** Prevents text truncation, incorrect line wrapping, and broken TUI layouts during browser resizing.
- **Where It Is Used in This Project:** Handled in [`worker/sandbox/pty_session.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/sandbox/pty_session.py), [`frontend/src/components/TerminalView.tsx`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/frontend/src/components/TerminalView.tsx), and [`worker/tasks/execution.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/tasks/execution.py).
- **Real-World Examples:** Remote desktop clients, WebTTY implementations (Wetty, ttyd), Kubernetes `kubectl exec -it`.

### 14.4 OS Signals, Session Process Groups & SIGINT Keystroke Interception
- **Concept Learned:** Out-of-band asynchronous event delivery (`SIGINT`, `SIGTERM`, `SIGKILL`) across network boundaries.
- **Simple Explanation:** When a user types `Ctrl+C` in a physical terminal, the line discipline translates byte `\x03` into a `SIGINT` signal directed to the foreground process group. Over a network WebSocket connection, this must be captured on the frontend, transmitted as a structured frame (`{"type": "signal", "signal": "SIGINT"}`), and dispatched via `os.kill(child_pid, signal.SIGINT)` in the execution sandbox.
- **Why It Matters:** Prevents long-running or runaway interactive scripts (e.g., infinite loops) from permanently blocking the interactive terminal session.
- **Where It Is Used in This Project:** Dispatched in [`worker/sandbox/pty_session.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/sandbox/pty_session.py) and triggered by both keyboard (`Ctrl+C` / `\x03`) and UI interrupt button in [`frontend/src/components/TerminalView.tsx`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/frontend/src/components/TerminalView.tsx).
- **Real-World Examples:** POSIX signal architecture, Docker stop/kill signal propagation, Kubernetes termination grace period.

### 14.5 Full-Duplex Multiplexing via Bidirectional WebSocket & Distributed Redis Pub/Sub Backplane
- **Concept Learned:** Decoupling multi-replica web gateways from stateless execution workers via dual pub/sub event channels.
- **Simple Explanation:** Rather than tying a browser WebSocket directly to a specific worker process socket (which breaks horizontal scaling and load balancing), the architecture separates communication into two asynchronous channels:
  1. **Downstream Channel (`rce:stream:<id>`):** Transmits standard output, errors, and lifecycle events from worker to browser.
  2. **Upstream Channel (`rce:input:<id>`):** Transmits keystrokes, resize commands, and signals from browser to worker.
- **Why It Matters:** Any FastAPI replica can receive the client WebSocket, while any Celery worker node can execute the code container. Redis acts as a high-performance in-memory backplane with sub-millisecond dispatch latency.
- **Where It Is Used in This Project:** Orchestrated in [`backend/app/api/v1/endpoints/websocket.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/backend/app/api/v1/endpoints/websocket.py) and [`worker/tasks/execution.py`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/worker/tasks/execution.py).
- **Real-World Examples:** Enterprise message backplanes (Redis, Kafka, NATS), cloud IDE architectures (GitHub Codespaces, Gitpod, AWS Cloud9).

---

## 15. Cloud-Native Kubernetes Orchestration, Helm Packaging & Autoscaling

### 15.1 Deployments vs. StatefulSets & Stable Pod Network Identity
- **Concept Learned:** Kubernetes Deployments manage interchangeable stateless pods, while StatefulSets manage stateful workloads with stable ordinals, dedicated PersistentVolumeClaims, and headless DNS resolution.
- **Simple Explanation:** A Deployment creates pods with random names (`backend-7f8b4c-x9kzn`) that can be killed and replaced freely. A StatefulSet creates pods with predictable identifiers (`postgres-0`, `redis-0`) where each pod re-attaches to its own dedicated persistent storage upon rescheduling.
- **Why It Matters:** Databases require write-ahead log integrity. If a PostgreSQL pod restarts on a different node but mounts the wrong volume, data corruption or split-brain occurs. StatefulSets guarantee `postgres-0` always binds to `pvc-postgres-0`.
- **Where It Is Used in This Project:** StatefulSets for PostgreSQL and Redis in [`helm/rce-platform/templates/statefulset-postgres.yaml`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/helm/rce-platform/templates/statefulset-postgres.yaml) and [`statefulset-redis.yaml`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/helm/rce-platform/templates/statefulset-redis.yaml); Deployments for frontend, backend, and worker.
- **Real-World Examples:** Zalando Postgres Operator, Redis Sentinel, Apache Kafka brokers.

### 15.2 Pod Security Standards (PSS) & Restricted Admission Profile
- **Concept Learned:** Kubernetes namespace-level admission enforcement preventing privilege escalation via `pod-security.kubernetes.io/enforce: restricted`.
- **Simple Explanation:** The Restricted profile requires every container to: drop ALL Linux capabilities, run as non-root, set `allowPrivilegeEscalation: false`, use `readOnlyRootFilesystem: true`, and declare `seccompProfile: RuntimeDefault`. Any pod violating these constraints is rejected at admission time.
- **Why It Matters:** Prevents container breakout attacks (e.g., CVE-2024-21626 runc, Dirty COW kernel exploits) from escalating to host-level root access.
- **Where It Is Used in This Project:** Enforced at namespace level in [`namespace.yaml`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/helm/rce-platform/templates/namespace.yaml) and applied via `_helpers.tpl` security context templates.
- **Real-World Examples:** CIS Kubernetes Benchmark, PCI-DSS container compliance, DoD Iron Bank hardened images.

### 15.3 Zero-Trust NetworkPolicies & Microsegmentation
- **Concept Learned:** Distributed in-cluster firewalling using default-deny-all policies with label-selector whitelists.
- **Simple Explanation:** By default, every Kubernetes pod can reach every other pod. A `default-deny-all` NetworkPolicy blocks all ingress and egress. Then explicit rules open only the exact ports needed: frontend → backend (8000), backend → PostgreSQL (5432) and Redis (6379), worker → Redis (6379). Workers receive zero ingress.
- **Why It Matters:** If a student's sandbox code achieves arbitrary code execution, NetworkPolicies prevent lateral movement to databases, metadata services (`169.254.169.254`), or other student pods.
- **Where It Is Used in This Project:** Implemented in [`networkpolicies.yaml`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/helm/rce-platform/templates/networkpolicies.yaml) with 6 policies (default-deny, frontend, backend, worker, postgres, redis).
- **Real-World Examples:** Cilium eBPF microsegmentation, Calico tiered policy, AWS Security Groups for Pods.

### 15.4 Horizontal Pod Autoscaling (HPA v2) & Little's Law Queue-Depth Scaling
- **Concept Learned:** Autoscaling worker replicas based on custom Prometheus queue-depth metrics rather than CPU utilization.
- **Simple Explanation:** CPU-based HPA fails for I/O-bound or sleep-heavy workers: a sleeping process uses 0% CPU while thousands of tasks queue up. Instead, Little's Law ($L = \lambda W$) predicts that queue backlog ($L$) is the leading indicator. Worker replicas are calculated as $\text{Replicas} = \lceil \frac{\text{Queue Depth}}{\text{Target Per Worker}} \rceil$.
- **Why It Matters:** During deadline bursts (e.g., 200 students submitting at 11:59 PM), queue-depth HPA detects backlog within seconds and scales workers from 2 to 20 pods, maintaining sub-second queueing latency.
- **Where It Is Used in This Project:** Configured in [`hpa-worker.yaml`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/helm/rce-platform/templates/hpa-worker.yaml) with `rce_worker_queue_depth` custom metric (target: 5 per worker, max: 20 replicas).
- **Real-World Examples:** AWS SQS-based Celery autoscaling, Uber dispatch engine scaling.

### 15.5 Helm Chart Parameterization & Environment Portability
- **Concept Learned:** Packaging Kubernetes manifests into parameterized Helm charts with Go template syntax and centralized `values.yaml`.
- **Simple Explanation:** Instead of hardcoding image tags, replica counts, and database passwords in YAML, Helm templates reference `{{ .Values.worker.replicaCount }}` and `{{ .Values.postgres.env.POSTGRES_PASSWORD | b64enc }}`. Different environments (dev, staging, production) are configured simply by overriding values files.
- **Why It Matters:** Enables reproducible, one-command deployments (`helm install rce-lab ./helm/rce-platform`) across local minikube, cloud GKE/EKS/AKS clusters, and CI/CD pipelines.
- **Where It Is Used in This Project:** Full chart in [`helm/rce-platform/`](file:///d:/projects/real-time-remote-computer-lab-docs/real-time-remote-computer-lab-docs/helm/rce-platform) with 17 templates and `values.yaml`.
- **Real-World Examples:** CNCF Artifact Hub, Bitnami charts, Datadog Helm chart.










