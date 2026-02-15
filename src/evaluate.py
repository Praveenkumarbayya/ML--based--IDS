"""Evaluation suite: precision, recall, F1, confusion matrix, ROC-AUC.

Consumes the artefacts produced by src/train.py and writes structured
metrics (JSON + CSV) plus confusion matrix / ROC curve PNGs so the
interim report has evaluation figures that are reproducible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    f1_score, precision_score, recall_score, roc_auc_score, roc_curve,
)

from src.config import MODELS_DIR
from src.models import SUPPORTED_MODELS, TrainedModel
from src.preprocessing import PreprocessingPipeline
from src.utils import get_logger


logger = get_logger("ids.evaluate")


@dataclass
class ModelMetrics:
    name: str
    accuracy: float
    precision_macro: float
    recall_macro: float
    f1_macro: float
    precision_per_class: dict[str, float]
    recall_per_class: dict[str, float]
    f1_per_class: dict[str, float]
    confusion_matrix: list[list[int]]
    roc_auc: float | None
    classification_report: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "accuracy": self.accuracy,
            "precision_macro": self.precision_macro,
            "recall_macro": self.recall_macro,
            "f1_macro": self.f1_macro,
            "precision_per_class": self.precision_per_class,
            "recall_per_class": self.recall_per_class,
            "f1_per_class": self.f1_per_class,
            "confusion_matrix": self.confusion_matrix,
            "roc_auc": self.roc_auc,
            "classification_report": self.classification_report,
        }


def _per_class(metric_fn, y_true, y_pred, labels: list[str]) -> dict[str, float]:
    values = metric_fn(y_true, y_pred, average=None, zero_division=0)
    return {label: float(values[i]) for i, label in enumerate(labels)}


def evaluate_model(
    model: TrainedModel,
    X_test: np.ndarray,
    y_test: np.ndarray,
    class_labels: list[str],
) -> ModelMetrics:
    y_pred = model.predict(X_test)

    # ROC-AUC needs probabilities and is only well-defined for binary here.
    roc_auc: float | None = None
    if len(class_labels) == 2:
        try:
            y_proba = model.predict_proba(X_test)[:, 1]
            roc_auc = float(roc_auc_score(y_test, y_proba))
        except Exception:
            roc_auc = None

    report = classification_report(
        y_test, y_pred, target_names=class_labels, output_dict=True, zero_division=0
    )

    return ModelMetrics(
        name=model.name,
        accuracy=float(accuracy_score(y_test, y_pred)),
        precision_macro=float(precision_score(y_test, y_pred, average="macro", zero_division=0)),
        recall_macro=float(recall_score(y_test, y_pred, average="macro", zero_division=0)),
        f1_macro=float(f1_score(y_test, y_pred, average="macro", zero_division=0)),
        precision_per_class=_per_class(precision_score, y_test, y_pred, class_labels),
        recall_per_class=_per_class(recall_score, y_test, y_pred, class_labels),
        f1_per_class=_per_class(f1_score, y_test, y_pred, class_labels),
        confusion_matrix=confusion_matrix(y_test, y_pred).tolist(),
        roc_auc=roc_auc,
        classification_report=report,
    )


def _plot_confusion_matrix(cm: np.ndarray, labels: list[str], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(5, 4))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yticklabels(labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.set_title("Confusion Matrix")
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, f"{cm[i, j]}", ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _plot_roc(model: TrainedModel, X_test: np.ndarray, y_test: np.ndarray, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    try:
        y_proba = model.predict_proba(X_test)[:, 1]
    except Exception:
        return
    fpr, tpr, _ = roc_curve(y_test, y_proba)
    auc = roc_auc_score(y_test, y_proba)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(fpr, tpr, label=f"{model.name} (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.4)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def evaluate_all(models_dir: Path = MODELS_DIR) -> dict[str, ModelMetrics]:
    """Evaluate every saved model against both the train-holdout and the
    official NSL-KDD test set. The holdout is the same-distribution metric
    used for the F1>=0.85 acceptance target; the official test set is the
    harder novel-attack benchmark reported for transparency."""
    pipeline = PreprocessingPipeline.load(models_dir)
    class_labels = list(pipeline.label_encoder_binary.classes_)

    eval_sets: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for tag, x_file, y_file in (
        ("holdout", "X_holdout.npy", "y_holdout.npy"),
        ("official_test", "X_test.npy", "y_test.npy"),
    ):
        x_path = models_dir / x_file
        y_path = models_dir / y_file
        if x_path.exists() and y_path.exists():
            eval_sets[tag] = (np.load(x_path), np.load(y_path))

    if not eval_sets:
        raise FileNotFoundError("No evaluation sets found under models/. Re-run training.")

    plots_dir = models_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, ModelMetrics] = {}
    all_metrics: dict[str, dict[str, ModelMetrics]] = {tag: {} for tag in eval_sets}

    for name in SUPPORTED_MODELS:
        model_path = models_dir / f"{name}.joblib"
        if not model_path.exists():
            logger.warning(f"Skipping {name} — no artefact at {model_path}")
            continue
        model = TrainedModel.load(model_path)

        for tag, (X, y) in eval_sets.items():
            metrics = evaluate_model(model, X, y, class_labels)
            all_metrics[tag][name] = metrics
            auc = f"{metrics.roc_auc:.4f}" if metrics.roc_auc is not None else "n/a"
            logger.info(
                f"  [{tag:>13}] {name}: acc={metrics.accuracy:.4f} "
                f"f1={metrics.f1_macro:.4f} roc_auc={auc}"
            )
            _plot_confusion_matrix(
                np.array(metrics.confusion_matrix), class_labels,
                plots_dir / f"confusion_{name}_{tag}.png",
            )
            if tag == "official_test":
                _plot_roc(model, X, y, plots_dir / f"roc_{name}.png")

        # Promote the official-test metrics as the primary return value.
        if "official_test" in all_metrics and name in all_metrics["official_test"]:
            results[name] = all_metrics["official_test"][name]
        elif "holdout" in all_metrics and name in all_metrics["holdout"]:
            results[name] = all_metrics["holdout"][name]

    _write_reports(all_metrics, models_dir)
    return results


def _write_reports(
    all_metrics: dict[str, dict[str, ModelMetrics]], directory: Path
) -> None:
    """Persist metrics as JSON + comparative CSV for every evaluation set."""
    json_blob = {
        tag: {name: m.as_dict() for name, m in models.items()}
        for tag, models in all_metrics.items()
    }
    json_path = directory / "evaluation_report.json"
    json_path.write_text(json.dumps(json_blob, indent=2))

    rows = []
    for tag, models in all_metrics.items():
        for name, m in models.items():
            rows.append({
                "evaluation_set": tag,
                "model": name,
                "accuracy": m.accuracy,
                "precision_macro": m.precision_macro,
                "recall_macro": m.recall_macro,
                "f1_macro": m.f1_macro,
                "roc_auc": m.roc_auc,
            })
    df = pd.DataFrame(rows).sort_values(["evaluation_set", "f1_macro"], ascending=[True, False])
    csv_path = directory / "evaluation_summary.csv"
    df.to_csv(csv_path, index=False)
    logger.info(f"Evaluation report written to {json_path}")
    logger.info(f"Comparative summary written to {csv_path}")


if __name__ == "__main__":
    evaluate_all()
