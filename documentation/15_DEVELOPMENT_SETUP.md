# Local Development & Environment Setup Guide
## Secure Real-Time Remote Code Execution Laboratory Platform

**Document Version:** 1.0.0  
**Target Environment:** Windows 10/11 (WSL2 / Docker Desktop), macOS (Apple Silicon / Intel), Ubuntu 22.04 LTS

---

## 1. Prerequisites & Toolchain Requirements

Ensure the following tools and runtimes are installed on your host workstation before proceeding:

| Dependency | Minimum Version | Verification Command | Purpose |
| :--- | :--- | :--- | :--- |
| **Docker & Docker Compose** | Docker 24.0+ / Compose v2 | `docker --version` | Sandbox containers and local infrastructure |
| **Python** | 3.11.x | `python --version` | Backend API and worker daemon runtime |
| **Node.js & npm** | Node 18.x LTS / npm 9.x+ | `node -v && npm -v` | Frontend development server and bundler |
| **Git** | 2.40+ | `git --version` | Version control |

> [!IMPORTANT]
> **Windows Users (WSL2 Required):**  
> On Windows, Docker Desktop must be configured to use the **WSL2-based engine**. Sandboxing relies on Linux kernel primitives (cgroups v2, namespaces) that are not natively supported on Windows containers. Ensure Docker Desktop Settings $\rightarrow$ General $\rightarrow$ "Use the WSL 2 based engine" is enabled.

---

## 2. Repository Layout & Workspace Architecture

The repository is structured as a unified monorepo for cohesive local development:

```
real-time-remote-computer-lab-docs/
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── api/              # HTTP REST and WebSocket route handlers
│   │   ├── core/             # Configuration, security (JWT), logging
│   │   ├── models/           # SQLAlchemy ORM database models
│   │   ├── schemas/          # Pydantic request/response schemas
│   │   ├── services/         # Business logic & repository services
│   │   └── main.py           # FastAPI entrypoint
│   ├── alembic/              # Database migration scripts
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile            # Backend container specification
├── worker/                   # Distributed Execution Worker
│   ├── tasks/                # Celery / async worker task definitions
│   ├── sandbox/              # Docker SDK isolation wrapper & cgroup controller
│   ├── requirements.txt      # Worker dependencies
│   └── Dockerfile            # Worker container specification
├── frontend/                 # React + TypeScript Web Application
│   ├── src/
│   │   ├── components/       # Monaco Editor, xterm Terminal, Navbar
│   │   ├── hooks/            # WebSocket and API custom hooks
│   │   ├── pages/            # Lab Workspace, Login, History
│   │   └── App.tsx           # React root component
│   ├── package.json          # Node dependencies
│   └── vite.config.ts        # Vite build configuration
├── docker/                   # Sandboxed Runtime Base Images
│   └── python/
│       ├── Dockerfile        # Minimal unprivileged Python 3.11 sandbox image
│       └── seccomp-profile.json # Hardened seccomp syscall filter
├── documentation/            # Architectural and research documentation
├── docker-compose.dev.yml    # Local multi-container development topology
└── .env.example              # Template environment variables
```

---

## 3. Step-by-Step Installation

### Step 3.1: Clone and Configure Environment Variables
Copy the template configuration file to create local configuration:

```bash
cp .env.example .env
```

Review and adjust `.env` parameters if needed:
```ini
# --- PostgreSQL Configuration ---
POSTGRES_USER=lab_admin
POSTGRES_PASSWORD=dev_secret_password
POSTGRES_DB=remote_lab_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://lab_admin:dev_secret_password@localhost:5432/remote_lab_db

# --- Redis Configuration ---
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_URL=redis://localhost:6379/0

# --- Security & JWT ---
SECRET_KEY=super_secret_dev_key_change_in_production_32_bytes_min
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# --- Execution Engine Constraints ---
SANDBOX_IMAGE_PYTHON=lab-sandbox-python:3.11
EXECUTION_TIMEOUT_SECONDS=5
SANDBOX_MEMORY_LIMIT=128m
SANDBOX_CPU_QUOTA=50000
SANDBOX_MAX_PIDS=64
```

---

### Step 3.2: Launch Local Infrastructure (PostgreSQL & Redis)
Use Docker Compose to launch background database and caching services:

```bash
docker compose -f docker-compose.dev.yml up -d postgres redis
```

Verify services are healthy:
```bash
docker ps
```
Both `postgres` and `redis` should show status `Up` (healthy).

---

### Step 3.3: Build the Python Execution Sandbox Image
The worker requires a local unprivileged Docker image to execute submitted code:

```bash
docker build -t lab-sandbox-python:3.11 ./docker/python
```

Verify the image was created:
```bash
docker images lab-sandbox-python:3.11
```

---

### Step 3.4: Setup Backend Virtual Environment & Database
Initialize the Python virtual environment and install backend requirements:

```bash
cd backend
python -m venv venv

# Activate on Linux / macOS:
source venv/bin/activate

# Activate on Windows (PowerShell):
# .\venv\Scripts\Activate.ps1

pip install --upgrade pip
pip install -r requirements.txt
```

Run database migrations to generate database tables:
```bash
alembic upgrade head
```

Start the FastAPI development server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
The API and interactive OpenAPI documentation will be accessible at:
- **API Base:** `http://localhost:8000`
- **Swagger UI:** `http://localhost:8000/docs`

---

### Step 3.5: Start the Execution Worker Daemon
Open a separate terminal window, activate the virtual environment, and start the worker process:

```bash
cd worker
# Activate virtual environment
celery -A tasks.worker worker --loglevel=info --concurrency=4
```

---

### Step 3.6: Setup and Start the Frontend Client
Open a third terminal window to start the React client:

```bash
cd frontend
npm install
npm run dev
```

The frontend development server will launch at:
- **URL:** `http://localhost:5173`

---

## 4. Verification & Sanity Checks

### 4.1 Verify Sandbox Security Isolation
Execute a standalone test using Docker CLI to confirm cgroup limits and unprivileged execution:

```bash
# Test 1: Confirm non-root execution (UID should be 1001)
docker run --rm lab-sandbox-python:3.11 id

# Test 2: Confirm network isolation (Should fail with network unreachable)
docker run --rm --network none lab-sandbox-python:3.11 python -c "import urllib.request; urllib.request.urlopen('https://google.com')"

# Test 3: Confirm memory limit triggers OOM killer
docker run --rm --memory=128m --memory-swap=128m lab-sandbox-python:3.11 python -c "a = 'x' * (200 * 1024 * 1024)"
```

### 4.2 Automated End-to-End Test Suite
Run the automated test suite from the backend directory:

```bash
cd backend
pytest tests/ -v
```
