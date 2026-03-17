"""
ML Regression service — multi-model return forecasting with full evaluation.

Models (each with its own optimised preprocessing pipeline):
  1. Random Forest  — base features + StandardScaler (non-linear, feature importances)
  2. Ridge          — extended features + RobustScaler + winsorisation (linear, robust)
  3. Gradient Boost — base features + StandardScaler (stump-based, sequential)

Evaluation: walk-forward expanding-window with purging gap to avoid target overlap.
Target: excess forward return (raw - 20-day rolling trend) for stationarity.
Ensemble: R²-weighted average of the three model predictions.
Confidence interval: ± 1.28 std of RF tree predictions (80% CI).
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Optional, Callable

import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler, RobustScaler

from ..schemas.ml_regression import (
    FeatureImportance,
    ModelEval,
    ModelPrediction,
    MLPredictionResponse,
)
from .market_data import get_price_df as _get_cached_df
from .universe import get_name as get_stock_name
from .ml.model_store import save_regression_bundle, load_regression_bundle

logger = logging.getLogger(__name__)

# ── Cache ─────────────────────────────────────────────────────────────────────
from ..core.cache import cache as _cache_mgr
_ML_CACHE_TTL = 3600  # 1 hour

# Base technical features (available from analytics.py)
_BASE_FEATURES = [
    "rsi_14", "macd", "macd_signal", "bb_width", "vol_ratio",
    "price_vs_sma20", "price_vs_sma50", "return_5d", "return_20d", "atr_normalized",
]
# Engineered features (computed here for Ridge's extended pipeline)
_EXTRA_FEATURES = [
    "rsi_14_ma10", "macd_hist", "return_10d", "return_60d", "momentum_accel",
    "vol_20d", "vol_ratio_20_60", "bb_position", "sma_spread",
    "price_vs_sma200", "rsi_roc", "vol_ratio_ma5",
]
_ALL_FEATURES = _BASE_FEATURES + _EXTRA_FEATURES

_BASE_LABELS = [
    "RSI-14", "MACD", "MACD Signal", "BB Width", "Volume Ratio",
    "Price/SMA20", "Price/SMA50", "Return 5d", "Return 20d", "ATR Norm",
]

_MIN_TRAIN = 180
_DEMEAN_WINDOW = 20


# ── Feature engineering ───────────────────────────────────────────────────────

def _engineer_features(df):
    """Add derived features from existing columns (in-place)."""
    close = df["close"]

    # Smoothed RSI — reduces noise, captures trend of momentum
    df["rsi_14_ma10"] = df["rsi_14"].rolling(10, min_periods=5).mean()

    # MACD histogram — momentum acceleration
    df["macd_hist"] = df["macd_histogram"]

    # Multi-scale momentum
    df["return_10d"] = close.pct_change(10)
    df["return_60d"] = close.pct_change(60)
    df["momentum_accel"] = df["return_20d"] - df["return_5d"]

    # Realised volatility (annualised)
    df["vol_20d"] = df["daily_return"].rolling(20, min_periods=10).std() * np.sqrt(252)
    vol_60d = df["daily_return"].rolling(60, min_periods=30).std() * np.sqrt(252)
    df["vol_ratio_20_60"] = df["vol_20d"] / vol_60d.replace(0, np.nan)

    # Bollinger position (0 = lower band, 1 = upper band)
    bb_range = (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
    df["bb_position"] = (close - df["bb_lower"]) / bb_range

    # Trend strength / SMA convergence
    df["sma_spread"] = (df["sma_20"] - df["sma_50"]) / close
    df["price_vs_sma200"] = (close / df["sma_200"]) - 1

    # RSI rate-of-change (5-day)
    df["rsi_roc"] = df["rsi_14"].diff(5)

    # Volume regime
    df["vol_ratio_ma5"] = df["vol_ratio"].rolling(5, min_periods=3).mean()

    return df


# ── Walk-forward evaluation ───────────────────────────────────────────────────

def _walk_forward_eval(
    model_factory: Callable,
    X: np.ndarray,
    y: np.ndarray,
    horizon_days: int,
    scaler_cls=StandardScaler,
    winsorize: bool = False,
    min_train: int = _MIN_TRAIN,
    step: int | None = None,
) -> ModelEval:
    """Walk-forward expanding-window evaluation with purging gap."""
    if step is None:
        step = max(horizon_days, 20)

    n = len(X)
    all_preds: list[float] = []
    all_actuals: list[float] = []

    t = min_train
    while t + step <= n:
        train_end = max(20, t - horizon_days)  # purge gap
        if train_end < 40:
            t += step
            continue

        scaler = scaler_cls()
        X_tr = scaler.fit_transform(X[:train_end])
        X_te = scaler.transform(X[t : t + step])

        if winsorize:
            X_tr = np.clip(X_tr, -3, 3)
            X_te = np.clip(X_te, -3, 3)

        model = model_factory()
        model.fit(X_tr, y[:train_end])
        preds = model.predict(X_te)

        all_preds.extend(preds.tolist())
        all_actuals.extend(y[t : t + step].tolist())
        t += step

    ap = np.array(all_preds)
    aa = np.array(all_actuals)

    if len(ap) < 10:
        # Fallback: single split
        split = int(n * 0.8)
        scaler = scaler_cls()
        X_tr = scaler.fit_transform(X[:split])
        X_te = scaler.transform(X[split:])
        if winsorize:
            X_tr = np.clip(X_tr, -3, 3)
            X_te = np.clip(X_te, -3, 3)
        model = model_factory()
        model.fit(X_tr, y[:split])
        ap = model.predict(X_te)
        aa = y[split:]

    mae = float(mean_absolute_error(aa, ap))
    rmse = float(np.sqrt(mean_squared_error(aa, ap)))
    r2 = float(r2_score(aa, ap)) if len(aa) > 1 else 0.0
    dir_acc = float(np.mean(np.sign(ap) == np.sign(aa))) * 100

    return ModelEval(
        mae=round(mae * 100, 4),
        rmse=round(rmse * 100, 4),
        r2=round(r2, 4),
        directional_accuracy=round(dir_acc, 2),
        cv_mae=round(mae * 100, 4),
    )


# ── Main prediction function ─────────────────────────────────────────────────

def _prepare_inference_inputs(df, horizon_days: int):
    """
    Given a feature-engineered df, return (current_price, x_latest_base,
    x_latest_all, recent_trend) needed for inference. Returns None on failure.
    """
    df_feat = df.dropna(subset=_ALL_FEATURES)
    if len(df_feat) < 80:
        return None
    current_price = float(df_feat["close"].iloc[-1])
    x_latest_base = df_feat[_BASE_FEATURES].iloc[-1:].values.astype(float)
    x_latest_all = df_feat[_ALL_FEATURES].iloc[-1:].values.astype(float)

    bret_latest = df_feat["close"].pct_change(horizon_days)
    recent_trend = float(
        bret_latest.rolling(_DEMEAN_WINDOW, min_periods=min(15, _DEMEAN_WINDOW)).mean().iloc[-1]
    )
    if np.isnan(recent_trend):
        recent_trend = 0.0
    return current_price, x_latest_base, x_latest_all, recent_trend


_MLOPS_TTL = 86400  # 24h — survive daily restarts


def _record_mlops_metrics(symbol: str, horizon_days: int, bundle: dict, from_pkl: bool) -> None:
    """Store eval metrics for the model-health dashboard."""
    _cache_mgr.set(f"mlops:reg:{symbol}_{horizon_days}", {
        "symbol": symbol,
        "horizon_days": horizon_days,
        "rf_r2": bundle["eval_rf"].r2,
        "rf_dir_acc": bundle["eval_rf"].directional_accuracy,
        "rf_mae": bundle["eval_rf"].mae,
        "ridge_r2": bundle["eval_ridge"].r2,
        "ridge_dir_acc": bundle["eval_ridge"].directional_accuracy,
        "ridge_mae": bundle["eval_ridge"].mae,
        "gbm_r2": bundle["eval_gbm"].r2,
        "gbm_dir_acc": bundle["eval_gbm"].directional_accuracy,
        "gbm_mae": bundle["eval_gbm"].mae,
        "best_model": min(
            {"rf": bundle["eval_rf"].cv_mae, "ridge": bundle["eval_ridge"].cv_mae,
             "gbm": bundle["eval_gbm"].cv_mae},
            key=lambda k: {"rf": bundle["eval_rf"].cv_mae, "ridge": bundle["eval_ridge"].cv_mae,
                           "gbm": bundle["eval_gbm"].cv_mae}[k],
        ),
        "from_pkl": from_pkl,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }, _MLOPS_TTL)


def _build_result_from_bundle(
    bundle: dict,
    symbol: str,
    horizon_days: int,
    current_price: float,
    x_latest_base,
    x_latest_all,
    recent_trend: float,
    from_pkl: bool = False,
) -> MLPredictionResponse:
    """Run inference using pre-trained models from a PKL bundle."""
    rf = bundle["rf"]
    scaler_rf: StandardScaler = bundle["scaler_rf"]
    ridge = bundle["ridge"]
    scaler_ridge: RobustScaler = bundle["scaler_ridge"]
    gbm = bundle["gbm"]
    eval_rf: ModelEval = bundle["eval_rf"]
    eval_ridge: ModelEval = bundle["eval_ridge"]
    eval_gbm: ModelEval = bundle["eval_gbm"]

    x_latest_rf = scaler_rf.transform(x_latest_base)
    x_latest_ridge = np.clip(scaler_ridge.transform(x_latest_all), -3, 3)
    x_latest_gbm = x_latest_rf

    pred_rf    = float(rf.predict(x_latest_rf)[0]) + recent_trend
    pred_ridge = float(ridge.predict(x_latest_ridge)[0]) + recent_trend
    pred_gbm   = float(gbm.predict(x_latest_gbm)[0]) + recent_trend

    w_rf  = max(eval_rf.r2, 0.01)
    w_ri  = max(eval_ridge.r2, 0.01)
    w_gb  = max(eval_gbm.r2, 0.01)
    w_sum = w_rf + w_ri + w_gb
    ensemble_return = (pred_rf * w_rf + pred_ridge * w_ri + pred_gbm * w_gb) / w_sum
    ensemble_price  = round(current_price * (1 + ensemble_return), 2)

    tree_preds = np.array([t.predict(x_latest_rf)[0] + recent_trend for t in rf.estimators_])
    std_return = float(np.std(tree_preds))
    ci_low  = round(current_price * (1 + ensemble_return - 1.28 * std_return), 2)
    ci_high = round(current_price * (1 + ensemble_return + 1.28 * std_return), 2)

    preds_array = np.array([pred_rf, pred_ridge, pred_gbm])
    agreement_score = max(0.0, 100.0 - float(np.std(preds_array) * 1000))

    cv_scores = {"rf": eval_rf.cv_mae, "ridge": eval_ridge.cv_mae, "gbm": eval_gbm.cv_mae}
    best_model = min(cv_scores, key=cv_scores.get)

    fi = rf.feature_importances_
    feature_importances = sorted(
        [FeatureImportance(feature=_BASE_LABELS[i], importance=round(float(fi[i]), 4))
         for i in range(len(_BASE_FEATURES))],
        key=lambda x: x.importance,
        reverse=True,
    )

    def pct(v: float) -> float:
        return round(v * 100, 3)

    _record_mlops_metrics(symbol, horizon_days, bundle, from_pkl)

    return MLPredictionResponse(
        symbol=symbol,
        company_name=get_stock_name(symbol),
        current_price=round(current_price, 2),
        horizon_days=horizon_days,
        predictions={
            "rf":    ModelPrediction(predicted_return=pct(pred_rf),    predicted_price=round(current_price * (1 + pred_rf), 2)),
            "ridge": ModelPrediction(predicted_return=pct(pred_ridge),  predicted_price=round(current_price * (1 + pred_ridge), 2)),
            "gbm":   ModelPrediction(predicted_return=pct(pred_gbm),   predicted_price=round(current_price * (1 + pred_gbm), 2)),
        },
        evaluations={"rf": eval_rf, "ridge": eval_ridge, "gbm": eval_gbm},
        ensemble_return=pct(ensemble_return),
        ensemble_price=ensemble_price,
        ci_low=ci_low,
        ci_high=ci_high,
        model_agreement_score=round(agreement_score, 1),
        feature_importances=feature_importances,
        best_model=best_model,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def get_ml_prediction(symbol: str, horizon_days: int = 30) -> Optional[MLPredictionResponse]:
    cache_key = f"ml:regression:{symbol}_{horizon_days}"
    cached = _cache_mgr.get(cache_key)
    if cached is not None:
        return cached

    df = _get_cached_df(symbol, "2y")
    if df is None or len(df) < 120:
        logger.warning(f"ML regression: insufficient data for {symbol}")
        return None

    df = df.copy()
    df = _engineer_features(df)

    inputs = _prepare_inference_inputs(df, horizon_days)
    if inputs is None:
        return None
    current_price, x_latest_base, x_latest_all, recent_trend = inputs

    # ── Try loading today's trained bundle from disk (skip training) ──────────
    bundle = load_regression_bundle(symbol, horizon_days)
    if bundle is not None:
        result = _build_result_from_bundle(
            bundle, symbol, horizon_days,
            current_price, x_latest_base, x_latest_all, recent_trend,
            from_pkl=True,
        )
        _cache_mgr.set(cache_key, result, _ML_CACHE_TTL)
        return result

    # ── No bundle for today — train from scratch ──────────────────────────────
    # ── Current price & latest features (before target drops) ─────────────────
    x_latest_base = x_latest_base  # already computed above
    x_latest_all = x_latest_all

    # ── Rolling trend (20-day window of backward horizon-returns) ─────────────
    bret = df["close"].pct_change(horizon_days)
    df["trend"] = bret.rolling(_DEMEAN_WINDOW, min_periods=min(15, _DEMEAN_WINDOW)).mean().fillna(0.0)

    # ── Target: excess forward return ─────────────────────────────────────────
    df["target"] = df["close"].shift(-horizon_days) / df["close"] - 1 - df["trend"]
    df = df.dropna(subset=_ALL_FEATURES + ["target"])

    if len(df) < 80:
        return None

    X_base = df[_BASE_FEATURES].values.astype(float)
    X_all = df[_ALL_FEATURES].values.astype(float)
    y = df["target"].values.astype(float)

    # ── Model factories ───────────────────────────────────────────────────────
    def make_rf():
        return RandomForestRegressor(
            n_estimators=500, max_depth=2, min_samples_leaf=30,
            random_state=42, n_jobs=1)

    def make_ridge():
        return Ridge(alpha=100.0)

    def make_gbm():
        return GradientBoostingRegressor(
            n_estimators=100, max_depth=1, learning_rate=0.01,
            min_samples_leaf=20, subsample=0.7, random_state=42)

    # ── Walk-forward evaluation (per-model optimal pipeline) ──────────────────
    eval_rf = _walk_forward_eval(
        make_rf, X_base, y, horizon_days,
        scaler_cls=StandardScaler, winsorize=False)
    eval_ridge = _walk_forward_eval(
        make_ridge, X_all, y, horizon_days,
        scaler_cls=RobustScaler, winsorize=True)
    eval_gbm = _walk_forward_eval(
        make_gbm, X_base, y, horizon_days,
        scaler_cls=StandardScaler, winsorize=False)

    # ── Fit final models on ALL labelled data ─────────────────────────────────
    scaler_rf = StandardScaler()
    X_base_s = scaler_rf.fit_transform(X_base)
    x_latest_rf = scaler_rf.transform(x_latest_base)

    scaler_ridge = RobustScaler()
    X_all_s = scaler_ridge.fit_transform(X_all)
    X_all_s = np.clip(X_all_s, -3, 3)
    x_latest_ridge = np.clip(scaler_ridge.transform(x_latest_all), -3, 3)

    x_latest_gbm = x_latest_rf

    rf = make_rf();    rf.fit(X_base_s, y)
    ridge = make_ridge(); ridge.fit(X_all_s, y)
    gbm = make_gbm();  gbm.fit(X_base_s, y)

    # ── Save bundle to disk so today's subsequent calls skip training ─────────
    bundle = {
        "rf": rf, "scaler_rf": scaler_rf,
        "ridge": ridge, "scaler_ridge": scaler_ridge,
        "gbm": gbm,
        "eval_rf": eval_rf, "eval_ridge": eval_ridge, "eval_gbm": eval_gbm,
    }
    save_regression_bundle(symbol, horizon_days, bundle)

    result = _build_result_from_bundle(
        bundle, symbol, horizon_days,
        current_price, x_latest_base, x_latest_all, recent_trend,
        from_pkl=False,
    )
    _cache_mgr.set(cache_key, result, _ML_CACHE_TTL)
    return result
