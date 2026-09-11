# System Architecture
## Secure Real-Time Remote Code Execution Laboratory Platform

This document describes the high-level system architecture of the platform. For full technical details, see the complete [System Architecture Specification](documentation/02_SYSTEM_ARCHITECTURE.md) and [System Design Decisions](documentation/19_SYSTEM_DESIGN_DECISIONS.md).

---

## 1. High-Level Architectural Topology

```mermaid
graph TD
    Client["Client Browser<br>(React + TypeScript + Monaco + xterm.js)"]
    
    subgraph Edge & Ingress
        FastAPI["API Gateway & WebSocket Server<br>(FastAPI / ASGI)"]
    end
    
    subgraph Data & Messaging Tier
        Postgres[(Primary Database<br>PostgreSQL 15+)]
        RedisQ[("Task Broker & Streaming Bus<br>Redis (Queue + Pub/Sub)")]
    end
    
    subgraph Compute & Execution Tier
        Workers["Worker Pool<br>(Celery / Async Daemon)"]
        
        subgraph Sandbox Isolation Boundary
            Sandbox["Ephemeral Sandbox Container<br>(Docker / OCI Runtime)"]
            cgroups["Linux cgroups v2<br>(0.5 CPU, 128MB RAM, 64 PIDs)"]
            seccomp["Seccomp Filter<br>(Blocked Dangerous Syscalls)"]
            tmpfs["In-Memory RAM Disk<br>(tmpfs /tmp max 16MB)"]
            netnone["Network Isolation<br>(--net=none)"]
        end
    end

    Client <==>|"HTTPS (REST) & WSS (WebSockets)"| FastAPI
    FastAPI ==>|"Persist User/Submissions"| Postgres
    FastAPI ==>|"LPUSH Job Payload"| RedisQ
    RedisQ ==>|"BRPOP Job"| Workers
    Workers ==>|"Spawn Ephemeral Container"| Sandbox
    Sandbox --- cgroups
    Sandbox --- seccomp
    Sandbox --- tmpfs
    Sandbox --- netnone
    Workers ==>|"Publish stdout/stderr Chunks"| RedisQ
    RedisQ -.->|"Pub/Sub Stream Relay"| FastAPI
    FastAPI -.->|"WebSocket Frame Relay"| Client
```

---

## 2. Core Architecture Highlights

- **Decoupled Asynchronous Processing:** FastAPI accepts submissions and buffers them in Redis, protecting the web server from compute starvation.
- **Real-Time Stream Multiplexing:** Sandbox standard output and error are streamed through Redis Pub/Sub directly to FastAPI WebSocket handlers and rendered in `xterm.js`.
- **Zero-Trust Hardened Isolation:** Unprivileged execution, read-only rootfs, in-memory `tmpfs`, zero network access (`--net=none`), and strict cgroups v2 resource quotas.
- **PostgreSQL Persistence:** ACID compliance for user accounts, submissions, and telemetry metadata.

---

## 3. Measurable Engineering Goals & Operational Limits

- **Execution Timeout:** Default **5.0 s** hard cutoff via watchdog timer.
- **CPU Limit:** **0.5 CPU core** (50% CFS scheduler quota via cgroups v2).
- **Memory Limit:** Hard limit of **128 MB** (swap disabled; OOM-killer armed).
- **Concurrency:** Target **50 concurrent streaming executions** per worker node.
- **Output Limit:** Maximum **1 MB** (or 10,000 lines) of output per run.
