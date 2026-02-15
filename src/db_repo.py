"""Repository facade for audit persistence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db_models import Alert, EvaluationRun, ModelRun, Prediction


class PredictionRepository:
    """Thin wrapper around the ORM so callers stay SQL-free."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_prediction(
        self,
        endpoint: str,
        model_used: str,
        prediction: str,
        confidence: float,
        latency_ms: float,
        client_ip: str | None,
        raw_features: dict[str, Any],
        class_probabilities: dict[str, float],
    ) -> tuple[int, str]:
        request_id = str(uuid.uuid4())
        row = Prediction(
            request_id=request_id,
            endpoint=endpoint,
            model_used=model_used,
            prediction=prediction,
            confidence=float(confidence),
            latency_ms=float(latency_ms),
            client_ip=client_ip,
            raw_features=raw_features,
            class_probabilities=class_probabilities,
        )
        self.session.add(row)
        await self.session.flush()
        return row.id, request_id

    async def raise_alert(self, prediction_id: int, severity: str) -> Alert:
        alert = Alert(prediction_id=prediction_id, severity=severity)
        self.session.add(alert)
        await self.session.flush()
        return alert

    async def list_predictions(
        self,
        limit: int = 100,
        offset: int = 0,
        only_malicious: bool = False,
        model: str | None = None,
    ) -> list[Prediction]:
        stmt = select(Prediction).order_by(desc(Prediction.created_at)).limit(limit).offset(offset)
        conditions = []
        if only_malicious:
            conditions.append(Prediction.prediction == "Malicious")
        if model:
            conditions.append(Prediction.model_used == model)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_alerts(
        self, limit: int = 100, unacked_only: bool = True,
    ) -> list[Alert]:
        stmt = select(Alert).order_by(desc(Alert.created_at)).limit(limit)
        if unacked_only:
            stmt = stmt.where(Alert.acknowledged == False)  # noqa: E712
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def acknowledge_alert(self, alert_id: int, ack_by: str) -> Alert | None:
        alert = await self.session.get(Alert, alert_id)
        if alert is None:
            return None
        alert.acknowledged = True
        alert.ack_by = ack_by
        alert.ack_at = datetime.now(timezone.utc)
        await self.session.flush()
        return alert

    async def record_model_run(
        self, name: str, cv_score: float | None,
        train_seconds: float | None, best_params: dict[str, Any],
    ) -> ModelRun:
        row = ModelRun(
            model_name=name, cv_score=cv_score,
            train_seconds=train_seconds, best_params=best_params,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def record_evaluation(
        self, name: str, evaluation_set: str,
        accuracy: float, precision_macro: float, recall_macro: float,
        f1_macro: float, roc_auc: float | None,
        confusion_matrix: list[list[int]], per_class: dict[str, Any],
    ) -> EvaluationRun:
        row = EvaluationRun(
            model_name=name,
            evaluation_set=evaluation_set,
            accuracy=accuracy,
            precision_macro=precision_macro,
            recall_macro=recall_macro,
            f1_macro=f1_macro,
            roc_auc=roc_auc,
            confusion_matrix=confusion_matrix,
            per_class=per_class,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def evaluation_summary(self) -> dict[str, Any]:
        """Return the most recent evaluation per (model, evaluation_set)."""
        stmt = select(EvaluationRun).order_by(desc(EvaluationRun.created_at))
        result = await self.session.execute(stmt)
        rows = list(result.scalars().all())

        latest: dict[tuple[str, str], EvaluationRun] = {}
        for r in rows:
            key = (r.model_name, r.evaluation_set)
            if key not in latest:
                latest[key] = r

        out: dict[str, dict[str, dict[str, Any]]] = {}
        for (model_name, eval_set), r in latest.items():
            out.setdefault(eval_set, {})[model_name] = {
                "accuracy": r.accuracy,
                "precision_macro": r.precision_macro,
                "recall_macro": r.recall_macro,
                "f1_macro": r.f1_macro,
                "roc_auc": r.roc_auc,
                "confusion_matrix": r.confusion_matrix,
                "per_class": r.per_class,
                "created_at": r.created_at.isoformat(),
            }
        return out
