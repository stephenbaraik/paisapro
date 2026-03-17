"""
Strategy backtesting — technical signal strategy vs Nifty 50 benchmark.

Extracted from analytics.py.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..schemas.analytics import BacktestResult, EquityPoint
from .universe import NIFTY_INDEX

RISK_FREE_RATE = 0.065


def backtest_strategy(symbol: str) -> BacktestResult:
    from .market_data import get_price_df

    df = get_price_df(symbol, "2y")
    nifty_df = get_price_df(NIFTY_INDEX, "2y")

    _empty = BacktestResult(
        symbol=symbol, equity_curve=[], total_return=0.0,
        benchmark_return=0.0, alpha=0.0, sharpe_ratio=0.0,
        num_trades=0, win_rate=0.0,
    )

    if df is None or len(df) < 100:
        return _empty

    df = df.copy()

    # Vectorised composite score (same logic as compute_technical_signals)
    rsi = df["rsi_14"].fillna(50)
    macd = df["macd"].fillna(0)
    macd_sig = df["macd_signal"].fillna(0)
    sma20 = df["sma_20"].fillna(df["close"])
    sma50 = df["sma_50"].fillna(df["close"])
    close = df["close"]
    bb_upper = df["bb_upper"].fillna(close * 1.1)
    bb_lower = df["bb_lower"].fillna(close * 0.9)

    score = (
        np.where(rsi < 30, 2.0, np.where(rsi > 70, -2.0, 0.0))
        + np.where(macd > macd_sig, 1.5, -1.5)
        + np.where(sma20 > sma50, 1.0, -1.0)
        + np.where(close < bb_lower, 1.5, np.where(close > bb_upper, -1.5, 0.0))
    )

    df["composite_score"] = score
    df["position"] = (score > 0.5).astype(float)
    df["position_lag"] = df["position"].shift(1).fillna(0)
    df["strategy_return"] = df["position_lag"] * df["daily_return"]

    clean = df.dropna(subset=["strategy_return", "daily_return"]).copy()
    if len(clean) < 20:
        return _empty

    strat_eq = (1 + clean["strategy_return"]).cumprod()

    # Align benchmark to Nifty if available
    if nifty_df is not None and not nifty_df.empty:
        nifty_s = nifty_df.set_index("date")["daily_return"].dropna()
        aligned = nifty_s.reindex(clean["date"].values).fillna(0)
        bench_eq = (1 + aligned.values).cumprod()
    else:
        bench_eq = (1 + clean["daily_return"]).cumprod()

    strat_eq = strat_eq / strat_eq.iloc[0] * 100
    bench_eq_norm = bench_eq / bench_eq[0] * 100

    total_return = float(strat_eq.iloc[-1] - 100)
    bench_return = float(bench_eq_norm[-1] - 100)

    strat_ann_ret = float(clean["strategy_return"].mean() * 252)
    strat_ann_vol = float(clean["strategy_return"].std() * np.sqrt(252))
    sharpe = (strat_ann_ret - RISK_FREE_RATE) / strat_ann_vol if strat_ann_vol > 0 else 0.0

    bench_ann_ret = float(clean["daily_return"].mean() * 252)
    alpha = (strat_ann_ret - bench_ann_ret) * 100

    num_trades = int(clean["position_lag"].diff().abs().sum())
    active = clean["strategy_return"] != 0
    win_rate = float((clean.loc[active, "strategy_return"] > 0).mean() * 100) if active.any() else 0.0

    dates = clean["date"].values
    strat_arr = strat_eq.values
    equity_curve = [
        EquityPoint(
            date=str(dates[i])[:10],
            strategy=round(float(strat_arr[i]), 2),
            benchmark=round(float(bench_eq_norm[i]), 2),
        )
        for i in range(0, len(clean), 5)
    ]

    return BacktestResult(
        symbol=symbol,
        equity_curve=equity_curve,
        total_return=round(total_return, 2),
        benchmark_return=round(bench_return, 2),
        alpha=round(alpha, 2),
        sharpe_ratio=round(sharpe, 3),
        num_trades=num_trades,
        win_rate=round(win_rate, 1),
    )
