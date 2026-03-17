"""
Technical signal computation.

Extracted from analytics.py. Stateless — takes a DataFrame, returns a TechnicalSignal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..schemas.analytics import (
    SignalDirection, IndicatorSignal, TechnicalSignal,
)
from .universe import get_name, get_sector


def compute_technical_signals(symbol: str, df: pd.DataFrame) -> TechnicalSignal:
    """Compute RSI, MACD, SMA crossover, and Bollinger Band signals, return composite."""
    last = df.iloc[-1]
    signals: list[IndicatorSignal] = []
    score = 0.0

    def _safe(col: str) -> float:
        v = last.get(col, np.nan)
        return float(v) if not (isinstance(v, float) and np.isnan(v)) else np.nan

    # RSI
    rsi = _safe("rsi_14")
    if not np.isnan(rsi):
        if rsi < 30:
            d, s = SignalDirection.BUY, 2.0
        elif rsi > 70:
            d, s = SignalDirection.SELL, -2.0
        else:
            d, s = SignalDirection.HOLD, 0.0
        signals.append(IndicatorSignal(name="RSI", direction=d, score=s, value=round(rsi, 2)))
        score += s

    # MACD
    macd, macd_sig = _safe("macd"), _safe("macd_signal")
    if not np.isnan(macd) and not np.isnan(macd_sig):
        if macd > macd_sig:
            d, s = SignalDirection.BUY, 1.5
        else:
            d, s = SignalDirection.SELL, -1.5
        signals.append(IndicatorSignal(name="MACD", direction=d, score=s, value=round(macd, 4)))
        score += s

    # SMA crossover
    sma20, sma50 = _safe("sma_20"), _safe("sma_50")
    if not np.isnan(sma20) and not np.isnan(sma50):
        if sma20 > sma50:
            d, s = SignalDirection.BUY, 1.0
        else:
            d, s = SignalDirection.SELL, -1.0
        signals.append(IndicatorSignal(name="SMA_Cross", direction=d, score=s, value=round(sma20, 2)))
        score += s

    # Bollinger Bands
    close, bb_upper, bb_lower = _safe("close"), _safe("bb_upper"), _safe("bb_lower")
    if not np.isnan(close) and not np.isnan(bb_upper) and not np.isnan(bb_lower):
        if close < bb_lower:
            d, s = SignalDirection.BUY, 1.5
        elif close > bb_upper:
            d, s = SignalDirection.SELL, -1.5
        else:
            d, s = SignalDirection.HOLD, 0.0
        signals.append(IndicatorSignal(name="BB", direction=d, score=s, value=round(close, 2)))
        score += s

    if score > 0.5:
        direction = SignalDirection.BUY
    elif score < -0.5:
        direction = SignalDirection.SELL
    else:
        direction = SignalDirection.HOLD

    confidence = min(abs(score) / 6.0 * 100, 100)

    return TechnicalSignal(
        symbol=symbol,
        company_name=get_name(symbol),
        sector=get_sector(symbol),
        current_price=round(close, 2) if not np.isnan(close) else 0.0,
        composite_signal=direction,
        composite_score=round(score, 2),
        confidence_score=round(confidence, 1),
        signals=signals,
    )
