"""Data loading module for NSL-KDD dataset."""

import pandas as pd
import numpy as np
from pathlib import Path

from src.config import (
    COLUMN_NAMES, TRAIN_FILE, TEST_FILE,
    ATTACK_CATEGORY_MAP, RAW_DATA_DIR,
)


def load_nsl_kdd(file_path: Path) -> pd.DataFrame:
    """Load an NSL-KDD data file into a DataFrame with proper column names.

    The NSL-KDD files are comma-separated with no header row. Some releases
    include a trailing blank line which pandas parses as a NaN-label row —
    those rows are dropped here so downstream label mapping is total.
    """
    df = pd.read_csv(file_path, names=COLUMN_NAMES, header=None, skip_blank_lines=True)
    df = df.dropna(subset=["label"])
    df = df.drop(columns=["difficulty_level"], errors="ignore")
    return df.reset_index(drop=True)


def map_labels_binary(df: pd.DataFrame) -> pd.DataFrame:
    """Map multi-class attack labels to binary (Benign / Malicious)."""
    df = df.copy()
    df["binary_label"] = df["label"].apply(
        lambda x: "Benign" if x.strip() == "normal" else "Malicious"
    )
    return df


def map_labels_category(df: pd.DataFrame) -> pd.DataFrame:
    """Map specific attack types to attack categories (DoS, Probe, R2L, U2R)."""
    df = df.copy()
    df["attack_category"] = df["label"].str.strip().map(ATTACK_CATEGORY_MAP)
    # Any unmapped label is treated as an unknown attack
    df["attack_category"] = df["attack_category"].fillna("Unknown")
    return df


def load_train_test(
    train_path: Path = TRAIN_FILE,
    test_path: Path = TEST_FILE,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and label-map both train and test sets."""
    train_df = load_nsl_kdd(train_path)
    test_df = load_nsl_kdd(test_path)

    train_df = map_labels_binary(train_df)
    train_df = map_labels_category(train_df)

    test_df = map_labels_binary(test_df)
    test_df = map_labels_category(test_df)

    return train_df, test_df


def get_dataset_summary(df: pd.DataFrame, name: str = "Dataset") -> dict:
    """Return a summary dict of the dataset."""
    summary = {
        "name": name,
        "shape": df.shape,
        "columns": list(df.columns),
        "dtypes": df.dtypes.value_counts().to_dict(),
        "missing_values": int(df.isnull().sum().sum()),
        "duplicates": int(df.duplicated().sum()),
    }
    if "binary_label" in df.columns:
        summary["binary_label_distribution"] = df["binary_label"].value_counts().to_dict()
    if "attack_category" in df.columns:
        summary["attack_category_distribution"] = df["attack_category"].value_counts().to_dict()
    return summary
