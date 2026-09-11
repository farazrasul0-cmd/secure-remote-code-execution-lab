# Worker Service
## Secure Real-Time Remote Code Execution Laboratory Platform

The worker service is an autonomous, scalable background consumer daemon that:
1. Dequeues execution jobs from the Redis queue.
2. Spawns ephemeral, hardened Docker sandbox containers.
3. Attaches to `stdout` and `stderr` streams.
4. Streams execution output chunks to Redis Pub/Sub in real time.
5. Enforces wall-clock execution timeouts (5.0s) and resource constraints via cgroups v2.
6. Writes final execution telemetry back to PostgreSQL.
