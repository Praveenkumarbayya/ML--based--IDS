"""Unified CLI for the Intrusion Detection System.

Examples:
    python main.py train --fast              # quick training (single hyperparam config)
    python main.py train --full              # full grid-search
    python main.py train --models random_forest xgboost
    python main.py evaluate                  # evaluate every saved model
    python main.py serve                     # start the FastAPI inference service
    python main.py predict --sample sample.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.config import API_HOST, API_PORT, MODELS_DIR
from src.evaluate import evaluate_all
from src.models import SUPPORTED_MODELS
from src.train import train_all
from src.utils import get_logger


logger = get_logger("ids.cli")


def _cmd_train(args: argparse.Namespace) -> int:
    models = args.models or list(SUPPORTED_MODELS)
    unknown = set(models) - set(SUPPORTED_MODELS)
    if unknown:
        logger.error(f"Unknown model(s): {sorted(unknown)}. Supported: {SUPPORTED_MODELS}")
        return 2
    train_all(models=models, fast=not args.full)
    return 0


def _cmd_evaluate(_: argparse.Namespace) -> int:
    import json as _json
    from src.config import MODELS_DIR

    results = evaluate_all()
    if not results:
        logger.error("No trained models found. Run `python main.py train` first.")
        return 1

    report_path = MODELS_DIR / "evaluation_report.json"
    all_metrics = _json.loads(report_path.read_text())

    target_f1 = 0.85

    holdout = all_metrics.get("holdout", {})
    test = all_metrics.get("official_test", {})

    if holdout:
        best_name = max(holdout, key=lambda n: holdout[n]["f1_macro"])
        best = holdout[best_name]
        logger.info(
            f"[holdout      ] best: {best_name}  "
            f"accuracy={best['accuracy']:.4f}  f1_macro={best['f1_macro']:.4f}"
        )
        if best["f1_macro"] < target_f1:
            logger.warning(
                f"Holdout F1={best['f1_macro']:.4f} is below the {target_f1} target — "
                "run `python main.py train --full` for a wider grid."
            )
        else:
            logger.info(
                f"Acceptance target F1>={target_f1} met on holdout "
                f"({best['f1_macro']:.4f})"
            )

    if test:
        best_name = max(test, key=lambda n: test[n]["f1_macro"])
        best = test[best_name]
        logger.info(
            f"[official test] best: {best_name}  "
            f"accuracy={best['accuracy']:.4f}  f1_macro={best['f1_macro']:.4f}"
        )
        logger.info(
            "Note: NSL-KDDTest+ intentionally contains attack types absent "
            "from KDDTrain+. Published benchmarks commonly report test F1 "
            "in the 0.75-0.85 range. See Tavallaee et al. (2009)."
        )
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
    return 0


def _cmd_predict(args: argparse.Namespace) -> int:
    from api.main import registry
    from api.schemas import NetworkFlow
    import numpy as np
    import pandas as pd

    registry.load()
    if not registry.models:
        logger.error("No models loaded. Train first.")
        return 1

    sample = json.loads(Path(args.sample).read_text())
    flow = NetworkFlow(**sample)
    df = pd.DataFrame([flow.model_dump()])
    X = registry.preprocessor.column_transformer.transform(df)

    model_name = args.model or registry.default_model
    model = registry.models[model_name]
    proba = model.predict_proba(X)[0]
    idx = int(np.argmax(proba))
    label = registry.preprocessor.label_encoder_binary.inverse_transform([idx])[0]

    print(json.dumps({
        "model_used": model_name,
        "prediction": str(label),
        "confidence": float(proba[idx]),
        "class_probabilities": {
            str(registry.preprocessor.label_encoder_binary.inverse_transform([i])[0]): float(proba[i])
            for i in range(len(proba))
        },
    }, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ids", description="Intrusion Detection System CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    train_p = sub.add_parser("train", help="Train one or more models")
    train_p.add_argument("--models", nargs="*", choices=SUPPORTED_MODELS)
    mode = train_p.add_mutually_exclusive_group()
    mode.add_argument("--fast", action="store_true", default=True,
                      help="Quick training (single hyperparameter config, default)")
    mode.add_argument("--full", action="store_true",
                      help="Full grid-search over the hyperparameter grids in config.py")
    train_p.set_defaults(func=_cmd_train)

    eval_p = sub.add_parser("evaluate", help="Evaluate every saved model")
    eval_p.set_defaults(func=_cmd_evaluate)

    serve_p = sub.add_parser("serve", help="Start the FastAPI inference service")
    serve_p.add_argument("--host", default=API_HOST)
    serve_p.add_argument("--port", type=int, default=API_PORT)
    serve_p.add_argument("--reload", action="store_true")
    serve_p.set_defaults(func=_cmd_serve)

    predict_p = sub.add_parser("predict", help="One-off prediction from a JSON file")
    predict_p.add_argument("--sample", required=True, help="Path to a JSON file with a NetworkFlow payload")
    predict_p.add_argument("--model", default=None, choices=list(SUPPORTED_MODELS))
    predict_p.set_defaults(func=_cmd_predict)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
