"""SQLAlchemy ORM models for the persisted audit trail."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    endpoint: Mapped[str] = mapped_column(String(64))
    model_used: Mapped[str] = mapped_column(String(64), index=True)
    prediction: Mapped[str] = mapped_column(String(32), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[float] = mapped_column(Float)
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_features: Mapped[dict[str, Any]] = mapped_column(JSON)
    class_probabilities: Mapped[dict[str, float]] = mapped_column(JSON)

    alert: Mapped["Alert | None"] = relationship("Alert", back_populates="prediction", uselist=False)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("predictions.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)  # low|medium|high
    acknowledged: Mapped[bool] = mapped_column(default=False, index=True)
    ack_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ack_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    prediction: Mapped[Prediction] = relationship("Prediction", back_populates="alert")


class ModelRun(Base):
    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(64), index=True)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    cv_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    train_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_params: Mapped[dict[str, Any]] = mapped_column(JSON)


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(64), index=True)
    evaluation_set: Mapped[str] = mapped_column(String(32), index=True)  # holdout|official_test
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    accuracy: Mapped[float] = mapped_column(Float)
    precision_macro: Mapped[float] = mapped_column(Float)
    recall_macro: Mapped[float] = mapped_column(Float)
    f1_macro: Mapped[float] = mapped_column(Float)
    roc_auc: Mapped[float | None] = mapped_column(Float, nullable=True)
    confusion_matrix: Mapped[list[list[int]]] = mapped_column(JSON)
    per_class: Mapped[dict[str, Any]] = mapped_column(JSON)
