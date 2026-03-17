"""
Unified market data service.

Single source of truth for price DataFrames.
Fetch priority: in-memory cache → Supabase → yfinance fallback.

Replaces the private _get_cached_df / _fetch_yfinance / _add_indicators helpers
that were embedded in analytics.py and duplicated across other services.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import numpy as np
import pandas as pd
import yfinance as yf

from ..core.cache import cache
from ..data.stock_repository import (
    get_prices, save_prices, upsert_meta,
    load_all_prices_bulk, db_symbol,
)
from .universe import get_symbols, get_name, get_sector, get_names, get_sectors, NIFTY_INDEX

logger = logging.getLogger(__name__)

HIST_CACHE_TTL = 86400   # 24 h
CACHE_PREFIX = "stock:df:"

_PERIOD_DAYS = {
    "1mo": 30, "3mo": 92, "6mo": 183,
    "1y": 365, "2y": 730, "5y": 1825,
}


# ── Technical indicators (kept here to avoid a separate import cycle) ─────────

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all technical indicators in-place on an OHLCV DataFrame."""
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    df["sma_20"] = close.rolling(20).mean()
    df["sma_50"] = close.rolling(50).mean()
    df["sma_200"] = close.rolling(200).mean()
    df["ema_12"] = close.ewm(span=12, adjust=False).mean()
    df["ema_26"] = close.ewm(span=26, adjust=False).mean()
    df["macd"] = df["ema_12"] - df["ema_26"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_histogram"] = df["macd"] - df["macd_signal"]

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    df["bb_mid"] = bb_mid
    df["bb_upper"] = bb_mid + 2 * bb_std
    df["bb_lower"] = bb_mid - 2 * bb_std
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / bb_mid

    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    df["atr_14"] = tr.rolling(14).mean()

    df["vol_sma_20"] = volume.rolling(20).mean()
    df["vol_ratio"] = volume / df["vol_sma_20"].replace(0, np.nan)
    df["daily_return"] = close.pct_change()
    df["price_vs_sma20"] = (close / df["sma_20"]) - 1
    df["price_vs_sma50"] = (close / df["sma_50"]) - 1
    df["atr_normalized"] = df["atr_14"] / close
    df["return_5d"] = close.pct_change(5)
    df["return_20d"] = close.pct_change(20)

    return df


# ── yfinance fetch ────────────────────────────────────────────────────────────

def _fetch_yfinance(symbol: str, period: str = "max") -> pd.DataFrame:
    try:
        raw = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True)
        if raw is None or raw.empty:
            logger.warning("yfinance: no data for %s", symbol)
            return pd.DataFrame()
        df = raw.reset_index()
        df.rename(columns={
            "Date": "date", "Open": "open", "High": "high",
            "Low": "low", "Close": "close", "Volume": "volume",
        }, inplace=True)
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        df = df[["date", "open", "high", "low", "close", "volume"]].copy()
        df = df[df["close"] > 0].reset_index(drop=True)
        logger.info("yfinance: fetched %d rows for %s", len(df), symbol)
        return df
    except Exception as exc:
        logger.error("yfinance error for %s: %s", symbol, exc)
        return pd.DataFrame()


def _trim_period(df: pd.DataFrame, period: str) -> Optional[pd.DataFrame]:
    n_days = _PERIOD_DAYS.get(period, 365)
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=n_days)
    trimmed = df[df["date"] >= cutoff].copy().reset_index(drop=True)
    return trimmed if len(trimmed) >= 20 else None


# ── Public API ────────────────────────────────────────────────────────────────

def get_price_df(symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """
    Return a DataFrame of OHLCV + indicators for the requested period.

    Fetch priority:
      1. In-memory cache (24h TTL) — zero network cost.
      2. Supabase stock_prices — zero network cost if fresh (≤3 days old, ≥50 rows).
      3. yfinance — free fallback. Result saved to Supabase.
    """
    raw_key = f"{CACHE_PREFIX}{symbol}"

    # 1. In-memory cache
    raw_df = cache.get(raw_key)
    if raw_df is not None:
        return _trim_period(raw_df, period)

    # 2. Supabase
    sb_df = get_prices(symbol)
    if not sb_df.empty:
        latest = sb_df["date"].max()
        days_stale = (pd.Timestamp.now() - latest).days
        if days_stale <= 3 and len(sb_df) >= 50:
            sb_df = add_indicators(sb_df)
            cache.set(raw_key, sb_df, HIST_CACHE_TTL)
            return _trim_period(sb_df, period)

    # 3. yfinance fallback
    raw_df = _fetch_yfinance(symbol, period="max")
    if raw_df.empty:
        if not sb_df.empty:
            sb_df = add_indicators(sb_df)
            cache.set(raw_key, sb_df, HIST_CACHE_TTL)
            return _trim_period(sb_df, period)
        return None

    raw_df = add_indicators(raw_df)
    upsert_meta([symbol], get_names(), get_sectors())
    save_prices(symbol, raw_df)
    cache.set(raw_key, raw_df, HIST_CACHE_TTL)
    return _trim_period(raw_df, period)


def get_nifty_df(period: str = "1y") -> Optional[pd.DataFrame]:
    return get_price_df(NIFTY_INDEX, period)


def invalidate_symbol(symbol: str) -> None:
    cache.invalidate(f"{CACHE_PREFIX}{symbol}")


def invalidate_all() -> None:
    cache.invalidate_prefix(CACHE_PREFIX)


def preload_all() -> int:
    """
    Bulk-load ALL stock price data from Supabase in one query, then cache per symbol.
    Called on startup to avoid cold-start latency.
    """
    symbols = get_symbols()
    if not symbols:
        return 0

    already = sum(1 for sym in symbols if cache.has(f"{CACHE_PREFIX}{sym}"))
    if already == len(symbols):
        return already

    logger.info("Bulk-loading stock prices from Supabase…")
    import pandas as pd
    cutoff = (pd.Timestamp.now() - pd.Timedelta(days=750)).strftime("%Y-%m-%d")
    big_df = load_all_prices_bulk(cutoff)

    if big_df.empty:
        logger.warning("Bulk load returned no data")
        return already

    logger.info("Bulk load complete: %d rows. Splitting per symbol…", len(big_df))

    now = time.time()
    loaded = 0

    def _process_group(sym_bare: str, group_df: pd.DataFrame) -> bool:
        ns = f"{sym_bare}.NS"
        key = f"{CACHE_PREFIX}{ns}"
        if cache.has(key):
            return False
        df = group_df.drop(columns=["symbol"]).reset_index(drop=True)
        if len(df) < 20:
            return False
        df = add_indicators(df)
        cache.set(key, df, HIST_CACHE_TTL)
        return True

    groups = {sym: grp.copy() for sym, grp in big_df.groupby("symbol")}
    with ThreadPoolExecutor(max_workers=16) as pool:
        futs = {pool.submit(_process_group, sym, grp): sym for sym, grp in groups.items()}
        for fut in as_completed(futs):
            try:
                if fut.result():
                    loaded += 1
            except Exception:
                pass

    total = already + loaded
    logger.info("Preload done: %d newly cached, %d total in cache", loaded, total)
    return total
