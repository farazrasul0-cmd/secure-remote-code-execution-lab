# End-to-End Manual Testing Roadmap & Production Validation Guide
## Secure Real-Time Remote Code Execution Laboratory Platform (v2.0.0)

**Document Version:** 2.0.0  
**Target Audience:** Production Debugging Engineers, SREs, Faculty Reviewers, and System Testers  
**Primary Execution OS:** Windows 10/11 (PowerShell 7+ or Windows PowerShell 5.1) with Docker Desktop (WSL 2 backend)  
**Target Deployment:** Local Hybrid Dev Stack -> Docker Compose -> Local Kubernetes  

---

## How To Use This Document ("Human Testing Mode")

> [!IMPORTANT]
> **Strict Phase-by-Phase Discipline:**
> 1. **Start from Phase 0.** Do not skip any phases or steps.
> 2. **Run every command exactly as specified.** Pay close attention to which terminal tab to use and the working directory (`Cwd`).
> 3. **Observe the expected output.** Compare your terminal output with the provided "What Success Looks Like" sections.
> 4. **If an error occurs, STOP IMMEDIATELY.** Do not attempt subsequent steps with broken prerequisites. Copy the exact terminal error output and provide it to the debugging engineer (Codex).
> 5. **Fix the root cause completely.** Verify with the diagnosis commands in the phase before moving forward.
> 6. **Mark the phase as Complete in the [Testing Status Tracking Table](#system-testing-status-tracking-table) and proceed.**

---

## System Testing Status Tracking Table

Use this matrix to track your verification progress:

| Phase | Subsystem Under Test | Status | Date Verified | Blocking Issues Encountered | Resolution / Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Phase 0** | Host Environment & Prerequisites | ⏳ Pending | | | |
| **Phase A** | Infrastructure (Docker, Postgres, Redis) | ⏳ Pending | | | |
| **Phase B** | Database Migrations & Schemas | ⏳ Pending | | | |
| **Phase C** | Backend API Gateway & REST Auth | ⏳ Pending | | | |
| **Phase D** | Celery Worker Fleet & Queue Pipeline | ⏳ Pending | | | |
| **Phase E** | Sandbox Execution & Adversarial Containment | ⏳ Pending | | | |
| **Phase F** | Frontend Web IDE & Monaco Editor | ⏳ Pending | | | |
| **Phase G** | WebSocket Live Output Streaming | ⏳ Pending | | | |
| **Phase H** | Interactive PTY Pseudo-Terminal | ⏳ Pending | | | |
| **Phase I** | Algorithmic Problem Autograding | ⏳ Pending | | | |
| **Phase J** | Collaborative Multi-User Rooms | ⏳ Pending | | | |
| **Phase K** | Observability, Metrics & Distributed Tracing | ⏳ Pending | | | |
| **Phase L** | Production Kubernetes Deployment & Helm Validation | ⏳ Pending | | | |

---

## Terminal Management Architecture

Throughout this testing protocol, you will maintain multiple concurrent terminal sessions. Label your PowerShell windows or tabs as follows:

- **Terminal 1 (Infrastructure & Docker):** Hosts `docker compose` logs and container status commands.
- **Terminal 2 (API Gateway - Backend):** Runs the FastAPI ASGI server (`uvicorn`).
- **Terminal 3 (Compute Worker - Celery):** Runs the Celery worker daemon with execution logging.
- **Terminal 4 (Web IDE - Frontend):** Runs the Vite React development server (`npm run dev`).
- **Terminal 5 (Interactive Tester / CLI):** Dedicated to running verification scripts, curl requests, and database queries.

---

# Phase 0: Host Environment & Prerequisites Validation

### Objective
Verify that the host workstation has all necessary software runtimes, CLI tools, network ports, and virtualization extensions installed and operational before launching any code.

### Required Components
- Windows 10/11 with WSL 2 backend active
- Git 2.40+
- Python 3.12+ (64-bit)
- Node.js 20+ LTS & npm 10+
- Docker Desktop 24+ (running Linux containers with cgroups v2 enabled)
- Port availability: `5432` (Postgres), `6379` (Redis), `8001` (FastAPI), `5173` (Vite)

---

### Step 0.1: Verify Software Runtime Versions
Open **Terminal 5 (Interactive Tester)** and run:

```powershell
# Navigate to project root
cd d:\projects\real-time-remote-computer-lab-docs\real-time-remote-computer-lab-docs

# 1. Check Git
git --version

# 2. Check Python version
python --version

# 3. Check Node & npm versions
node --version
npm --version

# 4. Check Docker version
docker --version
docker compose version
```

#### What Success Looks Like
```text
git version 2.40+ or higher
Python 3.12.x
v20.x.x
10.x.x
Docker version 24.x+ or higher
Docker Compose version v2.x+
```

---

### Step 0.2: Verify Docker Desktop Daemon Status
In **Terminal 5**, run:

```powershell
docker info --format "Server Version: {{.ServerVersion}}, Operating System: {{.OperatingSystem}}, Cgroup Version: {{.CgroupVersion}}"
```

#### What Success Looks Like
```text
Server Version: 26.x.x (or 24.x/27.x), Operating System: Docker Desktop, Cgroup Version: 2
```

> [!WARNING]
> **If Failed:** If the command hangs, says `error during connect: This error may indicate that the docker daemon is not running`, or shows `Cgroup Version: 1`:
> 1. Launch **Docker Desktop** from the Windows Start menu.
> 2. Ensure **Settings -> General -> Use the WSL 2 based engine** is checked.
> 3. Verify Docker finishes booting and the status bar turns **Green (Engine running)**.

---

### Step 0.3: Check Local Port Availability
Ensure no stale local services or background servers are monopolizing the required ports. In **Terminal 5**, run:

```powershell
Get-NetTCPConnection -LocalPort 5432, 6379, 8001, 5173 -State Listen -ErrorAction SilentlyContinue | Select-Object LocalAddress, LocalPort, OwningProcess
```

#### What Success Looks Like
```text
(No output returned — meaning all 4 ports are completely free and available)
```

> [!TIP]
> **If Port Conflict Exists:** If a process ID (`OwningProcess`) is returned, identify it using:
> `Get-Process -Id <OwningProcess>`
> If it is an old uvicorn or orphaned postgres instance, terminate it:
> `Stop-Process -Id <OwningProcess> -Force`

---

### Phase 0 Completion Checklist
- [ ] Git, Python 3.12, Node 20, and Docker are verified.
- [ ] Docker engine is active with cgroups v2.
- [ ] Ports 5432, 6379, 8001, and 5173 are free.

---

# Phase A: Infrastructure Testing (Docker, PostgreSQL, Redis)

### Objective
Start the persistent backing services (PostgreSQL 16 relational database and Redis 7 memory cache/message broker) using Docker Compose and verify container health checks and network bridges.

### Required Components
- `docker-compose.dev.yml`
- Docker network: `rce_dev_network`
- PostgreSQL container: `rce_postgres_dev` (Port 5432)
- Redis container: `rce_redis_dev` (Port 6379)

---

### Step A.1: Ensure `.env` Files Exist
In **Terminal 5**, verify that both root `.env` and `backend/.env` are present:

```powershell
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
if (-not (Test-Path "backend/.env")) { Copy-Item ".env" "backend/.env" }
Get-Item .env, backend/.env | Select-Object Name, Length, LastWriteTime
```

#### What Success Looks Like
Both `.env` and `backend/.env` files exist with non-zero length.

---

### Step A.2: Start PostgreSQL and Redis via Docker Compose
In **Terminal 1 (Infrastructure)**, execute:

```powershell
docker compose -f docker-compose.dev.yml up -d
```

#### What Success Looks Like
```text
[+] Running 3/3
 ✔ Network rce_dev_network      Created
 ✔ Container rce_postgres_dev   Started
 ✔ Container rce_redis_dev      Started
```

---

### Step A.3: Verify Container Health Checks
Wait 10 seconds, then in **Terminal 5**, run:

```powershell
docker ps --filter "name=rce_" --format "table {{.Names}}	{{.Status}}	{{.Ports}}"
```

#### What Success Looks Like
```text
NAMES              STATUS                    PORTS
rce_postgres_dev   Up (healthy)              0.0.0.0:5432->5432/tcp
rce_redis_dev      Up (healthy)              0.0.0.0:6379->6379/tcp
```
Both containers must report **`Up (healthy)`**.

---

### Step A.4: Test Redis Connection & Ping
In **Terminal 5**, execute a Redis ping:

```powershell
docker exec -it rce_redis_dev redis-cli ping
```

#### What Success Looks Like
```text
PONG
```

---

### Step A.5: Test PostgreSQL Socket & Credential Access
In **Terminal 5**, query PostgreSQL directly:

```powershell
docker exec -it rce_postgres_dev psql -U rce_user -d rce_db -c "SELECT version();"
```

#### What Success Looks Like
```text
                                                 version
---------------------------------------------------------------------------------------------------------
 PostgreSQL 16.x on x86_64-pc-linux-musl, compiled by gcc...
(1 row)
```

> [!CAUTION]
> **Diagnosing Failure:** If PostgreSQL or Redis fails to become healthy:
> - Run: `docker logs rce_postgres_dev --tail 50`
> - Run: `docker logs rce_redis_dev --tail 50`
> - If port 5432 or 6379 is bound by a native Windows service, stop the local Windows service or change port mapping in `docker-compose.dev.yml`.

---

### Phase A Completion Checklist
- [ ] `rce_dev_network` created.
- [ ] PostgreSQL is `healthy` and responds to `SELECT version();`.
- [ ] Redis is `healthy` and responds with `PONG`.

---

# Phase B: Database Migrations & Schema Initialization

### Objective
Apply Alembic database migrations to create all required tables: `users`, `submissions`, `execution_logs`, `problems`, `test_cases`, `rooms`, and `room_members`.

### Required Components
- Virtual environment at `backend/venv`
- `backend/alembic.ini`
- Migrations in `backend/alembic/versions/`

---

### Step B.1: Initialize Python Virtual Environment
In **Terminal 5**, verify or create the Python virtual environment:

```powershell
# If venv does not exist, create it:
if (-not (Test-Path "backend\venv\Scripts\python.exe")) {
    python -m venv backend\venv
}

# Activate virtual environment
.\backend\venv\Scripts\activate

# Verify Python points to backend venv
where.exe python
```

#### What Success Looks Like
The output path must point to `...\backend\venv\Scripts\python.exe`.

---

### Step B.2: Install Backend Dependencies
In **Terminal 5** (with virtual environment active):

```powershell
pip install -r backend/requirements.txt
```

#### What Success Looks Like
```text
Successfully installed ... fastapi uvicorn sqlalchemy asyncpg alembic celery redis pydantic ...
```

---

### Step B.3: Run Alembic Database Migrations
In **Terminal 5**, navigate to `backend` and run:

```powershell
cd backend
alembic upgrade head
cd ..
```

#### What Success Looks Like
```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial_schema, initial schema: users, submissions, execution_logs
INFO  [alembic.runtime.migration] Running upgrade 001_initial_schema -> 002_autograding, autograding problems and test cases
```

---

### Step B.4: Inspect PostgreSQL Schema Tables
In **Terminal 5**, verify that all tables exist:

```powershell
docker exec -it rce_postgres_dev psql -U rce_user -d rce_db -c "\dt"
```

#### What Success Looks Like
```text
               List of relations
 Schema |       Name        | Type  |  Owner
--------+-------------------+-------+----------
 public | alembic_version   | table | rce_user
 public | execution_logs    | table | rce_user
 public | problems          | table | rce_user
 public | room_members      | table | rce_user
 public | rooms             | table | rce_user
 public | submissions       | table | rce_user
 public | test_cases        | table | rce_user
 public | users             | table | rce_user
(8 rows)
```

---

### Phase B Completion Checklist
- [ ] Backend virtual environment active with all requirements.
- [ ] `alembic upgrade head` completes with 0 errors.
- [ ] All 8 database tables present in `rce_db`.

---

# Phase C: Backend API Gateway & REST Authentication Testing

### Objective
Start the FastAPI application on port `8001` via Uvicorn, test the OpenAPI documentation endpoint, register a test user, authenticate to receive a JWT bearer token, and query language metadata.

### Required Components
- FastAPI ASGI Server (`backend/app/main.py`)
- Port: `8001`

---

### Step C.1: Start the API Gateway
Switch to **Terminal 2 (API Gateway - Backend)**:

```powershell
cd d:\projects\real-time-remote-computer-lab-docs\real-time-remote-computer-lab-docs
.\backend\venv\Scripts\activate
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8001 --reload
```

#### What Success Looks Like
```text
INFO:     Will watch for changes in: ['...']
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
INFO:     Started reloader process [...]
INFO:     Started server process [...]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```
> [!NOTE]
> Keep **Terminal 2 open and running** continuously.

---

### Step C.2: Verify Health Check & Root Endpoints
Switch to **Terminal 5 (Interactive Tester)** and run:

```powershell
# 1. Test root endpoint
curl.exe -s http://localhost:8001/ | ConvertFrom-Json

# 2. Test health check
curl.exe -s http://localhost:8001/health | ConvertFrom-Json
```

#### What Success Looks Like
```json
{
  "status": "healthy",
  "service": "rce-backend-api",
  "version": "2.0.0"
}
```

---

### Step C.3: Register a New Student User
In **Terminal 5**, register a test user:

```powershell
$registerPayload = @{
    email = "student@test.lab"
    username = "student1"
    password = "SecurePassword123!"
    full_name = "Alice Student"
} | ConvertTo-Json

$regResponse = curl.exe -s -X POST http://localhost:8001/api/v1/auth/register `
  -H "Content-Type: application/json" `
  -d $registerPayload

$regResponse
```

#### What Success Looks Like
```json
{
  "id": "...",
  "email": "student@test.lab",
  "username": "student1",
  "full_name": "Alice Student",
  "role": "student",
  "is_active": true
}
```

---

### Step C.4: Authenticate & Obtain JWT Token
In **Terminal 5**, log in with OAuth2 password grant form:

```powershell
$tokenResponse = curl.exe -s -X POST http://localhost:8001/api/v1/auth/login `
  -H "Content-Type: application/x-www-form-urlencoded" `
  -d "username=student1&password=SecurePassword123!" | ConvertFrom-Json

# Save token to PowerShell variable for subsequent requests
$token = $tokenResponse.access_token
Write-Host "JWT Access Token received: $($token.Substring(0, 25))..." -ForegroundColor Green
```

#### What Success Looks Like
```text
JWT Access Token received: eyJhbGciOiJIUzI1NiIsInR5...
```

---

### Step C.5: Test Polyglot Languages Registry Endpoint
In **Terminal 5**, query supported programming runtimes:

```powershell
curl.exe -s http://localhost:8001/api/v1/languages | ConvertFrom-Json
```

#### What Success Looks Like
A list of supported languages (`python`, `c`, `cpp`, `rust`, `go`, `javascript`) with default starter code templates.

---

### Phase C Completion Checklist
- [ ] FastAPI starts cleanly on `http://localhost:8001`.
- [ ] `/health` returns `healthy`.
- [ ] User registration and JWT login succeed.
- [ ] Languages endpoint returns valid runtime list.

---

# Phase D: Celery Worker Fleet & Queue Pipeline Testing

### Objective
Start the Celery worker daemon, verify connection to the Redis broker, ensure registration of execution tasks (`rce.tasks.execute_code`), and verify worker prefetch limits.

### Required Components
- Celery worker entrypoint: `worker/tasks/execution.py`
- Broker: `redis://localhost:6379/0`
- Concurrency: 2 worker processes

---

### Step D.1: Build the Hardened Sandbox Docker Image
Before starting workers, build the unprivileged sandbox execution image so the worker can invoke it. In **Terminal 5**:

```powershell
docker build -t lab-sandbox-python:3.11 docker/python/
```

#### What Success Looks Like
```text
Successfully tagged lab-sandbox-python:3.11
```

---

### Step D.2: Start the Celery Execution Worker
Switch to **Terminal 3 (Compute Worker - Celery)**:

```powershell
cd d:\projects\real-time-remote-computer-lab-docs\real-time-remote-computer-lab-docs
.\backend\venv\Scripts\activate
celery -A worker.tasks.execution worker --loglevel=info --concurrency=2 --pool=threads
```

#### What Success Looks Like
```text
 -------------- celery@YOUR-HOSTNAME v5.x.x
--- ***** ----- 
-- ******* ---- Windows-10-...
- *** --- * --- 
- ** ---------- [config]
- ** ---------- .> app:         rce_execution_worker
- ** ---------- .> transport:   redis://localhost:6379/0
- ** ---------- .> results:     redis://localhost:6379/0
- *** --- * --- .> concurrency: 2 (threads)
-- ******* ---- .> task events: OFF (enable -E to monitor tasks)
--- ***** ----- 
 -------------- [queues]
                .> celery           exchange=celery(direct) key=celery

[tasks]
  . rce.tasks.execute_code

[INFO/MainProcess] Connected to redis://localhost:6379/0
[INFO/MainProcess] celery@YOUR-HOSTNAME ready.
```
> [!NOTE]
> Keep **Terminal 3 open and running** continuously.

---

### Phase D Completion Checklist
- [ ] `lab-sandbox-python:3.11` Docker image built.
- [ ] Celery connects to `redis://localhost:6379/0`.
- [ ] Task `rce.tasks.execute_code` registered.
- [ ] Celery reports `ready`.

---

# Phase E: Sandbox Execution & Adversarial Containment Testing

### Objective
Execute real code submissions through the backend -> worker pipeline, verifying correct standard output, standard input piping, and deterministic containment of hostile payloads (fork bombs, memory bombs, infinite loops, and disk filling).

---

### Step E.1: Submit Benign Python Execution ("Hello World")
In **Terminal 5 (Interactive Tester)**, submit valid Python code:

```powershell
$codePayload = @{
    language = "python"
    code = "print('Hello from Secure Sandbox!')`nimport sys`nprint('Python version:', sys.version.split()[0])"
    stdin = ""
} | ConvertTo-Json

$subResponse = curl.exe -s -X POST http://localhost:8001/api/v1/submissions `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d $codePayload | ConvertFrom-Json

$submissionId = $subResponse.id
Write-Host "Submission Enqueued with ID: $submissionId" -ForegroundColor Green
```

Observe **Terminal 3 (Celery Worker)**:
```text
[INFO/MainProcess] Task rce.tasks.execute_code[...] received
[INFO/ThreadPoolExecutor-0_0] Starting execution of submission: ...
[INFO/ThreadPoolExecutor-0_0] Task rce.tasks.execute_code[...] succeeded
```

Query the execution result in **Terminal 5**:
```powershell
Start-Sleep -Seconds 2
$result = curl.exe -s -H "Authorization: Bearer $token" http://localhost:8001/api/v1/submissions/$submissionId | ConvertFrom-Json
$result | Select-Object id, status, language, execution_time_ms, memory_peak_bytes
```

#### What Success Looks Like
```text
status             : COMPLETED (or SUCCESS)
execution_time_ms  : < 1500
```

---

### Step E.2: Adversarial Test — Infinite CPU Spin (Watchdog Timeout)
Test whether runaway infinite loops are strictly terminated at the 5.0-second limit. In **Terminal 5**:

```powershell
$infinitePayload = @{
    language = "python"
    code = "print('Spinning forever...')`nwhile True:`n    pass"
} | ConvertTo-Json

$sub = curl.exe -s -X POST http://localhost:8001/api/v1/submissions `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d $infinitePayload | ConvertFrom-Json

Write-Host "Awaiting watchdog timeout enforcement on $($sub.id)..." -ForegroundColor Yellow
Start-Sleep -Seconds 7

$res = curl.exe -s -H "Authorization: Bearer $token" http://localhost:8001/api/v1/submissions/$($sub.id) | ConvertFrom-Json
$res | Select-Object id, status, execution_time_ms
```

#### What Success Looks Like
```text
status            : TIME_LIMIT_EXCEEDED
```
The watchdog timer cleanly terminated the sandbox with `SIGKILL`.

---

### Step E.3: Adversarial Test — Memory Bomb (OOM Killer)
Test whether exceeding the 128 MB RAM ceiling triggers kernel OOM termination. In **Terminal 5**:

```powershell
$memPayload = @{
    language = "python"
    code = "print('Allocating 1 Gigabyte RAM...')`nx = bytearray(10**9)"
} | ConvertTo-Json

$sub = curl.exe -s -X POST http://localhost:8001/api/v1/submissions `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d $memPayload | ConvertFrom-Json

Start-Sleep -Seconds 3

$res = curl.exe -s -H "Authorization: Bearer $token" http://localhost:8001/api/v1/submissions/$($sub.id) | ConvertFrom-Json
$res | Select-Object id, status
```

#### What Success Looks Like
```text
status : MEMORY_LIMIT_EXCEEDED (or exit code 137 / SIGKILL)
```

---

### Step E.4: Adversarial Test — Network Exfiltration (Air-Gap)
Test whether network sockets are blocked by the `--net=none` air-gap. In **Terminal 5**:

```powershell
$netPayload = @{
    language = "python"
    code = "import socket`ns = socket.socket(socket.AF_INET, socket.SOCK_STREAM)`ns.settimeout(2)`ns.connect(('8.8.8.8', 53))"
} | ConvertTo-Json

$sub = curl.exe -s -X POST http://localhost:8001/api/v1/submissions `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d $netPayload | ConvertFrom-Json

Start-Sleep -Seconds 3

$res = curl.exe -s -H "Authorization: Bearer $token" http://localhost:8001/api/v1/submissions/$($sub.id) | ConvertFrom-Json
$res | Select-Object id, status
```

#### What Success Looks Like
Status indicates failure (`RUNTIME_ERROR` with `Network is unreachable` or `Errno 101`), confirming the sandbox is completely air-gapped from the internet.

---

### Phase E Completion Checklist
- [ ] Benign Python execution returns standard output.
- [ ] Infinite loops terminated at 5.0s with `TIME_LIMIT_EXCEEDED`.
- [ ] Memory bombs terminated with `MEMORY_LIMIT_EXCEEDED`.
- [ ] Network connections rejected by air-gap.

---

# Phase F: Frontend Web IDE & Monaco Editor Testing

### Objective
Start the React 18 + Vite frontend development server, verify proxy forwarding of `/api` and `/ws` to port `8001`, and confirm Monaco Editor rendering in the browser.

### Required Components
- Vite dev server at `http://localhost:5173`
- Reverse proxy config in `frontend/vite.config.ts`

---

### Step F.1: Start the Frontend Application
Switch to **Terminal 4 (Web IDE - Frontend)**:

```powershell
cd d:\projects\real-time-remote-computer-lab-docs\real-time-remote-computer-lab-docs\frontend
npm run dev
```

#### What Success Looks Like
```text
  VITE v5.x.x  ready in ... ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h + enter to show help
```
> [!NOTE]
> Keep **Terminal 4 open and running** continuously.

---

### Step F.2: Browser Verification
Open Google Chrome, Edge, or Firefox and navigate to:
**`http://localhost:5173`**

#### What Success Looks Like in Browser
1. The **Secure Remote Code Execution Laboratory** header displays with version `v2.0.0`.
2. The **Monaco Code Editor** loads with syntax highlighting and line numbers.
3. The **Language Selector** allows choosing between Python, C, C++, Rust, Go, and JavaScript.
4. The **xterm.js Terminal** displays below or beside the editor with a blinking cursor.

---

### Phase F Completion Checklist
- [ ] Frontend builds and launches on `http://localhost:5173`.
- [ ] Monaco Editor initializes cleanly without JS console errors.
- [ ] Language dropdown populates starter code.

---

# Phase G: Full-Duplex WebSocket Live Streaming Testing

### Objective
Verify that output from the worker streams character-by-character over WebSockets to the frontend terminal in real time, with sub-50ms latency.

---

### Step G.1: Run a Streaming Python Loop
In the browser at `http://localhost:5173`:
1. Select **Python** from the language dropdown.
2. Enter the following streaming code:
   ```python
   import time
   print("Starting real-time counter...")
   for i in range(1, 6):
       print(f"Tick {i}/5")
       time.sleep(0.5)
   print("Execution finished successfully!")
   ```
3. Click the **"Run Code"** button.

#### What Success Looks Like
- The terminal in the browser displays `Tick 1/5`, `Tick 2/5`, `Tick 3/5` sequentially **in real time** (every 0.5s), NOT in a single delayed batch.
- Terminal 2 (API Gateway) shows:
  ```text
  INFO: ('127.0.0.1', ...) - "WebSocket /ws/v1/submissions/..." [accepted]
  ```
- Terminal 3 (Celery Worker) shows chunk emissions:
  ```text
  Publishing frame seq=1, seq=2, seq=3...
  ```

---

### Phase G Completion Checklist
- [ ] WebSocket connection establishes cleanly.
- [ ] Output streams tick-by-tick with low latency.
- [ ] Connection closes gracefully upon completion.

---

# Phase H: Interactive PTY Pseudo-Terminal Testing

### Objective
Verify character-by-character bidirectional standard input (`stdin`), interactive REPL behavior, terminal resizing, and out-of-band `Ctrl+C` interrupt signal dispatching.

---

### Step H.1: Test Interactive `input()` in Python
In the browser editor:
1. Enter the following interactive script:
   ```python
   name = input("Enter your name: ")
   print(f"Welcome to the Secure Lab, {name}!")
   age = input("Enter your age: ")
   print(f"In 5 years, you will be {int(age) + 5}.")
   ```
2. Click **"Run Code"**.
3. In the terminal pane, observe the prompt: `Enter your name: `.
4. Click inside the terminal and type `Faraz`, then press **Enter**.
5. Observe the prompt: `Enter your age: `. Type `24`, then press **Enter**.

#### What Success Looks Like
The terminal immediately echoes characters and prints:
```text
Welcome to the Secure Lab, Faraz!
In 5 years, you will be 29.
```

---

### Step H.2: Test Out-of-Band `Ctrl+C` (`SIGINT`) Interruption
1. In the browser editor, enter:
   ```python
   import time
   print("Infinite loop started. Press Ctrl+C to abort me!")
   try:
       while True:
           time.sleep(0.2)
   except KeyboardInterrupt:
       print("\nCaught SIGINT! Graceful shutdown.")
   ```
2. Click **"Run Code"**.
3. While the script is running, click the **"Interrupt (Ctrl+C)"** button in the UI or press `Ctrl+C` in the active terminal.

#### What Success Looks Like
The script catches the signal immediately and prints:
```text
Caught SIGINT! Graceful shutdown.
```
Execution finishes before the 5-second watchdog expires.

---

### Phase H Completion Checklist
- [ ] Interactive `input()` accepts keystrokes and processes `\n`.
- [ ] `Ctrl+C` delivers `SIGINT` to the sandbox process.

---

# Phase I: Algorithmic Problem Autograding Testing

### Objective
Verify the problem catalog, submit solutions to seeded algorithmic problems (e.g., Two Sum, Valid Palindrome), and verify test case evaluations with hidden oracle redaction.

---

### Step I.1: Inspect Seed Problems via API
In **Terminal 5 (Interactive Tester)**:

```powershell
$problems = curl.exe -s http://localhost:8001/api/v1/problems | ConvertFrom-Json
$problems | Select-Object id, title, difficulty, time_limit_ms, memory_limit_mb
```

#### What Success Looks Like
Returns list of problems (e.g., `Two Sum`, `Valid Palindrome`, `Fibonacci`).

---

### Step I.2: Submit Correct Solution to Problem 1 (Two Sum)
In **Terminal 5**, submit a valid solution to Problem 1:

```powershell
$twoSumCode = @'
import sys, json
def two_sum(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        diff = target - n
        if diff in seen:
            return [seen[diff], i]
        seen[n] = i
    return []

lines = sys.stdin.read().strip().splitlines()
if lines:
    nums = json.loads(lines[0])
    target = int(lines[1])
    print(json.dumps(two_sum(nums, target)))
'@

$subPayload = @{
    language = "python"
    code = $twoSumCode
} | ConvertTo-Json

$gradeRes = curl.exe -s -X POST http://localhost:8001/api/v1/problems/1/submit `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d $subPayload | ConvertFrom-Json

Write-Host "Grading triggered for submission: $($gradeRes.id)" -ForegroundColor Green
Start-Sleep -Seconds 4

$scorecard = curl.exe -s -H "Authorization: Bearer $token" http://localhost:8001/api/v1/problems/1/submissions/$($gradeRes.id)/scorecard | ConvertFrom-Json
$scorecard | Select-Object total_score, max_score, status, passed_tests, total_tests
```

#### What Success Looks Like
```text
total_score  : 100.0
max_score    : 100.0
status       : ACCEPTED
passed_tests : 5
total_tests  : 5
```
All hidden test cases show `[REDACTED: HIDDEN TEST CASE]` for privacy while granting full points.

---

### Phase I Completion Checklist
- [ ] Problem catalog loads.
- [ ] Correct solution receives `ACCEPTED` and `100.0` score.
- [ ] Hidden test cases are sanitized.

---

# Phase J: Collaborative Multi-User Coding Rooms Testing

### Objective
Create a collaborative room, verify WebSocket join events, synchronize code across multiple browser windows, and broadcast simultaneous execution results to all participants.

---

### Step J.1: Create a Collaborative Room
In **Terminal 5**:

```powershell
$roomPayload = @{
    name = "Systems Lab Team Alpha"
    language = "python"
    initial_code = "# Collaborative Pair Programming Session\nprint('Hello Room!')"
} | ConvertTo-Json

$room = curl.exe -s -X POST http://localhost:8001/api/v1/rooms `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d $roomPayload | ConvertFrom-Json

$roomId = $room.id
Write-Host "Collaborative Room Created with ID: $roomId" -ForegroundColor Green
```

---

### Step J.2: Test Dual-Client Collaboration in Browser
1. Open a standard browser window at: `http://localhost:5173/rooms` (or click "Rooms").
2. Join room `Systems Lab Team Alpha`.
3. Open an **Incognito / Private browser window** and log in as a second user.
4. Join the exact same room ID.
5. In Window 1, type code in the editor.
6. Observe Window 2: Keystrokes and cursor positions synchronize in real time.
7. Click "Run Code" in Window 1: Both Window 1 and Window 2 display the live streaming terminal output simultaneously over `rce:room:exec:<id>`.

---

### Phase J Completion Checklist
- [ ] Room created successfully.
- [ ] Real-time document sync functions between two clients.
- [ ] Terminal execution broadcasts to all connected peers.

---

# Phase K: Observability, Metrics & Distributed Tracing Testing

### Objective
Verify Prometheus metrics scraping endpoint and W3C TraceContext distributed trace propagation across Redis and Celery.

---

### Step K.1: Test Prometheus Metrics Endpoint
In **Terminal 5**:

```powershell
curl.exe -s http://localhost:8001/metrics | Select-String -Pattern "rce_"
```

#### What Success Looks Like
Metrics are returned, including:
```text
rce_submissions_total{language="python",status="SUCCESS"} ...
rce_submission_duration_seconds_bucket{...} ...
rce_worker_queue_depth ...
```

---

### Step K.2: Verify W3C `traceparent` Generation
Check **Terminal 2 (API Gateway)** and **Terminal 3 (Celery Worker)** logs during execution:
```text
API: Injected traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
Worker: Extracted traceparent carrier. Linked child span 'rce.worker.sandbox_execution' to trace 4bf92f3577b34da6a3ce929d0e0e4736
```

---

### Phase K Completion Checklist
- [ ] `/metrics` endpoint returns valid Prometheus data.
- [ ] W3C TraceContext propagates across API and worker.

---

# Phase L: Production Kubernetes Deployment & Helm Validation

### Objective
Verify that the Helm chart (`helm/rce-platform/`) lints cleanly, templates without syntax errors, enforces PodSecurityStandards Restricted, and validates disaster recovery CronJobs.

---

### Step L.1: Lint the Helm Chart
In **Terminal 5**:

```powershell
helm lint helm/rce-platform/
```

#### What Success Looks Like
```text
==> Linting helm/rce-platform/
1 chart(s) linted, 0 chart(s) failed
```

---

### Step L.2: Validate Template Rendering & Security Context
In **Terminal 5**, render the templates locally:

```powershell
helm template rce-test helm/rce-platform/ --values helm/rce-platform/values.yaml > rendered-manifests.yaml
Select-String -Path rendered-manifests.yaml -Pattern "runAsNonRoot: true", "rce_worker_queue_depth"
```

#### What Success Looks Like
Templates render successfully, showing `runAsNonRoot: true`, `drop: [ALL]`, and the queue depth custom autoscaling metric.

---

### Step L.3: Execute Full Automated Test Suite
In **Terminal 5**, run all 88 unit, integration, and chaos resilience tests:

```powershell
.\backend\venv\Scripts\python.exe -m pytest backend/tests/ -v
```

#### What Success Looks Like
```text
======================= 88 passed in 20.xx s =======================
```

---

### Phase L Completion Checklist
- [ ] Helm chart passes `helm lint` with 0 failures.
- [ ] Manifests render with Restricted security contexts.
- [ ] All 88 automated tests pass with 100% success.

---

# Comprehensive Troubleshooting & Debugging Reference

| Symptom / Error | Probable Root Cause | Immediate Diagnostic Command | Corrective Action |
| :--- | :--- | :--- | :--- |
| **`ConnectionRefusedError: [Errno 111]` connecting to Postgres** | `rce_postgres_dev` is stopped or unhealthy | `docker ps -a --filter "name=postgres"` | Run `docker compose -f docker-compose.dev.yml up -d` |
| **`celery.exceptions.OperationalError: Error 10061 connecting to localhost:6379`** | Redis is not running or port 6379 is blocked | `docker exec -it rce_redis_dev redis-cli ping` | Ensure Redis container is `healthy` |
| **`docker: Error response from daemon: No such image: lab-sandbox-python:3.11`** | Sandbox image was not built locally | `docker images lab-sandbox-python` | Run `docker build -t lab-sandbox-python:3.11 docker/python/` |
| **WebSocket disconnects with code `1008` (Policy Violation)** | Missing or invalid JWT token in WebSocket query | Check query string `?token=...` | Re-authenticate via `/api/v1/auth/login` and refresh token |
| **`alembic.util.exc.CommandError: Can't locate revision`** | Branch mismatch or missing migration script | `git status backend/alembic/versions/` | Ensure working tree is clean on `develop` |
| **Monaco Editor shows white screen** | Vite proxy or npm build failure | Open Browser F12 Developer Console | Run `npm install` and check `vite.config.ts` |
| **Execution status stuck at `PENDING`** | Celery worker is not running or queue name mismatch | Check Terminal 3 (Worker window) | Ensure Celery command is running with `-A worker.tasks.execution worker` |
