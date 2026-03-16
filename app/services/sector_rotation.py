"""
Sector Rotation Analysis — momentum-based sector rotation signals.

Calculates 1M/3M/6M/12M sector returns, relative strength vs Nifty 50,
and identifies leading/lagging sectors to determine market phase.
"""

import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from .analytics import (
    get_stock_universe, _get_cached_df, get_stock_sector, get_stock_name,
    NIFTY_INDEX,
)
from ..schemas.advanced_analytics import (
    SectorMomentum, SectorRotationHistory, SectorRotationResponse,
)

_cache: tuple[SectorRotationResponse | None, float] = (None, 0.0)
_CACHE_TTL = 3600  # 1 hour


def _period_return(df: pd.DataFrame, days: int) -> float:
    if df is None or len(df) < days + 1:
        return 0.0
    recent = df.tail(days + 1)
    start = recent["close"].iloc[0]
    end = recent["close"].iloc[-1]
    return ((end - start) / start * 100) if start > 0 else 0.0


def _determine_market_phase(sectors: list[SectorMomentum]) -> str:
    """Classify market phase based on sector breadth."""
    overweight = sum(1 for s in sectors if s.signal == "OVERWEIGHT")
    underweight = sum(1 for s in sectors if s.signal == "UNDERWEIGHT")
    total = len(sectors) or 1

    avg_3m = np.mean([s.return_3m for s in sectors]) if sectors else 0
    avg_1m = np.mean([s.return_1m for s in sectors]) if sectors else 0

    if overweight / total > 0.6 and avg_3m > 5:
        return "EXPANSION"
    elif overweight / total > 0.4 and avg_1m < avg_3m * 0.3:
        return "PEAK"
    elif underweight / total > 0.6 and avg_3m < -5:
        return "CONTRACTION"
    elif underweight / total > 0.4 and avg_1m > avg_3m:
        return "TROUGH"
    elif avg_3m > 2:
        return "EXPANSION"
    elif avg_3m < -2:
        return "CONTRACTION"
    return "PEAK" if avg_1m < 0 else "TROUGH"


async def get_sector_rotation(force: bool = False) -> SectorRotationResponse:
    global _cache
    cached, ts = _cache
    if cached and not force and time.time() - ts < _CACHE_TTL:
        return cached

    universe = get_stock_universe()
    nifty_df = _get_cached_df(NIFTY_INDEX, "2y")
    nifty_12m = _period_return(nifty_df, 252) if nifty_df is not None else 0

    # Group stocks by sector
    sector_stocks: dict[str, list[str]] = {}
    for sym in universe:
        sec = get_stock_sector(sym)
        if sec and sec != "Unknown":
            sector_stocks.setdefault(sec, []).append(sym)

    sectors: list[SectorMomentum] = []
    rotation_history: list[SectorRotationHistory] = []

    for sector, symbols in sector_stocks.items():
        if len(symbols) < 2:
            continue

        returns_1m, returns_3m, returns_6m, returns_12m = [], [], [], []
        rsi_vals, vol_vals = [], []

        for sym in symbols:
            df = _get_cached_df(sym, "2y")
            if df is None or len(df) < 30:
                continue

            returns_1m.append(_period_return(df, 21))
            returns_3m.append(_period_return(df, 63))
            returns_6m.append(_period_return(df, 126))
            returns_12m.append(_period_return(df, 252))

            if "rsi_14" in df.columns:
                last_rsi = df["rsi_14"].dropna().iloc[-1] if not df["rsi_14"].dropna().empty else 50
                rsi_vals.append(last_rsi)
            if "daily_return" in df.columns:
                vol = df["daily_return"].dropna().tail(63).std() * np.sqrt(252) * 100
                vol_vals.append(vol)

        if not returns_3m:
            continue

        avg_1m = float(np.mean(returns_1m))
        avg_3m = float(np.mean(returns_3m))
        avg_6m = float(np.mean(returns_6m))
        avg_12m = float(np.mean(returns_12m))

        # Momentum score: weighted average of returns
        momentum = avg_1m * 0.4 + avg_3m * 0.3 + avg_6m * 0.2 + avg_12m * 0.1
        rel_strength = avg_12m - nifty_12m if nifty_12m else avg_12m

        signal = "OVERWEIGHT" if momentum > 3 else "UNDERWEIGHT" if momentum < -3 else "NEUTRAL"

        sectors.append(SectorMomentum(
            sector=sector,
            stock_count=len(symbols),
            return_1m=round(avg_1m, 2),
            return_3m=round(avg_3m, 2),
            return_6m=round(avg_6m, 2),
            return_12m=round(avg_12m, 2),
            momentum_score=round(momentum, 2),
            relative_strength=round(rel_strength, 2),
            signal=signal,
            avg_rsi=round(float(np.mean(rsi_vals)), 1) if rsi_vals else 50.0,
            avg_volatility=round(float(np.mean(vol_vals)), 1) if vol_vals else 20.0,
        ))

        # Build rotation history (monthly sector returns for last 12 months)
        sample_dfs = []
        for sym in symbols[:10]:  # sample up to 10 stocks per sector
            df = _get_cached_df(sym, "2y")
            if df is not None and len(df) > 200 and "close" in df.columns:
                s = df.set_index("date")["close"].resample("ME").last().pct_change() * 100
                s.name = sym
                sample_dfs.append(s)

        if sample_dfs:
            combined = pd.concat(sample_dfs, axis=1).tail(12)
            monthly_avg = combined.mean(axis=1)
            cum_ret = 0.0
            for dt, ret in monthly_avg.items():
                if pd.notna(ret):
                    cum_ret += ret
                    rotation_history.append(SectorRotationHistory(
                        date=dt.strftime("%Y-%m-%d"),
                        sector=sector,
                        cumulative_return=round(cum_ret, 2),
                    ))

    # Sort by momentum
    sectors.sort(key=lambda s: s.momentum_score, reverse=True)
    leading = [s.sector for s in sectors[:3]]
    lagging = [s.sector for s in sectors[-3:]]
    phase = _determine_market_phase(sectors)

    result = SectorRotationResponse(
        sectors=sectors,
        rotation_history=rotation_history,
        leading_sectors=leading,
        lagging_sectors=lagging,
        market_phase=phase,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    _cache = (result, time.time())
    return result
