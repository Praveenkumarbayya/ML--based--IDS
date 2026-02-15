"""Unit tests for src/models.py and a fast smoke training run."""

from __future__ import annotations

import numpy as np
import pytest

from src.models import SUPPORTED_MODELS, TrainedModel, build_estimator
from src.train import train_single_model


@pytest.mark.parametrize("name", SUPPORTED_MODELS)
def test_build_estimator_supports_all_names(name):
    est = build_estimator(name)
    assert hasattr(est, "fit") and hasattr(est, "predict")


def test_build_estimator_rejects_unknown():
    with pytest.raises(ValueError):
        build_estimator("no_such_model")


def test_trained_model_save_load_roundtrip(tmp_path, small_train_df, fitted_pipeline):
    X_train, y_train = fitted_pipeline.fit_transform(small_train_df)
    trained = train_single_model("logistic_regression", X_train, y_train, fast=True, cv_folds=3)
    out = trained.save(tmp_path)
    reloaded = TrainedModel.load(out)
    # Predictions on the same input should match after reload.
    assert np.array_equal(trained.predict(X_train[:50]), reloaded.predict(X_train[:50]))


def test_predict_proba_sums_to_one(fitted_pipeline, small_train_df):
    X_train, y_train = fitted_pipeline.fit_transform(small_train_df)
    trained = train_single_model("random_forest", X_train, y_train, fast=True, cv_folds=3)
    proba = trained.predict_proba(X_train[:20])
    assert np.allclose(proba.sum(axis=1), 1.0, atol=1e-6)
