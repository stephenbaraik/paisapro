"""
PKL model persistence for RF classifiers and regression bundles.

Models are saved to disk keyed by (symbol, date). On startup or first call,
models are loaded from disk rather than retrained — training only happens
when no valid PKL exists for today.

Storage layout:
  {MODEL_DIR}/rf_{SYMBOL}_{YYYYMMDD}.pkl        ← RF classifier (one per stock)
  {MODEL_DIR}/reg_{SYMBOL}_{HORIZON}d_{YYYYMMDD}.pkl  ← regression bundle

Stale files (older than 1 day) are cleaned up automatically on daily refresh.
"""

from __future__ import annotations

import logging
import os
import pickle
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default: models/ folder next to the backend package
# Override via MODEL_STORE_DIR env var (e.g. /data/models on HF Spaces)
_DEFAULT_DIR = Path(__file__).resolve().parents[4] / "models"
MODEL_DIR = Path(os.environ.get("MODEL_STORE_DIR", str(_DEFAULT_DIR)))


def _ensure_dir() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)


def _pkl_path(symbol: str, today: date) -> Path:
    safe = symbol.replace(".", "_").replace("^", "")
    return MODEL_DIR / f"rf_{safe}_{today.strftime('%Y%m%d')}.pkl"


def save_model(symbol: str, clf) -> None:
    """Persist a trained classifier to disk for today's date."""
    _ensure_dir()
    path = _pkl_path(symbol, date.today())
    try:
        with open(path, "wb") as f:
            pickle.dump(clf, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.debug("Saved RF model for %s → %s", symbol, path.name)
    except Exception as exc:
        logger.warning("Failed to save RF model for %s: %s", symbol, exc)


def load_model(symbol: str) -> Optional[object]:
    """Load today's classifier from disk. Returns None if not found or corrupt."""
    path = _pkl_path(symbol, date.today())
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            clf = pickle.load(f)
        logger.debug("Loaded RF model for %s from disk", symbol)
        return clf
    except Exception as exc:
        logger.warning("Failed to load RF model for %s: %s", symbol, exc)
        path.unlink(missing_ok=True)  # delete corrupt file
        return None


def purge_stale_models() -> int:
    """Delete PKL files not dated today. Called on daily refresh."""
    if not MODEL_DIR.exists():
        return 0
    today_str = date.today().strftime("%Y%m%d")
    removed = 0
    for f in MODEL_DIR.glob("*.pkl"):
        if today_str not in f.name:
            try:
                f.unlink()
                removed += 1
            except Exception:
                pass
    if removed:
        logger.info("Purged %d stale model files", removed)
    return removed


# ── Regression bundle store ───────────────────────────────────────────────────
# Stores {rf, scaler_rf, ridge, scaler_ridge, gbm, eval_rf, eval_ridge, eval_gbm}

def _reg_pkl_path(symbol: str, horizon_days: int, today: date) -> Path:
    safe = symbol.replace(".", "_").replace("^", "")
    return MODEL_DIR / f"reg_{safe}_{horizon_days}d_{today.strftime('%Y%m%d')}.pkl"


def save_regression_bundle(symbol: str, horizon_days: int, bundle: dict) -> None:
    """Persist a trained regression bundle to disk for today's date."""
    _ensure_dir()
    path = _reg_pkl_path(symbol, horizon_days, date.today())
    try:
        with open(path, "wb") as f:
            pickle.dump(bundle, f, protocol=pickle.HIGHEST_PROTOCOL)
        logger.debug("Saved regression bundle for %s/%dd → %s", symbol, horizon_days, path.name)
    except Exception as exc:
        logger.warning("Failed to save regression bundle for %s: %s", symbol, exc)


def load_regression_bundle(symbol: str, horizon_days: int) -> Optional[dict]:
    """Load today's regression bundle from disk. Returns None if not found or corrupt."""
    path = _reg_pkl_path(symbol, horizon_days, date.today())
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            bundle = pickle.load(f)
        logger.debug("Loaded regression bundle for %s/%dd from disk", symbol, horizon_days)
        return bundle
    except Exception as exc:
        logger.warning("Failed to load regression bundle for %s: %s", symbol, exc)
        path.unlink(missing_ok=True)
        return None
