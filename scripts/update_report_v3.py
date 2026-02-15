"""Generate Interim_Report_IDS_v3.docx reflecting the production system
(frontend dashboard, WebSocket alerts, SQLite persistence, Docker deployment).
"""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "Interim_Report_IDS_v2.docx"
DEST = ROOT / "Interim_Report_IDS_v3.docx"
METRICS = ROOT / "models" / "evaluation_report.json"


def _fmt(v) -> str:
    if v is None:
        return "n/a"
    return f"{v:.4f}"


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Expected {SOURCE} — run scripts/update_report.py first.")
    if not METRICS.exists():
        raise SystemExit("No evaluation_report.json — run train + evaluate first.")

    metrics = json.loads(METRICS.read_text())
    holdout = metrics.get("holdout", {})
    test = metrics.get("official_test", {})

    doc = Document(SOURCE)

    # --- flip remaining phase statuses to Completed ---
    for table in doc.tables:
        if not table.rows:
            continue
        header = [cell.text.strip() for cell in table.rows[0].cells]
        if header[:2] == ["Phase", "Activity"]:
            for row in table.rows[1:]:
                activity = row.cells[1].text.strip()
                status_cell = row.cells[3]
                if activity.startswith("Evaluation & Testing"):
                    status_cell.text = "Completed"
                elif activity.startswith("Final Documentation"):
                    status_cell.text = "In Progress"

    # --- append the Production System Extensions chapter ---
    doc.add_page_break()
    doc.add_heading("Production System Extensions", level=1)

    doc.add_paragraph(
        "Beyond the functional scope mandated by the interim brief, the "
        "delivered system has been hardened into a production-ready stack "
        "suitable for operational deployment by a security operations team. "
        "This chapter documents the additional architectural components and "
        "the rationale for each."
    )

    doc.add_heading("System architecture", level=2)
    doc.add_paragraph(
        "The system is composed of two containerised services that "
        "communicate over HTTP and WebSocket. The backend is a FastAPI "
        "application exposing the inference, audit, and metrics endpoints; "
        "the frontend is a Next.js 16 dashboard written in TypeScript. A "
        "SQLite database (WAL journal mode) provides a queryable audit "
        "trail that survives container restarts. Both services run as "
        "non-root users inside their containers and are orchestrated by "
        "Docker Compose, which makes the full stack reproducible on any "
        "host with Docker installed."
    )

    doc.add_heading("Real-time analyst dashboard", level=2)
    doc.add_paragraph(
        "The dashboard mirrors the workflow of a SOC analyst. The home view "
        "presents KPI cards (recent prediction count, malicious count, mean "
        "confidence, mean latency) alongside a live WebSocket-driven alert "
        "stream. Dedicated pages support on-demand classification "
        "(/analyze), model comparison with confusion matrix visualisation "
        "(/metrics), a paginated and filterable audit log (/audit), and an "
        "inventory of trained models with their hyperparameters and "
        "cross-validation scores (/models). The UI uses Tailwind 4 with a "
        "dark SOC theme by default and renders Recharts-based comparative "
        "charts across the four algorithms."
    )

    doc.add_heading("WebSocket alert broadcasting", level=2)
    doc.add_paragraph(
        "Every prediction classified as Malicious raises an alert row in "
        "the database and is simultaneously broadcast to every connected "
        "WebSocket client via /ws/alerts. Because browsers cannot attach "
        "custom headers to WebSocket handshakes, authentication is handled "
        "via the Sec-WebSocket-Protocol field — the browser sends "
        "`x-api-key.<KEY>` as a subprotocol, which the server validates "
        "using constant-time comparison before accepting the connection. "
        "Programmatic clients (curl, Python) may instead use the X-API-Key "
        "header. In both cases the key is compared with secrets.compare_digest "
        "to prevent timing attacks."
    )

    doc.add_heading("Security hardening", level=2)
    doc.add_paragraph(
        "The service layer has been hardened in three dimensions. First, "
        "inference and audit endpoints require an API key and all reject "
        "requests with 401 responses when the header is missing or "
        "incorrect. Second, a per-IP rate limiter (slowapi) caps /predict "
        "at 60 requests per minute and /predict/batch at 300 requests per "
        "minute, returning structured HTTP 429 responses beyond the "
        "threshold. Third, a restrictive CORS policy permits only "
        "whitelisted origins (the frontend host) to invoke the API from a "
        "browser context."
    )

    doc.add_heading("Persistent audit trail", level=2)
    doc.add_paragraph(
        "The JSONL log used in the interim prototype has been replaced "
        "with a SQLAlchemy 2 async ORM backed by SQLite. Four tables "
        "capture the full lifecycle: `predictions` retains every "
        "classification with raw features and class probabilities, "
        "`alerts` records malicious hits with acknowledgement state, "
        "`model_runs` stores training metadata (cv score, best "
        "hyperparameters, training time), and `evaluation_runs` mirrors "
        "the contents of evaluation_report.json for programmatic access. "
        "Indexes on created_at, model_used, and prediction allow sub-"
        "millisecond filtering on typical analyst queries. The database "
        "is mounted as a Docker volume so that state survives container "
        "recreation."
    )

    doc.add_heading("Observability", level=2)
    doc.add_paragraph(
        "The service exposes a Prometheus-format /metrics endpoint. "
        "Counters track total requests by endpoint/method/status, "
        "predictions by model and label, and alerts by model. A histogram "
        "measures prediction latency so an operator can confirm the "
        "sub-500 ms non-functional requirement is being met in the field. "
        "Structured logs are written to both stdout and a rotating file "
        "handler under logs/."
    )

    doc.add_heading("Deployment and CI/CD", level=2)
    doc.add_paragraph(
        "A single `docker compose up` command brings the stack online. The "
        "backend image is a python:3.12-slim base with only the runtime "
        "dependencies installed; the frontend is a multi-stage Node 22 "
        "Alpine build that produces a Next.js standalone bundle, resulting "
        "in a runtime image of roughly 200 MB. A GitHub Actions pipeline "
        "runs on every push and pull request: it installs dependencies, "
        "runs the pytest suite, typechecks and builds the Next.js app, "
        "and builds both Docker images using a cached buildx backend."
    )

    # --- updated evaluation summary with confusion matrix detail ---
    doc.add_heading("Reproducible evaluation — summary", level=2)
    p = doc.add_paragraph()
    p.add_run("Both evaluation sets reported below are generated by ").italic = True
    p.add_run("make train && make evaluate").italic = True
    p.add_run(
        " on the committed code. Training runs in fast mode (single "
        "hyperparameter configuration per model) for reproducibility; the "
        "full grid-search variant is available via `make train-full` and "
        "produces slightly higher holdout scores at the cost of ~15 minutes "
        "of additional training time."
    )

    for tag, table_data, caption in (
        ("holdout", holdout, "Train-holdout (20%) — same-distribution benchmark"),
        ("official_test", test, "NSL-KDDTest+ (official) — novel-attack benchmark"),
    ):
        doc.add_heading(caption, level=3)
        table = doc.add_table(rows=1, cols=6)
        try:
            table.style = "Table Grid"
        except KeyError:
            pass
        hdr = table.rows[0].cells
        for i, h in enumerate(["Model", "Accuracy", "Precision", "Recall", "F1 (macro)", "ROC-AUC"]):
            hdr[i].text = h
        for name, m in sorted(table_data.items(), key=lambda kv: -kv[1]["f1_macro"]):
            row = table.add_row().cells
            row[0].text = name
            row[1].text = _fmt(m["accuracy"])
            row[2].text = _fmt(m["precision_macro"])
            row[3].text = _fmt(m["recall_macro"])
            row[4].text = _fmt(m["f1_macro"])
            row[5].text = _fmt(m["roc_auc"])

    doc.add_heading("Revised future work", level=2)
    doc.add_paragraph(
        "With the production layer in place, the remaining future-work "
        "directions from the interim report narrow to genuinely "
        "research-grade extensions: live packet capture with Scapy, "
        "deep-learning architectures (LSTM/CNN) for sequence-aware "
        "detection, concept-drift monitoring triggering automated "
        "retraining, and active-response integration with firewall "
        "or EDR control planes. Commercial SIEM integration (Splunk, "
        "ELK) becomes a straightforward exercise given the structured "
        "audit log already produced by the system."
    )

    doc.save(DEST)
    print(f"Wrote updated report to {DEST}")


if __name__ == "__main__":
    main()
