"""End-to-end integration test — trains on a small subset and exercises
the full pipeline (preprocess → train → save → load → evaluate).

Kept separate from the fast unit tests so a developer can skip it with
`pytest -k "not integration"` when iterating locally.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from src.evaluate import evaluate_all
from src.models import TrainedModel
from src.preprocessing import PreprocessingPipeline
from src.train import train_single_model


@pytest.mark.integration
def test_train_evaluate_small_subset(tmp_path: Path, small_train_df, small_test_df):
    pipeline = PreprocessingPipeline()
    X_train, y_train = pipeline.fit_transform(small_train_df)
    X_test, y_test = pipeline.transform(small_test_df)
    pipeline.save(tmp_path)
    np.save(tmp_path / "X_test.npy", X_test)
    np.save(tmp_path / "y_test.npy", y_test)

    trained = train_single_model("random_forest", X_train, y_train, fast=True, cv_folds=3)
    trained.save(tmp_path)

    # Reload and evaluate.
    results = evaluate_all(models_dir=tmp_path)
    assert "random_forest" in results
    metrics = results["random_forest"]
    assert 0.0 <= metrics.accuracy <= 1.0
    assert 0.0 <= metrics.f1_macro <= 1.0
