# Wingify Assignment — Financial Document Analyzer

A production‑grade system for uploading and analyzing financial documents (e.g., quarterly updates, 10‑Ks, investor decks) using an AI agentic pipeline. The goal of the assignment was to debug a deliberately broken prototype and turn it into an enterprise‑ready, full‑stack solution with secure APIs, persistent storage, and a modern frontend.

> **Challenge note:** The original brief states that “every single line of code contains bugs, inefficiencies, or poor practices.” This README explains what the system does, how to run it locally, what’s implemented, and what remains planned as follow‑ups.

---

## 🚀 What’s Included in This Submission

- **FastAPI backend** with modular app factory, CORS/trusted hosts, and health endpoint.
- **MongoDB + Beanie ODM** models for `User` and `Document` with statuses (`UPLOADED`, `PROCESSING`, `COMPLETED`, `FAILED`) and a field to store the final analysis payload.
- **JWT authentication** (bearer tokens), **bcrypt** password hashing, and **role scaffolding** (Admin/User).
- **Simple rate limiting** dependency (sliding time window) for authenticated requests.
- **CrewAI agents & tasks**: _document verification_, _financial analysis_, _risk assessment_, and _investment recommendation_ wired to an OpenAI LLM and a search tool.
- **Pluggable tools** for PDF parsing/metric extraction/search with clear seams for upgrading to robust implementations (OCR, table extraction, etc.).
- **Project structure** ready for adding routers, services, observability, and job workers.
- **Docker‑ready** baseline with environment‑driven settings.

---

## 🧭 Architecture (High Level)

```
Client (Web)  ──►  FastAPI (Auth, Upload, Orchestration, History)
                    │
                    ├── MongoDB (Users, Documents, Analyses, Audit)
                    │
                    ├── LLM Agents (CrewAI + OpenAI)
                    │      ├─ Document Verifier
                    │      ├─ Financial Analyst
                    │      ├─ Risk Assessor
                    │      └─ Investment Advisor
                    │
                    └── Tools (PDF parsing, metric extraction, search)
```

**Key flows**
1) **Auth**: register/login → JWT bearer token for all protected routes.  
2) **Upload**: PDF is stored, `Document` status set to `UPLOADED`.  
3) **Analyze**: Orchestrated CrewAI tasks run (verify → analyze → risk → recommendation) and persist a single `analysis` payload back on the `Document` record.  
4) **Retrieve**: Client fetches status & results; can export or trigger re‑runs.

---

## 🧑‍💻 Tech Stack

- **Backend**: FastAPI, Pydantic, Beanie (MongoDB), python‑jose (JWT), passlib (bcrypt)
- **AI/Agents**: CrewAI, OpenAI Chat API (configurable model), Serper (search)
- **Storage**: MongoDB (7.x suggested), GridFS/S3 (future) for large files
- **Tasks/Workers (planned)**: Celery/RQ/Huey (with Redis) for long‑running jobs
- **Frontend**: React + Vite (suggested), Tailwind + shadcn/ui (suggested)
- **Observability (planned)**: LLM traces, request logging, metrics dashboards

---

## 📦 Project Structure (relevant parts)

```
.
├─ api/                    # Routers (auth, documents, analysis) – add here
├─ auth/
│  └─ security.py          # JWT, hashing, current user dependency
├─ config/
│  └─ settings.py          # Pydantic settings (env‑driven)
├─ database/
│  └─ mongodb.py           # Motor/Beanie connection helpers
├─ models/
│  ├─ user.py              # User model (email/username/role/etc.)
│  └─ document.py          # Document model (status/analysis/etc.)
├─ crew/
│  ├─ agents.py            # CrewAI agents (analyst, verifier, risk, advisor)
│  ├─ task.py              # CrewAI tasks (verify/analyze/risk/reco)
│  └─ tools.py             # Tools (parse PDF, metrics, search)
├─ api/deps.py             # Rate‑limit dependency and common deps
├─ main.py                 # App factory, middleware, health, router mount
├─ data/                   # Sample PDFs (e.g., TSLA Q2 2025)
└─ README.md
```


## ⚙️ Getting Started (Local)

### Prerequisites
- **Python 3.11** (required)
- **MongoDB 7.x** (local Docker or managed cluster)
- **Node.js 18+** (for the web app if you scaffold it)
- (Optional) **Redis** if you add background jobs

### 1) Clone & Environment
```bash
git clone <your-fork-url> wingify-financial-analyzer
cd wingify-financial-analyzer
cp .env.example .env    # then edit .env
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

**`.env` example**
```
# --- FastAPI / App ---
PROJECT_NAME=Financial Document Analyzer
VERSION=0.1.0
DEBUG=true
API_V1_STR=/api/v1
BACKEND_CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# --- Security ---
SECRET_KEY=please_change_me
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
RATE_LIMIT_CALLS=60
RATE_LIMIT_PERIOD=60

# --- Storage ---
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=wingify_finance
UPLOAD_DIR=./uploads

# --- LLM / Tools ---
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.2
SERPER_API_KEY=serper_...
```

### 2) Run MongoDB (Docker)
```bash
docker run -d --name mongo -p 27017:27017 mongo:7
```

### 3) Start the API
```bash
uvicorn main:app --reload --port 8000
```
Open http://localhost:8000/docs for the interactive API (if `DEBUG=true`).

### 4) (Optional) Frontend
Create a React app (Vite or CRA), set `VITE_API_BASE=http://localhost:8000`, and implement the flows below.

---

## 🧪 API Quickstart

The exact routers may vary in your fork, but a production API will typically include:

- **Auth**
  - `POST /api/v1/auth/register` → create account
  - `POST /api/v1/auth/login` → exchange credentials for JWT
  - `GET  /api/v1/auth/me` → current user

- **Documents**
  - `POST /api/v1/documents` (multipart/form-data) → upload PDF
  - `GET  /api/v1/documents` → list my docs (filters by status/date/type)
  - `GET  /api/v1/documents/{doc_id}` → details (+ analysis if completed)
  - `DELETE /api/v1/documents/{doc_id}` → delete

- **Analysis**
  - `POST /api/v1/analysis/{doc_id}` → kick off analysis pipeline
  - `GET  /api/v1/analysis/{doc_id}/status` → check status/progress
  - `GET  /api/v1/analysis/{doc_id}/result` → final merged report
  - `POST /api/v1/analysis/{doc_id}/export` → download as PDF/JSON

> The backend already includes JWT verification, rate limiting, and Beanie models. Plug your routers into the app (see `main.py`) and wire handlers to agents/tasks.

---

## 🔐 Security & Roles

- **JWT Bearer Auth** with access‑token expiry.
- **Password hashing** via bcrypt.
- **Role scaffold**: `admin` / `user` (extend to RBAC on endpoints).
- **Rate limiting** per user (in‑memory sliding window; swap for Redis in prod).
- **Upload hygiene**: enforce content types, size caps, and scanning (to add).

---

## 📈 Analysis Pipeline (CrewAI)

1. **Verification** — validates the document, detects period/type, extracts top‑level metrics.  
2. **Financial Analysis** — trends, ratios, cash flow/BS quality, industry context.  
3. **Risk Assessment** — liquidity, credit, market, operational, regulatory, ESG.  
4. **Investment Recommendation** — thesis, targets, sizing, scenarios (bull/base/bear).

Each step has a `Task` with an `expected_output` shape for structured, reviewable results. Tools (PDF parsing, metrics extraction, search) are injected per agent.

> You can run tasks synchronously first; then lift long‑running work into a background queue with progress updates pushed to the client (SSE/WebSocket/polling).

---

## 🧩 Handling Edge Cases (from the brief)

- Large/secured PDFs, non‑English or scanned content (add OCR + table parsers)
- Concurrent uploads and long analyses (move to background workers; idempotency)
- Network/database faults (retries with backoff; DLQs; circuit breakers)
- Rate limits and timeouts (client backoff; “Retry‑After”; resumable uploads)
- Malicious inputs (MIME enforcement, antivirus scan, signed URLs, size limits)
- CORS and session handling (strict origins; refresh tokens/PKCE if needed)

---

## 🛠️ Developer Experience

- **Type & style**: mypy/pyright, ruff/flake8, black (suggested)
- **Testing**: pytest + httpx + mongomock (suggested)
- **Observability**: structured logs, LLM trace hooks, Prometheus/Grafana (suggested)
- **Migrations**: Beanie `init_beanie` with revisions (or pydantic‑model versioning)

---

## 🐳 Docker Compose (example)

```yaml
version: "3.9"

services:
  api:
    build: .
    command: uvicorn main:app --host 0.0.0.0 --port 8000
    environment:
      - MONGODB_URI=mongodb://mongo:27017
      - MONGODB_DB=wingify_finance
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SERPER_API_KEY=${SERPER_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
      - DEBUG=true
    depends_on:
      - mongo
    ports:
      - "8000:8000"

  mongo:
    image: mongo:7
    container_name: wingify-mongo
    restart: unless-stopped
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

volumes:
  mongo_data: {}
```

> If you add a separate **web** container, set `VITE_API_BASE=http://localhost:8000` and expose it on another port (e.g., 5173).

---

## ✅ Status & Today’s Work (highlights)

- Wired **MongoDB + Beanie** models for `User` and `Document`.
- Implemented **JWT auth** + password hashing + `get_current_user`.
- Added **rate limiting** dependency and CORS/trusted hosts.
- Created **CrewAI agents & tasks** (verification, analysis, risk, recommendation).
- Stitched **tools** for parsing, metric extraction, and search (stubbed for upgrades).
- App factory with **health endpoint**, startup/shutdown hooks, and upload dir bootstrap.
- Baseline **Docker** instructions and environment configuration.

---

## 🐉 Known Issues & Next Steps

- **Duplicate/legacy models**: ensure there’s a single source of truth for `Document` and remove any legacy duplicates; migrate collections if needed.
- **Tools** are **placeholder** implementations; replace with robust PDF/OCR/table extraction (e.g., unstructured, docTR, pdfplumber, Camelot/Tabula).
- **Background jobs**: move analysis runs off the request thread (Celery/RQ + Redis) and stream progress to the UI (WebSockets/SSE).
- **RBAC**: gate admin capabilities (user management, global search, deletes) with role checks.
- **File storage**: switch large binaries to GridFS/S3; keep metadata in Mongo.
- **Observability**: add LLM trace collection, request metrics, and error dashboards.
- **E2E tests**: add happy‑path and adversarial cases (corrupted PDFs, huge docs, etc.).

---

## 📄 Sample Test Document

You can try Tesla’s Q2‑2025 update (or any investor PDF) by placing it in `data/` and invoking the analysis route. The analysis merges Verification → Financial → Risk → Recommendation into a single doc‑level report.


## 🧭 Roadmap / Next Steps

### Backend
1) **WebSocket live progress**
   - Add `websocket` route (e.g., `/ws/analysis/{doc_id}`) broadcasting pipeline events: `queued → parsing → analyzing → risk → recommendation → completed/failed`.
   - Suggested pattern: enqueue analysis (Celery task) → push state to Redis pub/sub → FastAPI background WS task relays to clients subscribed to the `doc_id` channel.

2) **Document deletion APIs**
   - `DELETE /api/v1/documents/{doc_id}`: soft-delete metadata and mark binary for purge.
   - `DELETE /api/v1/documents/{doc_id}/hard`: admin-only hard delete (and storage object from GridFS/S3).
   - Add authorization checks: owner or admin; emit audit log entries.

3) **CrewAI instruction hardening**
   - Externalize prompts to versioned files (e.g., `prompts/*.md`) with structured “expected_output” contracts.
   - Add guardrails: max token limits, deterministic temperature for verification, retries with exponential backoff, and JSON schema validation before persisting.

4) **Redis + Celery queue**
   - Queue long-running analyses with **Celery** (or RQ/Huey).
   - Single source of truth for status in Redis (or database), with periodic heartbeats to detect stalled tasks.
   - Idempotency keys: per `(doc_id, prompt_hash)` to avoid duplicate runs.

5) **Notifications on completion**
   - Strategy A: **Webhooks** (user-supplied URL) with signed HMAC and retry.
   - Strategy B: **Email** via SES/SendGrid; **push** via FCM/Web Push.
   - Strategy C: **Serverless** hook (e.g., cloud function) subscribed to a queue topic that receives `ANALYSIS_COMPLETED` events, then fans out to channels.

6) **Security hardening**
   - File size/type enforcement (MIME sniff + magic numbers), antivirus scan hook, rate limits on uploads, signed download URLs.
   - RBAC middleware for admin-only endpoints, rotating JWT secret, refresh tokens (optional), and audit logging.

7) **Observability**
   - Structured logs with correlation IDs per request & doc_id.
   - LLM call tracing (latency, token usage, errors) + metrics (Prometheus).
   - SLA SLOs: p95 analysis duration, queue latency, failure rates.

---

### Frontend (React – based on your `App.jsx`)

1) **Routing (weblink)**
   - Use React Router:
     - `/login` – AuthCard
     - `/` – Dashboard (Uploader + Documents)
     - `/docs/:id` – DetailPanel view with polling/WS
     - `/settings` – API base, profile, API keys (future)
   - Keep `API_BASE` in `import.meta.env.VITE_API_BASE` with a runtime override via `window.__API_BASE__` for containerized deployments.

2) **Robust error handling**
   - Central `fetch` wrapper already returns `err.retryAfter` when 429; show toast/banner with “Retry in N sec” + exponential backoff.
   - Add boundary components: `<ErrorBoundary>` wrapping table/detail panels.
   - Show upload-specific errors (size/type/virus) and server validation messages.

3) **Nice-to-have UX**
   - Drag-to-upload (done), add paste-to-upload + progress bar per file.
   - Replace polling with a **WebSocket** client: auto-connect on `/docs/:id`, live badges.
   - Add **delete** button per doc (soft delete) with optimistic UI and undo.
   - Skeletons for detail view; “Copy as Markdown/JSON” export.
   - Keyboard shortcuts: `u` upload dialog, `r` refresh, `?` help.

4) **State & caching**
   - Keep a tiny cache keyed by `doc_id` (Map) to avoid refetch thrash.
   - Debounce analysis trigger and disable button while queued/processing.

5) **Accessibility & theming**
   - Respect reduced motion; ensure focus states; high-contrast theme toggle.

---

## 🔌 Example Additions (snippets)

### FastAPI: WebSocket endpoint

```python
# ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import DefaultDict, Set
from collections import defaultdict

router = APIRouter()
channels: DefaultDict[str, Set[WebSocket]] = defaultdict(set)

@router.websocket("/ws/analysis/{doc_id}")
async def ws_analysis(websocket: WebSocket, doc_id: str):
    await websocket.accept()
    channels[doc_id].add(websocket)
    try:
        await websocket.send_json({"type": "hello", "doc_id": doc_id})
        while True:
            await websocket.receive_text()  # optional ping/pong
    except WebSocketDisconnect:
        pass
    finally:
        channels[doc_id].discard(websocket)

# Somewhere in your Celery task, push updates:
# for step in ["queued","parsing","analyzing","risk","recommendation","completed"]:
#     for ws in list(channels[doc_id]):
#         await ws.send_json({"type":"progress","step":step})
```

### Celery: enqueue analysis

```python
# worker.py
from celery import Celery
celery = Celery(__name__, broker="redis://localhost:6379/0", backend="redis://localhost:6379/1")

@celery.task(bind=True, max_retries=3)
def analyze_doc(self, doc_id: str, prompt: str):
    # load doc, run CrewAI pipeline, persist results
    # publish WS/Redis events: {"doc_id": doc_id, "state": "analyzing", ...}
    return {"doc_id": doc_id, "status": "COMPLETED"}
```

### API: delete endpoints

```python
@router.delete("/api/v1/documents/{doc_id}", status_code=204)
async def soft_delete_document(doc_id: str, user=Depends(get_current_user)):
    # mark deleted_by, deleted_at; hide from default queries
    return Response(status_code=204)

@router.delete("/api/v1/documents/{doc_id}/hard", status_code=204, dependencies=[Depends(require_admin)])
async def hard_delete_document(doc_id: str):
    # remove metadata + binary; write audit record
    return Response(status_code=204)
```

### React: WebSocket client hook

```jsx
import { useEffect, useRef } from "react";

export function useAnalysisWS(docId, onEvent, base = API_BASE) {
  const wsRef = useRef(null);
  useEffect(() => {
    if (!docId) return;
    const url = (base.replace(/^http/, "ws")) + `/ws/analysis/${docId}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;
    ws.onmessage = (ev) => { try { onEvent(JSON.parse(ev.data)); } catch {} };
    ws.onclose = () => { /* maybe attempt limited reconnect */ };
    return () => ws.close();
  }, [docId, base, onEvent]);
  return wsRef;
}
```

## 🧱 Engineering Hygiene & Governance

### Performance: Singleton Metaclasses (resource-heavy services)
Use a Singleton for clients that are expensive to create (LLM, DB pools, PDF parsers, Serper, Redis). Prefer dependency injection, but enforce a safe singleton when lifecycle is process-wide.

```python
# core/singletons.py
from __future__ import annotations
import threading

class SingletonMeta(type):
    _instances = {}
    _lock = threading.Lock()
    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

# Example: OpenAI or Crew client
class LLMClient(metaclass=SingletonMeta):
    def __init__(self, api_key: str, model: str):  # type: ignore[no-redef]
        self.api_key = api_key
        self.model = model
        # init http session, retry policy, etc.
```

**Where to apply:** OpenAI/Crew client, Redis, Celery app instance, PDF OCR engine, Mongo motor client (already pooled). Avoid singletons for request-scoped objects.

---

### Testing: Pytest Matrix & Cases
- **Unit**: models (validation), utils (masking, rate limiter), auth (JWT), tools (parsers).
- **Integration**: FastAPI routes with `httpx.AsyncClient` + `mongomock` or test DB.
- **Property tests**: randomized inputs for parser/normalizers (e.g., Hypothesis).
- **E2E (optional)**: spin docker compose (api + mongo + redis) and run smoke tests.

Example tests:
```python
# tests/test_masking.py
from core.masking import mask_pii

def test_mask_email():
    assert mask_pii("alice@example.com") == "a***e@example.com"

def test_mask_phone():
    assert mask_pii("+1-415-555-1212") == "+*-***-***-1212"
```

```python
# tests/test_auth.py
import jwt, time
from auth.security import create_access_token, ALGORITHM, SECRET_KEY

def test_jwt_roundtrip():
    token = create_access_token({"sub":"u1"}, expires_minutes=1)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "u1"
```

```python
# tests/test_docs_api.py
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200
```

---

### Admin APIs & Console

**APIs**
- `POST /api/v1/admin/reset-password` (admin-only): reset or force-rotate user password, emit audit log.
- `GET  /api/v1/admin/errors` (admin-only): last N errors with correlation IDs, user ids (masked), request paths.
- `GET  /api/v1/admin/users/:id/logs` (admin-only): user-scoped logs/events (masked).
- `POST /api/v1/admin/users/:id/otp/issue` → issues a one-time code (email/SMS) for 2FA or recovery.
- `POST /api/v1/admin/users/:id/disable` / `enable` → toggles login.

**Frontend (admin pages)**
- `/admin` dashboard: error stream, failing jobs, queue depth, p95 analysis duration.
- `/admin/users` list + detail: reset password, enable/disable, OTP issue, view masked logs.
- `/admin/settings` system config (readonly in prod), key rotation reminders.

**OTP service**
- Store `{user_id, code_hash, expires_at, attempts}`.
- Rate-limit by user & IP; hash codes (never store plaintext); send via provider (SES/SendGrid/SMS).

---

### Logging & Privacy (user-id specific; PII masking)

**Correlation**
- Generate `X-Request-ID` per request; attach `user_id` if present.
- Persist to `audit_logs` with `when, who, action, target, status, request_id, ip`.

**Masking**
```python
# core/masking.py
import re

EMAIL = re.compile(r"([A-Za-z0-9._%+-])([^@]{0,})([A-Za-z0-9._%+-])(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE = re.compile(r"(\+?\d)[\d\-\s]{5,}(\d{4})")

def mask_pii(text: str) -> str:
    text = EMAIL.sub(lambda m: f"{m.group(1)}***{m.group(3)}{m.group(4)}", text)
    text = PHONE.sub(lambda m: f"{m.group(1)}***{m.group(2)}", text)
    return text
```

**Logging Filter**
```python
# core/logging_filters.py
import logging
from core.masking import mask_pii

class PIIMaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_pii(record.msg)
        return True
```

Wire into `logging.config.dictConfig` and ensure any `user_id` context is structured (JSON logger).

---

### Developer Onboarding: Makefile & Poetry

**Makefile**
```makefile
# Makefile
.PHONY: setup dev test lint fmt up down seed

setup:  ## Install tooling
\tpython -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install poetry pre-commit

dev:    ## Install deps and prepare git hooks
\tpoetry install
\tpre-commit install

test:   ## Run tests with coverage
\tpoetry run pytest -q --maxfail=1 --disable-warnings --cov=.

lint:   ## Static checks
\tpoetry run ruff check . && poetry run mypy .

fmt:    ## Format
\tpoetry run ruff format .

up:     ## Start infra (Mongo/Redis) via docker compose
\tdocker compose up -d

down:   ## Stop infra
\tdocker compose down -v
```

**Poetry (snippet)**

```toml
# pyproject.toml
[tool.poetry]
name = "wingify-financial-analyzer"
version = "0.1.0"
description = "Financial document analyzer (assignment)"
authors = ["Your Name <you@example.com>"]
readme = "README.md"
packages = [{include="."}]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "*"
uvicorn = {extras=["standard"], version="*"}
beanie = "*"
pydantic = "*"
python-jose = "*"
passlib = {version="*", extras=["bcrypt"]}
httpx = "*"
pymongo = "*"
pytest = "*"
pytest-asyncio = "*"
ruff = "*"
mypy = "*"
celery = "*"
redis = "*"

[tool.poetry.group.dev.dependencies]
pre-commit = "*"

[tool.mypy]
python_version = "3.11"
strict = true
```

---

### Type Hints & Stub Files (`.pyi`)
- Provide `.pyi` stubs for modules that wrap C libs or dynamically built attributes (e.g., `core/singletons.pyi`, `crew/tools/*.pyi`).  
- Useful for shared interfaces like `AnalysisToolProtocol`, `Masker`, or `Notifier`.
- Keep `__all__` in `.pyi` aligned with public API and run `mypy --strict` in CI.

Example stub:
```python
# crew/interfaces.pyi
from typing import Protocol, Dict, Any

class AnalysisTool(Protocol):
    def run(self, *, doc_id: str, payload: Dict[str, Any]) -> Dict[str, Any]: ...
```

---

### Pre-commit & Branch Protections

**pre-commit config**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.8
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.11.2
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: check-added-large-files
      - id: end-of-file-fixer
      - id: trailing-whitespace
```

**Git branches & commits**
- Protect `main`, `dev`, `stage`, `qa` in GitHub: require PRs, code owners, passing checks, linear history.
- Enforce naming via docs/CI: `feature/<JIRA-123>-short-slug`, `bugfix/<JIRA-234>-slug`, `chore/...`.
- Conventional Commits with JIRA:
  - `feat(JIRA-123): add Celery queue for analysis`
  - `fix(JIRA-234): mask emails in logs`
- Optional server-side hook (org-level) or CI regex check to block misnamed branches/commits.

---

### CI ideas
- Matrix: `py3.11` with `lint`, `typecheck`, `test`, `docker-build`.
- Spin services via `docker compose` and run API smoke tests.
- Upload coverage to badges; fail if < threshold.
