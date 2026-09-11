# Changelog

All notable changes to the Secure Real-Time Remote Code Execution Laboratory Platform will be documented in this file.

## [0.3.0] - 2026-09-11
### Added
- **Monorepo Directory Structure**: Scaffolded unified monorepo modules (`backend/`, `worker/`, `frontend/`, `docker/`, `database/`, `deployment/`).
- **Local Infrastructure (Docker Compose)**: Configured `docker-compose.dev.yml` provisioning PostgreSQL 15 and Redis 7 with persistent volumes and healthchecks.
- **Environment Configuration**: Created `.env.example` defining database, broker, security, and execution limit parameters.
- **FastAPI Backend Skeleton**: Created ASGI application with lifespan management, CORS middleware, structured logging, and central v1 API router.
- **System Health Endpoint**: Implemented `GET /api/v1/health` verifying API readiness, PostgreSQL connectivity, and Redis broker ping.
- **Asynchronous Database Foundation**: Implemented SQLAlchemy 2.0 `create_async_engine`, async sessionmaker, and `get_db` FastAPI dependency; established Alembic async migration setup (`alembic.ini`, `env.py`).
- **Execution Worker Skeleton**: Scaffolded Celery/async worker service with requirements, task definitions, and Dockerfile.
- **Docker Sandbox Runtime**: Created minimal Alpine Python 3.11 Dockerfile (`uid=1001`) and custom Seccomp-BPF policy.
- **Frontend Skeleton**: Scaffolded React 18 + TypeScript SPA with Vite, Monaco Editor, and xterm.js dependencies.
- **Developer Tooling**: Configured `ruff.toml` for Python 3.11 linting/formatting, `.pre-commit-config.yaml`, `.editorconfig`, and automated pytest test suite (`test_health.py` with 100% pass rate).

## [0.2.0] - 2026-09-11
### Added
- Created `documentation/13_REQUIREMENTS_SPECIFICATION.md` defining functional, non-functional, MVP, and measurable engineering requirements.
- Created `documentation/14_ARCHITECTURE_DECISION_RECORDS.md` documenting ADR-001 through ADR-005 (Docker vs gVisor vs Firecracker, WebSockets vs SSE, Redis Pub/Sub decoupling, PostgreSQL JSONB, tmpfs RAM mounts).
- Created `documentation/15_DEVELOPMENT_SETUP.md` with developer onboarding guide, prerequisites, step-by-step setup, and security validation tests.
- Created `documentation/16_USER_GUIDE.md` detailing user roles (Student, Instructor, Admin), execution outcomes (TLE, MLE, OLE, Runtime Error), and interface workflows.
- Created `documentation/17_RESEARCH_AND_EVALUATION_PLAN.md` detailing academic research questions (RQ1-RQ3), empirical benchmark metrics, and load testing methodology.
- Created `documentation/18_THREAT_MODEL.md` specifying STRIDE threat modeling, attack vector matrix, and Linux kernel defense-in-depth mitigations.
- Created `documentation/19_SYSTEM_DESIGN_DECISIONS.md` explaining producer-consumer decoupling, stream multiplexing protocol, stateless gateway topology, and ephemeral sandbox lifecycles.
- Created root `SYSTEM_ARCHITECTURE.md` mirroring updated architectural diagrams and measurable goals.

### Changed
- Updated project definition to **"Secure Real-Time Remote Code Execution Laboratory Platform"**.
- Restructured `README.md` and `PROJECT_ROADMAP.md` to reflect the Systems-First development order (Foundation $\rightarrow$ Sandbox Core $\rightarrow$ Worker/Broker $\rightarrow$ Backend Gateway $\rightarrow$ Frontend $\rightarrow$ Hardening $\rightarrow$ Cloud Deployment).
- Updated `documentation/01_PROJECT_OVERVIEW.md` and `documentation/02_SYSTEM_ARCHITECTURE.md` with detailed Mermaid sequence diagrams and decoupled Pub/Sub streaming architecture.
- Formally established MVP Scope (Version 1.0) and quantitative engineering limits (5.0s timeout, 128MB RAM, 0.5 CPU core, 64 PIDs, 1MB output cap, 50 concurrent streams).

## [0.1.0] - Initial
- Initial project documentation and architecture planning.
