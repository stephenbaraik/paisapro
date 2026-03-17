"""
Macro data repository — all Supabase I/O for macro_prices table.

Previously duplicated in services/macro.py as private helpers.
"""

from __future__ import annotations

import logging

import httpx
import pandas as pd

from ..core.config import get_settings

logger = logging.getLogger(__name__)


def _headers() -> dict:
    key = get_settings().supabase_service_role_key
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }


def _url(table: str) -> str:
    return f"{get_settings().supabase_url}/rest/v1/{table}"


def get_macro_prices(ticker: str) -> pd.DataFrame:
    """Load macro price history from Supabase (last 400 rows ≈ 1.5 years)."""
    try:
        resp = httpx.get(
            _url("macro_prices"),
            headers=_headers(),
            params={
                "ticker": f"eq.{ticker}",
                "select": "date,close",
                "order": "date.desc",
                "limit": "400",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Supabase macro read failed for %s: %s", ticker, exc)
        return pd.DataFrame()

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def save_macro_prices(ticker: str, df: pd.DataFrame) -> None:
    """Upsert macro price rows to Supabase macro_prices table."""
    rows = [
        {
            "ticker": ticker,
            "date": str(row["date"].date()),
            "close": round(float(row["close"]), 4),
        }
        for _, row in df.iterrows()
    ]

    for i in range(0, len(rows), 500):
        batch = rows[i:i + 500]
        try:
            resp = httpx.post(
                _url("macro_prices") + "?on_conflict=ticker,date",
                headers=_headers(), json=batch, timeout=30,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Supabase macro write failed for %s batch %d: %s", ticker, i, exc)

    logger.info("Saved %d macro rows for %s to Supabase", len(rows), ticker)
