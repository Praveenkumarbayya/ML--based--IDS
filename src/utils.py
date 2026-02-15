"""Shared utilities: logging, timing, JSON prediction audit log."""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from src.config import LOGS_DIR


_LOGGER_CACHE: dict[str, logging.Logger] = {}


def get_logger(name: str = "ids", level: int = logging.INFO) -> logging.Logger:
    """Return a cached logger with a consistent format.

    Writes to stdout and to logs/ids.log. Safe to call many times —
    handlers are attached only once.
    """
    if name in _LOGGER_CACHE:
        return _LOGGER_CACHE[name]

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(fmt)
        logger.addHandler(stream_handler)

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(LOGS_DIR / f"{name}.log", encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    _LOGGER_CACHE[name] = logger
    return logger


def timed(label: str | None = None) -> Callable:
    """Decorator that logs the wall-clock time of the wrapped function."""
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = get_logger("ids")
            tag = label or fn.__name__
            start = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
                return result
            finally:
                elapsed = time.perf_counter() - start
                logger.info(f"[timing] {tag} finished in {elapsed:.2f}s")
        return wrapper
    return decorator


class PredictionAuditLogger:
    """Append-only JSONL audit log for prediction requests.

    Rotates to a new file once the current file exceeds `max_bytes`
    (default 100MB, matching the non-functional requirement).
    """

    def __init__(self, path: Path | None = None, max_bytes: int = 100 * 1024 * 1024):
        self.path = path or (LOGS_DIR / "predictions.jsonl")
        self.max_bytes = max_bytes
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _rotate_if_needed(self) -> None:
        if self.path.exists() and self.path.stat().st_size >= self.max_bytes:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            rotated = self.path.with_name(f"{self.path.stem}.{ts}.jsonl")
            self.path.rename(rotated)

    def log(self, entry: dict[str, Any]) -> str:
        """Append an audit entry. Returns the assigned request_id."""
        self._rotate_if_needed()
        record = {
            "request_id": entry.get("request_id") or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **entry,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        return record["request_id"]


def set_global_seeds(seed: int) -> None:
    """Seed python, numpy, and any libraries that expose a RNG."""
    import random

    import numpy as np

    random.seed(seed)
    np.random.seed(seed)
    try:
        import os

        os.environ["PYTHONHASHSEED"] = str(seed)
    except Exception:
        pass
