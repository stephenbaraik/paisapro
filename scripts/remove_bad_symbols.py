"""
Find and remove stocks with no recent price data in Supabase.

Strategy:
  1. Load all symbols from the `stocks` table
  2. For each symbol, query the latest date in `stock_prices` (1 row, fast)
  3. Flag symbols with no rows OR latest date older than 180 days
  4. Confirm then delete
"""

import sys
import os
import logging
from datetime import datetime, timezone, timedelta

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("ENV", "production")

from backend.app.core.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()
SUPABASE_URL = settings.supabase_url
HEADERS = {
    "apikey": settings.supabase_service_role_key,
    "Authorization": f"Bearer {settings.supabase_service_role_key}",
    "Content-Type": "application/json",
}
STALE_CUTOFF = (datetime.now(timezone.utc) - timedelta(days=180)).strftime("%Y-%m-%d")


def get_all_symbols() -> list[str]:
    resp = httpx.get(
        f"{SUPABASE_URL}/rest/v1/stocks",
        headers=HEADERS,
        params={"select": "symbol", "order": "symbol.asc", "limit": "1000"},
        timeout=15,
    )
    resp.raise_for_status()
    return [r["symbol"] for r in resp.json()]


def get_latest_date(bare: str) -> str | None:
    """Return the most recent date for this symbol, or None if no rows."""
    resp = httpx.get(
        f"{SUPABASE_URL}/rest/v1/stock_prices",
        headers=HEADERS,
        params={
            "symbol": f"eq.{bare}",
            "select": "date",
            "order": "date.desc",
            "limit": "1",
        },
        timeout=10,
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0]["date"] if rows else None


def delete_symbol(bare: str) -> None:
    r1 = httpx.delete(
        f"{SUPABASE_URL}/rest/v1/stock_prices",
        headers=HEADERS,
        params={"symbol": f"eq.{bare}"},
        timeout=15,
    )
    r2 = httpx.delete(
        f"{SUPABASE_URL}/rest/v1/stocks",
        headers=HEADERS,
        params={"symbol": f"eq.{bare}"},
        timeout=15,
    )
    logger.info("  Deleted %-20s — prices: %s, stocks: %s", bare, r1.status_code, r2.status_code)


def main():
    logger.info("Loading symbols from Supabase…")
    symbols = get_all_symbols()
    logger.info("Found %d symbols\n", len(symbols))

    no_data: list[str] = []
    stale: list[str] = []

    for i, bare in enumerate(symbols, 1):
        try:
            latest = get_latest_date(bare)
        except Exception as e:
            logger.warning("[%d/%d] %s — query failed: %s", i, len(symbols), bare, e)
            continue

        if latest is None:
            no_data.append(bare)
            logger.info("[%d/%d] ✗ NO DATA  : %s", i, len(symbols), bare)
        elif latest < STALE_CUTOFF:
            stale.append(bare)
            logger.info("[%d/%d] ~ STALE    : %s (last: %s)", i, len(symbols), bare, latest)
        else:
            logger.info("[%d/%d] ✓ %s (last: %s)", i, len(symbols), bare, latest)

    to_remove = no_data + stale

    logger.info("\n--- Summary ---")
    logger.info("Total   : %d", len(symbols))
    logger.info("No data : %d — %s", len(no_data), no_data or "none")
    logger.info("Stale   : %d — %s", len(stale), stale or "none")
    logger.info("Remove  : %d", len(to_remove))

    if not to_remove:
        logger.info("\nAll symbols have recent data. Nothing to remove.")
        return

    print(f"\nDelete {len(to_remove)} symbols from Supabase? [y/N]: ", end="", flush=True)
    confirm = sys.stdin.readline().strip().lower()
    if confirm != "y":
        logger.info("Aborted.")
        return

    for bare in to_remove:
        delete_symbol(bare)

    logger.info("\nDone. Removed %d symbols.", len(to_remove))


if __name__ == "__main__":
    main()
