"""
Risk metrics and anomaly detection.

Extracted from analytics.py. Stateless computations on price DataFrames.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from ..schemas.analytics import (
    RiskMetrics, AnomalyAlert, AnomalyType, AnomalySeverity,
    CorrelationMatrix, CorrelationPair,
)

logger = logging.getLogger(__name__)

RISK_FREE_RATE = 0.065  # Indian 10-yr gilt


def compute_risk_metrics(
    symbol: str, df: pd.DataFrame, nifty_df: Optional[pd.DataFrame]
) -> RiskMetrics:
    returns = df["daily_return"].dropna()
    ann_return = float(returns.mean() * 252)
    ann_vol = float(returns.std() * np.sqrt(252))

    sharpe = (ann_return - RISK_FREE_RATE) / ann_vol if ann_vol > 0 else 0.0
    neg_ret = returns[returns < 0]
    down_vol = float(neg_ret.std() * np.sqrt(252)) if len(neg_ret) > 1 else ann_vol
    sortino = (ann_return - RISK_FREE_RATE) / down_vol if down_vol > 0 else 0.0

    cum = (1 + returns).cumprod()
    roll_max = cum.cummax()
    drawdown = (cum - roll_max) / roll_max
    max_dd = float(drawdown.min()) * 100

    var_95 = float(np.percentile(returns, 5)) * 100

    beta, alpha = 1.0, 0.0
    if nifty_df is not None and not nifty_df.empty and "daily_return" in nifty_df.columns:
        stock_s = df.set_index("date")["daily_return"].dropna()
        nifty_s = nifty_df.set_index("date")["daily_return"].dropna()
        common = stock_s.index.intersection(nifty_s.index)
        if len(common) > 30:
            s_vals = stock_s[common].values
            n_vals = nifty_s[common].values
            cov_mat = np.cov(s_vals, n_vals)
            if cov_mat[1, 1] > 0:
                beta = float(cov_mat[0, 1] / cov_mat[1, 1])
            nifty_ann = float(n_vals.mean() * 252)
            alpha = (ann_return - (RISK_FREE_RATE + beta * (nifty_ann - RISK_FREE_RATE))) * 100

    return RiskMetrics(
        symbol=symbol,
        sharpe_ratio=round(sharpe, 3),
        sortino_ratio=round(sortino, 3),
        max_drawdown=round(max_dd, 2),
        var_95=round(var_95, 3),
        beta=round(beta, 3),
        volatility=round(ann_vol * 100, 2),
        alpha=round(alpha, 2),
        annualized_return=round(ann_return * 100, 2),
    )


def detect_anomalies(symbol: str, df: pd.DataFrame) -> list[AnomalyAlert]:
    alerts: list[AnomalyAlert] = []
    if len(df) < 60:
        return alerts

    recent = df.iloc[-60:].copy()
    recent["abs_return"] = recent["daily_return"].abs()

    # Volume z-score
    vol_mean, vol_std = recent["volume"].mean(), recent["volume"].std()
    last_vol = recent["volume"].iloc[-1]
    vol_z = (last_vol - vol_mean) / vol_std if vol_std > 0 else 0.0
    if abs(vol_z) > 2.5:
        sev = AnomalySeverity.HIGH if abs(vol_z) > 3.5 else AnomalySeverity.MEDIUM
        alerts.append(AnomalyAlert(
            symbol=symbol, anomaly_type=AnomalyType.VOLUME_SPIKE, severity=sev,
            z_score=round(float(vol_z), 2),
            description=f"Unusual volume: {abs(vol_z):.1f}σ from 60-day mean",
        ))

    # Return z-score
    ret_mean, ret_std = recent["abs_return"].mean(), recent["abs_return"].std()
    last_ret = recent["abs_return"].iloc[-1]
    ret_z = (last_ret - ret_mean) / ret_std if ret_std > 0 else 0.0
    if abs(ret_z) > 2.5:
        sev = AnomalySeverity.HIGH if abs(ret_z) > 3.5 else AnomalySeverity.MEDIUM
        alerts.append(AnomalyAlert(
            symbol=symbol, anomaly_type=AnomalyType.PRICE_SPIKE, severity=sev,
            z_score=round(float(ret_z), 2),
            description=f"Unusual price move: {abs(ret_z):.1f}σ from 60-day mean",
        ))

    # IsolationForest
    try:
        feat_df = recent[["daily_return", "vol_ratio", "bb_width"]].dropna()
        if len(feat_df) >= 20:
            arr = feat_df.values
            iso = IsolationForest(contamination=0.05, random_state=42)
            preds = iso.fit_predict(arr)
            scores = iso.decision_function(arr)
            for i in range(-5, 0):
                if preds[i] == -1 and scores[i] < -0.15:
                    sev = AnomalySeverity.HIGH if scores[i] < -0.25 else AnomalySeverity.MEDIUM
                    alerts.append(AnomalyAlert(
                        symbol=symbol, anomaly_type=AnomalyType.ISOLATION_FOREST, severity=sev,
                        z_score=round(float(abs(scores[i]) * 10), 2),
                        description=f"IsolationForest anomaly (score={scores[i]:.3f})",
                    ))
                    break
    except Exception as exc:
        logger.debug("IsolationForest skipped for %s: %s", symbol, exc)

    return alerts


def compute_correlation_matrix(symbols: list[str]) -> CorrelationMatrix:
    from .market_data import get_price_df

    series_list: list[pd.Series] = []
    valid: list[str] = []

    for sym in symbols:
        df = get_price_df(sym, "1y")
        if df is not None and len(df) > 50:
            s = df.set_index("date")["daily_return"].dropna()
            s.name = sym
            series_list.append(s)
            valid.append(sym)

    if len(valid) < 2:
        return CorrelationMatrix(symbols=[], matrix=[], high_correlation_pairs=[])

    rets_df = pd.concat(series_list, axis=1).dropna()
    corr = rets_df.corr()
    n = len(valid)
    matrix = [[round(float(corr.iloc[i, j]), 3) for j in range(n)] for i in range(n)]

    pairs = [
        CorrelationPair(symbol1=valid[i], symbol2=valid[j], correlation=round(float(corr.iloc[i, j]), 3))
        for i in range(n)
        for j in range(i + 1, n)
        if abs(float(corr.iloc[i, j])) > 0.8
    ]

    return CorrelationMatrix(symbols=valid, matrix=matrix, high_correlation_pairs=pairs)
