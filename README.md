# AI Chargeback Risk & Evidence Response Agent

A synthetic/demo fintech risk-operations application for the Razorpay AI Builder Internship 2026 — Track 02: AI Risk Manager.

## Current phase: Phase 1 — Configuration, Database & Domain Foundation

This phase adds the backend foundation for environment-based configuration, database wiring, ORM domain models, separate Pydantic schemas, consistent API error responses, and seed-data scaffolding. It does **not** include authentication, ML model training, Gemini calls, final demo data, or autonomous financial actions.

All data in this repository is intended for synthetic/demo development only. Real secrets must stay in environment variables and must never be committed.

## Project structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/v1/health.py
│   │   ├── core/config.py
│   │   ├── core/errors.py
│   │   ├── db/base.py
│   │   ├── db/init_db.py
│   │   ├── db/session.py
│   │   ├── main.py
│   │   ├── models/
│   │   │   ├── customer.py
│   │   │   ├── device.py
│   │   │   ├── dispute.py
│   │   │   ├── merchant.py
│   │   │   ├── risk_prediction.py
│   │   │   └── transaction.py
│   │   ├── schemas/
│   │   └── seed/scaffold.py
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   └── package.json
├── .env.example
├── LICENSE
└── README.md
```

## Requirements

- Python 3.12 or newer
- Node.js 20 or newer
- npm 10 or newer

## Environment setup

Copy the safe example environment file if you want local overrides:

```bash
cp .env.example .env
```

Supported backend environment variables:

| Variable | Purpose | Default/example |
| --- | --- | --- |
| `APP_NAME` | FastAPI application title | `AI Chargeback Risk & Evidence Response Agent` |
| `APP_ENV` | Runtime environment; must be `development`, `test`, or `production` | `development` |
| `DATABASE_URL` | SQLAlchemy database URL. SQLite is used for local development; PostgreSQL-compatible URLs are supported for later deployment. | `sqlite:///./chargeback_risk.db` |
| `GEMINI_API_KEY` | Backend-only Gemini key reserved for later phases. Phase 1 does not call Gemini. | empty |
| `BACKEND_CORS_ORIGINS` | Comma-separated allowed frontend origins | `http://localhost:5173` |
| `VITE_API_BASE_URL` | Frontend development API base URL | `http://localhost:8000` |

Invalid configuration fails during settings validation with a clear error. Secrets such as `GEMINI_API_KEY` must be supplied through environment variables and must not be exposed in frontend code.

## Backend setup and startup

From the repository root:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend URLs:

- Health check: <http://localhost:8000/api/v1/health>
- Swagger/OpenAPI docs: <http://localhost:8000/docs>

Expected health response:

```json
{"status":"ok","service":"api"}
```

Errors use a stable API response shape:

```json
{"detail":"Not Found","code":"http_error"}
```

## Database initialization

The backend initializes tables on application startup for local development. To initialize a fresh database directly from the command line:

```bash
cd backend
python -c "from app.db.init_db import init_db; init_db()"
```

The Phase 1 schema includes synthetic/demo-ready domain tables for:

- customers
- merchants
- devices
- transactions
- disputes
- risk_predictions

Identifiers are string-safe UUIDs. Domain tables include `created_at` and `updated_at` timestamps plus indexes for common lookups such as transaction IDs, customer IDs, merchant IDs, model versions, and timestamps. The current initialization path is intentionally migration-ready so future phases can add Alembic without changing model definitions.

## Frontend setup and startup

Open a second terminal from the repository root:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:

- Dashboard shell: <http://localhost:5173>

The frontend uses Vite's development proxy so browser requests to `/api/v1/health` are forwarded to the backend at `http://localhost:8000`.

## Tests and checks

Backend tests:

```bash
cd backend
pytest
```

Frontend production build check:

```bash
cd frontend
npm run build
```

## Phase 1 limitations

- No authentication yet.
- No ML risk model yet.
- No Gemini investigation agent yet.
- No final synthetic demo seed data yet.
- No real or fake business metrics yet.
- No financial actions of any kind.

All future evidence and metrics must come from real tool/database/model output in later phases.
