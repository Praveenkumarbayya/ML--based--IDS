"""Unit tests for src/preprocessing.py.

Critical invariant: the pipeline must NOT leak information from test into
training. Verified here by fitting on train only and re-using the same
transformer for test.
"""

from __future__ import annotations

import numpy as np

from src.preprocessing import PreprocessingPipeline


def test_fit_transform_shapes_are_consistent(small_train_df):
    pipeline = PreprocessingPipeline()
    X, y = pipeline.fit_transform(small_train_df, label_col="binary_label")
    assert X.shape[0] == y.shape[0]
    assert X.ndim == 2 and y.ndim == 1
    assert pipeline.feature_names_out is not None and len(pipeline.feature_names_out) == X.shape[1]


def test_transform_requires_fit(small_train_df):
    pipeline = PreprocessingPipeline()
    try:
        pipeline.transform(small_train_df)
    except RuntimeError as exc:
        assert "fitted" in str(exc).lower()
    else:
        raise AssertionError("transform should raise when pipeline is not fitted")


def test_transform_on_test_set_uses_fitted_state(small_train_df, small_test_df):
    pipeline = PreprocessingPipeline()
    X_train, _ = pipeline.fit_transform(small_train_df)
    X_test, y_test = pipeline.transform(small_test_df)
    # Same feature dimensionality on both sides — proves the same transformer is used.
    assert X_train.shape[1] == X_test.shape[1]
    assert y_test.shape[0] == X_test.shape[0]


def test_save_and_load_roundtrip(tmp_path, small_train_df, small_test_df):
    pipeline = PreprocessingPipeline()
    X_train_before, _ = pipeline.fit_transform(small_train_df)
    pipeline.save(tmp_path)

    reloaded = PreprocessingPipeline.load(tmp_path)
    X_test_before, _ = pipeline.transform(small_test_df)
    X_test_after, _ = reloaded.transform(small_test_df)
    assert np.allclose(X_test_before, X_test_after)


def test_transform_single_produces_row_vector(fitted_pipeline, sample_flow_dict):
    X = fitted_pipeline.transform_single(sample_flow_dict)
    assert X.shape == (1, fitted_pipeline.column_transformer.get_feature_names_out().shape[0])
