# User & Operational Guide
## Secure Real-Time Remote Code Execution Laboratory Platform

**Document Version:** 1.0.0  
**Target Audience:** Students, Teaching Assistants, Instructors, and System Administrators  

---

## 1. User Roles & Permissions

The platform implements Role-Based Access Control (RBAC) with three distinct user personas:

| Role | Permissions & Capabilities |
| :--- | :--- |
| **Student / Learner** | - Write and execute code within the browser IDE.<br>- Supply interactive standard input (`stdin`).<br>- View live terminal output and error traces.<br>- Review personal execution history and telemetry. |
| **Instructor / TA** | - All Student capabilities.<br>- Inspect student submissions and historical telemetry for assigned labs.<br>- View aggregated execution statistics (error rates, average runtimes). |
| **System Administrator** | - All Instructor capabilities.<br>- Monitor worker queue health, active container count, and host resource utilization.<br>- Configure global security limits (timeouts, cgroup quotas, image registries). |

---

## 2. Student Workflow: Writing & Executing Code

```
[ Monaco Editor ] ──(Ctrl + Enter)──> [ Submit Job ] ──> [ Live WebSocket Stream ] ──> [ xterm.js Terminal ]
```

### 2.1 Account Authentication
1. Navigate to the platform landing page (`http://localhost:5173`).
2. Click **Register** to create an account with your university email, username, and password.
3. Upon login, the system receives a JSON Web Token (JWT) stored securely in client memory. All subsequent API and WebSocket requests automatically attach this bearer token.

### 2.2 The Interactive Workspace
The lab interface is divided into two primary synchronized panes:
- **Left Pane (Monaco Code Editor):**
  - Full-featured syntax highlighting for Python 3.11.
  - Line numbers, code folding, auto-indentation, and bracket matching.
  - Shortcut: Press `Ctrl + Enter` (or `Cmd + Enter` on macOS) to execute code immediately.
- **Right Top Pane (Standard Input `stdin` Panel):**
  - Collapsible text area to supply input data for programs requiring user prompts (e.g., `input()`, `sys.stdin.read()`).
- **Right Bottom Pane (Interactive Terminal / `xterm.js`):**
  - Emulates an ANSI/VT100 terminal.
  - Displays real-time, streaming `stdout` and `stderr` as your program generates it.

---

## 3. Interpreting Execution Outcomes

When code runs inside the sandbox, the system monitors its execution and displays an outcome status badge along with performance telemetry:

```
[ Status: TIME_LIMIT_EXCEEDED ]   Duration: 5002 ms   Memory: 18.4 MB   Exit Code: 137 (SIGKILL)
```

### Status Classification Table

| Status Badge | Meaning | Common Causes | Recommended Action |
| :--- | :--- | :--- | :--- |
| **`COMPLETED`** | Program executed to completion with exit code `0`. | Normal successful termination. | Review standard output in the terminal. |
| **`RUNTIME_ERROR`** | Program terminated with a non-zero exit code ($> 0$). | Uncaught Python exception (`ZeroDivisionError`, `IndexError`, `SyntaxError`). | Inspect the printed traceback in the terminal for line numbers. |
| **`TIME_LIMIT_EXCEEDED` (TLE)** | Process exceeded the **5.0 second** execution timeout. | Infinite loop (`while True:`), blocked I/O, or inefficient algorithm. | Verify loop termination conditions and algorithmic complexity ($O(N)$ vs $O(N^2)$). |
| **`MEMORY_LIMIT_EXCEEDED` (MLE)** | Process exceeded the **128 MB** RAM ceiling. Process terminated by Linux kernel OOM-killer (Exit Code 137). | Unbounded recursion, massive list allocations, memory leaks. | Profile data structures; avoid loading large datasets entirely into memory. |
| **`OUTPUT_LIMIT_EXCEEDED` (OLE)** | Program generated over **1 MB** (or 10,000 lines) of output. Output stream terminated. | Infinite loop containing `print()` statements. | Check loop exit conditions; avoid excessive debug logging. |
| **`RESOURCE_LIMIT_EXCEEDED`** | Program attempted to spawn more than **64 threads or child processes**. | Fork bombs or uncontrolled multiprocessing. | Keep execution within single or limited worker threads. |

---

## 4. Viewing Submission History & Telemetry

1. Navigate to the **History** tab in the top navigation bar.
2. The history view displays a chronological table of all past runs:
   - **Submission ID:** Unique UUID tracking the execution session.
   - **Timestamp:** Exact submission time.
   - **Status:** Outcome badge (Completed, TLE, MLE, etc.).
   - **Execution Time:** Wall-clock duration in milliseconds.
   - **Peak Memory:** Peak RAM consumption recorded by cgroups.
3. Click any historical entry to reload the exact code snapshot and review historical output logs.

---

## 5. Troubleshooting Common Issues

- **WebSocket Connection Failed:**
  - Verify that the backend server is running on port 8000.
  - Check browser console for authentication errors (expired JWT token). Refreshing the page will renew the session.
- **"Execution Engine Unavailable" Message:**
  - This indicates the Redis broker or Celery worker nodes are offline. Check that `celery -A tasks.worker` is active in the backend environment.
