"""
ML Regression service — multi-model return forecasting with full evaluation.

Models:
  1. Random Forest Regressor     — ensemble, non-linear, feature importances
  2. Ridge Regression            — linear baseline, fast, interpretable
  3. Gradient Boosting Regressor — highest accuracy, sequential boosting

Evaluation (per model, time-aware):
  - MAE, RMSE, R² on held-out test set (last 20% of data)
  - Directional accuracy (% correct up/down)
  - 5-fold TimeSeriesSplit cross-validated MAE

Ensemble: equal-weight average of the three model predictions.
Confidence interval: ± 1.28 std of RF tree predictions (80% CI).
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

from ..schemas.ml_regression import (
    FeatureImportance,
    ModelEval,
    ModelPrediction,
    MLPredictionResponse,
)
from .analytics import _get_cached_df, get_stock_name

logger = logging.getLogger(__name__)

# ── Cache ─────────────────────────────────────────────────────────────────────
_ml_cache: dict[str, tuple[MLPredictionResponse, float]] = {}
_ML_CACHE_TTL = 3600  # 1 hour

_FEATURES = [
    "rsi_14", "macd", "macd_signal", "bb_width", "vol_ratio",
    "price_vs_sma20", "price_vs_sma50", "return_5d", "return_20d", "atr_normalized",
]
_FEATURE_LABELS = [
    "RSI-14", "MACD", "MACD Signal", "BB Width", "Volume Ratio",
    "Price/SMA20", "Price/SMA50", "Return 5d", "Return 20d", "ATR Norm",
]


def _eval_model(model, X_train, y_train, X_test, y_test, n_splits=5) -> ModelEval:
    """Compute MAE, RMSE, R², directional accuracy, and CV MAE."""
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    mae  = float(mean_absolute_error(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    r2   = float(r2_score(y_test, y_pred)) if len(y_test) > 1 else 0.0

    # Directional accuracy: did we predict the correct sign?
    dir_acc = float(np.mean(np.sign(y_pred) == np.sign(y_test))) * 100

    # Time-series cross-validated MAE (on full dataset)
    X_full = np.vstack([X_train, X_test])
    y_full = np.concatenate([y_train, y_test])
    tscv = TimeSeriesSplit(n_splits=n_splits)
    cv_maes = []
    for tr_idx, val_idx in tscv.split(X_full):
        if len(tr_idx) < 20:
            continue
        model.fit(X_full[tr_idx], y_full[tr_idx])
        preds = model.predict(X_full[val_idx])
        cv_maes.append(mean_absolute_error(y_full[val_idx], preds))
    cv_mae = float(np.mean(cv_maes)) if cv_maes else mae

    # Refit on training data for final predictions
    model.fit(X_train, y_train)

    return ModelEval(
        mae=round(mae * 100, 4),
        rmse=round(rmse * 100, 4),
        r2=round(r2, 4),
        directional_accuracy=round(dir_acc, 2),
        cv_mae=round(cv_mae * 100, 4),
    )


def get_ml_prediction(symbol: str, horizon_days: int = 30) -> Optional[MLPredictionResponse]:
    cache_key = f"{symbol}_{horizon_days}"
    if cache_key in _ml_cache:
        result, ts = _ml_cache[cache_key]
        if time.time() - ts < _ML_CACHE_TTL:
            return result

    df = _get_cached_df(symbol, "2y")
    if df is None or len(df) < 120:
        logger.warning(f"ML regression: insufficient data for {symbol}")
        return None

    df = df.copy()

    # ── Target: n-day forward return (decimal) ────────────────────────────────
    df["target"] = df["close"].shift(-horizon_days) / df["close"] - 1
    df = df.dropna(subset=_FEATURES + ["target"])

    if len(df) < 80:
        return None

    X = df[_FEATURES].values.astype(float)
    y = df["target"].values.astype(float)

    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    if len(X_train) < 40 or len(X_test) < 10:
        return None

    # ── Models ────────────────────────────────────────────────────────────────
    rf  = RandomForestRegressor(n_estimators=200, max_depth=6, random_state=42, n_jobs=1)
    ridge = Ridge(alpha=1.0)
    gbm = GradientBoostingRegressor(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42)

    rf.fit(X_train, y_train)
    ridge.fit(X_train, y_train)
    gbm.fit(X_train, y_train)

    # ── Evaluations ───────────────────────────────────────────────────────────
    eval_rf    = _eval_model(RandomForestRegressor(n_estimators=200, max_depth=6, random_state=42, n_jobs=1),
                             X_train, y_train, X_test, y_test)
    eval_ridge = _eval_model(Ridge(alpha=1.0), X_train, y_train, X_test, y_test)
    eval_gbm   = _eval_model(GradientBoostingRegressor(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42),
                             X_train, y_train, X_test, y_test)

    # Refit final models on full training data for prediction
    rf.fit(X_train, y_train)
    ridge.fit(X_train, y_train)
    gbm.fit(X_train, y_train)

    # ── Predict on latest features ────────────────────────────────────────────
    x_latest = X[-1:, :]
    current_price = float(df["close"].iloc[-1])

    pred_rf    = float(rf.predict(x_latest)[0])
    pred_ridge = float(ridge.predict(x_latest)[0])
    pred_gbm   = float(gbm.predict(x_latest)[0])

    # Ensemble: equal-weight average
    ensemble_return = (pred_rf + pred_ridge + pred_gbm) / 3.0
    ensemble_price  = round(current_price * (1 + ensemble_return), 2)

    # ── Confidence interval: RF tree variance (80% CI = ±1.28 std) ───────────
    tree_preds = np.array([t.predict(x_latest)[0] for t in rf.estimators_])
    std_return = float(np.std(tree_preds))
    ci_low  = round(current_price * (1 + ensemble_return - 1.28 * std_return), 2)
    ci_high = round(current_price * (1 + ensemble_return + 1.28 * std_return), 2)

    # ── Model agreement score (0=disagree, 100=fully agree) ──────────────────
    preds_array = np.array([pred_rf, pred_ridge, pred_gbm])
    agreement_score = max(0.0, 100.0 - float(np.std(preds_array) * 1000))

    # ── Best model (lowest CV MAE) ────────────────────────────────────────────
    cv_scores = {"rf": eval_rf.cv_mae, "ridge": eval_ridge.cv_mae, "gbm": eval_gbm.cv_mae}
    best_model = min(cv_scores, key=cv_scores.get)

    # ── Feature importances (from RF) ────────────────────────────────────────
    fi = rf.feature_importances_
    feature_importances = sorted(
        [FeatureImportance(feature=_FEATURE_LABELS[i], importance=round(float(fi[i]), 4))
         for i in range(len(_FEATURES))],
        key=lambda x: x.importance,
        reverse=True,
    )

    def pct(v: float) -> float:
        return round(v * 100, 3)

    result = MLPredictionResponse(
        symbol=symbol,
        company_name=get_stock_name(symbol),
        current_price=round(current_price, 2),
        horizon_days=horizon_days,
        predictions={
            "rf":    ModelPrediction(predicted_return=pct(pred_rf),    predicted_price=round(current_price * (1 + pred_rf), 2)),
            "ridge": ModelPrediction(predicted_return=pct(pred_ridge),  predicted_price=round(current_price * (1 + pred_ridge), 2)),
            "gbm":   ModelPrediction(predicted_return=pct(pred_gbm),   predicted_price=round(current_price * (1 + pred_gbm), 2)),
        },
        evaluations={
            "rf":    eval_rf,
            "ridge": eval_ridge,
            "gbm":   eval_gbm,
        },
        ensemble_return=pct(ensemble_return),
        ensemble_price=ensemble_price,
        ci_low=ci_low,
        ci_high=ci_high,
        model_agreement_score=round(agreement_score, 1),
        feature_importances=feature_importances,
        best_model=best_model,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    _ml_cache[cache_key] = (result, time.time())
    return result
