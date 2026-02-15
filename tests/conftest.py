"""Shared pytest fixtures for the IDS test suite."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.config import (
    BINARY_FEATURES, CATEGORICAL_FEATURES, NUMERICAL_FEATURES, RANDOM_SEED,
)
from src.data_loader import load_nsl_kdd, map_labels_binary, map_labels_category
from src.preprocessing import PreprocessingPipeline


@pytest.fixture(scope="session")
def rng() -> np.random.Generator:
    return np.random.default_rng(RANDOM_SEED)


@pytest.fixture(scope="session")
def small_train_df() -> pd.DataFrame:
    """Load a small real-data sample so tests hit the actual column schema."""
    from src.config import TRAIN_FILE
    df = load_nsl_kdd(TRAIN_FILE).sample(n=2000, random_state=RANDOM_SEED)
    df = map_labels_binary(df)
    df = map_labels_category(df)
    return df.reset_index(drop=True)


@pytest.fixture(scope="session")
def small_test_df() -> pd.DataFrame:
    from src.config import TEST_FILE
    df = load_nsl_kdd(TEST_FILE).sample(n=500, random_state=RANDOM_SEED)
    df = map_labels_binary(df)
    df = map_labels_category(df)
    return df.reset_index(drop=True)


@pytest.fixture
def fitted_pipeline(small_train_df) -> PreprocessingPipeline:
    pipeline = PreprocessingPipeline()
    pipeline.fit_transform(small_train_df, label_col="binary_label")
    return pipeline


@pytest.fixture
def sample_flow_dict() -> dict:
    """A single benign NSL-KDD-like record shaped for the preprocessing pipeline."""
    base = {col: 0.0 for col in NUMERICAL_FEATURES}
    base.update({col: 0 for col in BINARY_FEATURES})
    base.update({
        "protocol_type": "tcp",
        "service": "http",
        "flag": "SF",
    })
    base["src_bytes"] = 491
    base["dst_bytes"] = 0
    return base
