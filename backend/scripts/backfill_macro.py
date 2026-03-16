"""
Macro Prices Backfill
=====================
Downloads 1-year daily close prices for macro indicators from Yahoo Finance
and persists them to Supabase `macro_prices`.

Run from the project root:
    python -m backend.scripts.backfill_macro

Requires: SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in .env
"""

from __future__ import annotations

import os
import sys
import logging

import httpx
import yfinance as yf
import pandas as pd
from dotenv import load_dotenv

# ── Bootstrap ──────────────────────────────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("backfill_macro")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    log.error("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in .env")
    sys.exit(1)


MACRO_TICKERS = {
    "India VIX":  "^INDIAVIX",
    "USD/INR":    "INR=X",
    "Nifty 50":   "^NSEI",
    "Gold (INR)": "GC=F",
    "Crude Oil":  "CL=F",
    "Bank Nifty": "^NSEBANK",
}


# ── Supabase helpers ──────────────────────────────────────────────────────────

def sb_headers() -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }


def sb_upsert(rows: list[dict]) -> bool:
    """Upsert rows into macro_prices with on_conflict=ticker,date."""
    try:
        resp = httpx.post(
            f"{SUPABASE_URL}/rest/v1/macro_prices?on_conflict=ticker,date",
            headers=sb_headers(),
            json=rows,
            timeout=30,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        log.error("Supabase upsert failed: %s", exc)
        return False


# ── Download & upload ──────────────────────────────────────────────────────────

def backfill():
    tickers = list(MACRO_TICKERS.values())
    log.info("Downloading macro data for %d tickers via yf.download…", len(tickers))

    raw = yf.download(
        tickers, period="1y", interval="1d",
        auto_adjust=True, threads=True, progress=False,
    )

    if raw.empty:
        log.error("yf.download returned empty — check network or tickers")
        sys.exit(1)

    total_written = 0

    for name, ticker in MACRO_TICKERS.items():
        try:
            if len(tickers) == 1:
                df = raw[["Close"]].copy()
            else:
                df = raw["Close"][[ticker]].copy()
            df = df.dropna().reset_index()
            df.columns = ["date", "close"]
            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        except Exception as e:
            log.warning("Failed to extract %s (%s): %s", name, ticker, e)
            continue

        if len(df) < 5:
            log.warning("Skipping %s — only %d rows", name, len(df))
            continue

        rows = [
            {
                "ticker": ticker,
                "date": str(row["date"].date()),
                "close": round(float(row["close"]), 4),
            }
            for _, row in df.iterrows()
        ]

        # Upload in 500-row chunks
        written = 0
        for i in range(0, len(rows), 500):
            chunk = rows[i : i + 500]
            if sb_upsert(chunk):
                written += len(chunk)

        log.info("  %-12s  %s  →  %d rows written", name, ticker, written)
        total_written += written

    log.info("Backfill complete: %d total rows written across %d tickers.", total_written, len(MACRO_TICKERS))


if __name__ == "__main__":
    backfill()
