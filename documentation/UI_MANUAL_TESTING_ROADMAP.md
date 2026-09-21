# End-to-End UI Manual Testing Roadmap & Verification Protocol
## Secure Real-Time Remote Code Execution Laboratory Platform (v2.0.0)

**Document Target:** Comprehensive Manual User Interface Verification Guide  
**Application URL:** [http://localhost:5173](http://localhost:5173)  
**API Gateway & OpenAPI UI:** [http://localhost:8001/docs](http://localhost:8001/docs)  
**Target Audience:** QA Engineers, SREs, Faculty Evaluators, and Frontend Developers  
**Primary Execution Browser:** Google Chrome / Microsoft Edge / Mozilla Firefox (latest versions)

---

## Testing Principles & Protocol Rules

> [!IMPORTANT]
> **Strict Execution Discipline:**
> 1. **Do Not Skip Phases:** Phases are designed as a sequential student and instructor journey. Complete each phase in order.
> 2. **Never Assume Automated Test Equivalence:** Even if backend integration tests pass, verify the actual browser rendering, DOM updates, CSS state badges, WebSocket events, and error alerts manually.
> 3. **Use Browser Developer Tools:** Keep Chrome DevTools open (`F12` -> **Console** and **Network** -> **WS** tabs) to monitor HTTP responses and live WebSocket frames.
> 4. **Record Issues Immediately:** If an anomaly is observed, log it in the [Bug Reporting Template](#bug-reporting-template) before proceeding.

---

## Progress Tracking Matrix

| Phase | Subsystem Under Test | Status | Date Tested | Tester Name | Blocker / Bug ID | Sign-Off |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Phase 1** | Environment & Application Startup | ✅ Passed | 2026-09-18 | Platform QA | None | Complete startup & cluster health verified |
| **Phase 2** | Authentication & User Session Lifecycle | ✅ Passed | 2026-09-18 | Platform QA | None | JWT register/login/persistence/logout verified |
| **Phase 3** | Workspace Layout, Navigation & Cluster Health | ✅ Passed | 2026-09-18 | Platform QA | None | Dynamic telemetry, navigation, and health badge verified |
| **Phase 4** | Monaco Code Editor UI & Stdin Drawer | ✅ Passed | 2026-09-18 | Platform QA | None | Polyglot boilerplate templates & stdin drawer verified |
| **Phase 5** | Standard Code Execution & Telemetry Dashboard | ✅ Passed | 2026-09-18 | Platform QA | None | Sub-second execution & telemetry telemetry cards verified |
| **Phase 6** | Virtual Terminal & Live Streaming UI | ✅ Passed | 2026-09-18 | Platform QA | None | Full xterm.js real-time chunk rendering & copy verified |
| **Phase 7** | Interactive PTY & Out-of-Band Signals (`Ctrl+C`) | ✅ Passed | 2026-09-18 | Platform QA | None | Full-duplex stdin streaming & SIGINT Ctrl+C verified |
| **Phase 8** | Polyglot Language Registry (C, C++, Rust, Go, JS) | ✅ Passed | 2026-09-18 | Platform QA | None | All 6 language toolchains compiling & executing verified |
| **Phase 9** | Algorithmic Problem Catalog UI | ✅ Passed | 2026-09-18 | Platform QA | None | Problem catalog, markdown descriptions & templates verified |
| **Phase 10** | Autograding Submission, Scorecard & Redaction | ✅ Passed | 2026-09-18 | Platform QA | None | Two Sum & Palindrome autograded 100/100, hidden cases redacted |
| **Phase 11** | Submission History, Audit Log & Code Replay | ✅ Passed | 2026-09-18 | Platform QA | None | Historical submissions listed, code replay & drawer verified |
| **Phase 12** | Collaborative Multi-User Rooms & Sync | ✅ Passed | 2026-09-18 | Platform QA | None | Room creation modal, 1-click join, live code & cursor sync verified |
| **Phase 13** | Monitoring, Prometheus Metrics & OpenAPI UI | ✅ Passed | 2026-09-18 | Platform QA | None | Prometheus `/metrics` scraped, Swagger `/docs` interactive verified |
| **Phase 14** | Adversarial Containment & Error Handling UI | ✅ Passed | 2026-09-18 | Platform QA | None | Infinite loop timeout, OOM kill, fork bomb & network isolation verified |
| **Phase 15** | Complete End-to-End Student User Journey | ✅ Passed | 2026-09-18 | Platform QA | None | Full assignment flow from onboarding to autograding verified |
| **Phase 16** | Production Readiness Sign-Off | ✅ Passed | 2026-09-18 | Lead SRE | None | 88/88 tests passing, Helm lint 0 errors, clean tree verified |

---

# Phase 1: Environment & Application Startup

### 1. Feature / Component
Host Infrastructure, Database Daemons, API Server, Worker Daemon, and Vite Frontend Dev Server.

### 2. Purpose
Confirm that all 5 required services are running, healthy, and network-accessible before launching the browser.

### 3. Required Services to be Running
- **PostgreSQL 15:** Docker container `rce_postgres_dev` on port `5432`
- **Redis 7:** Docker container `rce_redis_dev` on port `6379`
- **FastAPI API Gateway:** Running via Python venv on `http://localhost:8001`
- **Worker Daemon:** Running via Python venv executing `worker.daemon`
- **Vite React Frontend:** Running on `http://localhost:5173`

### 4. Exact Manual Steps
1. Open PowerShell and verify Docker containers:
   ```powershell
   docker ps --format "table {{.Names}}	{{.Status}}	{{.Ports}}"
   ```
2. Open a browser and navigate to: `http://localhost:8001/api/v1/health`
3. Navigate to: `http://localhost:5173`
4. Press `F12` to open Chrome DevTools. Check the **Console** tab for initial errors.

### 5. Buttons / Actions Used
- Browser URL Bar navigation
- DevTools Refresh (`Ctrl+F5` for hard reload)

### 6. Test Data / Code
N/A (Startup verification)

### 7. Expected Result
- Docker reports both `rce_postgres_dev` and `rce_redis_dev` as `Up (healthy)`.
- Navigating to `http://localhost:8001/api/v1/health` returns JSON:
  ```json
  {"status":"healthy","checks":{"database":"healthy","redis":"healthy"}}
  ```
- Navigating to `http://localhost:5173` renders the dark-themed Workstation UI immediately with zero unhandled JavaScript exceptions in the DevTools Console.
- In the top navigation bar, the cluster indicator displays: `Cluster Online` (with a pulsing green dot).

### 8. Possible Failure Symptoms
- Browser displays `ERR_CONNECTION_REFUSED` at `http://localhost:5173`.
- Cluster status pill displays `Cluster Offline` in red text.
- DevTools console displays CORS errors or network failure on `/api/v1/health`.

### 9. Logs to Check
- Frontend terminal: Vite compilation errors or port collision notices.
- Backend terminal: Uvicorn traceback or database connection refusal logs.
- Docker: `docker logs rce_postgres_dev` / `docker logs rce_redis_dev`.

### 10. Completion Checklist
- [ ] Docker containers verified active and healthy.
- [ ] Backend `/api/v1/health` reports status `healthy`.
- [ ] Frontend loads at `http://localhost:5173` with dark theme styling.
- [ ] Navbar displays `Cluster Online` with green pulsing badge.

---

# Phase 2: Authentication & User Session Lifecycle

### 2.1 Feature / Component
`AuthModal` (`components/AuthModal.tsx`), `Navbar` User Pill (`components/Navbar.tsx`), `AuthContext` (`context/AuthContext.tsx`).

### 2.2 Purpose
Validate registration of new student accounts, OAuth2 password grant login, JWT token persistence in `localStorage`, user role badge rendering, and clean sign-out.

### 2.3 Required Services to be Running
PostgreSQL, Redis, FastAPI Backend, Vite Frontend.

### 2.4 Exact Manual Steps
1. Navigate to `http://localhost:5173`.
2. Look at the top right of the Navbar. Click the button labeled **"Sign In / Register"**.
3. In the modal that appears, click the tab labeled **"Register"** (the modal title will change to **"Create Student Account"**).
4. Enter new student credentials:
   - **Username:** `test_student_ui`
   - **Email:** `test_student_ui@university.edu`
   - **Password:** `SecurePassword123!`
   - **Confirm Password:** `SecurePassword123!`
5. Click the primary button **"Create Account"**.
6. Observe the modal behavior and Navbar state.
7. Click the **"Sign Out"** icon button (door icon with arrow) in the Navbar user pill.
8. Click **"Sign In / Register"** again. Ensure the tab is set to **"Sign In"**.
9. Enter:
   - **Username or Email:** `test_student_ui`
   - **Password:** `SecurePassword123!`
10. Click **"Sign In"**.
11. Inspect `localStorage` via Chrome DevTools -> **Application** -> **Local Storage** -> `http://localhost:5173`. Look for key `rce_auth_token`.
12. Refresh the browser (`F5`). Verify the user remains logged in.

### 2.5 Buttons / Actions Used
- Button: `Sign In / Register` (Navbar)
- Tab: `Sign In` / `Register` (Modal toggle)
- Inputs: `Username`, `Email Address`, `Password`, `Confirm Password`
- Button: `Create Account` / `Sign In` (Modal footer)
- Button: `Sign Out` (Navbar user dropdown pill)
- Modal close: `x` button and background backdrop click

### 2.6 Test Data / Code
```text
Username: test_student_ui
Email: test_student_ui@university.edu
Password: SecurePassword123!
```

### 2.7 Expected Result
- Modal opens smoothly with backdrop blur (`bg-slate-950/80`).
- Registration creates account and closes modal immediately.
- Navbar replaces `Sign In / Register` with a rounded user pill showing:
  - Circular avatar with letter `"T"`
  - Username: `test_student_ui`
  - Subtitle badge: `STUDENT` (mono font, uppercase)
  - Sign Out button
- `localStorage` contains `rce_auth_token` with a valid JWT string (`eyJhbGci...`).
- Refreshing the page preserves session without requiring re-login.
- Clicking `Sign Out` removes token and restores `Sign In / Register` button.

### 2.8 Possible Failure Symptoms
- Password mismatch produces no validation feedback.
- Submitting displays red error alert: `Username already taken` or `HTTP 401: Unauthorized`.
- Page reload logs out the user unexpectedly.

### 2.9 Logs to Check
- DevTools Console: Network errors on `POST /api/v1/auth/register` or `/api/v1/auth/login`.
- Backend Terminal: Password hashing errors or database uniqueness constraint violations.

### 2.10 Completion Checklist
- [ ] Modal opens and toggles between Sign In and Register tabs cleanly.
- [ ] New user registration succeeds and auto-authenticates.
- [ ] User identity pill renders username and `STUDENT` role badge.
- [ ] Token is persisted in `localStorage` across page reload.
- [ ] Sign out terminates session cleanly and clears storage.

---

# Phase 3: Workspace Layout, Navigation & Cluster Health Monitor

### 3.1 Feature / Component
Application Shell (`App.tsx`), Navigation Bar (`Navbar.tsx`), Global Layout Grid.

### 3.2 Purpose
Verify responsive layout positioning, brand metadata, live cluster polling, and visual aesthetics of the laboratory environment.

### 3.3 Required Services to be Running
FastAPI Backend, Vite Frontend.

### 3.4 Exact Manual Steps
1. Navigate to `http://localhost:5173`.
2. Inspect the top header:
   - Verify logo icon (terminal glyph).
   - Verify title: `Secure RCE Platform`.
   - Verify version badge: `v1.0-prod`.
   - Verify subtitle: `Isolated Micro-Sandbox Lab & Real-Time Stream Engine`.
3. Locate the cluster health badge on the right of the header:
   - Verify it reads `Cluster Online` with a green pulsing dot.
4. Open the Network tab in DevTools, filter by `health`. Verify a polling request occurs every 15 seconds.
5. In your terminal, temporarily stop the backend (`Ctrl+C` in Terminal 2).
6. Wait 15 seconds and observe the cluster badge in the browser.
7. Restart the backend in Terminal 2:
   ```powershell
   .\backend\venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8001
   ```
8. Observe the cluster badge recover to green.

### 3.5 Buttons / Actions Used
- DevTools Network filtering
- Terminal service restart

### 3.6 Test Data / Code
N/A

### 3.7 Expected Result
- While backend is running, badge is green with text `Cluster Online`.
- When backend is terminated, badge dynamically turns red with text `Cluster Offline` without crashing the React application.
- When backend restarts, badge resumes `Cluster Online` automatically within 15 seconds.

### 3.8 Possible Failure Symptoms
- Badge stuck on `Checking cluster...` indefinitely.
- Badge stays red even after backend restart.
- Page layout breaks or causes horizontal scrollbar at standard 1920x1080 or 1440x900 resolution.

### 3.9 Logs to Check
- DevTools Network tab: inspect `/api/v1/health` response code (200 OK vs connection refused).

### 3.10 Completion Checklist
- [ ] Brand title, version badge, and subtitle render properly.
- [ ] Cluster health indicator reflects true backend state.
- [ ] Resilient recovery from backend restart verified.
- [ ] Split workstation columns (7-col editor, 5-col terminal) align properly.

---

# Phase 4: Monaco Code Editor UI & Stdin Drawer

### 4.1 Feature / Component
`CodeEditor` (`components/CodeEditor.tsx`), `StdinDrawer` (`components/StdinDrawer.tsx`), Monaco Editor React instance.

### 4.2 Purpose
Test code editing, syntax highlighting, keyboard shortcuts (`Ctrl+Enter`), boilerplate reset, and the collapsible Standard Input drawer.

### 4.3 Required Services to be Running
Vite Frontend, FastAPI Backend.

### 4.4 Exact Manual Steps
1. Log in as `student1` (`SecurePassword123!`).
2. Focus the Monaco Editor by clicking into the code area.
3. Observe initial content: should contain the Python 3.12 default starter code with syntax highlighting.
4. Type additional code into the editor (e.g. `print("Testing Monaco Editor")`).
5. Verify line numbering increments and cursor coordinates display properly.
6. Click the **Reset** button (`↺` icon) in the editor toolbar.
7. Verify that the editor content reverts to the default Python boilerplate.
8. Click the **"stdin"** button (`SlidersHorizontal` icon) in the editor toolbar.
9. Observe the drawer expand below the editor with the title `Standard Input (sys.stdin stream)`.
10. In the stdin textarea, enter:
    ```text
    Line 1: Sample Input
    Line 2: 42
    ```
11. Notice that the **stdin** button in the toolbar now displays an amber indicator dot.
12. Click the **"Clear"** button inside the stdin drawer. Verify textarea becomes empty and the amber dot disappears.
13. Click the **"x"** button on the stdin drawer to collapse it.

### 4.5 Buttons / Actions Used
- Monaco Editor text typing & cursor navigation
- Button: `↺` (Reset to boilerplate)
- Button: `stdin` (Toggle drawer)
- Textarea: Stdin drawer input
- Button: `Clear` (inside Stdin drawer)
- Button: `x` (Close Stdin drawer)

### 4.6 Test Data / Code
```python
# Custom editor input test
x = 100
y = 200
print(f"Sum = {x + y}")
```

### 4.7 Expected Result
- Monaco Editor loads with dark `vs-dark` theme and `Fira Code` font ligature support.
- Reset button replaces current code with official language boilerplate.
- Stdin drawer animates open/closed cleanly without shifting terminal layout.
- Amber badge correctly indicates non-empty pending standard input.

### 4.8 Possible Failure Symptoms
- Monaco fails to load and displays blank gray container.
- Reset button clears code to completely empty string instead of boilerplate.
- Stdin drawer cannot be closed or typing in textarea lags.

### 4.9 Logs to Check
- DevTools Console: Check for `@monaco-editor/react` loading or worker initialization errors.

### 4.10 Completion Checklist
- [ ] Syntax highlighting, indentation, and word wrap functional.
- [ ] Reset button restores default boilerplate.
- [ ] Stdin drawer opens, accepts multi-line text, and clears cleanly.
- [ ] Visual indicator dot reflects presence of stdin data.

---

# Phase 5: Standard Code Execution & Telemetry Dashboard

### 5.1 Feature / Component
Code Execution Dispatcher (`App.tsx` -> `handleRunCode`), `TelemetryPanel` (`components/TelemetryPanel.tsx`).

### 5.2 Purpose
Verify that clicking "Run" initiates an execution task, locks UI during execution, captures wall-clock duration, memory usage, exit code, and updates the telemetry status badge.

### 5.3 Required Services to be Running
PostgreSQL, Redis, FastAPI Backend, Worker Daemon, Vite Frontend.

### 5.4 Exact Manual Steps
1. Log in as `student1`.
2. Ensure language dropdown is set to **Python 3.12**.
3. Paste the following benign Python script into the editor:
   ```python
   import math
   results = [math.sqrt(i) for i in range(1, 1001)]
   print(f"Computed {len(results)} square roots.")
   print(f"Last value: {results[-1]:.4f}")
   ```
4. Click the green **"Run (Ctrl+Enter)"** button in the editor toolbar (or press `Ctrl+Enter` on your keyboard).
5. Watch the **"Run"** button change to `Executing...` with a spinning loader icon (`Loader2`).
6. Observe the **Telemetry Panel** below the terminal:
   - Status badge transitions to: `RUNNING IN SANDBOX` (with animated ping).
   - When execution finishes, status transitions to: `COMPLETED` (emerald green badge).
   - Inspect the 4 metric cards:
     1. **Wall Clock:** Displays duration (e.g. `450 ms` vs `Cap: 5000 ms`).
     2. **Peak Memory:** Displays memory (e.g. `14.2 MB` vs `Cap: 128 MB`).
     3. **Exit Code:** Displays `0` in green with label `Success`.
     4. **Stream Cap:** Displays `1.0 MB` with label `Truncation Guard`.
   - Containment specs display: `cgroups v2: cpu.max=50000/100000 | memory.max=128M | pids.max=64`, `--net=none`, `read-only rootfs`, `16MB tmpfs`.

### 5.5 Buttons / Actions Used
- Button: `Run (Ctrl+Enter)`
- Keyboard shortcut: `Ctrl+Enter` (Windows/Linux) or `Cmd+Enter` (macOS)

### 5.6 Test Data / Code
```python
import math
results = [math.sqrt(i) for i in range(1, 1001)]
print(f"Computed {len(results)} square roots.")
print(f"Last value: {results[-1]:.4f}")
```

### 5.7 Expected Result
- Button disables and shows spinner while running.
- Network tab registers `POST /api/v1/submissions` returning `HTTP 202 Accepted` or `200 OK` with submission `id`.
- Telemetry panel displays accurate wall-clock time and peak memory metrics.
- Exit code displays `0` in green.

### 5.8 Possible Failure Symptoms
- "Run" button does nothing or stays in `Executing...` state permanently.
- Browser alert: `Submission failed: ...`.
- Telemetry shows `Exit Code: -1` or `Abnormal Exit`.

### 5.9 Logs to Check
- Backend terminal: verify `POST /api/v1/submissions` 200/202 status.
- Worker terminal: verify `AsyncWorkerDaemon` picks up task from `rce:submissions` and outputs execution completion.

### 5.10 Completion Checklist
- [ ] Run button transitions to spinner during execution.
- [ ] Keyboard shortcut `Ctrl+Enter` triggers execution.
- [ ] Telemetry status badge reflects `RUNNING IN SANDBOX` then `COMPLETED`.
- [ ] Wall-clock time, memory usage, and exit code 0 displayed accurately.

---

# Phase 6: Virtual Terminal & Live Streaming UI

### 6.1 Feature / Component
`TerminalView` (`components/TerminalView.tsx`), `useExecutionStream` WebSocket hook, xterm.js Canvas/DOM engine.

### 6.2 Purpose
Verify that terminal output streams incrementally in real time over WebSockets with ANSI color support, xterm text selection, clipboard copy, and buffer clearing.

### 6.3 Required Services to be Running
PostgreSQL, Redis, FastAPI Backend, Worker Daemon, Vite Frontend.

### 6.4 Exact Manual Steps
1. Log in as `student1`.
2. Paste the following streaming countdown script into the editor:
   ```python
   import time
   print("\033[1;33m[START] Beginning real-time streaming test...\033[0m")
   for i in range(5, 0, -1):
       print(f"\033[1;34m-> T-minus {i} seconds\033[0m", flush=True)
       time.sleep(0.4)
   print("\033[1;32m[SUCCESS] Ignition and liftoff!\033[0m")
   ```
3. Click **"Run"**.
4. Observe the terminal pane:
   - Watch the terminal badge change from `IDLE` -> `CONNECTING...` -> `INTERACTIVE` (pulsing green dot).
   - Watch lines appear one-by-one at ~400ms intervals (NOT all at once at the end).
   - Observe ANSI color codes:
     - `[START]` in bold yellow (`\033[1;33m`).
     - `-> T-minus ...` in bold blue (`\033[1;34m`).
     - `[SUCCESS]` in bold green (`\033[1;32m`).
   - When execution finishes, badge updates to `COMPLETED`.
5. Click the **"Copy"** button in the terminal header:
   - Button text changes to `Copied` with a green checkmark for 2 seconds.
   - Paste clipboard into a text editor (Notepad) and verify copied text matches the terminal output.
6. Click the **"Clear"** button (`Trash2` icon) in the terminal header:
   - The terminal viewport clears completely.

### 6.5 Buttons / Actions Used
- Button: `Run`
- Button: `Copy` (Terminal toolbar)
- Button: `Clear` (Terminal toolbar)
- Mouse click: Focusing terminal canvas

### 6.6 Test Data / Code
```python
import time
print("[1;33m[START] Beginning real-time streaming test...[0m")
for i in range(5, 0, -1):
    print(f"[1;34m-> T-minus {i} seconds[0m", flush=True)
    time.sleep(0.4)
print("[1;32m[SUCCESS] Ignition and liftoff![0m")
```

### 6.7 Expected Result
- Live output chunks stream sequentially over WebSocket `ws://localhost:5173/ws/v1/submissions/{id}`.
- Terminal badge transitions seamlessly between states.
- ANSI escape codes format text with correct terminal colors.
- Copy button copies exact text buffer. Clear button purges screen.

### 6.8 Possible Failure Symptoms
- Output only appears all at once after 2 seconds (buffering bug).
- Terminal badge displays `CONNECTION ERROR` in red.
- ANSI escape codes appear as raw text (`\033[1;33m...`).

### 6.9 Logs to Check
- DevTools Network tab -> **WS** tab -> inspect `submissions/{id}` frames: check incoming frame messages have `sequence`, `data`, and `status`.
- Worker daemon log: verify `StreamChunk` publications to Redis `rce:stream:{id}`.

### 6.10 Completion Checklist
- [ ] Chunks arrive and render progressively at ~400ms intervals.
- [ ] ANSI escape sequences render in correct colors.
- [ ] Terminal badge reflects `INTERACTIVE` during stream and `COMPLETED` at conclusion.
- [ ] Copy button copies terminal buffer; Clear button empties terminal.

---

# Phase 7: Interactive PTY & Out-of-Band Signals (`Ctrl+C`)

### 7.1 Feature / Component
Bidirectional PTY Stdin (`TerminalView.tsx` -> `onData`), Out-of-band Signal Dispatch (`onSignal` -> `SIGINT`).

### 7.2 Purpose
Verify full-duplex interactive terminal execution: passing runtime inputs to Python `input()` statements and sending `Ctrl+C` interrupt signals to abort infinite loops.

### 7.3 Required Services to be Running
PostgreSQL, Redis, FastAPI Backend, Worker Daemon, Vite Frontend.

### 7.4 Exact Manual Steps

#### Test 7.A: Interactive `input()` prompt
1. Paste the following interactive prompt script:
   ```python
   name = input("Enter your name: ")
   print(f"Welcome to the Secure Lab, {name}!")
   age = input("Enter your age: ")
   print(f"In 5 years, you will be {int(age) + 5} years old.")
   ```
2. Click **"Run"**.
3. In the terminal pane, observe the prompt appear: `Enter your name: ` with a blinking cursor.
4. Click inside the terminal and type `Faraz`, then press **Enter**.
5. Observe immediate terminal echo: `Welcome to the Secure Lab, Faraz!`.
6. Observe second prompt appear: `Enter your age: `.
7. Type `24` and press **Enter**.
8. Observe final calculation: `In 5 years, you will be 29 years old.`.
9. Verify execution completes with exit code 0.

#### Test 7.B: Out-of-Band `Ctrl+C` (`SIGINT`) Interruption
1. Paste the following interruptible loop into the editor:
   ```python
   import time
   print("Infinite loop started. Press Ctrl+C to abort me!")
   try:
       while True:
           time.sleep(0.2)
   except KeyboardInterrupt:
       print("
Caught SIGINT! Graceful shutdown.")
   ```
2. Click **"Run"**.
3. Observe terminal displays: `Infinite loop started. Press Ctrl+C to abort me!`.
4. While running, click the **"Ctrl+C"** button (`Ban` icon) in the terminal toolbar (or click inside the terminal and press `Ctrl+C`).
5. Observe terminal immediately prints `^C` followed by:
   ```text
   Caught SIGINT! Graceful shutdown.
   ```
6. Execution terminates immediately with Exit Code `0` well before the 5.0-second watchdog expires.

### 7.5 Buttons / Actions Used
- Interactive typing inside the xterm canvas + **Enter** key
- Button: `Ctrl+C` (Terminal toolbar)
- Keyboard shortcut: `Ctrl+C` in active terminal

### 7.6 Test Data / Code
```text
Name input: Faraz
Age input: 24
```

### 7.7 Expected Result
- Keystrokes are captured by xterm, sent as `{"type":"stdin","data":"..."}` over WebSocket, received by worker, and injected into the container's PTY.
- The Python script receives input and responds immediately.
- `Ctrl+C` button dispatches `{"type":"signal","signal":"SIGINT"}`. Sandbox catches `KeyboardInterrupt` and exits cleanly.

### 7.8 Possible Failure Symptoms
- Typed characters do not appear or cannot be submitted with Enter.
- Prompt does not show until container times out with 137.
- Clicking Ctrl+C does nothing; script runs until 5-second watchdog kills it.

### 7.9 Logs to Check
- DevTools WS frames: verify upstream frames `{"type":"stdin","data":"Faraz\n"}` and `{"type":"signal","signal":"SIGINT"}`.
- Worker log: check `write_stdin` and `send_signal` execution.

### 7.10 Completion Checklist
- [ ] Interactive `input()` prompts displayed without trailing newline.
- [ ] User keystrokes sent and processed by live container.
- [ ] `Ctrl+C` button delivers `SIGINT` signal to active sandbox.
- [ ] Script catches `KeyboardInterrupt` and terminates gracefully.

---

# Phase 8: Polyglot Language Registry & Multi-Language Sandboxing UI

### 8.1 Feature / Component
Language Selector Dropdown (`CodeEditor.tsx`), Language Boilerplate Engine, Polyglot Compiler Workers.

### 8.2 Purpose
Verify that all supported programming languages (Python, C, C++, Rust, Go, JavaScript) load correct starter boilerplates, configure Monaco syntax modes, compile/execute in sandbox, and output correct results.

### 8.3 Required Services to be Running
PostgreSQL, Redis, FastAPI Backend, Worker Daemon, Vite Frontend.

### 8.4 Exact Manual Steps
Perform the following cycle for each language in the language selector dropdown:

1. **Python 3.12:**
   - Select `Python 3.12` from dropdown.
   - Verify header tag displays `Interpreted` and file is `main.py`.
   - Click **Run**. Verify output includes `=== Execution Environment Initialized ===` and exit code `0`.
2. **C17 (GCC 14):**
   - Select `C17 (GCC 14)` from dropdown.
   - Verify header tag displays `AOT Compiled` and file is `main.c`.
   - Verify boilerplate contains hardened GCC flags (`-O2 -fstack-protector-strong`).
   - Click **Run**. Verify output displays `Sum(1..100) = 5050` and exit code `0`.
3. **C++20 (G++ 14):**
   - Select `C++20 (G++ 14)` from dropdown.
   - Verify header tag displays `AOT Compiled` and file is `main.cpp`.
   - Click **Run**. Verify output displays `Calculated sum: 5050` and exit code `0`.
4. **Rust (rustc):**
   - Select `Rust (rustc)` from dropdown.
   - Verify header tag displays `AOT Compiled` and file is `main.rs`.
   - Click **Run**. Verify output displays `Calculated sum from vector: 5050` and exit code `0`.
5. **Go (1.22+):**
   - Select `Go (1.22+)` from dropdown.
   - Verify header tag displays `AOT Compiled` and file is `main.go`.
   - Click **Run**. Verify output displays `Calculated sum(1..100): 5050` and exit code `0`.
6. **JavaScript (Node 20):**
   - Select `JavaScript (Node 20)` from dropdown.
   - Verify header tag displays `JIT / Runtime` and file is `main.js`.
   - Click **Run**. Verify output displays `Calculated sum from array: 5050` and exit code `0`.

### 8.5 Buttons / Actions Used
- Dropdown select: `Python 3.12` / `C17 (GCC 14)` / `C++20 (G++ 14)` / `Rust (rustc)` / `Go (1.22+)` / `JavaScript (Node 20)`
- Button: `Run`

### 8.6 Test Data / Code
Default boilerplates loaded automatically upon language selection.

### 8.7 Expected Result
- Selecting each language immediately updates Monaco editor syntax highlighting, language tag, and file name.
- Code executes cleanly in the sandbox container with appropriate compiler/runtime toolchain.
- Exit code is `0` for all starter templates.

### 8.8 Possible Failure Symptoms
- Dropdown switches language but editor keeps previous language's code.
- Compilation error displayed in red in terminal (e.g. missing compiler flags).
- Dropdown disabled or unresponsive while idle.

### 8.9 Logs to Check
- Backend terminal: verify `POST /api/v1/submissions` payload has `"language": "<lang>"`.
- Worker terminal: verify compiler pipeline invocation (GCC, G++, rustc, go build, node).

### 8.10 Completion Checklist
- [ ] Python 3.12 executes and exits 0.
- [ ] C17 executes with stack protection and exits 0.
- [ ] C++20 executes with modern STL and exits 0.
- [ ] Rust executes memory-safe binary and exits 0.
- [ ] Go executes stripped binary and exits 0.
- [ ] JavaScript executes under Node 20 runtime and exits 0.

---

# Phase 9: Algorithmic Problem Catalog UI

### 9.1 Feature / Component
`ProblemPanel` (`components/ProblemPanel.tsx`), Problem Service REST client.

### 9.2 Purpose
Verify that student users can browse the algorithmic problem catalog, view difficulty levels, resource limits, problem descriptions, and sample test vectors.

### 9.3 Required Services to be Running
PostgreSQL, FastAPI Backend, Vite Frontend.

### 9.4 Exact Manual Steps
1. Log in as `student1`.
2. Look at the top panel titled **"Problem Catalog & Autograding"**.
3. Inspect the problem selector dropdown. Click it and verify the seeded problems:
   - `Two Sum Problem (EASY)`
   - `Valid Palindrome (EASY)`
   - `Nth Fibonacci Number (MEDIUM)`
4. Select **"Two Sum Problem (EASY)"**:
   - Verify the green difficulty badge: `EASY`.
   - Verify resource badges: `2000ms`, `128MB`, `4 Test Vectors`.
   - Read the problem description box: verify markdown problem statement, input format, output format, and example.
   - Inspect the **Sample Test Cases** cards:
     - Case #1 (Weight: 25 pts): Input `2 7 11 15\n9` -> Expected `0 1`.
     - Case #2 (Weight: 25 pts): Input `3 2 4\n6` -> Expected `1 2`.
5. Switch the dropdown to **"Valid Palindrome (EASY)"**:
   - Verify description updates to palindrome specifications.
   - Verify sample cases update (e.g. `racecar` -> `true`).
6. Switch the dropdown to **"Nth Fibonacci Number (MEDIUM)"**:
   - Verify amber difficulty badge: `MEDIUM`.
   - Verify description updates to Fibonacci specifications.

### 9.5 Buttons / Actions Used
- Dropdown: Problem selection (`Two Sum`, `Valid Palindrome`, `Nth Fibonacci`)
- Scroll: Problem description markdown container

### 9.6 Test Data / Code
N/A (Catalog inspection)

### 9.7 Expected Result
- Problem metadata, difficulty color coding, and resource limits render accurately.
- Switching problems instantly updates description and sample test cards without reload.
- Hidden test cases are NOT rendered in the problem catalog sample cases (information hiding).

### 9.8 Possible Failure Symptoms
- Dropdown is empty or displays `Loading problem specification...` permanently.
- Description markdown unformatted (raw text).
- Hidden test cases erroneously revealed in sample cases grid.

### 9.9 Logs to Check
- DevTools Network tab: inspect `GET /api/v1/problems` and `GET /api/v1/problems/{slug}` responses.

### 9.10 Completion Checklist
- [ ] Catalog loads all 3 seeded problems.
- [ ] Difficulty badges display correct color styles (green for EASY, amber for MEDIUM).
- [ ] Resource caps (2000ms, 128MB) and sample test vectors render clearly.
- [ ] Hidden test cases remain strictly concealed.

---

# Phase 10: Autograding Submission, Scorecard & Oracle Redaction UI

### 10.1 Feature / Component
`ProblemPanel` Submit Action, `GradingScorecard` Modal (`components/GradingScorecard.tsx`), Autograding Harness.

### 10.2 Purpose
Test algorithmic problem evaluation against full test suites, verify visual scorecards, test pass/fail indicators, and confirm cryptographic privacy redaction of hidden test cases.

### 10.3 Required Services to be Running
PostgreSQL, Redis, FastAPI Backend, Vite Frontend.

### 10.4 Exact Manual Steps

#### Test 10.A: Submit 100% Correct Solution to Two Sum
1. In the problem dropdown, select **"Two Sum Problem (EASY)"**.
2. Set language selector to **Python 3.12**.
3. Paste the following correct Two Sum solution into the editor:
   ```python
   import sys

   def solve():
       raw = sys.stdin.read().strip().splitlines()
       if not raw:
           return
       nums = list(map(int, raw[0].split()))
       target = int(raw[1])
       seen = {}
       for i, n in enumerate(nums):
           diff = target - n
           if diff in seen:
               print(f"{seen[diff]} {i}")
               return
           seen[n] = i

   if __name__ == "__main__":
       solve()
   ```
4. Click the purple gradient button **"Submit for Grading"** (`Sparkles` icon).
5. Observe the button state change to `Grading...` with a spinner.
6. The **Autograding Evaluation Scorecard** modal opens automatically:
   - Header shows: `Autograding Evaluation Scorecard`.
   - Overall Verdict badge: `Accepted` (emerald green).
   - Score Summary Card:
     - **Total Score:** `100 / 100` (large bold text).
     - **Percentage:** `100.0%` (green progress bar at full width).
     - **Test Cases:** `4 / 4 Passed`.
   - Resource Usage:
     - **Execution Time:** displays duration in milliseconds.
     - **Peak Memory:** displays memory in MB.
   - Test Vectors Breakdown (scrollable list):
     - **Case #1 (Sample):** `Accepted`, `25 / 25 pts`, displays input `2 7 11 15\n9` and expected `0 1`.
     - **Case #2 (Sample):** `Accepted`, `25 / 25 pts`, displays input `3 2 4\n6` and expected `1 2`.
     - **Case #3 (Hidden):** `Accepted`, `25 / 25 pts`, displays locked icon (`Lock`), with label `[REDACTED: HIDDEN TEST CASE]` for input and expected output!
     - **Case #4 (Hidden):** `Accepted`, `25 / 25 pts`, displays locked icon (`Lock`), with label `[REDACTED: HIDDEN TEST CASE]`!
7. Click the **"x"** button at the top right of the modal to close it.

#### Test 10.B: Submit Incorrect Solution (Wrong Answer)
1. In the editor, replace the code with a deliberately wrong solution:
   ```python
   print("999 999")
   ```
2. Click **"Submit for Grading"**.
3. When the scorecard modal appears, observe:
   - Overall Verdict badge: `WRONG_ANSWER` (rose red badge).
   - **Total Score:** `0 / 100` (`0.0%`).
   - **Test Cases:** `0 / 4 Passed`.
   - Sample cases show red `x` with actual output `999 999` vs expected.
   - Hidden cases still show `[REDACTED: HIDDEN TEST CASE]` (privacy preserved even on failure!).
4. Close the modal.

### 10.5 Buttons / Actions Used
- Button: `Submit for Grading` (in ProblemPanel header)
- Modal close: `x` button or backdrop click
- Modal scrollbar: Inspecting all 4 test vectors

### 10.6 Test Data / Code
Two Sum correct code (Test 10.A) vs wrong code (Test 10.B).

### 10.7 Expected Result
- Submitting opens the scorecard modal and evaluates synchronously or via worker.
- Correct solution scores `100/100`, status `ACCEPTED`.
- Wrong solution scores `0/100`, status `WRONG_ANSWER`.
- Hidden test cases ALWAYS redact inputs and expected outputs with `[REDACTED: HIDDEN TEST CASE]` for student accounts.

### 10.8 Possible Failure Symptoms
- Modal never opens or stays spinning indefinitely.
- Scorecard shows 0 points for correct solution.
- Hidden test case inputs leak to student view.

### 10.9 Logs to Check
- DevTools Network tab: inspect `POST /api/v1/problems/{slug}/submit` response JSON.
- Backend terminal: verify `GradingHarness` evaluation.

### 10.10 Completion Checklist
- [ ] 100% correct solution earns 100/100 and `ACCEPTED` badge.
- [ ] Scorecard displays percentage progress bar and resource metrics.
- [ ] Incorrect solution earns 0/100 and `WRONG_ANSWER` badge.
- [ ] Hidden test cases display `[REDACTED: HIDDEN TEST CASE]` in both pass and fail scenarios.

---

# Phase 11: Submission History, Audit Log & Code Replay UI

### 11.1 Feature / Component
`SubmissionHistory` Drawer (`components/SubmissionHistory.tsx`), Audit Log API.

### 11.2 Purpose
Verify that every execution and grading attempt is permanently logged, displays timestamps/metrics, and can be clicked to load historical code back into the Monaco editor.

### 11.3 Required Services to be Running
PostgreSQL, FastAPI Backend, Vite Frontend.

### 11.4 Exact Manual Steps
1. Log in as `student1`.
2. Look at the bottom of the page for the bar titled:
   `EXECUTION HISTORY & AUDIT LOG` with a badge showing record count (e.g. `X records`).
3. Click anywhere on the bar (or the chevron arrow `▲`) to expand the drawer.
4. Verify the table renders with columns:
   - **Language** (e.g. `python` badge)
   - **Status** (color-coded badge: `COMPLETED`, `WRONG_ANSWER`, `TIME_LIMIT_EXCEEDED`)
   - **Duration** (e.g. `450 ms`)
   - **Peak Memory** (e.g. `14.2 MB`)
   - **Timestamp** (formatted date and time)
   - **Action** (Code icon button `Load Code`)
5. Click the **Refresh** button (`RefreshCw` icon) in the drawer header to verify live updates.
6. Clear the Monaco editor so it is completely empty.
7. In the Submission History table, click the **"Load Code"** (`Code` icon) button on any previous successful submission.
8. Look at the Monaco Editor:
   - Verify the historical source code is restored instantly into the editor.
   - If the historical submission had stdin data, verify the Stdin Drawer opens with that data populated.
9. Click the chevron `▼` to collapse the drawer.

### 11.5 Buttons / Actions Used
- Bar click: Expand/collapse `Execution History & Audit Log`
- Button: `RefreshCw` (Refresh history records)
- Button: `Code` icon (Load Code into editor)

### 11.6 Test Data / Code
Historical submissions generated in Phases 5, 6, 7, and 10.

### 11.7 Expected Result
- History drawer expands smoothly to display up to 15 recent submissions.
- Statuses match actual outcomes (`COMPLETED` in green, `TIME_LIMIT_EXCEEDED` in amber, `RUNTIME_ERROR` in red).
- Clicking `Load Code` populates the editor with the exact historical code and stdin.

### 11.8 Possible Failure Symptoms
- History table displays `No execution records found` despite having run code.
- Clicking `Load Code` does not update the editor.
- Drawer does not expand or overlaps with page footer.

### 11.9 Logs to Check
- DevTools Network tab: inspect `GET /api/v1/submissions?page=1&size=15`.
- Database: query `SELECT count(*) FROM submissions;`.

### 11.10 Completion Checklist
- [ ] Drawer toggles between expanded and collapsed states.
- [ ] History records match previous runs with correct status colors and resource metrics.
- [ ] Clicking `Load Code` restores historical code and stdin into the active editor.
- [ ] Refresh button re-fetches records from backend.

---

# Phase 12: Collaborative Multi-User Rooms & Sync

### 12.1 Feature / Component
Collaborative Room API (`/api/v1/rooms`), Multi-User WebSocket Channel (`/ws/v1/rooms/{id}`), Dual-Client State Sync.

### 12.2 Purpose
Verify multi-user real-time laboratory workflows: room creation, dual-browser joining, presence broadcast, code delta synchronization, and shared execution triggers.

### 12.3 Required Services to be Running
PostgreSQL, Redis, FastAPI Backend, Vite Frontend.

### 12.4 Exact Manual Steps

#### Step 12.A: Setup Dual Browser Windows
1. Open **Window 1 (Standard Chrome)**:
   - Log in as `student1` (`SecurePassword123!`).
2. Open **Window 2 (Incognito / Private Window)**:
   - Navigate to `http://localhost:5173`.
   - Log in as `student2` (`SecurePassword123!`).
   *(If student2 is not yet registered, click "Register" and register `student2` / `student2@university.edu`).*

#### Step 12.B: Room Creation & Browsing via Visual UI (No DevTools Required)
1. In **Window 1 (Student 1)**:
   - Click the **"Collaborative Rooms"** button in the top navigation bar.
   - The **Collaborative Coding Rooms** modal will appear.
   - Switch to the **"Create New Room"** tab.
   - Fill in the room details:
     - **Room Name:** `Systems Lab Team Alpha`
     - **Programming Runtime:** `Python 3.12 (Isolated Sandbox)`
     - **Max Concurrent Members:** `10`
   - Click **"Create & Launch Room"**.
2. **Observe Window 1**:
   - The modal automatically closes, and the **Active Collaborative Room Session Banner** appears above the editor:
     `🟢 Systems Lab Team Alpha | PYTHON | 1 online (student@test.lab)`
   - The Monaco editor loads the room's initial code.
   - The top navbar displays a glowing green live session badge: `Systems Lab Team Alpha (1 online)`.

#### Step 12.C: Peer Joins Room via 1-Click Visual UI
1. In **Window 2 (Student 2 - Incognito)**:
   - Click the **"Collaborative Rooms"** button in the top navigation bar.
   - In the **"Active Rooms"** tab, verify `Systems Lab Team Alpha` appears with its `PYTHON` runtime badge and member count.
   - Click the **"Enter Room"** button on the `Systems Lab Team Alpha` card.
2. **Observe Both Windows**:
   - **Window 2** enters the room session banner: `🟢 Systems Lab Team Alpha | PYTHON | 2 online`.
   - **Window 1** automatically updates member count to `2 online` and shows Student 2 in the member list!
   - A transient notification appears informing Student 1 that `student2@university.edu joined the room`.

#### Step 12.D: Real-Time Code Sync & Cursor Movement Verification
1. In **Window 1**, type additional Python code into the Monaco editor, for example:
   ```python
   # Real-time collaboration test
   def calculate_metrics():
       return {"active_peers": 2, "status": "SYNCHRONIZED"}
   ```
2. **Observe Window 2**:
   - The code in Window 2 updates live in real-time as Student 1 types, without manual reloads!
3. In **Window 2**, move your cursor across lines in the editor or click on line 3.
4. **Observe Window 1**:
   - The editor toolbar displays the active peer indicator: `student2 L3:C1` with a pulsing beacon.
5. In **Window 2**, click **"Leave Room"** (or close the incognito window).
6. **Observe Window 1**:
   - Student 1 receives an immediate departure event and the active peer count returns to `1 online`.

*(Optional: You can also inspect the raw WebSocket frames in DevTools Network tab -> WS if you wish to verify the JSON payload schema).*

### 12.5 Buttons / Actions Used
- Top Navbar: **"Collaborative Rooms"** button / Live Session badge
- Modal: **"Create New Room"** and **"Active Rooms"** tabs
- Room Cards: **"Enter Room"** button
- Banner: **"Copy Room ID"** button & **"Leave Room"** button
- Monaco Code Editor: live typing synchronization and remote cursor beacon

### 12.6 Test Data / Code
Room name: `"Systems Lab Team Alpha"`  
Initial code: `# Collaborative Room Session\nprint('Hello from Team Alpha!')\n`

### 12.7 Expected Result
- Both students connect to the room WebSocket endpoint concurrently.
- Presence frames (`joined` and `left`) are broadcast immediately upon connection state change.
- Code deltas and cursor coordinates propagate bi-directionally across the Redis Pub/Sub room channel in real time.

### 12.8 Possible Failure Symptoms
- WebSocket connection rejected with code `1008` (Policy Violation / Unauthenticated).
- Messages sent by Student 1 never arrive in Student 2 console.
- Redis disconnects room pubsub unexpectedly.

### 12.9 Logs to Check
- Backend terminal: verify `ws/v1/rooms/{id}` connection logs and pubsub subscriptions.
- Redis: `redis-cli PUBSUB CHANNELS "rce:room:*"` confirms active channel.

### 12.10 Completion Checklist
- [ ] Room created and listed in database.
- [ ] Both clients connect with distinct JWT tokens.
- [ ] Student 1 observes Student 2 presence `joined`.
- [ ] Code delta and cursor move synchronize between both windows.
- [ ] Disconnection dispatches clean presence `left` event.

---

# Phase 13: Platform Observability, Metrics & OpenAPI UI

### 13.1 Feature / Component
Prometheus Metrics Scraping Endpoint (`/metrics`), OpenAPI Swagger UI (`/docs`), ReDoc Documentation (`/redoc`).

### 13.2 Purpose
Verify that site reliability engineers and instructors can inspect live Prometheus metrics, review API documentation, and interactively execute endpoints from the Swagger UI.

### 13.3 Required Services to be Running
FastAPI Backend, Vite Frontend.

### 13.4 Exact Manual Steps
1. In your browser, open a new tab and navigate to: `http://localhost:8001/metrics`.
2. Inspect the raw text output. Look for key platform metrics:
   - `rce_submissions_total{language="python",status="..."}`
   - `rce_execution_duration_seconds_bucket{...}`
   - `rce_memory_peak_bytes_bucket{...}`
   - `rce_active_sandboxes`
   - `rce_queue_depth`
   - `rce_rate_limit_hits_total`
3. Navigate to: `http://localhost:8001/docs`.
4. Observe the interactive OpenAPI Swagger UI:
   - Verify page title: `Secure Remote Code Execution Lab - API Documentation`.
   - Verify all tagged router groups exist:
     - `Authentication` (`/api/v1/auth/*`)
     - `Submissions & Sandbox Execution` (`/api/v1/submissions/*`)
     - `Problems & Autograding` (`/api/v1/problems/*`)
     - `Collaborative Rooms` (`/api/v1/rooms/*`)
     - `Polyglot Languages` (`/api/v1/languages`)
     - `System Health` (`/api/v1/health`)
5. Click on the green **"Authorize"** button at the top right:
   - Enter `username`: `student1`, `password`: `SecurePassword123!`.
   - Click **Authorize** and then **Close**.
6. Expand `GET /api/v1/languages` -> click **"Try it out"** -> click **"Execute"**:
   - Verify `Response body` returns status 200 with all 6 supported languages.
7. Expand `GET /api/v1/problems` -> click **"Try it out"** -> click **"Execute"**:
   - Verify `Response body` returns array of 3 seeded problems.
8. Navigate to: `http://localhost:8001/redoc`.
   - Verify clean ReDoc technical specification renders with schemas.

### 13.5 Buttons / Actions Used
- URL navigation: `/metrics`, `/docs`, `/redoc`
- Button: `Authorize` (Swagger UI modal)
- Button: `Try it out` -> `Execute`

### 13.6 Test Data / Code
Swagger OAuth2 authentication using `student1` / `SecurePassword123!`.

### 13.7 Expected Result
- `/metrics` exposes valid Prometheus text-formatted counters, histograms, and gauges.
- Swagger UI renders with complete schema models and allows authorized execution.
- ReDoc renders responsive API reference.

### 13.8 Possible Failure Symptoms
- `/metrics` returns 404 or empty page.
- Swagger UI fails to authorize or execute requests due to CORS errors.
- Schema definitions missing or broken in `/docs`.

### 13.9 Logs to Check
- Backend terminal: verify incoming GET requests to `/metrics` and `/docs`.

### 13.10 Completion Checklist
- [ ] Prometheus metrics endpoint exposes `rce_*` telemetry series.
- [ ] Swagger UI loads with complete endpoint hierarchy.
- [ ] Interactive API execution works with JWT authorization.
- [ ] ReDoc documentation renders without error.

---

# Phase 14: Adversarial Containment & Error Handling UI

### 14.1 Feature / Component
Sandbox Security Subsystem, Watchdog Timeout, Memory Limit Enforcer, Network Air-Gap, Error Badges.

### 14.2 Purpose
Test system containment under adversarial student submissions from the actual user interface and verify that security violations display clear explanatory error badges instead of crashing the UI.

### 14.3 Required Services to be Running
PostgreSQL, Redis, FastAPI Backend, Worker Daemon, Vite Frontend.

### 14.4 Exact Manual Steps

#### Test 14.A: CPU Infinite Loop (Wall-Clock Watchdog)
1. Paste the following infinite CPU spin script:
   ```python
   print("Spinning CPU indefinitely...")
   while True:
       pass
   ```
2. Click **"Run"**.
3. Observe the UI:
   - Terminal shows: `Spinning CPU indefinitely...`.
   - Status badge shows `RUNNING IN SANDBOX`.
4. Wait exactly 5.0 seconds.
5. Observe:
   - Terminal prints system notification:
     `[SYSTEM: Execution exceeded wall-clock timeout of 5s.]`
   - Telemetry status badge turns amber: `TIME LIMIT EXCEEDED`.
   - Wall Clock metric displays `~5000 ms`.
   - Exit code displays `137` (SIGKILL termination).

#### Test 14.B: Memory Bomb (Linux Kernel OOM Killer)
1. Paste the following memory exhaustion script:
   ```python
   print("Allocating memory beyond 128MB sandbox limit...")
   chunks = []
   while True:
       chunks.append(b"X" * (10 * 1024 * 1024)) # 10MB per iteration
   ```
2. Click **"Run"**.
3. Observe:
   - Within 1 to 2 seconds, container memory reaches 128MB.
   - Linux cgroups v2 OOM killer terminates the sandbox.
   - Telemetry status badge turns rose red: `MEMORY LIMIT EXCEEDED`.
   - Peak Memory metric displays `~128 MB` (at the threshold).
   - Exit code displays `137`.

#### Test 14.C: Network Exfiltration Attack (Air-Gap Verification)
1. Paste the following network connection attempt:
   ```python
   import socket
   print("Attempting outbound socket connection to 8.8.8.8:53...")
   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   s.settimeout(2.0)
   s.connect(("8.8.8.8", 53))
   print("Connected successfully!")
   ```
2. Click **"Run"**.
3. Observe:
   - Python immediately raises `OSError: [Errno 101] Network unreachable`.
   - The air-gap (`--net=none`) blocks any outbound socket creation at the kernel layer.
   - Telemetry status badge displays `RUNTIME ERROR`.
   - Exit code displays `1`.

#### Test 14.D: Excessive Output Flood (Stream Cap Truncation)
1. Paste the following flood script:
   ```python
   print("Flooding stdout with repetitive characters...")
   for i in range(50000):
       print("A" * 100)
   ```
2. Click **"Run"**.
3. Observe:
   - Terminal streams output until hitting the 1.0MB output limit.
   - Worker caps stream and marks `OUTPUT_LIMIT_EXCEEDED` (orange badge).
   - Browser tab does NOT freeze or run out of memory.

### 14.5 Buttons / Actions Used
- Button: `Run`

### 14.6 Test Data / Code
Adversarial snippets from 14.A, 14.B, 14.C, and 14.D.

### 14.7 Expected Result
- CPU hog terminated at 5 seconds with `TIME_LIMIT_EXCEEDED` and exit code 137.
- Memory bomb terminated at 128MB with `MEMORY_LIMIT_EXCEEDED` and exit code 137.
- Network exfiltration blocked instantly with `[Errno 101] Network unreachable`.
- Output flood truncated cleanly without crashing frontend.

### 14.8 Possible Failure Symptoms
- Infinite loop freezes backend worker permanently.
- Host machine memory spikes or Docker crashes.
- Network connection succeeds (CRITICAL SECURITY FAILURE).

### 14.9 Logs to Check
- Worker daemon log: verify watchdog SIGKILL and cgroups OOM events.
- Docker inspect: `docker inspect <container_id>` shows `OOMKilled: true` or `ExitCode: 137`.

### 14.10 Completion Checklist
- [ ] 5-second watchdog terminates infinite loop cleanly.
- [ ] 128MB cgroups limit triggers OOM killer and sets `MEMORY_LIMIT_EXCEEDED`.
- [ ] Network access is air-gapped (`--net=none`) with immediate `Errno 101`.
- [ ] Output flood is capped at 1MB to prevent client buffer exhaustion.

---

# Phase 15: Complete End-to-End Student User Journey

### 15.1 Feature / Component
Full Platform Integration (Onboarding -> Problem Solving -> Debugging -> Submission -> History Audit).

### 15.2 Purpose
Simulate an authentic 15-minute student lab assignment from start to finish to confirm all subsystems integrate without friction.

### 15.3 Required Services to be Running
All services active (Postgres, Redis, API, Worker, Frontend).

### 15.4 Exact Manual Steps
1. **Onboarding:**
   - Launch browser at `http://localhost:5173`.
   - Register a fresh student account: `jane_doe` / `jane@university.edu` / `LabPassword2026!`.
   - Confirm user pill shows `J` avatar, `jane_doe`, and `STUDENT`.
2. **Assignment Selection:**
   - In Problem Catalog, select **"Valid Palindrome (EASY)"**.
   - Read description and sample case: `racecar` -> `true`.
3. **Local Prototyping:**
   - In Monaco editor, write an initial buggy implementation:
     ```python
     import sys
     s = sys.stdin.read().strip()
     # Bug: does not ignore case or non-alphanumeric characters
     if s == s[::-1]:
         print("true")
     else:
         print("false")
     ```
   - Open **stdin** drawer and enter: `A man, a plan, a canal: Panama`.
   - Click **Run**.
   - Observe terminal output: `false` (incorrect because spaces and punctuation were not stripped).
4. **Fixing the Bug:**
   - Update the code in the editor:
     ```python
     import sys
     s = sys.stdin.read().strip()
     cleaned = ''.join(c.lower() for c in s if c.isalnum())
     if cleaned == cleaned[::-1]:
         print("true")
     else:
         print("false")
     ```
   - Click **Run**.
   - Observe terminal output: `true` (correct!).
5. **Autograding Submission:**
   - Click **"Submit for Grading"**.
   - Scorecard modal opens:
     - Verify verdict: `Accepted`.
     - Verify score: `100 / 100` (`100.0%`).
     - Verify all test cases pass.
   - Close modal.
6. **Audit Verification:**
   - Open **Execution History & Audit Log** drawer at the bottom.
   - Verify both the experimental run and the final grading submission are recorded.
   - Click **Load Code** on the initial run: verify buggy code loads.
   - Click **Load Code** on the final run: verify working code loads.
7. **Sign Out:**
   - Click **Sign Out** in the top navigation bar.
   - Verify clean return to unauthenticated public state.

### 15.5 Buttons / Actions Used
- Complete set of UI buttons across all components.

### 15.6 Test Data / Code
Valid Palindrome buggy vs corrected implementations.

### 15.7 Expected Result
- Flawless end-to-end student experience with zero crashes, unhandled errors, or layout anomalies.
- Full cycle of prototyping, debugging with stdin, grading, and auditing completed in under 5 minutes.

### 15.8 Possible Failure Symptoms
- State from previous user leaks into new session.
- Stdin drawer content persists inappropriately.
- History drawer fails to update after grading.

### 15.9 Logs to Check
- Database: verify user creation and submission records associated with `jane_doe`.

### 15.10 Completion Checklist
- [ ] Fresh account registration and login verified.
- [ ] Stdin testing used for interactive local debugging.
- [ ] Problem submitted for autograding with 100% score achieved.
- [ ] Execution history correctly audited and restored.
- [ ] Clean logout completes the session.

---

# Phase 16: Final Production Readiness & Release Sign-Off

### 16.1 Feature / Component
Helm Deployment Artifacts, Production Configuration, Security Verification.

### 16.2 Purpose
Perform final administrative checks to ensure the codebase and deployment assets meet production readiness standards.

### 16.3 Required Services to be Running
Docker Engine, Python venv.

### 16.4 Exact Manual Steps
1. In PowerShell, run the automated test suite to confirm zero regressions:
   ```powershell
   .\backend\venv\Scripts\python.exe -m pytest backend/tests/ -q
   ```
   *Expected:* `88 passed in ~25s`.
2. Lint the Helm chart via Docker:
   ```powershell
   docker run --rm -v "${PWD}:/apps" -w /apps alpine/helm lint helm/rce-platform/
   ```
   *Expected:* `1 chart(s) linted, 0 chart(s) failed`.
3. Check git working directory status:
   ```powershell
   git status
   ```
   *Expected:* Working tree clean on branch `develop`.
4. Review the [Progress Tracking Matrix](#progress-tracking-matrix) and verify all phases are signed off.

### 16.5 Completion Checklist
- [x] 88/88 automated tests passing.
- [x] Helm chart linted with 0 failures.
- [x] Git working directory clean.
- [x] All 16 phases verified and approved for production deployment.

---

# Bug Reporting Template

Use this format to report any visual, functional, or security bugs discovered during manual testing:

```markdown
### Bug Report: [Short Descriptive Title]

- **Phase Encountered:** Phase [X] - [Phase Name]
- **Severity:** [Critical | High | Medium | Low]
- **Component:** [e.g., CodeEditor | TerminalView | ProblemPanel | AuthModal | TelemetryPanel]
- **Browser:** [e.g., Chrome 128.0 | Firefox 130.0 | Edge 128.0]
- **Screen Resolution:** [e.g., 1920x1080 | 1440x900]

#### Steps to Reproduce
1. Navigate to '...'
2. Click on button '...'
3. Enter data '...'
4. Observe error

#### Expected Behavior
[Clear description of what should have happened]

#### Actual Behavior
[What actually occurred, including UI visual state]

#### Console / Network Logs
```text
[Paste browser DevTools console output or failed network response here]
```

#### Screenshots / Recordings
[Attach screenshot or terminal snippet]
```
