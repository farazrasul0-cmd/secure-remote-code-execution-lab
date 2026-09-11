# Architecture Decision Records (ADRs)
## Secure Real-Time Remote Code Execution Laboratory Platform

This document captures the principal architectural decisions made for the platform, detailing the context, options considered, trade-offs, and final rationale.

---

## ADR-001: Selection of Execution Isolation Technology

### Status
Accepted

### Context
Executing arbitrary, untrusted user code poses critical security risks to the host operating system, including privilege escalation, denial of service (CPU/RAM exhaustion), network scanning, and container breakout. We must select an isolation mechanism that balances security depth, startup latency, operational complexity, and developer ergonomics.

### Options Considered
1. **Linux Process Sandboxing (`nsjail` / `isolate`):**
   - *Description:* Lightweight process isolation using direct Linux `clone()` syscall flags, namespaces, and `seccomp-bpf` filters.
   - *Pros:* Near-zero overhead (<10ms startup), negligible memory footprint.
   - *Cons:* Highly OS-specific (Linux kernel only), difficult to configure for complex interpreted runtimes (e.g., Python standard libraries, JVM), high barrier to local cross-platform development (Windows/macOS developers need custom VMs).
2. **Standard Docker Containers (`runc` with cgroups v2 & seccomp):**
   - *Description:* Standard OCI container runtime leveraging Linux namespaces (`pid`, `net`, `ipc`, `mnt`, `uts`), cgroups v2 resource controllers, unprivileged user namespaces, read-only root filesystems, and dropped capabilities (`CAP_DROP ALL`).
   - *Pros:* Universally portable across Linux, macOS, and Windows (via WSL2/Docker Desktop); mature language images; rich Python Docker SDK; rapid prototyping.
   - *Cons:* Shared Linux kernel; potential vulnerability to zero-day kernel exploits if misconfigured; cold-start latency (~300–800ms).
3. **Application Kernel Sandboxes (Google gVisor `runsc`):**
   - *Description:* User-space kernel that intercepts and implements Linux system calls in Go, completely separating untrusted code from the host kernel.
   - *Pros:* Virtualized kernel surface eliminates host kernel exploit risk while maintaining container API compatibility.
   - *Cons:* Syscall-heavy programs suffer significant performance degradation (2x–5x slowdown on file I/O); requires specialized Linux host kernel configuration not readily available in default Windows/macOS Docker environments.
4. **Hardware MicroVMs (AWS Firecracker):**
   - *Description:* Minimalist virtual machines running on KVM hypervisor.
   - *Pros:* True hardware-level virtualization isolation; sub-second boot times (~50ms); used in AWS Lambda.
   - *Cons:* Requires bare-metal Linux with `/dev/kvm` hardware virtualization support; cannot run inside nested standard container environments or standard developer laptops without hardware passthrough.

### Decision
Adopt **Standard Docker Containers with Hardened Isolation (cgroups v2, dropped capabilities, read-only rootfs, `tmpfs`, no network)** for MVP and Version 1.0.  
Maintain an abstraction layer (`ExecutionSandbox` interface) so the backend can transition to **Google gVisor (`runsc`)** or **AWS Firecracker** for production Linux deployments without refactoring application logic.

---

## ADR-002: Real-Time Communication Protocol (WebSockets vs. SSE vs. Polling)

### Status
Accepted

### Context
The platform requires bi-directional or continuous streaming of standard output, standard error, execution telemetry, and interactive standard input (`stdin`) between the user's browser and the remote execution container.

### Options Considered
1. **Short / Long Polling (HTTP REST):**
   - *Pros:* Simplest to implement, stateless.
   - *Cons:* Excessive network overhead, high latency, poor user experience (choppy terminal output), high database/broker query load.
2. **Server-Sent Events (SSE):**
   - *Pros:* HTTP-native, automatic reconnection, simple client-side `EventSource` API, low protocol overhead.
   - *Cons:* Unidirectional only (server $\rightarrow$ client). Supporting interactive terminal input (`stdin`) requires an auxiliary HTTP POST endpoint, introducing race conditions and correlation overhead between the incoming input stream and outgoing output stream.
3. **WebSockets (`RFC 6455`):**
   - *Pros:* Full-duplex persistent TCP connection over a single socket; minimal per-frame framing overhead (2–10 bytes); native support for bi-directional streaming (client sends `stdin`, server sends `stdout`/`stderr`); standard for terminal emulators like `xterm.js`.
   - *Cons:* State-holding connections require careful load balancing; firewall traversal can occasionally be restricted without proper WSS configuration.

### Decision
Adopt **WebSockets** for execution sessions. Full-duplex communication is essential for terminal interactivity (sending keystrokes/stdin and receiving stdout chunks simultaneously). Standard HTTP REST will handle authentication, code submission ingestion, and historical record retrieval.

---

## ADR-003: Asynchronous Task Distribution & Output Streaming Decoupling

### Status
Accepted

### Context
Code execution durations are nondeterministic (ranging from 50ms to 15s). The FastAPI web server must remain non-blocking and stateless. Furthermore, worker output must be streamed to the client in real time rather than buffered until task completion.

### Options Considered
1. **Synchronous Execution inside FastAPI Request Handler:**
   - *Pros:* No broker needed, single codebase.
   - *Cons:* Disastrous architectural anti-pattern. Spawning containers inside ASGI worker processes starves the event loop, causing connection drops, memory exhaustion, and total server failure under load.
2. **Celery with Redis Result Backend (Traditional Task Queue):**
   - *Pros:* Industrial standard for Python background processing, automatic retries, task scheduling.
   - *Cons:* Celery's result backend (`AsyncResult`) is designed for batch return values upon task completion. Passing incremental streaming output chunks through Celery result state polling introduces latency and excessive database/Redis load.
3. **Hybrid Architecture: Celery / Worker Pool for Dispatch + Redis Pub/Sub for Real-Time Streaming:**
   - *Pros:* Combines robust task routing and horizontal worker scalability with ultra-low-latency in-memory message publishing. The worker publishes output chunks to `exec:{submission_id}` in Redis; the FastAPI WebSocket handler subscribes to that channel and pushes frames downstream to the browser.
   - *Cons:* Requires maintaining two communication paths (Queue for dispatch, Pub/Sub for telemetry/stdio).

### Decision
Adopt the **Hybrid Architecture**:
- **Task Dispatch:** Enqueued to Redis and consumed by worker processes.
- **Stream Relaying:** Workers stream raw stdout/stderr chunks directly into **Redis Pub/Sub**, which the FastAPI WebSocket gateway relays to connected clients in real time.

---

## ADR-004: Primary Persistence & Telemetry Store

### Status
Accepted

### Context
The platform must store user identities, role-based access control (RBAC), code submission metadata, compiler/runtime options, execution telemetry (runtime, memory usage, exit codes), and audit trails.

### Options Considered
1. **Document Store (MongoDB):**
   - *Pros:* Flexible schema for execution telemetry and arbitrary output logs.
   - *Cons:* Weaker relational integrity for user accounts, lab assignments, and permissions; lacks robust transactional guarantees for audit trails.
2. **Relational Database (PostgreSQL):**
   - *Pros:* ACID compliance, relational integrity (foreign keys linking users to submissions), enterprise-grade indexing, mature connection poolers (`asyncpg`), and native **JSONB** support for flexible runtime telemetry metrics without sacrificing schema rigidity.
   - *Cons:* Requires schema migration management (handled via Alembic).

### Decision
Adopt **PostgreSQL 15+**. Core relational entities (Users, Roles, Submissions) use strictly typed columns, while heterogeneous execution metrics (cgroup statistics, compiler flags, error traces) are stored in indexed `JSONB` columns.

---

## ADR-005: Sandbox Filesystem & Mount Strategy

### Status
Accepted

### Context
When executing untrusted code, the container requires access to the source code file. Writing code to the host filesystem and bind-mounting it into the container introduces host disk I/O bottlenecks and potential directory traversal risks.

### Options Considered
1. **Host Bind Mount (`-v /host/path:/sandbox/path`):**
   - *Pros:* Easy to inspect files on the host for debugging.
   - *Cons:* Requires disk writes on the host VM; exposes host directory permissions; leaves leftover files on disk if the worker crashes before cleaning up.
2. **Docker Volumes:**
   - *Pros:* Managed by the Docker daemon.
   - *Cons:* Persistent state requires explicit garbage collection; high volume creation/destruction overhead.
3. **Memory-Backed `tmpfs` Mount (`--tmpfs /tmp:rw,noexec,nosuid,size=16m`):**
   - *Pros:* Code resides exclusively in RAM; zero host disk I/O; automatically purged from memory the instant the container terminates; `noexec` and `nosuid` flags prevent binary execution inside temporary directories; strict size ceiling prevents RAM exhaustion via disk-filling scripts.
   - *Cons:* Memory used counts against the container's memory ceiling.

### Decision
Adopt **`tmpfs` Memory-Backed Mounts** with a strictly enforced 16 MB limit and read-only container rootfs (`--read-only`). The source code is injected directly into memory, executed, and wiped upon container exit without touching physical disk.
