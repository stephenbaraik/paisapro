"""
ML Regression — robust multi-model return forecasting for OHLC financial data.

Design principles (Lopez de Prado / AQR style):
  ─ Log-return target: more Gaussian, additive, heteroscedasticity-corrected
  ─ Vol-adjusted target: divide by rolling realised vol → Sharpe-signal target
  ─ Rolling-window walk-forward CV (max 2y lookback) + embargo to eliminate
    label leakage between train and test sets
  ─ OHLC-specific features capture intraday microstructure (candle body, wicks,
    overnight gaps, range) which close-only indicators miss
  ─ Feature set split: trees use all features uncorrelated via max_features='sqrt';
    ElasticNet uses full set + winsorisation to handle correlated inputs
  ─ Bundle versioning: changing _BUNDLE_VERSION forces retrain on next call,
    old PKLs are silently discarded

Models:
  1. Random Forest          — OHLC + base features, max_features='sqrt'
  2. ElasticNet             — all features, RobustScaler + winsorise (l1+l2)
  3. HistGradientBoosting   — OHLC + base features, early stopping

Evaluation per model (walk-forward OOS):
  ─ MAE / RMSE / R²
  ─ Directional accuracy (sign hit rate)
  ─ Signal Sharpe ratio  (annualised Sharpe of long/short strategy on predictions)

Ensemble: Sharpe-weighted average (upweight models that produce tradeable signals).
Confidence interval: ±1.28 σ from RF tree distribution (80% CI).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import ElasticNet
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

from ..core.cache import cache as _cache_mgr

_ML_CACHE_TTL  = 3600   # 1 hour — re-infer with fresh prices
_MLOPS_TTL     = 86400  # 24 h — survive daily restarts

# ── Bundle versioning ─────────────────────────────────────────────────────────
# Bump this whenever features / target / model architecture changes.
# Old PKLs are silently invalidated and models retrain once.
_BUNDLE_VERSION = "v3-ohlc-log-sharpe"

# ── Feature lists ─────────────────────────────────────────────────────────────

# 1. OHLC microstructure features (new — use open/high/low)
_OHLC_FEATURES = [
    "hl_pct",           # (high-low)/close — intraday range / daily volatility
    "oc_ret",           # (close-open)/open — intraday direction (bull/bear candle)
    "body_pct",         # |close-open|/(high-low) — candle body strength (0=doji, 1=marubozu)
    "upper_wick",       # (high - max(c,o))/(high-low) — selling pressure at top
    "lower_wick",       # (min(c,o) - low)/(high-low) — buying support at bottom
    "gap",              # (open - prev_close)/prev_close — overnight gap
    "dist_52w_high",    # (rolling_max_252 - close)/close — distance from year high
    "dist_52w_low",     # (close - rolling_min_252)/close — distance from year low
    "williams_r_14",    # Williams %R(14) — overbought/oversold relative to range
    "channel_pos_20",   # (close - low_20d)/(high_20d - low_20d) — Donchian position
]

# 2. Close-price technical indicators (from add_indicators)
_BASE_FEATURES = [
    "rsi_14", "macd", "macd_signal", "bb_width", "vol_ratio",
    "price_vs_sma20", "price_vs_sma50", "return_5d", "return_20d", "atr_normalized",
]

# 3. Derived / engineered features
_EXTRA_FEATURES = [
    "rsi_14_ma10", "macd_hist", "return_10d", "return_60d", "momentum_accel",
    "log_vol_20d", "vol_ratio_20_60", "bb_position", "sma_spread",
    "price_vs_sma200", "rsi_roc", "vol_ratio_ma5",
]

# Tree models use OHLC + base (decorrelated via max_features='sqrt')
_TREE_FEATURES = _OHLC_FEATURES + _BASE_FEATURES          # 20 features
# Linear model uses everything (regularisation handles collinearity)
_ALL_FEATURES  = _OHLC_FEATURES + _BASE_FEATURES + _EXTRA_FEATURES  # 32 features

_TREE_LABELS = [
    # OHLC
    "HL Range %", "Intraday Return", "Candle Body", "Upper Wick", "Lower Wick",
    "Overnight Gap", "Dist 52w High", "Dist 52w Low", "Williams %R", "Channel Pos 20d",
    # Base technical
    "RSI-14", "MACD", "MACD Signal", "BB Width", "Volume Ratio",
    "Price/SMA20", "Price/SMA50", "Return 5d", "Return 20d", "ATR Norm",
]

_MIN_TRAIN   = 200    # minimum rows before first CV fold
_ROLL_WINDOW = 500    # max rows in rolling train window (~2 trading years)
_DEMEAN_WIN  = 20     # rolling window for trend removal


# ── OHLC feature engineering ─────────────────────────────────────────────────

def _add_ohlc_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add microstructure features from open/high/low/close. In-place."""
    c  = df["close"]
    o  = df["open"]
    h  = df["high"]
    l  = df["low"]
    rng = (h - l).replace(0, np.nan)

    df["hl_pct"]       = rng / c
    df["oc_ret"]       = (c - o) / o.replace(0, np.nan)
    df["body_pct"]     = (c - o).abs() / rng
    df["upper_wick"]   = (h - np.maximum(c, o)) / rng
    df["lower_wick"]   = (np.minimum(c, o) - l) / rng
    df["gap"]          = (o - c.shift(1)) / c.shift(1).replace(0, np.nan)

    high_252 = c.rolling(252, min_periods=100).max()
    low_252  = c.rolling(252, min_periods=100).min()
    df["dist_52w_high"] = (high_252 - c) / c.replace(0, np.nan)
    df["dist_52w_low"]  = (c - low_252) / c.replace(0, np.nan)

    h14 = h.rolling(14, min_periods=7).max()
    l14 = l.rolling(14, min_periods=7).min()
    df["williams_r_14"] = (h14 - c) / (h14 - l14).replace(0, np.nan)

    h20 = h.rolling(20, min_periods=10).max()
    l20 = l.rolling(20, min_periods=10).min()
    df["channel_pos_20"] = (c - l20) / (h20 - l20).replace(0, np.nan)

    return df


def _add_extra_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived close/volume features. In-place."""
    close = df["close"]

    df["rsi_14_ma10"]   = df["rsi_14"].rolling(10, min_periods=5).mean()
    df["macd_hist"]     = df["macd_histogram"]
    df["return_10d"]    = close.pct_change(10)
    df["return_60d"]    = close.pct_change(60)
    df["momentum_accel"] = df["return_20d"] - df["return_5d"]

    daily_log = np.log(close / close.shift(1).replace(0, np.nan))
    vol_20  = daily_log.rolling(20, min_periods=10).std() * np.sqrt(252)
    vol_60  = daily_log.rolling(60, min_periods=30).std() * np.sqrt(252)
    df["log_vol_20d"]    = np.log(vol_20 + 1e-9)           # log-vol is more normal
    df["vol_ratio_20_60"] = vol_20 / vol_60.replace(0, np.nan)

    bb_range = (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
    df["bb_position"]    = (close - df["bb_lower"]) / bb_range
    df["sma_spread"]     = (df["sma_20"] - df["sma_50"]) / close
    df["price_vs_sma200"] = (close / df["sma_200"]) - 1
    df["rsi_roc"]        = df["rsi_14"].diff(5)
    df["vol_ratio_ma5"]  = df["vol_ratio"].rolling(5, min_periods=3).mean()

    return df


# ── Target construction ───────────────────────────────────────────────────────

def _build_target(df: pd.DataFrame, horizon_days: int) -> pd.Series:
    """
    Vol-adjusted log return — the most robust financial regression target.

    target = log(close[t+h] / close[t]) / realised_vol[t] - rolling_trend[t]

    Dividing by vol makes the target stationary across different volatility
    regimes (high-vol periods otherwise dominate the loss function).
    Subtracting the rolling trend removes the drift component.
    """
    close = df["close"]
    log_fwd = np.log(close.shift(-horizon_days) / close.replace(0, np.nan))

    # Realised vol (annualised log-return std, 20-day)
    daily_log = np.log(close / close.shift(1).replace(0, np.nan))
    rvol = daily_log.rolling(20, min_periods=10).std() * np.sqrt(252 / horizon_days)
    rvol = rvol.replace(0, np.nan).fillna(method="ffill").fillna(0.01)

    vol_adj = log_fwd / rvol

    # Rolling trend (20-day mean of backward horizon returns, vol-adjusted)
    log_bwd   = np.log(close / close.shift(horizon_days).replace(0, np.nan))
    trend_raw = (log_bwd / rvol).rolling(_DEMEAN_WIN, min_periods=min(10, _DEMEAN_WIN)).mean()
    return (vol_adj - trend_raw).fillna(np.nan)


def _recent_trend_and_vol(df: pd.DataFrame, horizon_days: int) -> tuple[float, float]:
    """
    Return (rolling_trend, realised_vol) for the most recent row.
    Used at inference to reconstruct the absolute return from the vol-adjusted prediction.
    """
    close = df["close"]
    daily_log = np.log(close / close.shift(1).replace(0, np.nan))
    rvol = daily_log.rolling(20, min_periods=10).std() * np.sqrt(252 / horizon_days)
    rvol = rvol.replace(0, np.nan).fillna(method="ffill").fillna(0.01)

    log_bwd   = np.log(close / close.shift(horizon_days).replace(0, np.nan))
    trend_raw = (log_bwd / rvol).rolling(_DEMEAN_WIN, min_periods=min(10, _DEMEAN_WIN)).mean()

    latest_vol   = float(rvol.iloc[-1]) if not rvol.empty else 0.01
    latest_trend = float(trend_raw.iloc[-1]) if not trend_raw.empty else 0.0
    if np.isnan(latest_trend):
        latest_trend = 0.0
    return latest_trend, latest_vol


# ── Walk-forward cross-validation ────────────────────────────────────────────

def _walk_forward_eval(
    model_factory: Callable,
    X: np.ndarray,
    y: np.ndarray,
    horizon_days: int,
    scaler_cls=StandardScaler,
    winsorize: bool = False,
    min_train: int = _MIN_TRAIN,
    roll_window: int = _ROLL_WINDOW,
    step: int | None = None,
) -> ModelEval:
    """
    Rolling-window walk-forward CV with embargo.

    - Rolling window: train only on the most recent `roll_window` rows before
      the test period (recent regime is more predictive than 5-year-old data).
    - Embargo: skip `embargo = horizon_days // 2` rows between train end and
      test start to ensure no label overlap (forward-looking targets).
    """
    if step is None:
        step = max(horizon_days, 20)

    embargo = horizon_days // 2
    n = len(X)

    all_preds:   list[float] = []
    all_actuals: list[float] = []

    t = min_train
    while t + step <= n:
        test_start = t + embargo           # skip embargo rows after train end
        test_end   = test_start + step
        if test_end > n:
            break

        train_end  = t
        train_start = max(0, train_end - roll_window)

        X_tr = X[train_start:train_end]
        y_tr = y[train_start:train_end]
        X_te = X[test_start:test_end]
        y_te = y[test_start:test_end]

        # Skip folds with NaN targets
        mask_tr = np.isfinite(y_tr)
        mask_te = np.isfinite(y_te)
        if mask_tr.sum() < 40 or mask_te.sum() < 5:
            t += step
            continue

        scaler = scaler_cls()
        X_tr_s = scaler.fit_transform(X_tr[mask_tr])
        X_te_s = scaler.transform(X_te[mask_te])

        if winsorize:
            X_tr_s = np.clip(X_tr_s, -3, 3)
            X_te_s = np.clip(X_te_s, -3, 3)

        model = model_factory()
        model.fit(X_tr_s, y_tr[mask_tr])
        preds = model.predict(X_te_s)

        all_preds.extend(preds.tolist())
        all_actuals.extend(y_te[mask_te].tolist())
        t += step

    ap = np.array(all_preds)
    aa = np.array(all_actuals)

    if len(ap) < 10:
        # Fallback: single purged split (no rolling, just 80/20)
        split = int(n * 0.8)
        test_start = split + embargo
        if test_start >= n:
            return ModelEval(mae=99.0, rmse=99.0, r2=-1.0, directional_accuracy=50.0,
                             cv_mae=99.0, sharpe_ratio=0.0)
        scaler = scaler_cls()
        X_tr_s = scaler.fit_transform(X[:split])
        X_te_s = scaler.transform(X[test_start:])
        if winsorize:
            X_tr_s = np.clip(X_tr_s, -3, 3)
            X_te_s = np.clip(X_te_s, -3, 3)
        model = model_factory()
        mask = np.isfinite(y[:split])
        if mask.sum() < 30:
            return ModelEval(mae=99.0, rmse=99.0, r2=-1.0, directional_accuracy=50.0,
                             cv_mae=99.0, sharpe_ratio=0.0)
        model.fit(X_tr_s[mask], y[:split][mask])
        ap = model.predict(X_te_s)
        aa = y[test_start:]
        fin = np.isfinite(aa)
        ap, aa = ap[fin], aa[fin]

    if len(ap) < 5:
        return ModelEval(mae=99.0, rmse=99.0, r2=-1.0, directional_accuracy=50.0,
                         cv_mae=99.0, sharpe_ratio=0.0)

    mae      = float(mean_absolute_error(aa, ap))
    rmse     = float(np.sqrt(mean_squared_error(aa, ap)))
    r2       = float(r2_score(aa, ap))
    dir_acc  = float(np.mean(np.sign(ap) == np.sign(aa))) * 100

    # Signal Sharpe: long when pred>0, short when pred<0 — applied to actual returns
    # The target is vol-adjusted, so signal_pnl ~ 1 when right, -1 when wrong
    signal_pnl = np.sign(ap) * aa
    pnl_mean   = float(np.mean(signal_pnl))
    pnl_std    = float(np.std(signal_pnl)) + 1e-9
    # Annualise: multiply by sqrt(252 / step) where step ≈ avg holding period
    ann_sharpe = pnl_mean / pnl_std * float(np.sqrt(max(252 / max(step, 1), 1)))

    return ModelEval(
        mae=round(mae * 100, 4),
        rmse=round(rmse * 100, 4),
        r2=round(r2, 4),
        directional_accuracy=round(dir_acc, 2),
        cv_mae=round(mae * 100, 4),
        sharpe_ratio=round(ann_sharpe, 3),
    )


# ── Inference helpers ─────────────────────────────────────────────────────────

def _prepare_inference_inputs(
    df: pd.DataFrame, horizon_days: int
) -> tuple[float, np.ndarray, np.ndarray, float, float] | None:
    """
    Extract current-state feature vectors and recent_trend/vol for inference.
    Returns (current_price, x_tree, x_all, recent_trend, recent_vol) or None.
    """
    df_feat = df.dropna(subset=_ALL_FEATURES)
    if len(df_feat) < 80:
        return None

    current_price  = float(df_feat["close"].iloc[-1])
    x_tree = df_feat[_TREE_FEATURES].iloc[-1:].values.astype(float)
    x_all  = df_feat[_ALL_FEATURES].iloc[-1:].values.astype(float)

    recent_trend, recent_vol = _recent_trend_and_vol(df_feat, horizon_days)
    return current_price, x_tree, x_all, recent_trend, recent_vol


def _vol_adj_to_simple_return(pred_vol_adj: float, recent_trend: float, recent_vol: float,
                               horizon_days: int) -> float:
    """
    Convert a vol-adjusted log-return prediction back to a simple price return.

    pred_vol_adj is the model output in vol-normalised space.
    Denormalise: log_return = (pred_vol_adj + recent_trend) * recent_vol
    Convert log → simple: simple_return = exp(log_return) - 1
    """
    log_return = (pred_vol_adj + recent_trend) * recent_vol
    return float(np.exp(log_return) - 1)


# ── MLOps metric collection ───────────────────────────────────────────────────

def _record_mlops_metrics(symbol: str, horizon_days: int, bundle: dict,
                          from_pkl: bool) -> None:
    cv_maes = {m: bundle[f"eval_{m}"].cv_mae for m in ("rf", "ridge", "gbm")}
    _cache_mgr.set(f"mlops:reg:{symbol}_{horizon_days}", {
        "symbol": symbol, "horizon_days": horizon_days,
        "rf_r2":          bundle["eval_rf"].r2,
        "rf_dir_acc":     bundle["eval_rf"].directional_accuracy,
        "rf_mae":         bundle["eval_rf"].mae,
        "rf_sharpe":      bundle["eval_rf"].sharpe_ratio,
        "ridge_r2":       bundle["eval_ridge"].r2,
        "ridge_dir_acc":  bundle["eval_ridge"].directional_accuracy,
        "ridge_mae":      bundle["eval_ridge"].mae,
        "ridge_sharpe":   bundle["eval_ridge"].sharpe_ratio,
        "gbm_r2":         bundle["eval_gbm"].r2,
        "gbm_dir_acc":    bundle["eval_gbm"].directional_accuracy,
        "gbm_mae":        bundle["eval_gbm"].mae,
        "gbm_sharpe":     bundle["eval_gbm"].sharpe_ratio,
        "best_model":     min(cv_maes, key=cv_maes.get),
        "from_pkl":       from_pkl,
        "evaluated_at":   datetime.now(timezone.utc).isoformat(),
    }, _MLOPS_TTL)


# ── Build response from bundle ────────────────────────────────────────────────

def _build_result_from_bundle(
    bundle: dict,
    symbol: str,
    horizon_days: int,
    current_price: float,
    x_tree: np.ndarray,
    x_all: np.ndarray,
    recent_trend: float,
    recent_vol: float,
    from_pkl: bool = False,
) -> MLPredictionResponse:
    """Run inference using pre-trained models from a PKL bundle."""
    rf         = bundle["rf"]
    scaler_rf  = bundle["scaler_rf"]
    enet       = bundle["ridge"]          # stored as "ridge" for schema compat
    scaler_enet = bundle["scaler_ridge"]
    gbm        = bundle["gbm"]
    eval_rf    = bundle["eval_rf"]
    eval_ridge = bundle["eval_ridge"]
    eval_gbm   = bundle["eval_gbm"]

    x_tree_s = scaler_rf.transform(x_tree)
    x_all_s  = np.clip(scaler_enet.transform(x_all), -3, 3)

    pred_rf_va    = float(rf.predict(x_tree_s)[0])
    pred_ridge_va = float(enet.predict(x_all_s)[0])
    pred_gbm_va   = float(gbm.predict(x_tree_s)[0])

    # Convert vol-adjusted predictions back to simple returns
    pred_rf    = _vol_adj_to_simple_return(pred_rf_va,    recent_trend, recent_vol, horizon_days)
    pred_ridge = _vol_adj_to_simple_return(pred_ridge_va, recent_trend, recent_vol, horizon_days)
    pred_gbm   = _vol_adj_to_simple_return(pred_gbm_va,   recent_trend, recent_vol, horizon_days)

    # Sharpe-weighted ensemble (upweight models that produce tradeable signals)
    w_rf  = max(eval_rf.sharpe_ratio,    0.01)
    w_ri  = max(eval_ridge.sharpe_ratio, 0.01)
    w_gb  = max(eval_gbm.sharpe_ratio,   0.01)
    w_sum = w_rf + w_ri + w_gb
    ensemble_return = (pred_rf * w_rf + pred_ridge * w_ri + pred_gbm * w_gb) / w_sum
    ensemble_price  = round(current_price * (1 + ensemble_return), 2)

    # 80% CI from RF tree variance (in vol-adj space, then convert)
    tree_preds_va = np.array([t.predict(x_tree_s)[0] for t in rf.estimators_])
    std_va = float(np.std(tree_preds_va))
    ci_low_ret  = _vol_adj_to_simple_return(pred_rf_va - 1.28 * std_va,
                                            recent_trend, recent_vol, horizon_days)
    ci_high_ret = _vol_adj_to_simple_return(pred_rf_va + 1.28 * std_va,
                                            recent_trend, recent_vol, horizon_days)
    ci_low  = round(current_price * (1 + ci_low_ret), 2)
    ci_high = round(current_price * (1 + ci_high_ret), 2)

    # Model agreement (normalised by vol level so it's meaningful across stocks)
    preds_arr = np.array([pred_rf, pred_ridge, pred_gbm])
    vol_scale = abs(ensemble_return) + 1e-6
    agreement_score = max(0.0, 100.0 - float(np.std(preds_arr) / vol_scale * 10))

    cv_scores = {"rf": eval_rf.cv_mae, "ridge": eval_ridge.cv_mae, "gbm": eval_gbm.cv_mae}
    best_model = min(cv_scores, key=cv_scores.get)

    # Feature importances from RF (tree-feature set only)
    fi = rf.feature_importances_
    feature_importances = sorted(
        [FeatureImportance(feature=_TREE_LABELS[i], importance=round(float(fi[i]), 4))
         for i in range(len(_TREE_FEATURES))],
        key=lambda x: x.importance, reverse=True,
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
            "rf":    ModelPrediction(predicted_return=pct(pred_rf),
                                     predicted_price=round(current_price * (1 + pred_rf), 2)),
            "ridge": ModelPrediction(predicted_return=pct(pred_ridge),
                                     predicted_price=round(current_price * (1 + pred_ridge), 2)),
            "gbm":   ModelPrediction(predicted_return=pct(pred_gbm),
                                     predicted_price=round(current_price * (1 + pred_gbm), 2)),
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


# ── Main entrypoint ───────────────────────────────────────────────────────────

def get_ml_prediction(symbol: str, horizon_days: int = 30) -> Optional[MLPredictionResponse]:
    cache_key = f"ml:regression:{symbol}_{horizon_days}"
    cached = _cache_mgr.get(cache_key)
    if cached is not None:
        return cached

    df = _get_cached_df(symbol, "2y")
    if df is None or len(df) < 150:
        logger.warning("ML regression: insufficient data for %s (%s rows)",
                       symbol, len(df) if df is not None else 0)
        return None

    df = df.copy()
    _add_ohlc_features(df)
    _add_extra_features(df)

    inputs = _prepare_inference_inputs(df, horizon_days)
    if inputs is None:
        return None
    current_price, x_tree, x_all, recent_trend, recent_vol = inputs

    # ── Try PKL bundle from today (skip training) ─────────────────────────────
    bundle = load_regression_bundle(symbol, horizon_days)
    if bundle is not None and bundle.get("_version") == _BUNDLE_VERSION:
        result = _build_result_from_bundle(
            bundle, symbol, horizon_days,
            current_price, x_tree, x_all, recent_trend, recent_vol,
            from_pkl=True,
        )
        _cache_mgr.set(cache_key, result, _ML_CACHE_TTL)
        return result

    # ── Train from scratch ────────────────────────────────────────────────────
    df["target"] = _build_target(df, horizon_days)
    df_clean = df.dropna(subset=_ALL_FEATURES + ["target"])

    if len(df_clean) < 100:
        return None

    X_tree = df_clean[_TREE_FEATURES].values.astype(float)
    X_all  = df_clean[_ALL_FEATURES].values.astype(float)
    y      = df_clean["target"].values.astype(float)

    # ── Model factories ───────────────────────────────────────────────────────

    def make_rf():
        # max_features='sqrt' → trees are decorrelated → lower variance ensemble
        # max_depth=4 gives more expressive power than 2, but min_samples_leaf=25
        # acts as the main regulariser
        return RandomForestRegressor(
            n_estimators=200, max_depth=4, max_features="sqrt",
            min_samples_leaf=25, bootstrap=True, random_state=42, n_jobs=1,
        )

    def make_enet():
        # l1_ratio=0.1 → mostly Ridge (l2) with slight Lasso (l1) sparsity
        # RobustScaler + winsorise handles fat tails in financial features
        return ElasticNet(alpha=0.01, l1_ratio=0.1, max_iter=5000, random_state=42)

    def make_gbm():
        # HistGradientBoostingRegressor: native NaN support, early stopping,
        # much faster than GradientBoostingRegressor, similar to LightGBM
        return HistGradientBoostingRegressor(
            max_iter=300, learning_rate=0.03, max_depth=3,
            min_samples_leaf=20, l2_regularization=1.0,
            early_stopping=True, validation_fraction=0.15,
            n_iter_no_change=20, random_state=42,
        )

    # ── Walk-forward evaluation ───────────────────────────────────────────────
    eval_rf = _walk_forward_eval(
        make_rf, X_tree, y, horizon_days,
        scaler_cls=StandardScaler, winsorize=False,
    )
    eval_ridge = _walk_forward_eval(
        make_enet, X_all, y, horizon_days,
        scaler_cls=RobustScaler, winsorize=True,
    )
    eval_gbm = _walk_forward_eval(
        make_gbm, X_tree, y, horizon_days,
        scaler_cls=StandardScaler, winsorize=False,
    )

    # ── Fit final models on all labelled data ─────────────────────────────────
    scaler_rf = StandardScaler()
    X_tree_s = scaler_rf.fit_transform(X_tree)
    x_tree_s = scaler_rf.transform(x_tree)

    scaler_enet = RobustScaler()
    X_all_s = np.clip(scaler_enet.fit_transform(X_all), -3, 3)

    # Final GBM: fit on full data (no early stopping on final model)
    gbm_final = HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.03, max_depth=3,
        min_samples_leaf=20, l2_regularization=1.0,
        early_stopping=False, random_state=42,
    )

    rf = make_rf()
    rf.fit(X_tree_s, y)

    enet = make_enet()
    enet.fit(X_all_s, y)

    gbm_final.fit(X_tree_s, y)

    bundle = {
        "_version": _BUNDLE_VERSION,
        "rf": rf, "scaler_rf": scaler_rf,
        "ridge": enet, "scaler_ridge": scaler_enet,
        "gbm": gbm_final,
        "eval_rf": eval_rf, "eval_ridge": eval_ridge, "eval_gbm": eval_gbm,
    }
    save_regression_bundle(symbol, horizon_days, bundle)

    result = _build_result_from_bundle(
        bundle, symbol, horizon_days,
        current_price, x_tree, x_all, recent_trend, recent_vol,
        from_pkl=False,
    )
    _cache_mgr.set(cache_key, result, _ML_CACHE_TTL)
    return result
