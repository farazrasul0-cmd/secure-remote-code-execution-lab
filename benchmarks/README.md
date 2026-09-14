# Systems Benchmarking & Evaluation Suite
## Secure Real-Time Remote Code Execution Laboratory Platform

This directory contains the automated performance evaluation tools, load testing suites, and empirical research evaluation scripts for the platform.

---

## 1. Directory Structure

```
benchmarks/
├── benchmark_engine.py      # Automated Python evaluation harness (RQ1, RQ2, RQ3)
├── load_test_k6.js          # High-concurrency k6 load testing script
├── README.md                # Usage and reproduction instructions
└── results/                 # Output directory for empirical evaluation data
    ├── benchmark_report.json
    └── benchmark_report.md
```

---

## 2. Automated Python Benchmark Harness (`benchmark_engine.py`)

The benchmark harness conducts controlled experiments measuring:
1. **RQ1: Virtualization Overhead:** Bare-metal execution vs. sandbox isolation across 4 distinct algorithmic workloads.
2. **RQ2: Queueing & Scalability:** Throughput modeling using Little's Law ($L = \lambda W$) across varying worker concurrency levels.
3. **RQ3: Threat Containment:** Adversarial security verification (Fork bombs, Memory bombs, Network exfiltration, CPU loops).

### Running the Harness
From the repository root:
```bash
python benchmarks/benchmark_engine.py
```

Results are saved automatically to `benchmarks/results/benchmark_report.json` and `benchmarks/results/benchmark_report.md`.

---

## 3. Distributed Load Testing with k6 (`load_test_k6.js`)

The k6 script simulates realistic multi-tenant classroom traffic, ramping from 1 to 25 Virtual Users (VUs):
* Registers and authenticates test users with JWT tokens.
* Submits varying Python workloads (arithmetic, sorting, regular expressions).
* Evaluates API submission latency percentiles ($p50, p95, p99$).
* Validates sliding window rate limiting and `HTTP 429 Retry-After` handling.

### Running with k6
```bash
# Ensure the API gateway is running at http://localhost:8000
k6 run benchmarks/load_test_k6.js
```
