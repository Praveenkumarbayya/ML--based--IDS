"""FastAPI tests using httpx AsyncClient via the TestClient shim.

These tests assume models are already trained (see the Makefile target
`make train` or the integration test in `test_integration.py`).
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from api.main import app, registry
from src.config import MODELS_DIR
from src.settings import get_settings

# Force a known API key for the test run — must happen before the app is used.
_TEST_KEY = "pytest-api-key-abcdefghijklmnop"
os.environ["API_KEY"] = _TEST_KEY
get_settings.cache_clear()


@pytest.fixture(scope="module")
def client() -> TestClient:
    # Force a reload so the module-level TestClient doesn't race with lifespan.
    registry.models.clear()
    registry.preprocessor = None
    registry.load(MODELS_DIR)
    with TestClient(app) as c:
        c.headers.update({"X-API-Key": _TEST_KEY})
        yield c


@pytest.fixture(scope="module")
def unauth_client() -> TestClient:
    registry.load(MODELS_DIR)
    with TestClient(app) as c:
        yield c


def _has_models() -> bool:
    return (MODELS_DIR / "column_transformer.joblib").exists() and any(
        (MODELS_DIR / f"{n}.joblib").exists()
        for n in ("random_forest", "xgboost", "lightgbm", "logistic_regression")
    )


pytestmark = pytest.mark.skipif(
    not _has_models(), reason="Models not trained; run `python main.py train --fast`."
)


def test_health_returns_ok_when_models_loaded(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["preprocessor_loaded"] is True
    assert len(body["models_loaded"]) >= 1


def test_metadata_exposes_models_and_labels(client):
    resp = client.get("/metadata")
    assert resp.status_code == 200
    body = resp.json()
    assert body["available_models"]
    assert set(body["class_labels"]) == {"Benign", "Malicious"}


def test_predict_on_benign_sample_returns_structured_response(client, sample_flow_dict):
    resp = client.post("/predict", json={"features": sample_flow_dict})
    assert resp.status_code == 200
    body = resp.json()
    assert body["prediction"] in {"Benign", "Malicious"}
    assert 0.0 <= body["confidence"] <= 1.0
    assert set(body["class_probabilities"]) == {"Benign", "Malicious"}


def test_predict_rejects_unknown_model(client, sample_flow_dict):
    resp = client.post(
        "/predict",
        json={"features": sample_flow_dict, "model_name": "not_a_model"},
    )
    assert resp.status_code == 400


def test_predict_batch_returns_same_count(client, sample_flow_dict):
    payload = {"records": [sample_flow_dict] * 5}
    resp = client.post("/predict/batch", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 5
    assert len(body["predictions"]) == 5


def test_malformed_payload_rejected_with_422(client):
    resp = client.post("/predict", json={"features": {"protocol_type": 42}})
    assert resp.status_code in (400, 422)


def test_predict_without_api_key_returns_401(unauth_client, sample_flow_dict):
    resp = unauth_client.post("/predict", json={"features": sample_flow_dict})
    assert resp.status_code == 401


def test_health_is_public(unauth_client):
    resp = unauth_client.get("/health")
    assert resp.status_code == 200


def test_metrics_endpoint_exposes_prometheus(unauth_client):
    resp = unauth_client.get("/metrics")
    assert resp.status_code == 200
    assert "ids_api_requests_total" in resp.text
