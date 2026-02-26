# Interior World

Monorepo for an Interior-AI-style product with a Next.js frontend, FastAPI API service, Celery worker, Postgres, and Redis.

## Services

- `web`: Next.js app (App Router, TypeScript)
- `api`: FastAPI orchestration layer + DB access
- `worker`: Celery long-running task processor
- `infra`: operational notes and environment defaults

## Local quick start

1. Copy environment template:
   - `cp .env.example .env` (PowerShell: `Copy-Item .env.example .env`)
2. Start stack:
   - `docker compose up --build`
3. Verify health:
   - API health: `http://localhost:8000/health`
   - Web app: `http://localhost:3000`

## Local service commands (without Docker)

### API

1. `cd api`
2. `python -m pip install -r requirements-dev.txt`
3. `alembic upgrade head`
4. `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

### Worker

1. `cd worker`
2. `python -m pip install -r requirements.txt`
3. `set PYTHONPATH=%cd%;..\\api` (PowerShell: `$env:PYTHONPATH="$PWD;..\\api"`)
4. `celery -A worker_app.celery_app:celery_app worker --loglevel=info`

### Web

1. `cd web`
2. `npm ci`
3. `npm run dev`

## API bootstrap endpoint

- `POST /v1/sessions/bootstrap`
- Creates or refreshes anonymous session and sets `sid` cookie.

## Operations

- Runbook: `docs/RUNBOOK.md`
- Observability reference: `docs/OBSERVABILITY.md`
- E2E test suite: `docs/E2E_TEST_SUITE.md`
- Compatibility assumptions: `API_COMPATIBILITY_NOTES.md`
