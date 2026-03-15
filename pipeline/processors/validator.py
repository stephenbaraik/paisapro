"""
Data quality validation for fetched stock data.
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


def validate_price_dataframe(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """
    Validates and cleans a price DataFrame.
    - Drops rows with null close prices
    - Removes duplicates by date
    - Filters out extreme outliers (>50% daily move, likely data errors)
    - Ensures positive values
    """
    if df.empty:
        return df

    initial_rows = len(df)

    # Drop nulls
    df = df.dropna(subset=["close", "open", "high", "low"])

    # Remove duplicate dates
    df = df.drop_duplicates(subset=["date"], keep="last")

    # Filter non-positive prices
    df = df[(df["close"] > 0) & (df["open"] > 0) & (df["high"] > 0) & (df["low"] > 0)]

    # OHLC consistency checks
    df = df[(df["high"] >= df["low"]) & (df["high"] >= df["close"]) & (df["low"] <= df["close"])]

    # Remove extreme single-day moves (>60%) — likely bad data
    df = df.sort_values("date").reset_index(drop=True)
    daily_ret = df["close"].pct_change().abs()
    df = df[daily_ret.isna() | (daily_ret <= 0.60)]

    removed = initial_rows - len(df)
    if removed > 0:
        logger.info(f"{symbol}: removed {removed} invalid rows")

    return df.reset_index(drop=True)


def validate_stock_info(info: dict) -> bool:
    """Returns True if stock info is complete enough to store."""
    required = ["symbol", "company_name", "current_price"]
    return all(info.get(k) for k in required)
