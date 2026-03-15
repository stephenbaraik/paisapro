"""
Main pipeline runner.
Modes:
  - backfill: Fetch full history for all symbols (run once on setup)
  - daily:    Fetch today's data + update stock info (run after market close ~6pm IST)
  - indices:  Update index values only (lightweight, can run every 15min during market hours)
"""

import os
import sys
import logging
import time
from datetime import date
from dotenv import load_dotenv

load_dotenv()

import httpx
from fetchers.nse_fetcher import (
    NIFTY_500_SYMBOLS, INDICES,
    fetch_stock_info, fetch_historical_prices, fetch_index_data,
)
from processors.indicators import add_technical_indicators
from processors.validator import validate_price_dataframe, validate_stock_info
from storage.db_writer import (
    upsert_stock_info, upsert_price_history, upsert_index_data, log_pipeline_run,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DELAY_BETWEEN_SYMBOLS = 1.2  # seconds — respects yfinance rate limits


def get_db() -> dict:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
    return {
        "base_url": f"{url}/rest/v1",
        "headers": {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates",
        },
    }


def run_backfill():
    """Full historical backfill — run once during project setup."""
    db = get_db()
    logger.info(f"Starting full backfill for {len(NIFTY_500_SYMBOLS)} symbols (max available history)")

    total_rows = 0
    errors = 0

    for i, symbol in enumerate(NIFTY_500_SYMBOLS):
        logger.info(f"[{i+1}/{len(NIFTY_500_SYMBOLS)}] Processing {symbol}")

        # 1. Stock info
        info = fetch_stock_info(symbol)
        if info and validate_stock_info(info):
            upsert_stock_info(db, info)

        # 2. Historical prices — fetch all available history
        df = fetch_historical_prices(symbol)
        df = validate_price_dataframe(df, symbol)

        if not df.empty:
            df = add_technical_indicators(df)
            rows = upsert_price_history(db, df, symbol)
            total_rows += rows
            logger.info(f"  Wrote {rows} rows for {symbol}")
        else:
            logger.warning(f"  No data for {symbol}")
            errors += 1

        time.sleep(DELAY_BETWEEN_SYMBOLS)

    log_pipeline_run(db, "backfill", "completed", len(NIFTY_500_SYMBOLS), total_rows, errors)
    logger.info(f"Backfill complete. Total rows: {total_rows}, Errors: {errors}")


def run_daily():
    """Daily update — run after market close (6pm IST / 12:30 UTC)."""
    db = get_db()
    logger.info(f"Starting daily update for {len(NIFTY_500_SYMBOLS)} symbols")

    total_rows = 0
    errors = 0

    for i, symbol in enumerate(NIFTY_500_SYMBOLS):
        # Update latest price info
        info = fetch_stock_info(symbol)
        if info and validate_stock_info(info):
            upsert_stock_info(db, info)

        # Fetch only today's data
        df = fetch_historical_prices(symbol, start_year=date.today().year, end_date=date.today())
        df = validate_price_dataframe(df, symbol)

        if not df.empty:
            df = add_technical_indicators(df)
            rows = upsert_price_history(db, df, symbol)
            total_rows += rows

        if (i + 1) % 50 == 0:
            logger.info(f"Progress: {i+1}/{len(NIFTY_500_SYMBOLS)}")

        time.sleep(DELAY_BETWEEN_SYMBOLS)

    # Update indices
    for name, symbol in INDICES.items():
        index_data = fetch_index_data(symbol)
        if index_data:
            index_data["name"] = name
            upsert_index_data(db, index_data)

    log_pipeline_run(db, "daily", "completed", len(NIFTY_500_SYMBOLS), total_rows, errors)
    logger.info(f"Daily update complete. Rows written: {total_rows}")


def run_indices():
    """Lightweight index update — can run every 15min during market hours."""
    db = get_db()
    for name, symbol in INDICES.items():
        index_data = fetch_index_data(symbol)
        if index_data:
            index_data["name"] = name
            upsert_index_data(db, index_data)
            logger.info(f"Updated {name}: {index_data['current_value']}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"
    if mode == "backfill":
        run_backfill()
    elif mode == "daily":
        run_daily()
    elif mode == "indices":
        run_indices()
    else:
        print(f"Unknown mode: {mode}. Use: backfill | daily | indices")
        sys.exit(1)
