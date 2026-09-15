# Complete System Architecture & Operational Diagrams
## Secure Real-Time Remote Code Execution Laboratory Platform

**Document Version:** 2.0.0  
**Format:** Native GitHub Flavored Markdown / Mermaid.js  

---

## 1. Complete Distributed System Architecture

```mermaid
flowchart TB
    subgraph ClientTier ["Client Browser Tier"]
        UI["React 18 Single Page Application"]
        Monaco["Monaco Code Editor (Polyglot Runtimes)"]
        XTerm["xterm.js Interactive ANSI Terminal"]
        UI --- Monaco
        UI --- XTerm
    end

    subgraph IngressTier ["Ingress & Load Balancing"]
        Ingress["Kubernetes Ingress / Nginx Reverse Proxy"]
        TLS["TLS 1.3 Termination & OWASP Security Headers"]
        Ingress --- TLS
    end

    subgraph GatewayTier ["Backend API Gateway (FastAPI ASGI)"]
        Auth["JWT Authenticator (Argon2id)"]
        RateLimit["Sliding Window Rate Limiter (Redis ZSET)"]
        SubService["Submission & Autograding Service"]
        RoomService["Collaborative Room Service (CRDT Sync)"]
        WSHub["Full-Duplex Bidirectional WebSocket Hub"]
        OTel["OpenTelemetry Tracer (W3C traceparent)"]
    end

    subgraph BrokerTier ["Distributed Memory Backplane (Redis 7)"]
        Queue["Celery Task FIFO Queue"]
        PubSub["Pub/Sub Streaming Bus (rce:stream:id)"]
        ReplayBuffer["Circular Sequence Buffer (60s TTL)"]
        RoomSync["Collaborative Sync Channel (rce:room:sync)"]
    end

    subgraph ComputeTier ["Execution Compute Workers (Celery Fleet)"]
        Worker1["Celery Worker Daemon (Node 1)"]
        Worker2["Celery Worker Daemon (Node 2)"]
        Watchdog["Watchdog Timeout Supervisor (SIGKILL)"]
        PTY["POSIX PTY Session Manager (pty.openpty)"]
        Multiplexer["Stream Multiplexer (Byte Capper)"]
    end

    subgraph SandboxTier ["Pluggable Sandbox Execution Engines"]
        DockerBox["Hardened OCI Container Sandbox (cgroups v2 + Seccomp)"]
        MicroVMBox["Micro-VM Hardware Hypervisor (Linux KVM /dev/kvm)"]
        ProcessBox["Local Process Isolation (Testing Fallback)"]
    end

    subgraph PersistenceTier ["Durable Storage Tier"]
        Postgres[(PostgreSQL 16 StatefulSet with 10Gi PVC)]
        Backups[(Automated Backup PVC - Daily pg_dump CronJob)]
        Postgres -.-> Backups
    end

    %% Connections
    ClientTier ==>|HTTPS / REST| Ingress
    ClientTier ==>|WSS / Full-Duplex WebSockets| Ingress
    Ingress ==> GatewayTier
    GatewayTier --> BrokerTier
    GatewayTier --> PersistenceTier
    BrokerTier --> ComputeTier
    ComputeTier --> SandboxTier
    ComputeTier -.->|Stream Chunks| BrokerTier
    BrokerTier -.->|Live Output Push| GatewayTier
```

---

## 2. Six-Layer Concentric Sandbox Security Perimeter

```mermaid
flowchart LR
    UntrustedCode["Untrusted User Source Code"] --> L1

    subgraph L1 ["Layer 1: Ingress Microsegmentation"]
        Nginx["Nginx Reverse Proxy"]
        RL["Sliding Window Rate Limiter"]
        NP["K8s Default-Deny NetworkPolicy"]
    end

    L1 --> L2

    subgraph L2 ["Layer 2: Unprivileged Execution Envelope"]
        UID["Non-root UID 10001:GID 10001"]
        CapDrop["Capability Drop: CAP_DROP ALL"]
        PSS["PodSecurityStandard: Restricted"]
    end

    L2 --> L3

    subgraph L3 ["Layer 3: Namespace Boundary"]
        PIDNS["PID Namespace (Target is PID 1)"]
        NetNS["Network Namespace (--net=none)"]
        MountNS["Mount Namespace (pivot_root)"]
    end

    L3 --> L4

    subgraph L4 ["Layer 4: cgroups v2 Governance"]
        CPU["cpu.max (0.5 CPU Core CFS Quota)"]
        Mem["memory.max (128 MB Ceiling, Swap=0)"]
        PIDs["pids.max (64 Task Cap - Defeats Fork Bombs)"]
    end

    L4 --> L5

    subgraph L5 ["Layer 5: Seccomp-BPF Syscall Filter"]
        SyscallFilter["Blocks 350+ Dangerous Syscalls (ptrace, bpf, mount, clone3)"]
    end

    L5 --> L6

    subgraph L6 ["Layer 6: Micro-VM Hardware Hypervisor"]
        KVM["Linux KVM (/dev/kvm) Hardware Virtualization"]
        Ring1["Ring -1 Hypervisor Boundary (Guest Kernel Isolation)"]
    end

    L6 --> HostProtected["Host Operating System Kernel & Hardware 100% Protected"]
```

---

## 3. Asynchronous Execution Lifecycle Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User as Student / Browser
    participant API as FastAPI Gateway
    participant DB as PostgreSQL 16
    participant Redis as Redis 7 (Queue + Pub/Sub)
    participant Worker as Celery Worker
    participant Sandbox as Sandbox Engine (cgroups/KVM)

    User->>API: POST /api/v1/submissions (code, lang, stdin)
    API->>API: Rate Limiter (Redis ZSET Sliding Window)
    API->>DB: INSERT submission (status = PENDING)
    API->>Redis: LPUSH Celery Queue (with W3C traceparent)
    API-->>User: HTTP 202 Accepted (submission_id)

    User->>API: WebSocket Connect (/ws/v1/submissions/{id})
    API->>Redis: SUBSCRIBE rce:stream:{id}
    API->>Redis: Check Replay Buffer (rce:buffer:{id})

    Redis->>Worker: BRPOP Celery Queue (Prefetch=1)
    Worker->>Worker: Extract W3C TraceContext & Start Child Span
    Worker->>Sandbox: Initialize Sandbox Directory & cgroups limits
    Worker->>Worker: Start Watchdog Timer (5.0s SIGKILL limit)

    alt Polyglot Runtime (C/C++, Rust, Go)
        Worker->>Sandbox: Stage 1: Compile Code (-fstack-protector, PIE, RELRO)
        Sandbox-->>Worker: Compilation Diagnostics
    end

    Worker->>Sandbox: Stage 2: Execute Binary / Script
    loop Output Streaming
        Sandbox-->>Worker: Stdout / Stderr Chunks
        Worker->>Redis: PUBLISH rce:stream:{id} (monotonic seq frame)
        Worker->>Redis: RPUSH rce:buffer:{id} (60s TTL)
        Redis-->>API: Pub/Sub Message Received
        API-->>User: WebSocket Frame -> Render in xterm.js
    end

    opt Interactive Upstream Input
        User->>API: WebSocket Keystroke / Resize / Signal
        API->>Redis: PUBLISH rce:input:{id}
        Redis-->>Worker: Receive Upstream Event
        Worker->>Sandbox: Route to PTY stdin / ioctl TIOCSWINSZ / SIGINT
    end

    Sandbox-->>Worker: Process Exit (Status Code, Peak Memory)
    Worker->>Sandbox: Teardown & Reap Temporary Files
    Worker->>DB: UPDATE submission (status = SUCCESS / TLE / MLE, runtime_ms)
    Worker->>Redis: PUBLISH Final Execution Status
    Redis-->>API: Final Event Forwarded
    API-->>User: WebSocket Close (Execution Complete)
```

---

## 4. Kubernetes Production Deployment Architecture

```mermaid
flowchart TB
    subgraph K8sCluster ["Production Kubernetes Cluster (Namespace: rce-platform)"]
        subgraph IngressLayer ["Ingress Controller"]
            IngressResource["Ingress (rce-lab.local)"]
        end

        subgraph Workloads ["Microservice Deployments (PodSecurity: Restricted)"]
            FrontendPod["Frontend Deployment (nginx:alpine)\nReplicas: 2"]
            BackendPod["Backend API Deployment (FastAPI)\nReplicas: 2 to 8 (HPA)"]
            WorkerPod["Worker Deployment (Celery)\nReplicas: 2 to 20 (Queue-Depth HPA)"]
        end

        subgraph StatefulLayer ["Stateful Storage Tier"]
            RedisStateful["Redis 7 StatefulSet\nAppend-Only File (AOF) + 2Gi PVC"]
            PostgresStateful["PostgreSQL 16 StatefulSet\n10Gi PersistentVolumeClaim"]
        end

        subgraph ResilienceJobs ["Disaster Recovery & CronJobs"]
            BackupCron["PostgreSQL Backup CronJob\nDaily at 02:00 UTC -> 20Gi PVC"]
            PromRules["PrometheusRule Declarative Alerts\n(Queue Depth, 5xx Rate, OOM Kills)"]
        end

        subgraph HPAControllers ["Horizontal Pod Autoscalers (v2)"]
            HPABackend["HPA Backend (CPU: 70%, Mem: 80%)"]
            HPAWorker["HPA Worker (Custom Metric: rce_worker_queue_depth > 5)"]
        end
    end

    IngressResource ==> FrontendPod
    IngressResource ==> BackendPod
    BackendPod --> RedisStateful
    BackendPod --> PostgresStateful
    WorkerPod --> RedisStateful
    HPABackend -.-> BackendPod
    HPAWorker -.-> WorkerPod
    BackupCron -.-> PostgresStateful
```

---

## 5. Automated CI/CD GitOps Pipeline Architecture

```mermaid
flowchart LR
    subgraph GitEvents ["GitHub Repository Triggers"]
        PR["Pull Request -> develop"]
        PushMain["Push / Merge -> main"]
        Tag["Release Tag -> v*.*.*"]
    end

    subgraph CIWorkflows ["Continuous Integration (GitHub Actions)"]
        Linter["Job 1: Python Ruff Lint & Format Check"]
        Tester["Job 2: Pytest Full Suite (88/88 Tests)"]
        Typecheck["Job 3: Frontend TypeScript Typecheck (tsc)"]
        HelmLint["Job 4: Helm Chart Lint & Template Validation"]
    end

    subgraph SecWorkflows ["Security & Vulnerability Scanning"]
        TrivyScan["Aqua Security Trivy Scanner (CVE & Secrets)"]
        SeccompCheck["Seccomp-BPF Profile Integrity Validation"]
    end

    subgraph CDWorkflows ["Continuous Delivery (GHCR Registry)"]
        DockerBuild["Docker Buildx Multi-Arch Builds"]
        PublishImages["Publish Images to GHCR:\n• backend-api:v2.0.0\n• worker:v2.0.0\n• frontend-ide:v2.0.0\n• sandbox-python:v2.0.0"]
    end

    PR ==> CIWorkflows
    CIWorkflows ==> SecWorkflows
    PushMain ==> SecWorkflows
    Tag ==> CDWorkflows
```

---

## 6. OpenTelemetry Distributed Tracing Flow

```mermaid
flowchart TD
    Client["Client Request: POST /api/v1/submissions"] --> SpanRoot["Span 1: [FastAPI] POST /api/v1/submissions\n(TraceID: a1b2c3...4d5e, SpanID: 001)"]

    SpanRoot --> RateLimitSpan["Span 1.1: [RateLimiter] check_sliding_window"]
    SpanRoot --> DBSpan["Span 1.2: [PostgreSQL] insert_pending_submission"]
    SpanRoot --> InjectTrace["Inject W3C traceparent into Task Payload:\n'00-a1b2c3...4d5e-001-01'"]

    InjectTrace --> RedisQueue["Redis FIFO Queue (task_submissions)"]

    RedisQueue --> ExtractTrace["Celery Worker extracts traceparent carrier"]

    ExtractTrace --> SpanWorker["Span 2: [Celery Worker] rce.worker.sandbox_execution\n(TraceID: a1b2c3...4d5e, ParentSpanID: 001, SpanID: 002)"]

    SpanWorker --> SpanCompile["Span 2.1: [Polyglot] compile_source_code"]
    SpanWorker --> SpanExecute["Span 2.2: [Sandbox] execute_sandbox_binary"]
    SpanWorker --> SpanStream["Span 2.3: [Multiplexer] stream_stdout_chunks"]
    SpanWorker --> SpanDBUpdate["Span 2.4: [PostgreSQL] finalize_submission_metrics"]

    SpanRoot -.-> Jaeger["OpenTelemetry Collector / Jaeger APM Waterfall Visualization"]
    SpanWorker -.-> Jaeger
```
