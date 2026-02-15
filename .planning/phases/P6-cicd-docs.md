# Phase 6 — CI/CD + Report v3

## Goal
Every push runs lints/tests and builds the container images. The interim
report reflects the delivered production system.

## Tasks
1. `.github/workflows/ci.yml` — on push/pr:
   - set up Python 3.12, install deps, run `pytest`
   - set up Node 22 + pnpm, run `pnpm lint`, `pnpm build`
   - run `docker build` for both Dockerfiles (no push)
2. Update `README.md` with a production-stack diagram section.
3. `scripts/update_report.py` v2 — regenerates `Interim_Report_IDS_v3.docx`
   with a new "System Architecture" section including the frontend/WebSocket/DB
   components, and a "Production Deployment" section covering Docker.

## Acceptance
- CI is green on push.
- The v3 report reads like a production system, not a prototype.
