"""Prometheus metrics for the inference service."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response


REQUEST_COUNTER = Counter(
    "ids_api_requests_total",
    "Total number of API requests",
    ["endpoint", "method", "status"],
)

PREDICTION_COUNTER = Counter(
    "ids_predictions_total",
    "Total number of predictions made",
    ["model", "label"],
)

PREDICTION_LATENCY = Histogram(
    "ids_prediction_latency_seconds",
    "Latency of a prediction in seconds",
    ["endpoint", "model"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)

ALERT_COUNTER = Counter(
    "ids_alerts_total",
    "Total number of malicious-flow alerts raised",
    ["model"],
)


def metrics_endpoint() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
