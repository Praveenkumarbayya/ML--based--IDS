"""FastAPI inference service for the Intrusion Detection System.

Loads preprocessing + every available trained model on startup and exposes:
  - GET  /health           (public)
  - GET  /metadata         (public)
  - GET  /metrics          (public, Prometheus format)
  - POST /predict          (API key required, rate-limited)
  - POST /predict/batch    (API key required, rate-limited)
  - GET  /audit/predictions (API key required)
  - GET  /audit/alerts      (API key required)
  - POST /audit/alerts/{id}/ack (API key required)
  - WS   /ws/alerts         (API key required)

All predictions are persisted to the configured database.
"""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from api.metrics import (
    ALERT_COUNTER, PREDICTION_COUNTER, PREDICTION_LATENCY,
    REQUEST_COUNTER, metrics_endpoint,
)
from api.realtime import ws_manager
from api.schemas import (
    AlertOut, AuditPredictionOut, BatchPredictionRequest, BatchPredictionResponse,
    ErrorResponse, HealthResponse, MetadataResponse, NetworkFlow,
    PredictionRequest, PredictionResponse,
)
from api.security import require_api_key
from src.config import MODELS_DIR
from src.db import db_session, init_db
from src.db_repo import PredictionRepository
from src.models import SUPPORTED_MODELS, TrainedModel
from src.preprocessing import PreprocessingPipeline
from src.settings import Settings, get_settings
from src.utils import get_logger


logger = get_logger("ids.api")


class ModelRegistry:
    """In-memory registry populated on FastAPI startup."""

    def __init__(self):
        self.preprocessor: PreprocessingPipeline | None = None
        self.models: dict[str, TrainedModel] = {}
        self.default_model: str | None = None
        self.class_labels: list[str] = []
        self.feature_names: list[str] = []

    def load(self, models_dir: Path = MODELS_DIR, override_default: str | None = None) -> None:
        try:
            self.preprocessor = PreprocessingPipeline.load(models_dir)
            self.class_labels = list(self.preprocessor.label_encoder_binary.classes_)
            names = self.preprocessor.feature_names_out
            self.feature_names = list(names) if names is not None else []
            logger.info(f"Preprocessor loaded. Classes={self.class_labels}")
        except Exception as exc:
            logger.exception(f"Failed to load preprocessor: {exc}")
            self.preprocessor = None
            return

        for name in SUPPORTED_MODELS:
            path = models_dir / f"{name}.joblib"
            if path.exists():
                try:
                    self.models[name] = TrainedModel.load(path)
                    logger.info(f"Loaded model: {name}")
                except Exception as exc:
                    logger.exception(f"Failed to load {name}: {exc}")

        if override_default and override_default in self.models:
            self.default_model = override_default
        else:
            self.default_model = self._pick_default()
        logger.info(f"Default model: {self.default_model}")

    def _pick_default(self) -> str | None:
        if not self.models:
            return None
        scored = [(n, m.cv_score) for n, m in self.models.items() if m.cv_score is not None]
        if scored:
            scored.sort(key=lambda t: t[1], reverse=True)
            return scored[0][0]
        return next(iter(self.models))

    def resolve(self, requested: str | None) -> TrainedModel:
        name = requested or self.default_model
        if name is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No models are loaded. Train models first (python -m src.train).",
            )
        if name not in self.models:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model '{name}' not loaded. Available: {sorted(self.models)}",
            )
        return self.models[name]


registry = ModelRegistry()
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    registry.load(override_default=settings.default_model)
    await init_db()
    yield
    await ws_manager.disconnect_all()
    logger.info("API shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="IDS Inference API",
        description="Production-grade ML Network Intrusion Detection System.",
        version="2.0.0",
        lifespan=lifespan,
    )

    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
        REQUEST_COUNTER.labels(
            endpoint=request.url.path, method=request.method, status="429",
        ).inc()
        return JSONResponse(
            status_code=429,
            content=ErrorResponse(
                error="rate_limited",
                detail=f"Rate limit exceeded: {exc.detail}",
            ).model_dump(),
        )

    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def count_requests(request: Request, call_next):
        response = await call_next(request)
        REQUEST_COUNTER.labels(
            endpoint=request.url.path,
            method=request.method,
            status=str(response.status_code),
        ).inc()
        return response

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = str(uuid.uuid4())
        logger.exception(f"[{request_id}] Unhandled error on {request.url.path}: {exc}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="internal_error",
                detail=str(exc),
                request_id=request_id,
            ).model_dump(),
        )

    return app


app = create_app()


# ---------------------------------------------------------------------------
# Public endpoints (no auth, no rate limit)
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok" if registry.preprocessor and registry.models else "degraded",
        models_loaded=sorted(registry.models.keys()),
        preprocessor_loaded=registry.preprocessor is not None,
    )


@app.get("/metadata", response_model=MetadataResponse)
async def metadata() -> MetadataResponse:
    return MetadataResponse(
        available_models=sorted(registry.models.keys()),
        default_model=registry.default_model,
        class_labels=registry.class_labels,
        feature_names=registry.feature_names,
    )


@app.get("/metrics")
async def metrics():
    return metrics_endpoint()


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _features_to_matrix(records: list[NetworkFlow]) -> np.ndarray:
    if registry.preprocessor is None:
        raise HTTPException(503, detail="Preprocessor unavailable")
    df = pd.DataFrame([r.model_dump() for r in records])
    return np.asarray(registry.preprocessor.column_transformer.transform(df))


def _decode(label_index: int) -> str:
    return str(registry.preprocessor.label_encoder_binary.inverse_transform([label_index])[0])


def _top_feature_contributions(
    raw_features: dict, k: int = 5,
) -> list[dict]:
    """Cheap "explainability" — returns top-k non-zero numeric features.

    Real SHAP would be ideal but 100ms budget makes it impractical for this
    scope. This heuristic surfaces the raw attribute values that an analyst
    should review, which is what a SOC operator cares about.
    """
    items = [
        (k, v) for k, v in raw_features.items()
        if isinstance(v, (int, float)) and v != 0
    ]
    items.sort(key=lambda t: abs(t[1]), reverse=True)
    return [{"feature": name, "value": value} for name, value in items[:k]]


# ---------------------------------------------------------------------------
# Authenticated endpoints
# ---------------------------------------------------------------------------

@app.post(
    "/predict",
    response_model=PredictionResponse,
    responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}},
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(lambda: get_settings().rate_limit_predict)
async def predict(
    request: Request,
    req: PredictionRequest,
    session: AsyncSession = Depends(db_session),
) -> PredictionResponse:
    started = time.perf_counter()
    model = registry.resolve(req.model_name)
    X = _features_to_matrix([req.features])
    proba = model.predict_proba(X)[0]
    label_idx = int(np.argmax(proba))
    label = _decode(label_idx)
    elapsed_s = time.perf_counter() - started
    elapsed_ms = elapsed_s * 1000

    raw_features = req.features.model_dump()
    class_probs = {_decode(i): float(proba[i]) for i in range(len(proba))}

    repo = PredictionRepository(session)
    prediction_id, request_id = await repo.record_prediction(
        endpoint="/predict",
        model_used=model.name,
        prediction=label,
        confidence=float(proba[label_idx]),
        latency_ms=elapsed_ms,
        client_ip=get_remote_address(request),
        raw_features=raw_features,
        class_probabilities=class_probs,
    )

    PREDICTION_COUNTER.labels(model=model.name, label=label).inc()
    PREDICTION_LATENCY.labels(endpoint="/predict", model=model.name).observe(elapsed_s)

    top_features = _top_feature_contributions(raw_features)

    if label == "Malicious":
        alert = await repo.raise_alert(
            prediction_id=prediction_id,
            severity="high" if proba[label_idx] > 0.9 else "medium",
        )
        ALERT_COUNTER.labels(model=model.name).inc()
        await ws_manager.broadcast({
            "type": "alert",
            "alert_id": alert.id,
            "request_id": request_id,
            "prediction_id": prediction_id,
            "model_used": model.name,
            "prediction": label,
            "confidence": float(proba[label_idx]),
            "severity": alert.severity,
            "latency_ms": elapsed_ms,
            "top_features": top_features,
            "timestamp": alert.created_at.isoformat(),
        })

    return PredictionResponse(
        request_id=request_id,
        model_used=model.name,
        prediction=label,  # type: ignore[arg-type]
        confidence=float(proba[label_idx]),
        class_probabilities=class_probs,
        latency_ms=elapsed_ms,
        top_features=top_features,
    )


@app.post(
    "/predict/batch",
    response_model=BatchPredictionResponse,
    dependencies=[Depends(require_api_key)],
)
@limiter.limit(lambda: get_settings().rate_limit_batch)
async def predict_batch(
    request: Request,
    req: BatchPredictionRequest,
    session: AsyncSession = Depends(db_session),
) -> BatchPredictionResponse:
    started = time.perf_counter()
    model = registry.resolve(req.model_name)
    X = _features_to_matrix(req.records)
    proba = model.predict_proba(X)
    label_idx = np.argmax(proba, axis=1)
    elapsed_s = time.perf_counter() - started
    elapsed_ms = elapsed_s * 1000

    labels = registry.preprocessor.label_encoder_binary.inverse_transform(label_idx)
    client_ip = get_remote_address(request)
    repo = PredictionRepository(session)

    predictions = []
    for i, rec in enumerate(req.records):
        raw = rec.model_dump()
        class_probs = {_decode(j): float(proba[i, j]) for j in range(proba.shape[1])}
        label = str(labels[i])
        _pid, _rid = await repo.record_prediction(
            endpoint="/predict/batch",
            model_used=model.name,
            prediction=label,
            confidence=float(proba[i, label_idx[i]]),
            latency_ms=elapsed_ms / len(req.records),
            client_ip=client_ip,
            raw_features=raw,
            class_probabilities=class_probs,
        )
        PREDICTION_COUNTER.labels(model=model.name, label=label).inc()
        predictions.append({
            "prediction": label,
            "confidence": float(proba[i, label_idx[i]]),
            "class_probabilities": class_probs,
        })

    PREDICTION_LATENCY.labels(endpoint="/predict/batch", model=model.name).observe(elapsed_s)

    return BatchPredictionResponse(
        model_used=model.name,
        count=len(req.records),
        latency_ms=elapsed_ms,
        predictions=predictions,
    )


# ---------------------------------------------------------------------------
# Audit endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/audit/predictions",
    response_model=list[AuditPredictionOut],
    dependencies=[Depends(require_api_key)],
)
async def audit_predictions(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    only_malicious: bool = Query(False),
    model: str | None = Query(None),
    session: AsyncSession = Depends(db_session),
) -> list[AuditPredictionOut]:
    repo = PredictionRepository(session)
    rows = await repo.list_predictions(
        limit=limit, offset=offset,
        only_malicious=only_malicious, model=model,
    )
    return [AuditPredictionOut.model_validate(r) for r in rows]


@app.get(
    "/audit/alerts",
    response_model=list[AlertOut],
    dependencies=[Depends(require_api_key)],
)
async def audit_alerts(
    limit: int = Query(100, ge=1, le=1000),
    unacked_only: bool = Query(True),
    session: AsyncSession = Depends(db_session),
) -> list[AlertOut]:
    repo = PredictionRepository(session)
    rows = await repo.list_alerts(limit=limit, unacked_only=unacked_only)
    return [AlertOut.model_validate(r) for r in rows]


@app.post(
    "/audit/alerts/{alert_id}/ack",
    response_model=AlertOut,
    dependencies=[Depends(require_api_key)],
)
async def ack_alert(
    alert_id: int,
    session: AsyncSession = Depends(db_session),
) -> AlertOut:
    repo = PredictionRepository(session)
    alert = await repo.acknowledge_alert(alert_id, ack_by="api")
    if alert is None:
        raise HTTPException(404, detail=f"Alert {alert_id} not found")
    return AlertOut.model_validate(alert)


# ---------------------------------------------------------------------------
# Metrics summary endpoint (for frontend)
# ---------------------------------------------------------------------------

@app.get("/metrics/models", dependencies=[Depends(require_api_key)])
async def models_metrics():
    """Returns the evaluation results from the latest `evaluate` run."""
    import json
    report = MODELS_DIR / "evaluation_report.json"
    if not report.exists():
        return {}
    return json.loads(report.read_text())


@app.get("/metrics/training", dependencies=[Depends(require_api_key)])
async def training_metrics():
    """Returns training summary — cv score, hyperparameters, train time."""
    import json
    summary = MODELS_DIR / "training_summary.json"
    if not summary.exists():
        return {}
    return json.loads(summary.read_text())


# ---------------------------------------------------------------------------
# WebSocket — live alerts
# ---------------------------------------------------------------------------

@app.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket):
    # Auth accepts the API key via either the X-API-Key header (curl/python)
    # or the Sec-WebSocket-Protocol subprotocol `x-api-key.<KEY>` (browsers
    # cannot set custom headers on WebSocket handshakes).
    settings = get_settings()
    expected = settings.api_key

    api_key: str | None = websocket.headers.get("x-api-key")
    subprotocol_to_accept: str | None = None

    if api_key is None:
        requested = websocket.headers.get("sec-websocket-protocol", "")
        for proto in [p.strip() for p in requested.split(",") if p.strip()]:
            if proto.startswith("x-api-key."):
                api_key = proto[len("x-api-key.") :]
                subprotocol_to_accept = proto
                break

    if not api_key or not secrets_compare(api_key, expected):
        await websocket.close(code=4401, reason="invalid api key")
        return

    await ws_manager.connect(websocket, subprotocol=subprotocol_to_accept)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)


def secrets_compare(a: str, b: str) -> bool:
    import secrets as _s
    return _s.compare_digest(a, b)


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )


if __name__ == "__main__":
    main()
