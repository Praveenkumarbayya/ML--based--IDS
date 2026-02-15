# Production Upgrade Roadmap

## Goal
Transform the IDS capstone from a command-line prototype into a production-grade
network intrusion detection system with a real-time dashboard, persistent audit
trail, and deployable container stack.

## Success criteria (roadmap-wide)
- A non-technical user can open a browser, see live classifications, and act on them.
- The entire stack is brought up with a single `docker compose up`.
- No mocks, no fakes, no synthetic data. Every prediction goes through the real
  NSL-KDD-trained models.
- All audit data is persisted in a queryable database; logs survive restarts.
- CI runs on every push: lints, tests, builds images.

## Phase map

| # | Phase | Output | Exit criteria |
|---|---|---|---|
| P1 | Backend hardening | settings, API-key auth, CORS, rate limiter, `/metrics` | curl with invalid key → 401; 429 after N req/min |
| P2 | Persistence layer | SQLite + SQLAlchemy; predictions + alerts tables | audit log queryable via SQL; survives restart |
| P3 | Real-time stream | WebSocket `/ws/alerts`; broadcast on malicious prediction | wscat connects, receives alert in <100 ms |
| P4 | Frontend dashboard | Next.js 15 + TS + Tailwind + shadcn; 5 pages | lighthouse perf ≥ 90; live alerts visible |
| P5 | Containerization | Dockerfiles (backend + frontend) + compose | `docker compose up` brings the whole stack |
| P6 | CI/CD + report v3 | GitHub Actions + updated .docx | actions pass on push; report reflects prod state |

## Non-goals (explicitly deferred)
- Kubernetes / Helm — out of scope; Docker Compose is sufficient.
- Live packet capture — out of project scope per interim report.
- Multi-tenant auth / SSO — single API-key is appropriate for capstone scope.
- Distributed tracing — logs + /metrics cover this adequately.

## Tech stack (locked)
- Backend: FastAPI + uvicorn + SQLAlchemy 2 + aiosqlite + pydantic-settings + slowapi
- Frontend: Next.js 15 App Router + TypeScript + Tailwind 4 + shadcn/ui + TanStack Query + Recharts
- Database: SQLite (WAL mode) — fits single-node deployment
- Container: Docker + Compose
- CI: GitHub Actions
