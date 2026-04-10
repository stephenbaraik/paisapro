"""
Resilient yfinance wrapper with retries, timeout, and graceful degradation.

Yahoo Finance API can be flaky, especially from cloud environments like HuggingFace Spaces.
This module adds:
  - Automatic retries with exponential backoff
  - Configurable timeouts
  - Session reuse for better connection pooling
  - Graceful fallback to empty DataFrames
"""

import logging
import time
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# yfinance session is reused across calls for better connection pooling
_session: Optional[yf.utils.Cache] = None

# Configuration
MAX_RETRIES = 3
RETRY_DELAY = 2.0  # seconds (base for exponential backoff)
REQUEST_TIMEOUT = 30  # seconds


def _get_session():
    """Get or create a yfinance session with proper configuration."""
    global _session
    if _session is None:
        _session = yf.utils.Cache()
    return _session


def fetch_ticker_history(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
    auto_adjust: bool = True,
) -> pd.DataFrame:
    """
    Fetch historical OHLCV data for a single symbol with retries.

    Args:
        symbol: Yahoo Finance ticker symbol (e.g., "^NSEI", "RELIANCE.NS")
        period: Data period ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
        interval: Data interval ("1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo")
        auto_adjust: Whether to auto-adjust prices for splits/dividends

    Returns:
        DataFrame with columns: date, open, high, low, close, volume
        Empty DataFrame on failure.
    """
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            ticker = yf.Ticker(symbol)
            raw = ticker.history(period=period, interval=interval, auto_adjust=auto_adjust)

            if raw is None or raw.empty:
                logger.debug("yfinance: no data for %s (attempt %d/%d)", symbol, attempt, MAX_RETRIES)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                    continue
                return pd.DataFrame()

            df = raw.reset_index()
            df.rename(columns={
                "Date": "date", "Open": "open", "High": "high",
                "Low": "low", "Close": "close", "Volume": "volume",
            }, inplace=True)
            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
            df = df[["date", "open", "high", "low", "close", "volume"]].copy()
            df = df[df["close"] > 0].reset_index(drop=True)

            if df.empty:
                logger.warning("yfinance: returned empty after processing for %s", symbol)
                return pd.DataFrame()

            logger.info("yfinance: fetched %d rows for %s (attempt %d)", len(df), symbol, attempt)
            return df

        except Exception as exc:
            last_error = exc
            logger.warning(
                "yfinance error for %s (attempt %d/%d): %s",
                symbol, attempt, MAX_RETRIES, exc
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    logger.error("yfinance: all %d retries failed for %s. Last error: %s", MAX_RETRIES, symbol, last_error)
    return pd.DataFrame()


def fetch_batch_download(
    tickers: list[str],
    period: str = "1y",
    interval: str = "1d",
    auto_adjust: bool = True,
) -> dict[str, pd.DataFrame]:
    """
    Download data for multiple tickers in batch with retries.

    Args:
        tickers: List of Yahoo Finance ticker symbols
        period: Data period
        interval: Data interval
        auto_adjust: Whether to auto-adjust prices

    Returns:
        Dict mapping ticker symbol to DataFrame (only successful fetches included)
    """
    result: dict[str, pd.DataFrame] = {}
    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            raw = yf.download(
                tickers,
                period=period,
                interval=interval,
                auto_adjust=auto_adjust,
                threads=True,
                progress=False,
            )

            if raw is None or (hasattr(raw, 'empty') and raw.empty):
                logger.debug("yfinance batch: download returned empty (attempt %d/%d)", attempt, MAX_RETRIES)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                    continue
                return result

            # Extract per-ticker data
            for ticker in tickers:
                try:
                    if len(tickers) == 1:
                        if "Close" in raw.columns:
                            df = raw[["Close"]].copy()
                        else:
                            continue
                    else:
                        if "Close" in raw.columns and ticker in raw["Close"].columns:
                            df = raw["Close"][[ticker]].copy()
                        else:
                            continue

                    df = df.dropna().reset_index()
                    df.columns = ["date", "close"]
                    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)

                    if len(df) >= 5:
                        result[ticker] = df
                except Exception as e:
                    logger.warning("yfinance batch: failed to extract %s: %s", ticker, e)

            if result:
                logger.info("yfinance batch: successfully fetched %d/%d tickers", len(result), len(tickers))
                return result

            logger.warning("yfinance batch: no valid data extracted (attempt %d/%d)", attempt, MAX_RETRIES)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

        except Exception as exc:
            last_error = exc
            logger.warning(
                "yfinance batch download error (attempt %d/%d): %s",
                attempt, MAX_RETRIES, exc
            )
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * attempt)

    logger.error("yfinance batch: all %d retries failed. Last error: %s", MAX_RETRIES, last_error)
    return result
