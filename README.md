# AI Chargeback Risk & Evidence Response Agent

A synthetic/demo fintech risk-operations application for the Razorpay AI Builder Internship 2026 — Track 02: AI Risk Manager.

## Current phase: Phase 12 — Security, Testing & Reliability Hardening

Earlier phases added the backend foundation, ML risk prediction, traceable investigation cases, a backend-only Gemini investigation layer, frontend reviewer workflows, and versioned evidence packages with non-executing recommendations. Phase 12 hardens CORS validation, structured request logging, bounded Gemini retries, and regression/integration test coverage; it does **not** include authentication or autonomous financial actions.

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
| `GEMINI_API_KEY` | Backend-only Gemini key used only by the Phase 7 investigation service. | empty |
| `GEMINI_MODEL` | Backend-only Gemini model used for controlled investigations. | `gemini-2.5-flash` |
| `GEMINI_TIMEOUT_SECONDS` | Maximum duration for a Gemini request. | `20` |
| `GEMINI_MAX_RETRIES` | Bounded safe retries for transient Gemini investigation failures. | `1` |
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

The Phase 9 frontend provides Dashboard, Transactions, Cases, Model Metrics, and Settings & Health routes. It uses `VITE_API_BASE_URL` when supplied; otherwise Vite's development proxy forwards `/api` requests to `http://localhost:8000`. Dashboard, transactions, health, and model views display only API-derived data and explicit loading, empty, and error states.

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
- Gemini investigations require a backend-only `GEMINI_API_KEY`; ML prediction remains available when Gemini is unavailable.
- No financial actions of any kind. Recommendations always require human approval.

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

### Phase 8 — Evidence Response Package & Bounded Recommendation

`POST /api/v1/cases/{case_id}/investigate` remains the controlled, backend-only Gemini investigation trigger. A successful investigation advances a case from `NEW` to `INVESTIGATING`; Gemini failures leave the case unchanged.

While a case is `INVESTIGATING`, `POST /api/v1/cases/{case_id}/evidence` creates an immutable, versioned reviewer package. It includes transaction evidence, database-derived customer transaction history, prior disputes, the independently stored ML prediction and its actual model-derived factors, and a bounded proposed response. Every claim includes its database source table and record ID; unavailable data is represented as `Evidence unavailable`. Repeating the endpoint produces a newer snapshot so reviewers can regenerate after available evidence changes.

`POST /api/v1/cases/{case_id}/recommendation` requires a generated package and stores a versioned recommendation tied to its source package. Its categories are limited to `MANUAL_REVIEW`, `MONITOR`, `REQUEST_ADDITIONAL_VERIFICATION`, `PRIORITIZE_CHARGEBACK_RESPONSE`, `PREPARE_EVIDENCE_PACKAGE`, and `LOW_PRIORITY_REVIEW`. Every response prominently returns `human_approval_required: true` and `financial_action_executed: false`. The response workflow performs only evidence/recommendation persistence and reviewer case-status updates; it has no refund, reversal, transfer, account-closure, or payment-network submission capability.

### Phase 6: risk investigation cases and evidence traceability

`POST /api/v1/cases` creates a human-review investigation case from an existing transaction's latest persisted ML prediction. It also captures deterministic evidence from only linked database records. `GET /api/v1/cases/{case_id}` returns the case and its audit history, `PATCH /api/v1/cases/{case_id}` updates the reviewer or advances the case through its validated workflow, and `GET /api/v1/cases/{case_id}/evidence` lists traceable evidence items.

Each evidence item records a source table and source record ID. When a related record is absent, the API returns the exact factual content `Evidence unavailable` with an `EVIDENCE_UNAVAILABLE` verification status rather than inventing a claim. This phase does not call Gemini and cannot execute financial actions.

Allowed status transitions are: `NEW → INVESTIGATING → READY_FOR_REVIEW → APPROVED|REJECTED → CLOSED`. Reviewer assignment is auditable independently of a status transition.

## Phase 5 — FastAPI Risk & Investigation Data APIs

Phase 5 exposes the persisted ML model and synthetic investigation data through documented, versioned REST endpoints. Train the model before calling prediction or model-metadata endpoints, then seed the local development database:

```bash
cd backend
python -m app.ml.train_model
# Start the API in another terminal, then POST /api/v1/seed once in development.
```

| Endpoint | Purpose |
| --- | --- |
| `POST /api/v1/risk/predict` | Validates model-ready features, runs the persisted quantitative model, and stores an audit prediction record. It is only a human-review recommendation and never performs a financial action. |
| `GET /api/v1/transactions` | Paginated synthetic transaction list with customer, status, and currency filters. |
| `GET /api/v1/transactions/{transaction_id}` | Database-backed transaction detail and related customer/merchant facts. |
| `GET /api/v1/customers/{customer_id}/history` | Database-derived customer transaction aggregates and history. |
| `GET /api/v1/customers/{customer_id}/disputes` | Synthetic dispute records stored in the database. |
| `GET /api/v1/risk/summary` | Aggregate statistics calculated from stored transaction and prediction records. |
| `GET /api/v1/model/metrics` | Actual persisted held-out evaluation JSON, not constants. |
| `GET /api/v1/model/info` | Safe persisted model version and selection metadata. |

Swagger documents requests, response contracts, and examples at <http://localhost:8000/docs>. The APIs intentionally expose no Gemini capability, model weights, training examples, or autonomous payment controls.

## Phase 7 — Gemini Tool-Using Investigation Agent

`POST /api/v1/cases/{case_id}/investigate` invokes Gemini only from the backend to synthesize an existing case's database-grounded evidence. The independently persisted ML prediction remains the sole quantitative risk signal and continues to work when Gemini is unavailable.

The agent can call only these allowlisted backend tools: `get_transaction`, `get_customer_history`, `get_previous_disputes`, `get_device_history`, `get_related_transactions`, `get_merchant_policy`, `create_evidence_report`, and `recommend_action`. Tool names outside this list are rejected. The agent must return a Pydantic-validated JSON result with a human-review-only recommendation, and every cited evidence ID must have been returned by an executed tool. The persisted `agent_investigations` record stores the model name, tool-call trace, cited evidence references, and validated response. This is synthetic/demo functionality only; it never executes refunds, reversals, transfers, or account changes.

If `GEMINI_API_KEY` is absent or Gemini fails/times out, the investigation endpoint returns a controlled HTTP 503 response. The ML prediction endpoint does not depend on Gemini configuration or availability.
