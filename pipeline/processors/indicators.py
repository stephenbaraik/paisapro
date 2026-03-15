"""
Technical indicator calculations for Indian stock data.
Applied on historical OHLCV DataFrames before storing to Supabase.
"""

import pandas as pd
import numpy as np


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds common technical indicators to an OHLCV DataFrame.
    Input df must have: close, high, low, volume columns.
    """
    df = df.copy().sort_values("date").reset_index(drop=True)
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # Moving Averages
    df["sma_20"] = close.rolling(20).mean().round(4)
    df["sma_50"] = close.rolling(50).mean().round(4)
    df["sma_200"] = close.rolling(200).mean().round(4)
    df["ema_12"] = close.ewm(span=12, adjust=False).mean().round(4)
    df["ema_26"] = close.ewm(span=26, adjust=False).mean().round(4)

    # MACD
    df["macd"] = (df["ema_12"] - df["ema_26"]).round(4)
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean().round(4)
    df["macd_histogram"] = (df["macd"] - df["macd_signal"]).round(4)

    # RSI (14-period)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi_14"] = (100 - (100 / (1 + rs))).round(4)

    # Bollinger Bands (20-period, 2 std)
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    df["bb_upper"] = (bb_mid + 2 * bb_std).round(4)
    df["bb_mid"] = bb_mid.round(4)
    df["bb_lower"] = (bb_mid - 2 * bb_std).round(4)
    df["bb_width"] = ((df["bb_upper"] - df["bb_lower"]) / bb_mid).round(6)

    # Average True Range (14-period)
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["atr_14"] = tr.rolling(14).mean().round(4)

    # Volume indicators
    df["vol_sma_20"] = volume.rolling(20).mean().round(0)
    df["vol_ratio"] = (volume / df["vol_sma_20"]).round(4)

    # Daily return
    df["daily_return_pct"] = (close.pct_change() * 100).round(4)

    return df
