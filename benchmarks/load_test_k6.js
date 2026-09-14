// ==============================================================================
// k6 Load Testing & High-Concurrency Benchmark Suite
// Secure Real-Time Remote Code Execution Laboratory Platform
// ==============================================================================
//
// Execution Command:
//   k6 run --vus 25 --duration 60s benchmarks/load_test_k6.js
//
// Metrics Collected:
//   - http_req_duration (p50, p90, p95, p99)
//   - submission_latency
//   - rate_limit_rejections (HTTP 429)
//   - http_req_failed
// ==============================================================================

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

// Custom Telemetry Metrics
const submissionTrend = new Trend('submission_latency_ms');
const rateLimitHits = new Counter('rate_limit_hits_total');
const successfulSubmissions = new Rate('successful_submissions_rate');

export const options = {
  scenarios: {
    // Ramp up from 1 to 20 virtual users to measure degradation curve
    concurrency_stress: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '15s', target: 5 },   // Baseline load
        { duration: '30s', target: 15 },  // Peak university lab load
        { duration: '15s', target: 25 },  // Stress threshold (rate-limit triggering)
        { duration: '10s', target: 0 },   // Cool-down
      ],
      gracefulRampDown: '5s',
    },
  },
  thresholds: {
    // 95% of successful API submissions must complete within 250ms
    'http_req_duration{status:202}': ['p(95)<250'],
    // General API response latency
    http_req_duration: ['p(50)<50', 'p(95)<300'],
  },
};

const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8000';

// Realistic Student Code Workloads
const CODE_WORKLOADS = [
  // 1. Basic Arithmetic / Fibonacci
  `
def fib(n):
    return n if n <= 1 else fib(n-1) + fib(n-2)
print("Fibonacci(15) =", fib(15))
  `.trim(),

  // 2. Data Processing & Sorting
  `
data = [i ** 2 for i in range(500)]
data.sort(reverse=True)
print("Max processed value:", data[0])
  `.trim(),

  // 3. String Manipulation & Pattern Matching
  `
import re
text = "The quick brown fox jumps over 1337 lazy dogs in the cloud lab!"
words = re.findall(r'\\w+', text)
print("Word count:", len(words))
  `.trim(),
];

export function setup() {
  // Pre-authenticate a test user to acquire JWT Bearer Token
  const testEmail = `loadtester_${Date.now()}@example.com`;
  const password = 'BenchmarkPassword123!';

  // Register user
  const regPayload = JSON.stringify({
    email: testEmail,
    password: password,
    full_name: 'Load Tester Agent',
  });

  const regRes = http.post(`${BASE_URL}/api/v1/auth/register`, regPayload, {
    headers: { 'Content-Type': 'application/json' },
  });

  check(regRes, {
    'setup registration successful': (r) => r.status === 201 || r.status === 400,
  });

  // Login and acquire access token
  const loginForm = {
    username: testEmail,
    password: password,
  };

  const loginRes = http.post(`${BASE_URL}/api/v1/auth/login`, loginForm);
  check(loginRes, {
    'setup login successful': (r) => r.status === 200,
  });

  const token = loginRes.json('access_token');
  return { token: token };
}

export default function (data) {
  const token = data.token;
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };

  // Select random code workload
  const selectedCode = CODE_WORKLOADS[Math.floor(Math.random() * CODE_WORKLOADS.length)];
  const payload = JSON.stringify({
    language: 'python',
    code: selectedCode,
    stdin: '',
  });

  const startTime = Date.now();
  const res = http.post(`${BASE_URL}/api/v1/submissions`, payload, { headers: headers });
  const latency = Date.now() - startTime;

  if (res.status === 202) {
    submissionTrend.add(latency);
    successfulSubmissions.add(1);
    check(res, {
      'status is 202 Accepted': (r) => r.status === 202,
      'has valid submission_id': (r) => r.json('id') !== undefined,
    });
  } else if (res.status === 429) {
    rateLimitHits.add(1);
    check(res, {
      'rate limit triggered with Retry-After header': (r) => r.headers['Retry-After'] !== undefined,
    });
  } else {
    successfulSubmissions.add(0);
  }

  // Inter-arrival think time simulating student typing/submitting (1 to 3 seconds)
  sleep(Math.random() * 2 + 1);
}

export function teardown(data) {
  // Query live Prometheus metrics at conclusion of load test
  const metricsRes = http.get(`${BASE_URL}/metrics`);
  check(metricsRes, {
    'metrics scrape successful': (r) => r.status === 200,
  });
}
