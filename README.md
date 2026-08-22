# AI Chargeback Risk & Evidence Response Agent

A synthetic/demo fintech risk-operations application for the Razorpay AI Builder Internship 2026 — Track 02: AI Risk Manager.

## Current phase: Phase 0 — Repository Foundation

This phase creates the basic runnable project shape only. It does **not** include authentication, business database models, machine learning, Gemini, fake metrics, or financial actions.

Think of this phase like building the empty workshop before creating the real product:

| Simple idea | Technical name |
| --- | --- |
| The service that answers data requests | Backend API |
| The screen humans use in a browser | Frontend app |
| A tiny endpoint that says the service is alive | Health check |
| A safe sample settings file | `.env.example` |
| Automated checks that prove code works | Tests |

## Project structure

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   └── api/v1/health.py
│   ├── tests/test_health.py
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── App.css
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── .env.example
├── .gitignore
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

Do not commit `.env`. Real secrets must stay in environment variables only.

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

## Phase 0 limitations

- No authentication yet.
- No database models yet.
- No ML risk model yet.
- No Gemini investigation agent yet.
- No real or fake business metrics yet.
- No financial actions of any kind.

All future evidence and metrics must come from real tool/database/model output in later phases.
