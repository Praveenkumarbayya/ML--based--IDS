"""Model factory for the Intrusion Detection System.

Exposes a uniform interface over scikit-learn, XGBoost, and LightGBM estimators
so the training and evaluation pipelines treat every candidate the same way.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

from src.config import MODELS_DIR, RANDOM_SEED


SUPPORTED_MODELS = ("random_forest", "xgboost", "lightgbm", "logistic_regression")


@dataclass
class TrainedModel:
    """Wraps a fitted estimator with the metadata needed to use it in production."""

    name: str
    estimator: BaseEstimator
    best_params: dict[str, Any]
    cv_score: float | None = None
    train_time_seconds: float | None = None

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self.estimator.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if hasattr(self.estimator, "predict_proba"):
            return self.estimator.predict_proba(X)
        # Fallback: one-hot from discrete predictions (rare — LR/RF/XGB/LGBM all support proba)
        preds = self.predict(X)
        n_classes = int(preds.max() + 1)
        proba = np.zeros((len(preds), n_classes), dtype=float)
        proba[np.arange(len(preds)), preds] = 1.0
        return proba

    def save(self, directory: Path = MODELS_DIR) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.name}.joblib"
        joblib.dump(
            {
                "name": self.name,
                "estimator": self.estimator,
                "best_params": self.best_params,
                "cv_score": self.cv_score,
                "train_time_seconds": self.train_time_seconds,
            },
            path,
        )
        return path

    @classmethod
    def load(cls, path: Path) -> "TrainedModel":
        payload = joblib.load(path)
        return cls(**payload)


def build_estimator(model_name: str) -> BaseEstimator:
    """Return an unfitted estimator for `model_name`.

    Defaults are chosen to be reasonable starting points — hyperparameter
    tuning (see src/train.py) overrides them.
    """
    name = model_name.lower()
    if name == "random_forest":
        return RandomForestClassifier(
            n_estimators=200,
            n_jobs=-1,
            random_state=RANDOM_SEED,
            class_weight="balanced",
        )
    if name == "logistic_regression":
        return LogisticRegression(
            max_iter=1000,
            random_state=RANDOM_SEED,
            class_weight="balanced",
        )
    if name == "xgboost":
        from xgboost import XGBClassifier

        return XGBClassifier(
            n_estimators=200,
            learning_rate=0.1,
            max_depth=6,
            tree_method="hist",
            n_jobs=-1,
            random_state=RANDOM_SEED,
            eval_metric="logloss",
        )
    if name == "lightgbm":
        from lightgbm import LGBMClassifier

        return LGBMClassifier(
            n_estimators=200,
            learning_rate=0.1,
            num_leaves=63,
            n_jobs=-1,
            random_state=RANDOM_SEED,
            class_weight="balanced",
            verbose=-1,
        )
    raise ValueError(f"Unknown model '{model_name}'. Supported: {SUPPORTED_MODELS}")


def prefix_params(model_name: str, grid: dict[str, list]) -> dict[str, list]:
    """Prefix a parameter grid so it works inside a sklearn Pipeline step named `clf`."""
    _ = model_name  # keeps the interface uniform across call-sites
    return {f"clf__{k}": v for k, v in grid.items()}
