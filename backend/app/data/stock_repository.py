"""
Stock data repository — all Supabase I/O for stock_prices and stocks tables.

Previously scattered across analytics.py as private helpers (_sb_headers, _sb_url,
_load_from_supabase, _save_to_supabase, _upsert_stocks_meta, _load_stock_universe).
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx
import pandas as pd

from ..core.config import get_settings

logger = logging.getLogger(__name__)


# ── Internal helpers ──────────────────────────────────────────────────────────

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


def _safe_f(v) -> Optional[float]:
    try:
        f = float(v)
        return None if f != f else round(f, 6)  # NaN → None
    except (TypeError, ValueError):
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def db_symbol(symbol: str) -> str:
    """Strip exchange suffix for DB storage: RELIANCE.NS → RELIANCE, ^NSEI → NSEI."""
    return symbol.replace(".NS", "").replace(".BO", "").replace("^", "")


def load_universe() -> tuple[list[str], dict[str, str], dict[str, str]]:
    """
    Fetch all stocks from Supabase stocks table.
    Returns (symbols_with_ns_suffix, names_map, sectors_map).
    """
    try:
        resp = httpx.get(
            _url("stocks"),
            headers=_headers(),
            params={"select": "symbol,company_name,sector", "order": "symbol.asc", "limit": "1000"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Failed to load stock universe from Supabase: %s", exc)
        return [], {}, {}

    symbols, names, sectors = [], {}, {}
    for row in data:
        bare = row["symbol"]
        ns = f"{bare}.NS"
        symbols.append(ns)
        names[ns] = row.get("company_name") or bare
        sectors[ns] = row.get("sector") or "Unknown"

    logger.info("Loaded stock universe: %d stocks from Supabase", len(symbols))
    return symbols, names, sectors


def get_prices(symbol: str) -> pd.DataFrame:
    """Load recent OHLCV rows from stock_prices (last 750 rows ≈ 3 years)."""
    db_sym = db_symbol(symbol)
    try:
        resp = httpx.get(
            _url("stock_prices"),
            headers=_headers(),
            params={
                "symbol": f"eq.{db_sym}",
                "select": "date,open,high,low,close,volume",
                "order": "date.desc",
                "limit": "750",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Supabase read failed for %s: %s", symbol, exc)
        return pd.DataFrame()

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    for col in df.columns:
        if col != "date":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("date").reset_index(drop=True)


def save_prices(symbol: str, df: pd.DataFrame) -> None:
    """Bulk-upsert OHLCV rows to stock_prices (upsert on symbol+date)."""
    db_sym = db_symbol(symbol)
    rows = []
    for _, row in df.iterrows():
        v = row.get("volume")
        rows.append({
            "symbol": db_sym,
            "date": str(row["date"].date()),
            "open": _safe_f(row.get("open")),
            "high": _safe_f(row.get("high")),
            "low": _safe_f(row.get("low")),
            "close": _safe_f(row.get("close")),
            "volume": int(v) if v and v == v else None,
        })

    for i in range(0, len(rows), 500):
        batch = rows[i:i + 500]
        try:
            resp = httpx.post(
                _url("stock_prices") + "?on_conflict=symbol,date",
                headers=_headers(), json=batch, timeout=30,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Supabase write failed for %s batch %d: %s", symbol, i, exc)

    logger.info("Saved %d rows for %s to Supabase", len(rows), symbol)


def upsert_meta(symbols: list[str], names: dict[str, str], sectors: dict[str, str]) -> None:
    """Ensure every symbol has a row in the stocks table."""
    rows = [
        {
            "symbol": db_symbol(sym),
            "company_name": names.get(sym) or db_symbol(sym),
            "exchange": "NSE",
            "sector": sectors.get(sym) or "Unknown",
        }
        for sym in symbols
    ]
    try:
        resp = httpx.post(_url("stocks"), headers=_headers(), json=rows, timeout=15)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("Supabase stocks meta upsert failed: %s", exc)


def load_all_prices_bulk(cutoff_date: str, page_size: int = 10000) -> pd.DataFrame:
    """
    Fetch all stock prices since cutoff_date in paginated batches.
    Returns a single combined DataFrame with a 'symbol' column.
    Used for the startup bulk preload.
    """
    all_data: list[dict] = []
    offset = 0

    while True:
        try:
            resp = httpx.get(
                _url("stock_prices"),
                headers=_headers(),
                params={
                    "select": "symbol,date,open,high,low,close,volume",
                    "date": f"gte.{cutoff_date}",
                    "order": "symbol.asc,date.asc",
                    "limit": str(page_size),
                    "offset": str(offset),
                },
                timeout=30,
            )
            resp.raise_for_status()
            page = resp.json()
        except Exception as exc:
            logger.warning("Bulk load page failed at offset %d: %s", offset, exc)
            break

        if not page:
            break
        all_data.extend(page)
        logger.info("  Fetched %d rows so far…", len(all_data))
        if len(page) < page_size:
            break
        offset += page_size

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    df["date"] = pd.to_datetime(df["date"])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df
