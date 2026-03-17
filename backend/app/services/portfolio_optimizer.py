"""
Portfolio optimization — Monte Carlo simulation + scipy SLSQP.

Extracted from analytics.py. Produces min-variance, max-Sharpe,
and risk-profile-targeted portfolio weights.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from ..schemas.analytics import (
    PortfolioOptimizationResult, PortfolioStats,
    EfficientFrontierPoint,
)

RISK_FREE_RATE = 0.065


def optimize_portfolio(
    symbols: list[str],
    risk_profile: str = "moderate",
    n_portfolios: int = 2000,
) -> Optional[PortfolioOptimizationResult]:
    from .market_data import get_price_df

    series_list: list[pd.Series] = []
    valid: list[str] = []

    for sym in symbols:
        df = get_price_df(sym, "2y")
        if df is not None and len(df) > 50:
            s = df.set_index("date")["daily_return"].dropna()
            s.name = sym
            series_list.append(s)
            valid.append(sym)

    if len(valid) < 2:
        return None

    rets_df = pd.concat(series_list, axis=1).dropna()
    n = len(valid)
    mu = rets_df.mean().values * 252
    cov = rets_df.cov().values * 252

    # Monte Carlo simulation
    mc: list[dict] = []
    for _ in range(n_portfolios):
        w = np.random.dirichlet(np.ones(n))
        r = float(w @ mu)
        v = float(np.sqrt(w @ cov @ w))
        sh = (r - RISK_FREE_RATE) / v if v > 0 else 0.0
        mc.append({"vol": v, "ret": r, "sharpe": sh, "w": w})

    def port_vol(w: np.ndarray) -> float:
        return float(np.sqrt(w @ cov @ w))

    def neg_sharpe(w: np.ndarray) -> float:
        r = float(w @ mu)
        v = port_vol(w)
        return -(r - RISK_FREE_RATE) / v if v > 0 else 0.0

    cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bnds = [(0.0, 1.0)] * n
    w0 = np.ones(n) / n

    res_minv = minimize(port_vol, w0, method="SLSQP", bounds=bnds, constraints=cons)
    res_maxs = minimize(neg_sharpe, w0, method="SLSQP", bounds=bnds, constraints=cons)

    def w_to_dict(w_arr: np.ndarray) -> dict[str, float]:
        return {sym: round(float(w), 4) for sym, w in zip(valid, w_arr)}

    min_var_w = w_to_dict(res_minv.x if res_minv.success else w0)
    max_shr_w = w_to_dict(res_maxs.x if res_maxs.success else w0)

    target_vols = {"conservative": 0.12, "moderate": 0.18, "aggressive": 0.25}
    tv = target_vols.get(risk_profile, 0.18)

    def vol_dist(w: np.ndarray) -> float:
        return (port_vol(w) - tv) ** 2

    res_rp = minimize(vol_dist, w0, method="SLSQP", bounds=bnds, constraints=cons)
    rp_w = w_to_dict(res_rp.x if res_rp.success else w0)

    # Efficient frontier from MC results
    all_vols = [p["vol"] for p in mc]
    v_bins = np.linspace(min(all_vols), max(all_vols), 51)
    frontier: list[EfficientFrontierPoint] = []
    for i in range(50):
        bucket = [p for p in mc if v_bins[i] <= p["vol"] < v_bins[i + 1]]
        if bucket:
            best = max(bucket, key=lambda p: p["ret"])
            frontier.append(EfficientFrontierPoint(
                vol=round(best["vol"] * 100, 2),
                ret=round(best["ret"] * 100, 2),
                sharpe=round(best["sharpe"], 3),
            ))

    corr = rets_df.corr()
    corr_matrix = [[round(float(corr.iloc[i, j]), 3) for j in range(n)] for i in range(n)]

    def port_stats(wd: dict) -> PortfolioStats:
        w = np.array([wd[s] for s in valid])
        r = float(w @ mu) * 100
        v = port_vol(w) * 100
        sh = (r / 100 - RISK_FREE_RATE) / (v / 100) if v > 0 else 0.0
        return PortfolioStats(expected_return=round(r, 2), volatility=round(v, 2), sharpe=round(sh, 3))

    mc_out = [
        EfficientFrontierPoint(
            vol=round(p["vol"] * 100, 2),
            ret=round(p["ret"] * 100, 2),
            sharpe=round(p["sharpe"], 3),
        )
        for p in mc[:500]
    ]

    return PortfolioOptimizationResult(
        symbols=valid,
        min_variance_weights=min_var_w,
        max_sharpe_weights=max_shr_w,
        risk_profile_weights=rp_w,
        risk_profile=risk_profile,
        efficient_frontier=frontier,
        correlation_matrix=corr_matrix,
        mc_results=mc_out,
        min_variance_stats=port_stats(min_var_w),
        max_sharpe_stats=port_stats(max_shr_w),
        risk_profile_stats=port_stats(rp_w),
    )
