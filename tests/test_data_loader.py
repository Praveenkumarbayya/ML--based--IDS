"""Unit tests for src/data_loader.py."""

from __future__ import annotations

import pandas as pd

from src.config import COLUMN_NAMES, TRAIN_FILE
from src.data_loader import (
    get_dataset_summary, load_nsl_kdd, load_train_test,
    map_labels_binary, map_labels_category,
)


def test_load_nsl_kdd_returns_dataframe_with_expected_columns():
    df = load_nsl_kdd(TRAIN_FILE)
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 100_000, "NSL-KDDTrain+ is expected to contain ~125k rows"
    # The difficulty_level column must be dropped.
    assert "difficulty_level" not in df.columns
    for col in COLUMN_NAMES[:-2]:  # skip label + difficulty
        assert col in df.columns


def test_map_labels_binary_produces_two_classes(small_train_df):
    mapped = map_labels_binary(small_train_df)
    classes = set(mapped["binary_label"].unique())
    assert classes.issubset({"Benign", "Malicious"})
    assert {"Benign", "Malicious"} & classes, "both classes should be represented"


def test_map_labels_category_assigns_known_categories(small_train_df):
    mapped = map_labels_category(small_train_df)
    valid = {"Benign", "DoS", "Probe", "R2L", "U2R", "Unknown"}
    assert set(mapped["attack_category"].unique()).issubset(valid)


def test_load_train_test_roundtrip():
    train_df, test_df = load_train_test()
    assert len(train_df) > 0 and len(test_df) > 0
    for df in (train_df, test_df):
        assert "binary_label" in df.columns
        assert "attack_category" in df.columns


def test_dataset_summary_has_expected_keys(small_train_df):
    summary = get_dataset_summary(small_train_df, "train-small")
    for key in ("name", "shape", "columns", "dtypes", "missing_values", "duplicates"):
        assert key in summary
    assert summary["name"] == "train-small"
