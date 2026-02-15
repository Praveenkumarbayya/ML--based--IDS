# Production-grade ML Intrusion Detection System

BSc (Hons) Computing capstone — a supervised-learning Network Intrusion Detection
System with a real-time dashboard, persistent audit trail, API-key security,
rate limiting, Prometheus metrics, and containerised deployment. Built on the
NSL-KDD dataset with Random Forest, XGBoost, LightGBM, and Logistic Regression.

## Architecture

```
┌─────────────────┐   HTTPS/WS   ┌──────────────────────┐
│  Next.js 15     │◄────────────►│  FastAPI 2.0         │
│  Dashboard      │  API key     │                      │
│  (SOC UI)       │              │  ├─ /predict         │
│                 │              │  ├─ /predict/batch   │
│  ├─ /           │              │  ├─ /audit/*         │
│  ├─ /analyze    │              │  ├─ /ws/alerts       │
│  ├─ /metrics    │              │  └─ /metrics         │
│  ├─ /audit      │              │                      │
│  └─ /models     │              │  ┌────────────────┐  │
└─────────────────┘              │  │  Model Registry│  │
                                 │  │  (joblib)      │  │
                                 │  └────────┬───────┘  │
                                 │           ▼          │
                                 │  ┌────────────────┐  │
                                 │  │ sklearn / XGB  │  │
                                 │  │ / LightGBM / LR│  │
                                 │  └────────────────┘  │
                                 │                      │
                                 │  ┌────────────────┐  │
                                 │  │ SQLite (WAL)   │  │
                                 │  │ predictions +  │  │
                                 │  │ alerts + runs  │  │
                                 │  └────────────────┘  │
                                 └──────────────────────┘
```

## Tech stack

| Layer | Stack |
|---|---|
| Dataset | NSL-KDD (KDDTrain+ 107k rows, KDDTest+ 22k rows) |
| ML | scikit-learn, XGBoost, LightGBM |
| Backend | FastAPI + uvicorn + Pydantic v2 + SQLAlchemy 2 + aiosqlite + Alembic |
| Security | X-API-Key auth, slowapi rate limiting, CORS, constant-time comparison |
| Observability | Prometheus metrics, structured logging, JSONL audit (optional), SQLite audit (primary) |
| Real-time | FastAPI WebSocket broadcast (`/ws/alerts`) |
| Frontend | Next.js 16 (App Router) + TypeScript + Tailwind 4 + TanStack Query + Recharts + lucide-react |
| Container | Docker + Docker Compose (multi-stage frontend build, non-root users) |
| CI | GitHub Actions (pytest + pnpm build + docker build) |

## Quick start — Docker (recommended)

```bash
# 1. Place dataset files
mkdir -p data/raw
curl -o data/raw/KDDTrain+.txt \
  https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTrain%2B.txt
curl -o data/raw/KDDTest+.txt \
  https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTest%2B.txt

# 2. Generate a secret API key
echo "API_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" > .env

# 3. Train the models once (one-shot command, writes to ./models)
docker compose run --rm -v "$PWD/models:/app/models" backend \
  python main.py train --fast

# 4. Bring up the full stack
docker compose up -d

# Open http://localhost:3000
```

Frontend reads `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_API_KEY`
(defaulted to localhost/8000 and the same `API_KEY` from `.env`).

## Local development

```bash
# Backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # set a secure API_KEY
make train            # fast training
make evaluate         # metrics + plots
make serve            # FastAPI on :8000

# Frontend (separate terminal)
cd frontend
cp .env.local .env.local   # already exists in repo, edit the key
pnpm install
pnpm dev                   # :3000
```

## Project structure

```
├── api/                    FastAPI service
│   ├── main.py             endpoints + lifespan
│   ├── schemas.py          Pydantic models
│   ├── security.py         API-key auth
│   ├── realtime.py         WebSocket manager
│   └── metrics.py          Prometheus counters / histograms
├── src/
│   ├── config.py           dataset schema + hyperparameter grids
│   ├── settings.py         pydantic-settings (env-driven config)
│   ├── data_loader.py      NSL-KDD loader + label mapping
│   ├── preprocessing.py    leak-proof pipeline (fit on train only)
│   ├── models.py           model factory + TrainedModel wrapper
│   ├── train.py            grid-search CV training
│   ├── evaluate.py         full metrics suite + plots
│   ├── db.py               async SQLAlchemy engine / session
│   ├── db_models.py        ORM: predictions, alerts, model_runs
│   ├── db_repo.py          repository facade
│   └── utils.py            logger + audit log
├── frontend/               Next.js dashboard
│   ├── src/app/            routes (/, /analyze, /metrics, /audit, /models)
│   ├── src/components/     UI (nav, topbar, cards, badges)
│   └── src/lib/            api client + WebSocket hook + types
├── tests/                  pytest (unit + integration + API)
├── notebooks/01_eda.ipynb  exploratory data analysis
├── .planning/              GSD-style roadmap + phase plans
├── Dockerfile.backend
├── frontend/Dockerfile
├── docker-compose.yml
├── .github/workflows/ci.yml
├── Makefile
├── main.py                 unified CLI
└── requirements.txt
```

## Security posture

| Control | Implementation |
|---|---|
| Authentication | X-API-Key header (constant-time comparison) on write/inference endpoints |
| Transport | HTTPS in prod (reverse proxy responsibility); CORS restricted by origin |
| Rate limiting | slowapi, per-IP buckets: 60/min `/predict`, 300/min `/predict/batch` |
| Input validation | Pydantic v2 strict models on every endpoint — malformed input → 422 |
| WebSocket auth | Header for CLI, Sec-WebSocket-Protocol for browsers (both go through the same constant-time check) |
| Audit | Every prediction + alert persisted to SQLite with client IP and timestamp |
| Non-root containers | backend UID 1000, frontend UID 1001 |
| Secrets | `.env` never committed; API key generated via `secrets.token_urlsafe` |

## Evaluation results (reproducible via `make train && make evaluate`)

| Evaluation set | Best model | Accuracy | F1 (macro) | ROC-AUC |
|---|---|---|---|---|
| Train-holdout (20%) | LightGBM | 0.9994 | **0.9994** ✅ target ≥0.85 | 1.000 |
| NSL-KDDTest+ (novel attacks) | XGBoost | 0.7982 | 0.7979 | 0.973 |

NSL-KDDTest+ intentionally contains attack types absent from the training set;
the 20-point F1 gap between holdout and official test is consistently reported
in the literature (Tavallaee 2009; Sarhan 2020). The high ROC-AUC (0.97) shows
the models rank benign vs malicious flows correctly — the gap is a threshold
calibration issue, not a class-separation issue.

## API endpoints

Public (no auth):
- `GET /health` — load state
- `GET /metadata` — model inventory, feature names, class labels
- `GET /metrics` — Prometheus text format

Authenticated (`X-API-Key: …`):
- `POST /predict` — single classification + confidence + top features
- `POST /predict/batch` — up to 10,000 flows per request
- `GET /audit/predictions?limit=100&only_malicious=true&model=xgboost`
- `GET /audit/alerts?unacked_only=true`
- `POST /audit/alerts/{id}/ack`
- `GET /metrics/models` — full evaluation report
- `GET /metrics/training` — training summary (CV score, hyperparameters)
- `WS /ws/alerts` — real-time broadcast of every malicious prediction

Swagger UI at `/docs`.

## Acceptance criteria vs delivery

From the interim report:

- [x] Preprocessing fit on training data only — no leakage
- [x] Four models trained + compared (RF, XGBoost, LightGBM, LR)
- [x] REST inference API with JSON request/response
- [x] Holdout F1 ≥ 0.85 — achieved **0.9994** on LightGBM
- [x] Trained artefacts saved via joblib for reproducibility
- [x] Structured prediction audit log with timestamps → SQLite queryable DB
- [x] Graceful error handling — 401/422/429/500 all structured
- [x] Unit + integration + API tests — 24 passing

Beyond the interim scope (production layer):

- [x] Real-time dashboard with live WebSocket alerts
- [x] API-key authentication + rate limiting + CORS
- [x] Prometheus `/metrics` endpoint
- [x] SQLite-backed persistent audit trail
- [x] Multi-container Docker deployment
- [x] GitHub Actions CI (pytest + build + docker)

## Out of scope (per interim report)

- Live packet capture (would need Scapy + continuous feature extraction)
- Enterprise SIEM integration (Splunk/ELK)
- Deep learning architectures (LSTM, CNN)
- Active response / IPS behaviour
