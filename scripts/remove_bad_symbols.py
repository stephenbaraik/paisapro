"""
Scan all symbols in the Supabase stocks table, test each against yfinance,
and delete the ones with no data from both stocks and stock_prices tables.
"""

import sys
import os
import time
import logging

import httpx
import yfinance as yf

# Allow importing backend config
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


def fetch_all_symbols() -> list[str]:
    resp = httpx.get(
        f"{SUPABASE_URL}/rest/v1/stocks",
        headers=HEADERS,
        params={"select": "symbol", "order": "symbol.asc", "limit": "1000"},
        timeout=15,
    )
    resp.raise_for_status()
    return [row["symbol"] for row in resp.json()]


def has_yfinance_data(symbol_ns: str) -> bool:
    try:
        df = yf.Ticker(symbol_ns).history(period="5d", interval="1d", auto_adjust=True)
        return df is not None and not df.empty
    except Exception:
        return False


def delete_symbol(bare: str) -> None:
    # Delete from stock_prices
    r1 = httpx.delete(
        f"{SUPABASE_URL}/rest/v1/stock_prices",
        headers=HEADERS,
        params={"symbol": f"eq.{bare}"},
        timeout=15,
    )
    # Delete from stocks
    r2 = httpx.delete(
        f"{SUPABASE_URL}/rest/v1/stocks",
        headers=HEADERS,
        params={"symbol": f"eq.{bare}"},
        timeout=15,
    )
    logger.info("  Deleted %s — stock_prices: %s, stocks: %s", bare, r1.status_code, r2.status_code)


def main():
    bare_symbols = fetch_all_symbols()
    logger.info("Loaded %d symbols from Supabase", len(bare_symbols))

    bad: list[str] = []

    for i, bare in enumerate(bare_symbols, 1):
        symbol_ns = f"{bare}.NS"
        ok = has_yfinance_data(symbol_ns)
        status = "✓" if ok else "✗ NO DATA"
        logger.info("[%d/%d] %s — %s", i, len(bare_symbols), symbol_ns, status)
        if not ok:
            bad.append(bare)
        # Avoid hammering Yahoo Finance
        if i % 10 == 0:
            time.sleep(1)

    logger.info("\n--- Results ---")
    logger.info("Total symbols: %d", len(bare_symbols))
    logger.info("Bad symbols:   %d", len(bad))

    if not bad:
        logger.info("All symbols have yfinance data. Nothing to remove.")
        return

    logger.info("\nSymbols to remove: %s", bad)
    confirm = input("\nDelete these from Supabase? [y/N]: ").strip().lower()
    if confirm != "y":
        logger.info("Aborted.")
        return

    for bare in bad:
        delete_symbol(bare)

    logger.info("\nDone. Removed %d symbols.", len(bad))


if __name__ == "__main__":
    main()
