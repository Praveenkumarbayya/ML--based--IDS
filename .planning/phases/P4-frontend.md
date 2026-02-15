# Phase 4 — Next.js Dashboard

## Goal
A real SOC-style dashboard a cybersecurity analyst would actually use.

## Stack (locked)
- Next.js 15 App Router, TypeScript strict, React 19
- Tailwind 4 + shadcn/ui, lucide-react icons
- TanStack Query for data fetching, Zustand for tiny UI state
- Recharts for plots
- Native WebSocket API for live alerts
- Dark theme by default (SOC UX standard)

## Pages
- `/` — Live dashboard: KPI cards (predictions/min, alerts/min, precision live),
  live alert feed (websocket), models-loaded panel
- `/analyze` — paste JSON features OR fill a form; returns classification,
  confidence, class probabilities, top contributing features bar chart
- `/metrics` — reads evaluation_runs via backend; renders:
  - comparative table across models (holdout + official_test)
  - confusion matrix heatmap per model
  - ROC curves overlaid
- `/audit` — paginated, filterable prediction log. Filters: time range, model,
  label, confidence ≥ X. Each row expandable to show raw features. Alerts have
  an "Acknowledge" button.
- `/models` — lists trained models with cv_score, train_time, best_params.
  Button: "Set as default" → calls backend, persists in settings.

## Project layout
```
frontend/
├── src/app/          (App Router)
│   ├── layout.tsx    (shared shell: sidebar, topbar, theme)
│   ├── page.tsx      (live dashboard)
│   ├── analyze/page.tsx
│   ├── metrics/page.tsx
│   ├── audit/page.tsx
│   └── models/page.tsx
├── src/components/
│   ├── ui/           (shadcn generated)
│   ├── alert-feed.tsx
│   ├── metric-card.tsx
│   └── nav.tsx
├── src/lib/
│   ├── api.ts        (typed fetch wrapper)
│   ├── ws.ts         (WebSocket hook)
│   └── types.ts      (mirrors Pydantic models)
├── src/hooks/
├── next.config.ts
└── package.json
```

## API contract consumed
- `GET /health`, `GET /metadata` — for boot state
- `POST /predict`, `POST /predict/batch` — analyze page
- `GET /audit/predictions` — audit page
- `GET /audit/alerts`, `POST /audit/alerts/:id/ack` — alert acknowledgement
- `GET /metrics/models` — metrics page (returns evaluation_runs)
- `WS /ws/alerts` — live feed

## Acceptance
- `pnpm dev` opens at :3000, proxies to backend at :8000
- All 5 pages render without mocks — data comes from the real backend
- Dashboard receives a live alert within 1s of a POST to `/predict` with a
  malicious sample, via WebSocket
- Lighthouse performance score ≥ 90 on production build
