"""Pydantic v2 schemas for the FastAPI inference service.

Every field matches an NSL-KDD feature exactly. Using explicit field
definitions (instead of a loose dict) gives us input validation and an
OpenAPI spec the marker / supervisor can open in a browser.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class NetworkFlow(BaseModel):
    """A single NSL-KDD network flow record."""

    model_config = ConfigDict(extra="ignore")

    duration: float = Field(0, description="Connection duration (seconds)")
    protocol_type: str = Field("tcp", description="tcp | udp | icmp")
    service: str = Field("http", description="Destination service (http, ftp_data, ...)")
    flag: str = Field("SF", description="TCP connection status flag")
    src_bytes: float = 0
    dst_bytes: float = 0
    land: int = Field(0, ge=0, le=1)
    wrong_fragment: float = 0
    urgent: float = 0
    hot: float = 0
    num_failed_logins: float = 0
    logged_in: int = Field(0, ge=0, le=1)
    num_compromised: float = 0
    root_shell: int = Field(0, ge=0, le=1)
    su_attempted: int = Field(0, ge=0, le=1)
    num_root: float = 0
    num_file_creations: float = 0
    num_shells: float = 0
    num_access_files: float = 0
    num_outbound_cmds: float = 0
    is_host_login: int = Field(0, ge=0, le=1)
    is_guest_login: int = Field(0, ge=0, le=1)
    count: float = 0
    srv_count: float = 0
    serror_rate: float = 0
    srv_serror_rate: float = 0
    rerror_rate: float = 0
    srv_rerror_rate: float = 0
    same_srv_rate: float = 0
    diff_srv_rate: float = 0
    srv_diff_host_rate: float = 0
    dst_host_count: float = 0
    dst_host_srv_count: float = 0
    dst_host_same_srv_rate: float = 0
    dst_host_diff_srv_rate: float = 0
    dst_host_same_src_port_rate: float = 0
    dst_host_srv_diff_host_rate: float = 0
    dst_host_serror_rate: float = 0
    dst_host_srv_serror_rate: float = 0
    dst_host_rerror_rate: float = 0
    dst_host_srv_rerror_rate: float = 0


class PredictionRequest(BaseModel):
    features: NetworkFlow
    model_name: str | None = Field(
        default=None,
        description="Optional: random_forest | xgboost | lightgbm | logistic_regression. "
                    "If omitted, the server chooses the best-performing model.",
    )


class BatchPredictionRequest(BaseModel):
    records: list[NetworkFlow] = Field(..., min_length=1, max_length=10_000)
    model_name: str | None = None


class FeatureContribution(BaseModel):
    feature: str
    value: float


class PredictionResponse(BaseModel):
    request_id: str
    model_used: str
    prediction: Literal["Benign", "Malicious"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    class_probabilities: dict[str, float]
    latency_ms: float
    top_features: list[FeatureContribution] = Field(default_factory=list)


class BatchPredictionResponse(BaseModel):
    model_used: str
    count: int
    latency_ms: float
    predictions: list[dict]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    models_loaded: list[str]
    preprocessor_loaded: bool


class MetadataResponse(BaseModel):
    available_models: list[str]
    default_model: str | None
    class_labels: list[str]
    feature_names: list[str]


class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    request_id: str | None = None


# --- audit schemas -------------------------------------------------------

class AuditPredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: str
    created_at: datetime
    endpoint: str
    model_used: str
    prediction: str
    confidence: float
    latency_ms: float
    client_ip: str | None
    raw_features: dict[str, Any]
    class_probabilities: dict[str, float]


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prediction_id: int
    created_at: datetime
    severity: str
    acknowledged: bool
    ack_by: str | None
    ack_at: datetime | None
