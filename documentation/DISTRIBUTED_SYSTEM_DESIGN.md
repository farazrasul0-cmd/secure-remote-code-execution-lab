# Distributed Systems Design & Cloud Orchestration
## Secure Real-Time Remote Code Execution Laboratory Platform

**Document Version:** 2.0.0  
**Domain:** Distributed Systems, Asynchronous Queuing & Kubernetes Scheduling  
**Academic Target:** Systems Engineering & Distributed Scalability  

---

## 1. Architectural Motivation: Decoupling Compute from Web Sockets

In a multi-tenant laboratory system, execution workloads are inherently bursty, resource-intensive, and unpredictable. A synchronous model—where an incoming HTTP or WebSocket thread directly forks or launches a container—is fundamentally flawed:
1. **Thread Pool Exhaustion:** 100 students clicking "Run" simultaneously would consume 100 OS processes/threads, causing web server starvation and dropped HTTP connections.
2. **Cascading OOM Failures:** Uncontrolled concurrent compilation and execution spikes saturate host physical memory, inducing kernel panics.
3. **Impedance Mismatch:** Web connections are ephemeral and lightweight (managed efficiently by ASGI async event loops), whereas compute sandboxing is CPU and memory intensive.

To solve this, our platform decouples compute from web connections using a distributed producer-consumer message backplane powered by Celery and Redis.

---

## 2. Distributed Component Roles & Communication

```
┌─────────────────────────┐          ┌─────────────────────────┐
│   FastAPI Web Tier      │          │   FastAPI Web Tier      │
│   (Replica A)           │          │   (Replica B)           │
│   Manages Client WS #1  │          │   Manages Client WS #2  │
└────────────┬────────────┘          └────────────┬────────────┘
             │                                    │
             │ Enqueues Job                       │ Enqueues Job
             ▼                                    ▼
┌──────────────────────────────────────────────────────────────┐
│                  Redis 7 Distributed Backplane               │
│ • FIFO Job Queue: task_submissions                           │
│ • Pub/Sub Real-Time Bus: rce:stream:<submission_id>          │
│ • Replay Buffers: rce:buffer:<submission_id> (60s TTL)       │
└────────────┬────────────────────────────────────┬────────────┘
             │                                    │
             │ Consumes Task (Worker Prefetch=1)  │ Consumes Task (Worker Prefetch=1)
             ▼                                    ▼
┌─────────────────────────┐          ┌─────────────────────────┐
│   Celery Compute Worker │          │   Celery Compute Worker │
│   (Worker Pod 1)        │          │   (Worker Pod 2)        │
│   Hosts Sandbox Container│          │   Hosts Micro-VM Sandbox│
└─────────────────────────┘          └─────────────────────────┘
```

### 2.1 The Producer (FastAPI ASGI)
- Serves REST endpoints and terminates WebSocket connections.
- Ingests submissions, performs sliding-window rate limiting, commits the initial `PENDING` record to PostgreSQL, and pushes the execution payload into the Redis FIFO queue.
- Subscribes to the specific Redis Pub/Sub channel for that submission, forwarding streamed chunks into the client's WebSocket without doing any heavy compute.

### 2.2 The Message Broker & Streaming Bus (Redis 7)
- Acts as a high-throughput FIFO queue for task distribution.
- Functions as a low-latency Pub/Sub backplane transmitting stdout/stderr chunks across nodes.
- Maintains in-memory circular list buffers with 60-second TTLs to allow gapless reconnection replay.

### 2.3 The Consumer (Celery Worker Fleet)
- Worker instances pull jobs from Redis using a strict `prefetch_count=1` setting to prevent task hoarding and ensure fair distribution across workers.
- Spawns and supervises ephemeral sandbox environments (Docker or Micro-VM).
- Multiplexes stdout/stderr streams, enforces timeouts via watchdog timers, and publishes output chunks directly to Redis Pub/Sub.

---

## 3. Distributed Resilience Patterns

### 3.1 Replay Buffers for Network Partition Tolerance
In mobile and university campus networks, client WiFi connections frequently suffer transient drops. 
- **The Problem:** In a pure Pub/Sub architecture (*at-most-once delivery*), chunks emitted during a 3-second network reconnect are lost forever.
- **Our Solution:** Every stream chunk is stamped with a strictly monotonic sequence ID (`seq: 1, 2, 3...`) and appended to a circular Redis list (`rce:buffer:<submission_id>`). When the client reconnects, the WebSocket passes `last_sequence_id`. The server replays all missing frames before resuming live streaming, guaranteeing **gapless output reconstruction**.

### 3.2 Poison Pill Quarantining
- **The Problem:** If an adversarial user submits corrupted bytecode that crashes the worker's deserialization loop, a naive queue redelivers the task to the next worker, causing a cascading crash across the entire fleet.
- **Our Solution:** The worker wraps execution in a defensive isolation block. Unhandled exceptions are caught, quarantined, converted into a structured `SYSTEM_ERROR` execution payload, and committed without retry, protecting the cluster.

### 3.3 Dynamic Horizontal Pod Autoscaling (HPA) via Little's Law
Worker pod autoscaling cannot rely on CPU metrics alone because compute tasks spend time waiting on I/O or compilation. 
- We configure **Kubernetes HPA v2** to scale on the custom Prometheus metric `rce_worker_queue_depth`.
- According to **Little's Law** ($L = \lambda W$), queue depth directly reflects pending latency.
- We target a queue depth of **5 pending tasks per worker**, with immediate scale-up (0s stabilization window) and conservative scale-down (300s window) to eliminate thrashing.

---

## 4. Distributed Observability via W3C TraceContext

In an asynchronous queue-driven architecture, traditional stack traces terminate at the API boundary. To achieve complete observability:
1. **Context Injection:** When FastAPI accepts `POST /api/v1/submissions`, it creates a root span and serializes the standard W3C `traceparent` header (`00-{trace_id}-{span_id}-{flags}`) into the task payload.
2. **Context Extraction:** The Celery worker extracts the `traceparent` carrier upon task dequeue and instantiates a child span (`rce.worker.sandbox_execution`) sharing the exact same 128-bit `trace_id`.
3. **High-Cardinality APM Filtering:** Spans are tagged with OpenTelemetry semantic conventions (`rce.submission_id`, `rce.language`, `rce.status`, `rce.exit_code`), enabling microsecond-accurate latency attribution across HTTP ingestion, queue wait time, sandbox initialization, and execution.
