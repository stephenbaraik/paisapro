"""
Random Forest classifier for BUY/HOLD/SELL signal prediction.

Fetch priority for each symbol's model:
  1. In-memory CacheManager (fastest — no disk I/O)
  2. Today's PKL file on disk (fast — avoids retraining)
  3. Train from scratch (only happens once per symbol per day)

Training only runs when:
  - No PKL exists for today (first run after daily refresh / fresh deployment)

This means 500 models train exactly once per day, during the first report build
after 6 PM IST. All subsequent report builds load from disk in milliseconds.
"""

from __future__ import annotations

import logging

import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from ...core.cache import cache
from ...schemas.analytics import SignalDirection
from .model_store import load_model, save_model, purge_stale_models

logger = logging.getLogger(__name__)

FEATURES = [
    "rsi_14", "macd", "macd_signal", "bb_width", "vol_ratio",
    "price_vs_sma20", "price_vs_sma50", "return_5d", "return_20d", "atr_normalized",
]

_RF_CACHE_TTL = 86400  # 24 h — aligned with daily refresh cycle


def train_rf_classifier(df: pd.DataFrame, symbol: str = "") -> tuple[float, SignalDirection]:
    """
    Return (prob_up, signal) for the given stock DataFrame.

    Lookup order: memory cache → PKL on disk → train from scratch.
    Training is persisted to disk immediately so subsequent calls skip training.
    """
    cache_key = f"ml:rf:{symbol}"

    # 1. In-memory cache (zero cost)
    if symbol:
        cached = cache.get(cache_key)
        if cached is not None:
            clf, _, _ = cached
            prob_up = _infer(clf, df)
            if prob_up is not None:
                sig = _prob_to_signal(prob_up)
                return round(prob_up, 3), sig
            _, cached_prob, cached_sig = cached
            return cached_prob, cached_sig

    # 2. PKL on disk (today's model — no training needed)
    if symbol:
        clf = load_model(symbol)
        if clf is not None:
            prob_up = _infer(clf, df)
            if prob_up is not None:
                sig = _prob_to_signal(prob_up)
                cache.set(cache_key, (clf, round(prob_up, 3), sig), _RF_CACHE_TTL)
                return round(prob_up, 3), sig

    # 3. Train from scratch
    clf, prob_up, sig = _train(df)
    if symbol and clf is not None:
        save_model(symbol, clf)
        cache.set(cache_key, (clf, round(prob_up, 3), sig), _RF_CACHE_TTL)

    return round(prob_up, 3), sig


def _infer(clf, df: pd.DataFrame) -> float | None:
    """Run inference on the latest row. Returns None if features unavailable."""
    try:
        df_c = df.dropna(subset=FEATURES + ["close"])
        if len(df_c) >= 1:
            return float(clf.predict_proba(df_c[FEATURES].values[-1:, :])[0][1])
    except Exception:
        pass
    return None


def _train(df: pd.DataFrame) -> tuple[object | None, float, SignalDirection]:
    """Train a new RF classifier. Returns (clf, prob_up, signal)."""
    df_c = df.dropna(subset=FEATURES + ["close"]).copy()
    if len(df_c) < 40:
        return None, 0.5, SignalDirection.HOLD

    df_c["target"] = (df_c["close"].shift(-5) > df_c["close"]).astype(int)
    df_c = df_c.dropna(subset=["target"])

    X = df_c[FEATURES].values
    y = df_c["target"].values.astype(int)

    split = int(len(X) * 0.8)
    X_train, y_train = X[:split], y[:split]

    if len(X_train) < 30 or len(set(y_train)) < 2:
        return None, 0.5, SignalDirection.HOLD

    clf = RandomForestClassifier(n_estimators=30, max_depth=3, random_state=42, n_jobs=1)
    clf.fit(X_train, y_train)

    prob_up = float(clf.predict_proba(df_c[FEATURES].values[-1:, :])[0][1])
    sig = _prob_to_signal(prob_up)
    return clf, round(prob_up, 3), sig


def _prob_to_signal(prob_up: float) -> SignalDirection:
    if prob_up > 0.6:
        return SignalDirection.BUY
    elif prob_up < 0.4:
        return SignalDirection.SELL
    return SignalDirection.HOLD


def invalidate_all_models() -> None:
    """
    Clear in-memory model cache and purge stale PKL files.
    Called on daily refresh so models retrain with today's data.
    """
    cache.invalidate_prefix("ml:rf:")
    purge_stale_models()
