# Contributing to Secure Real-Time Remote Code Execution Platform

Thank you for your interest in contributing to the **Secure Real-Time Remote Code Execution Laboratory Platform**. This project is engineered to rigorous academic and production standards across Operating Systems, Distributed Systems, and Cybersecurity.

We welcome contributions from researchers, systems engineers, and students.

---

## 1. Code of Conduct

All contributors and maintainers are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md). Please treat everyone with respect, professionalism, and academic integrity.

---

## 2. Development Principles

1. **Zero Compromise on Isolation:** Untrusted code execution must remain mathematically quarantined. Any PR altering container namespaces, cgroups, Seccomp profiles, or network settings must include adversarial test cases proving containment.
2. **100% Test Coverage & Green CI:** All 88+ existing automated tests must pass (`pytest backend/tests/ -v`). Any new feature must be accompanied by comprehensive unit, integration, or chaos tests.
3. **Strict Linting & Typing:** Python code must satisfy `ruff check` and `ruff format`. TypeScript code must satisfy `tsc --noEmit`.
4. **Reproducible Systems:** Infrastructure changes must be reflected in both `docker-compose.dev.yml` and the production Helm chart (`helm/rce-platform/`).

---

## 3. Git Branching & Commit Workflow

We follow an autonomous professional Git workflow modeled after GitFlow:

- **`main`**: Production-ready releases only. Every commit is tagged with semantic versioning (`v2.0.0`).
- **`develop`**: Primary integration branch for verified features.
- **`feature/<feature-name>`**: Dedicated feature branches branched from `develop`.

### Commit Message Convention (Conventional Commits)
Commits must follow the Conventional Commits specification:
- `feat(...)`: A new feature or capability.
- `fix(...)`: A bug fix or patch.
- `docs(...)`: Documentation updates or academic explanations.
- `refactor(...)`: Code changes that neither fix a bug nor add a feature.
- `perf(...)`: Performance optimization or benchmark harness improvement.
- `test(...)`: Adding or updating test suites.
- `chore(...)`: Maintenance, release tags, or dependency updates.

Example:
```bash
git commit -m "feat(sandbox): implement microvm kvm capability negotiation driver"
```

---

## 4. Local Development Setup

### Prerequisites
- Python 3.12+
- Node.js 20+ & npm
- Docker Engine 24+ with cgroups v2 support
- Git

### Initializing the Backend
```bash
# Clone the repository
git clone https://github.com/farazrasul0-cmd/secure-remote-code-execution-lab.git
cd secure-remote-code-execution-lab

# Setup virtual environment
python -m venv backend/venv
source backend/venv/bin/activate  # Or .\backend\venv\Scripts\activate on Windows

# Install dependencies
pip install -r backend/requirements.txt

# Run database migrations
alembic -c backend/alembic.ini upgrade head

# Run tests
pytest backend/tests/ -v
```

### Initializing the Frontend
```bash
cd frontend
npm install
npm run build
```

---

## 5. Submitting a Pull Request (PR)

1. Fork the repository and create your branch from `develop`:
   ```bash
   git checkout -b feature/my-enhancement develop
   ```
2. Make your modifications following code formatting:
   ```bash
   python -m ruff check backend/ worker/
   python -m ruff format backend/ worker/
   ```
3. Run the automated test suite:
   ```bash
   python -m pytest backend/tests/ -v
   ```
4. Push to your fork and submit a Pull Request targeting the `develop` branch.
5. Ensure all automated GitHub Actions checks pass:
   - Python Ruff Linting & Formatting
   - Full Pytest Test Suite (88/88)
   - Frontend TypeScript Typecheck
   - Helm Chart Linting
   - Aqua Security Trivy Scan

---

## 6. Academic Attribution

If you utilize this codebase for university coursework, graduate research, or comparative benchmarks, please cite the platform according to the citation metadata in `README.md`.
