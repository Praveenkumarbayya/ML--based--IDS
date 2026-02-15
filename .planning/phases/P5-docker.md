# Phase 5 — Containerization

## Goal
`docker compose up` from a clean checkout starts backend + frontend with trained
models loaded. No host Python or Node needed by the operator.

## Tasks
1. `Dockerfile.backend` — python:3.12-slim, non-root user, uvicorn entrypoint.
2. `frontend/Dockerfile` — multi-stage: deps → build → runner (node:22-alpine).
3. `docker-compose.yml`:
   - `backend` — builds ./Dockerfile.backend, mounts data/ + models/ +
     logs/, exposes 8000
   - `frontend` — builds ./frontend, env `NEXT_PUBLIC_API_URL`, depends_on
     backend healthcheck, exposes 3000
4. `.dockerignore` files (root + frontend)
5. `healthcheck` on backend service using `/health`
6. Training is an explicit one-shot target: `docker compose run --rm backend
   python main.py train` (not in main runtime).

## Acceptance
- On a fresh clone, `docker compose up` after placing the dataset files brings
  both services healthy.
- Browser at http://localhost:3000 shows the live dashboard fed by
  http://localhost:8000.
