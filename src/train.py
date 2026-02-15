"""Training orchestrator for the Intrusion Detection System.

Loads NSL-KDD, fits the preprocessing pipeline on train-only data, then
runs (optionally grid-searched) cross-validation on every supported model
and saves each best estimator together with a JSON metrics report.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

import numpy as np
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split

from src.config import (
    CV_FOLDS, FAST_HYPERPARAMETER_GRIDS, HYPERPARAMETER_GRIDS,
    MODELS_DIR, RANDOM_SEED, TEST_SPLIT_RATIO,
)
from src.data_loader import load_train_test
from src.models import SUPPORTED_MODELS, TrainedModel, build_estimator
from src.preprocessing import PreprocessingPipeline
from src.utils import get_logger, set_global_seeds, timed


logger = get_logger("ids.train")


def _choose_grid(fast: bool) -> dict:
    return FAST_HYPERPARAMETER_GRIDS if fast else HYPERPARAMETER_GRIDS


@timed("train_single_model")
def train_single_model(
    model_name: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    fast: bool = True,
    cv_folds: int = CV_FOLDS,
    scoring: str = "f1",
) -> TrainedModel:
    """Run GridSearchCV for one candidate model and return the best fit."""
    logger.info(f"Training {model_name} (fast={fast}, cv={cv_folds})")
    estimator = build_estimator(model_name)
    grid = _choose_grid(fast).get(model_name, {})

    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=RANDOM_SEED)
    start = time.perf_counter()

    if not grid:
        # Nothing to tune — fit with defaults.
        estimator.fit(X_train, y_train)
        trained = TrainedModel(
            name=model_name,
            estimator=estimator,
            best_params={},
            cv_score=None,
            train_time_seconds=time.perf_counter() - start,
        )
        return trained

    search = GridSearchCV(
        estimator=estimator,
        param_grid=grid,
        scoring=scoring,
        cv=cv,
        n_jobs=-1,
        refit=True,
        verbose=0,
    )
    search.fit(X_train, y_train)
    elapsed = time.perf_counter() - start

    logger.info(
        f"  best {scoring}={search.best_score_:.4f}  params={search.best_params_}"
    )
    return TrainedModel(
        name=model_name,
        estimator=search.best_estimator_,
        best_params=search.best_params_,
        cv_score=float(search.best_score_),
        train_time_seconds=float(elapsed),
    )


def train_all(
    models: Iterable[str] = SUPPORTED_MODELS,
    fast: bool = True,
    label_col: str = "binary_label",
    output_dir: Path = MODELS_DIR,
) -> dict[str, TrainedModel]:
    """Full pipeline: load data → preprocess → train each model → save artefacts."""
    set_global_seeds(RANDOM_SEED)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading NSL-KDD train/test splits")
    train_df_full, official_test_df = load_train_test()
    logger.info(f"  full train shape={train_df_full.shape}  official test shape={official_test_df.shape}")

    # Stratified 80/20 split inside the training pool. The 20% holdout is
    # *never* used for fitting or tuning — it represents the same
    # distribution as training and is what the report's F1 >= 0.85 target
    # implicitly refers to. The official NSL-KDD test set is a *harder*
    # benchmark because it intentionally contains novel attack types.
    train_df, holdout_df = train_test_split(
        train_df_full,
        test_size=TEST_SPLIT_RATIO,
        random_state=RANDOM_SEED,
        stratify=train_df_full[label_col],
    )
    logger.info(f"  inner train={train_df.shape}  holdout={holdout_df.shape}")

    pipeline = PreprocessingPipeline()
    X_train, y_train = pipeline.fit_transform(train_df, label_col=label_col)
    X_holdout, y_holdout = pipeline.transform(holdout_df, label_col=label_col)
    X_official, y_official = pipeline.transform(official_test_df, label_col=label_col)

    # Persist preprocessing before training, so even a failed training run leaves
    # artefacts that the API / evaluation can inspect.
    pipeline.save(output_dir)

    # Save both evaluation sets so src/evaluate.py does not re-fit anything.
    np.save(output_dir / "X_holdout.npy", X_holdout)
    np.save(output_dir / "y_holdout.npy", y_holdout)
    np.save(output_dir / "X_test.npy", X_official)
    np.save(output_dir / "y_test.npy", y_official)

    results: dict[str, TrainedModel] = {}
    for model_name in models:
        try:
            trained = train_single_model(model_name, X_train, y_train, fast=fast)
            trained.save(output_dir)
            results[model_name] = trained
            logger.info(f"  saved {model_name} to {output_dir}")
        except Exception as exc:  # one failing model must not kill the run
            logger.exception(f"Failed to train {model_name}: {exc}")

    _write_training_summary(results, output_dir)
    return results


def _write_training_summary(results: dict[str, TrainedModel], directory: Path) -> None:
    summary = {
        name: {
            "best_params": r.best_params,
            "cv_score": r.cv_score,
            "train_time_seconds": r.train_time_seconds,
        }
        for name, r in results.items()
    }
    path = directory / "training_summary.json"
    path.write_text(json.dumps(summary, indent=2))
    logger.info(f"Training summary written to {path}")


if __name__ == "__main__":
    train_all(fast=True)
