.PHONY: setup train train-full evaluate serve test test-fast lint clean help \
        frontend-install frontend-dev frontend-build \
        docker-build docker-up docker-down docker-logs docker-train \
        report

PYTHON ?= venv/bin/python

help:
	@echo "Local Python targets:"
	@echo "  setup           install backend dependencies"
	@echo "  train           fast training (single hyperparameter config)"
	@echo "  train-full      full grid-search training"
	@echo "  evaluate        run the evaluation suite"
	@echo "  serve           start the FastAPI service on :8000"
	@echo "  test            run the full pytest suite"
	@echo "  test-fast       skip the integration test"
	@echo ""
	@echo "Frontend targets:"
	@echo "  frontend-install"
	@echo "  frontend-dev    dev server on :3000"
	@echo "  frontend-build  production Next.js build"
	@echo ""
	@echo "Docker targets:"
	@echo "  docker-build    build backend + frontend images"
	@echo "  docker-up       start stack"
	@echo "  docker-down     stop stack"
	@echo "  docker-logs     tail logs"
	@echo "  docker-train    one-shot train inside backend container"
	@echo ""
	@echo "  clean           remove trained artefacts"
	@echo "  report          regenerate Interim_Report_IDS_v3.docx"

setup:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

train:
	$(PYTHON) main.py train --fast

train-full:
	$(PYTHON) main.py train --full

evaluate:
	$(PYTHON) main.py evaluate

serve:
	$(PYTHON) main.py serve

test:
	$(PYTHON) -m pytest tests/ -v

test-fast:
	$(PYTHON) -m pytest tests/ -v -k "not integration"

# --- frontend ---
frontend-install:
	cd frontend && pnpm install

frontend-dev:
	cd frontend && pnpm dev

frontend-build:
	cd frontend && pnpm build

# --- docker ---
docker-build:
	docker compose build

docker-up:
	docker compose up -d
	@echo "Dashboard: http://localhost:3000  |  API: http://localhost:8000/docs"

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-train:
	docker compose run --rm backend python main.py train --fast

# --- docs ---
report:
	$(PYTHON) scripts/update_report.py
	$(PYTHON) scripts/update_report_v3.py

clean:
	rm -rf models/*.joblib models/*.npy models/plots models/*.json models/*.csv
	rm -rf .pytest_cache __pycache__ */__pycache__ */*/__pycache__
	rm -rf data/ids.db data/ids.db-journal data/ids.db-shm data/ids.db-wal
	rm -rf logs/*.log logs/*.jsonl
