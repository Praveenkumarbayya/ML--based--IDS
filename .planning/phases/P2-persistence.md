# Phase 2 — Persistence Layer

## Goal
Replace the JSONL audit log with a queryable SQLite database. Predictions,
alerts, and model metadata live in typed SQLAlchemy models; migrations via
Alembic.

## Schema
- `predictions` — id, request_id, ts, endpoint, model_used, prediction, confidence, latency_ms, client_ip, raw_features (JSON)
- `alerts` — id, prediction_id FK, severity, acknowledged (bool), ack_by, ack_ts
  — only populated for Malicious predictions
- `model_runs` — id, model_name, trained_at, cv_score, train_seconds, best_params (JSON)
- `evaluation_runs` — id, model_name, evaluation_set, accuracy, precision, recall, f1_macro, roc_auc, created_at

## Tasks
1. Add SQLAlchemy 2, aiosqlite, alembic to requirements.
2. `src/db.py` — async engine, session factory, `get_db` FastAPI dependency.
3. `src/models_db.py` — ORM definitions matching the schema above.
4. Alembic init + first migration generating the four tables.
5. Replace `PredictionAuditLogger` with DB writes inside the API handlers.
6. Keep the JSONL log as a fallback but off by default (settings flag).
7. Training/evaluation CLI commands write their results to `model_runs` /
   `evaluation_runs` tables so the frontend can read them.
8. Add `GET /audit/predictions?limit=100&only_malicious=true` endpoint.
9. Add `GET /audit/alerts` + `POST /audit/alerts/{id}/ack`.

## Acceptance
- After making predictions, `sqlite3 data/ids.db "select count(*) from predictions"` > 0.
- Restart the API — the predictions are still there.
- The evaluation report JSON is reproducible from `evaluation_runs` table.
