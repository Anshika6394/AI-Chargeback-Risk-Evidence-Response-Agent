# AI Chargeback Risk & Evidence Response Agent

A synthetic/demo fintech risk-operations application for the Razorpay AI Builder Internship 2026 — Track 02: AI Risk Manager.

## Current phase: Phase 3 — ML Training, Model Comparison & Risk Scoring

Earlier phases added the backend foundation for environment-based configuration, database wiring, ORM domain models, separate Pydantic schemas, consistent API error responses, and seed-data scaffolding. It does **not** include authentication, Gemini calls, the investigation agent, dashboard workflows, or autonomous financial actions.

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

## Current limitations

- No authentication yet.
- No Gemini investigation agent yet.
- No final synthetic demo seed data yet.
- No real or fake business metrics yet.
- No financial actions of any kind.

All future evidence and metrics must come from real tool/database/model output in later phases.

## Phase 3 — ML Training, Model Comparison & Risk Scoring

Phase 3 adds a backend-only machine-learning package under `backend/app/ml`. It trains on deterministic synthetic/demo data seeded from the SQLAlchemy models, labels chargeback risk from actual synthetic dispute rows, and keeps Gemini completely out of quantitative prediction.

The training pipeline:

- extracts numerical and categorical features from synthetic transactions, customers, merchants, and devices;
- uses stratified train/validation/test splitting with a fixed seed;
- keeps the held-out test split out of model selection;
- preprocesses numerical values with scaling and categorical values with one-hot encoding;
- compares Logistic Regression, Random Forest, and XGBoost using validation Precision, Recall, F1, Accuracy, ROC-AUC, and confusion matrix;
- selects the final model by highest validation Recall, with F1 and ROC-AUC as tie-breakers because missed chargebacks are costlier than manual review;
- persists preprocessing and model together as `backend/artifacts/models/chargeback-risk-v1.joblib` plus versioned metadata JSON.

Train the model from the backend directory:

```bash
cd backend
python -m app.ml.train_model
```

Install backend development dependencies before running the test suite:

```bash
cd backend
python -m pip install -e '.[dev]'
```

Configurable ML environment variables:

| Variable | Purpose | Default/example |
| --- | --- | --- |
| `ML_MODEL_ARTIFACT_PATH` | Path to the persisted preprocessing+model artifact used by `predict_risk()` | `artifacts/models/chargeback-risk-v1.joblib` |
| `RISK_LOW_THRESHOLD` | Minimum 0–100 score for MEDIUM risk | `35` |
| `RISK_HIGH_THRESHOLD` | Minimum 0–100 score for HIGH risk | `70` |

The reusable prediction service is `app.ml.predict_risk(features, settings=None)`. It returns model probability, bounded 0–100 risk score, risk level (`LOW`, `MEDIUM`, `HIGH`), and model version. It does not call Gemini and does not execute financial actions.

## Phase 4 — Held-Out Evaluation, Explainability & Model Registry

Phase 4 evaluates the persisted validation-selected model on the untouched deterministic synthetic test split. The command below trains/selects using the training and validation splits, then performs one explicit held-out evaluation of that selected persisted artifact; test metrics do not affect model selection.

```bash
cd backend
python -m app.ml.train_model
```

It writes these reproducible, machine-readable/auditable artifacts under `backend/artifacts/models/`:

- `chargeback-risk-v1.evaluation.json` — actual Precision, Recall, F1, Accuracy, ROC-AUC, threshold, confusion matrix, support counts, class distribution, split provenance, and dataset fingerprint;
- `chargeback-risk-v1.evaluation.md` — human-readable rendering of the same calculated results;
- `chargeback-risk-v1.registry.json` — model version/type, feature schema, synthetic dataset metadata, metric snapshot, and absolute paths to the model, training metadata, and evaluation artifacts.

`predict_risk(..., top_n_factors=5)` now returns `model_derived_risk_factors`. Tree classifiers use their model-native feature importances and linear classifiers use coefficients, combined with the exact transformed input values. These factors are traceable to the feature schema and are deliberately separate from any future Gemini-generated narrative.

All Phase 4 metrics and explanations are derived from the synthetic demo dataset and persisted scikit-learn pipeline; they are not production performance claims or LLM output.
