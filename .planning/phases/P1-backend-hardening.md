# Phase 1 — Backend Hardening

## Goal
Harden the existing FastAPI service for production: env-driven config, API-key
authentication, CORS so the frontend can call it, rate limiting, and a metrics
endpoint.

## Tasks
1. Add `pydantic-settings` and create `src/settings.py`. All env knobs live here.
2. Add `.env.example` documenting every variable. `.env` in `.gitignore`.
3. Implement `api/security.py` — `APIKeyHeader` dependency, compares against
   `settings.api_key` via `secrets.compare_digest`.
4. Mount CORS middleware with origin from `settings.frontend_origin`.
5. Add `slowapi` rate limiter. Default: 60 req/min/ip on `/predict`, 300 on
   `/predict/batch`, unlimited on `/health` and `/metrics`.
6. Add `/metrics` endpoint (Prometheus text format): request count, 4xx/5xx
   counts, prediction count per class, mean latency.
7. Protect `/predict`, `/predict/batch`, `/ws/alerts` with API-key dependency;
   leave `/health` and `/metadata` public.

## Files touched / created
- `requirements.txt` (+= pydantic-settings, slowapi, prometheus-client)
- `src/settings.py` (new)
- `.env.example` (new)
- `api/security.py` (new)
- `api/metrics.py` (new)
- `api/main.py` (modified — wire CORS/auth/limiter)

## Acceptance
- `curl http://host/predict` without header → 401
- `curl -H "X-API-Key: wrong" ...` → 401
- 61st request in 1 min → 429
- `curl http://host/metrics` returns Prometheus-format body
