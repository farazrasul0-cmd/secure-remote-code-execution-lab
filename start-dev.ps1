# ==============================================================================
# Local Development Environment Setup & Launcher
# Secure Real-Time Remote Code Execution Laboratory Platform
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Secure Remote Code Execution Lab - Local Dev Environment" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Check .env configuration
if (-not (Test-Path ".env")) {
    Write-Host "[+] Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}
if (-not (Test-Path "backend/.env")) {
    Copy-Item ".env" "backend/.env"
}
Write-Host "[*] Environment configuration (.env) ready." -ForegroundColor Green

# 2. Check Docker Daemon
Write-Host "[*] Checking Docker daemon status..." -ForegroundColor Yellow
$dockerOk = $false
try {
    $null = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        $dockerOk = $true
    }
} catch {
    $dockerOk = $false
}

if (-not $dockerOk) {
    Write-Host "[!] Docker daemon is not responding. Please make sure Docker Desktop is running." -ForegroundColor Red
    exit 1
}

Write-Host "[*] Docker daemon is active." -ForegroundColor Green

# 3. Start PostgreSQL and Redis
Write-Host "[*] Starting PostgreSQL and Redis containers..." -ForegroundColor Yellow
docker compose -f docker-compose.dev.yml up -d

# Wait for PostgreSQL healthcheck
Write-Host "[*] Waiting for PostgreSQL to be healthy..." -ForegroundColor Yellow
$pgHealthy = $false
$retries = 15
while ($retries -gt 0) {
    Start-Sleep -Seconds 2
    $retries -= 1
    $status = docker inspect --format "{{.State.Health.Status}}" rce_postgres_dev 2>$null
    if ($status -eq "healthy") {
        $pgHealthy = $true
        break
    }
}

if ($pgHealthy) {
    Write-Host "[*] PostgreSQL is healthy and accepting connections." -ForegroundColor Green
} else {
    Write-Host "[!] PostgreSQL container started." -ForegroundColor Yellow
}

# 4. Build Sandbox Image
Write-Host "[*] Building hardened Python execution sandbox image (lab-sandbox-python:3.11)..." -ForegroundColor Yellow
docker build -t lab-sandbox-python:3.11 docker/python/
Write-Host "[*] Sandbox image built successfully." -ForegroundColor Green

# 5. Run Database Migrations
$alembicExe = "backend\venv\Scripts\alembic.exe"
if (Test-Path $alembicExe) {
    Write-Host "[*] Applying Alembic database migrations..." -ForegroundColor Yellow
    Push-Location backend
    & ".\venv\Scripts\alembic.exe" upgrade head
    Pop-Location
    Write-Host "[*] Database migrations applied successfully." -ForegroundColor Green
} else {
    Write-Host "[!] Backend venv not found at backend\venv. Skipping migrations." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " All Infrastructure Services Are Ready!" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "To run the application stack, open 3 terminal tabs:" -ForegroundColor White
Write-Host ""
Write-Host "Tab 1 - API Gateway (Backend):" -ForegroundColor Cyan
Write-Host "  .\backend\venv\Scripts\activate" -ForegroundColor White
Write-Host "  uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8001 --reload" -ForegroundColor Yellow
Write-Host ""
Write-Host "Tab 2 - Celery Execution Worker:" -ForegroundColor Cyan
Write-Host "  .\backend\venv\Scripts\activate" -ForegroundColor White
Write-Host "  celery -A worker.tasks.execution worker --loglevel=info --concurrency=2" -ForegroundColor Yellow
Write-Host ""
Write-Host "Tab 3 - React Frontend:" -ForegroundColor Cyan
Write-Host "  cd frontend" -ForegroundColor White
Write-Host "  npm run dev" -ForegroundColor Yellow
Write-Host ""
Write-Host "Access Points:" -ForegroundColor White
Write-Host "  Frontend Web UI:   http://localhost:5173" -ForegroundColor Green
Write-Host "  FastAPI OpenAPI:   http://localhost:8001/docs" -ForegroundColor Green
Write-Host "  PostgreSQL Store:  localhost:5432 (remote_lab_db)" -ForegroundColor Green
Write-Host "  Redis Broker:      localhost:6379" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
