"""Preprocessing pipeline for network intrusion detection.

Critical design principle: All transformations are fit on training data ONLY,
then applied to test/inference data using the same fitted transformers.
This prevents data leakage.
"""

import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.preprocessing import LabelEncoder, StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

from src.config import (
    CATEGORICAL_FEATURES, NUMERICAL_FEATURES, BINARY_FEATURES,
    MODELS_DIR, RANDOM_SEED,
)


class PreprocessingPipeline:
    """End-to-end preprocessing for NSL-KDD data.

    Handles:
    - Missing value imputation
    - Duplicate removal
    - Categorical encoding (one-hot)
    - Numerical scaling (standardization)
    - Label encoding (binary and multi-class)
    """

    def __init__(self):
        self.column_transformer = None
        self.label_encoder_binary = LabelEncoder()
        self.label_encoder_category = LabelEncoder()
        self.feature_names_out = None
        self._is_fitted = False

    def _build_column_transformer(self) -> ColumnTransformer:
        """Build the sklearn ColumnTransformer for feature preprocessing."""
        numerical_pipeline = Pipeline([
            ("scaler", StandardScaler()),
        ])

        categorical_pipeline = Pipeline([
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ])

        transformer = ColumnTransformer(
            transformers=[
                ("num", numerical_pipeline, NUMERICAL_FEATURES),
                ("cat", categorical_pipeline, CATEGORICAL_FEATURES),
                ("bin", "passthrough", BINARY_FEATURES),
            ],
            remainder="drop",
        )
        return transformer

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean raw data: handle missing values, remove duplicates."""
        df = df.copy()

        # Drop exact duplicates
        initial_rows = len(df)
        df = df.drop_duplicates()
        dropped = initial_rows - len(df)
        if dropped > 0:
            print(f"  Removed {dropped} duplicate rows")

        # Fill missing numerical values with median (rare in NSL-KDD but defensive)
        num_cols = [c for c in NUMERICAL_FEATURES if c in df.columns]
        for col in num_cols:
            if df[col].isnull().any():
                df[col] = df[col].fillna(df[col].median())

        # Fill missing categorical values with mode
        cat_cols = [c for c in CATEGORICAL_FEATURES if c in df.columns]
        for col in cat_cols:
            if df[col].isnull().any():
                df[col] = df[col].fillna(df[col].mode()[0])

        # Ensure numeric types for numerical columns
        for col in num_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        return df

    def fit_transform(
        self, df: pd.DataFrame, label_col: str = "binary_label"
    ) -> tuple[np.ndarray, np.ndarray]:
        """Fit the preprocessing pipeline on training data and transform it.

        Args:
            df: Training DataFrame with features and labels.
            label_col: Column to use as the target label.

        Returns:
            X: Transformed feature matrix.
            y: Encoded label array.
        """
        print("Fitting preprocessing pipeline on training data...")
        df = self._clean_data(df)

        # Separate features and labels
        feature_cols = NUMERICAL_FEATURES + CATEGORICAL_FEATURES + BINARY_FEATURES
        available_cols = [c for c in feature_cols if c in df.columns]
        X_raw = df[available_cols]
        y_raw = df[label_col]

        # Build and fit the column transformer.
        # np.asarray drops feature-name metadata so downstream models never
        # receive a DataFrame/ndarray mismatch between fit and predict time.
        self.column_transformer = self._build_column_transformer()
        X = np.asarray(self.column_transformer.fit_transform(X_raw))

        # Store feature names for later reference
        self.feature_names_out = self.column_transformer.get_feature_names_out()

        # Encode labels
        y = self.label_encoder_binary.fit_transform(y_raw)

        # Also fit category encoder if available
        if "attack_category" in df.columns:
            self.label_encoder_category.fit(df["attack_category"])

        self._is_fitted = True
        print(f"  Feature matrix shape: {X.shape}")
        print(f"  Label classes: {list(self.label_encoder_binary.classes_)}")
        return X, y

    def transform(
        self, df: pd.DataFrame, label_col: str = "binary_label"
    ) -> tuple[np.ndarray, np.ndarray]:
        """Transform new data using the already-fitted pipeline.

        This uses the SAME fitted transformers from fit_transform,
        preventing data leakage.
        """
        if not self._is_fitted:
            raise RuntimeError("Pipeline not fitted. Call fit_transform first.")

        df = self._clean_data(df)

        feature_cols = NUMERICAL_FEATURES + CATEGORICAL_FEATURES + BINARY_FEATURES
        available_cols = [c for c in feature_cols if c in df.columns]
        X_raw = df[available_cols]

        X = np.asarray(self.column_transformer.transform(X_raw))

        if label_col and label_col in df.columns:
            y = self.label_encoder_binary.transform(df[label_col])
            return X, y

        return X, None

    def transform_single(self, features: dict) -> np.ndarray:
        """Transform a single inference sample from a feature dictionary."""
        if not self._is_fitted:
            raise RuntimeError("Pipeline not fitted. Call fit_transform first.")

        df = pd.DataFrame([features])

        # Ensure all expected columns exist with defaults
        for col in NUMERICAL_FEATURES:
            if col not in df.columns:
                df[col] = 0.0
        for col in CATEGORICAL_FEATURES:
            if col not in df.columns:
                df[col] = "unknown"
        for col in BINARY_FEATURES:
            if col not in df.columns:
                df[col] = 0

        X = np.asarray(self.column_transformer.transform(df))
        return X

    def save(self, directory: Path = MODELS_DIR):
        """Save the fitted pipeline artifacts."""
        directory.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.column_transformer, directory / "column_transformer.joblib")
        joblib.dump(self.label_encoder_binary, directory / "label_encoder_binary.joblib")
        joblib.dump(self.label_encoder_category, directory / "label_encoder_category.joblib")
        joblib.dump(self.feature_names_out, directory / "feature_names.joblib")
        print(f"Pipeline saved to {directory}")

    @classmethod
    def load(cls, directory: Path = MODELS_DIR) -> "PreprocessingPipeline":
        """Load a previously fitted pipeline from disk."""
        pipeline = cls()
        pipeline.column_transformer = joblib.load(directory / "column_transformer.joblib")
        pipeline.label_encoder_binary = joblib.load(directory / "label_encoder_binary.joblib")
        pipeline.label_encoder_category = joblib.load(directory / "label_encoder_category.joblib")
        pipeline.feature_names_out = joblib.load(directory / "feature_names.joblib")
        pipeline._is_fitted = True
        return pipeline

    def get_label_name(self, encoded_label: int) -> str:
        """Convert an encoded label back to its string name."""
        return self.label_encoder_binary.inverse_transform([encoded_label])[0]
