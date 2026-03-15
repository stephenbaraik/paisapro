"""
Writes processed stock data to Supabase in batches.
Uses httpx REST API directly (no supabase Python package).
"""

import httpx
import pandas as pd
import logging
from typing import Optional

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def _post(db: dict, table: str, data) -> None:
    """POST (upsert) one or more records to a Supabase table."""
    payload = data if isinstance(data, list) else [data]
    resp = httpx.post(
        f"{db['base_url']}/{table}",
        headers=db["headers"],
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()


def upsert_stock_info(db: dict, stock_info: dict) -> bool:
    """Upsert a single stock's metadata."""
    try:
        _post(db, "stocks", stock_info)
        return True
    except Exception as e:
        logger.error(f"Failed to upsert stock info for {stock_info.get('symbol')}: {e}")
        return False


def upsert_price_history(db: dict, df: pd.DataFrame, symbol: str) -> int:
    """
    Batch upsert historical prices for a symbol.
    Returns number of rows successfully written.
    """
    if df.empty:
        return 0

    records = df.to_dict(orient="records")
    # Convert date objects to ISO strings and numpy types to native Python
    for r in records:
        if hasattr(r.get("date"), "isoformat"):
            r["date"] = r["date"].isoformat()
        for k, v in r.items():
            if hasattr(v, "item"):
                r[k] = v.item()

    written = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]
        try:
            _post(db, "stock_prices", batch)
            written += len(batch)
        except Exception as e:
            logger.error(f"Batch write failed for {symbol} rows {i}-{i+BATCH_SIZE}: {e}")

    return written


def upsert_index_data(db: dict, index_data: dict) -> bool:
    """Upsert market index current value."""
    try:
        _post(db, "market_indices", index_data)
        return True
    except Exception as e:
        logger.error(f"Failed to upsert index {index_data.get('symbol')}: {e}")
        return False


def log_pipeline_run(
    db: dict,
    run_type: str,
    status: str,
    symbols_processed: int,
    rows_written: int,
    errors: int,
    notes: Optional[str] = None,
) -> None:
    """Logs a pipeline execution record for monitoring."""
    try:
        # Use plain insert headers (no merge-duplicates for logs)
        headers = dict(db["headers"])
        headers.pop("Prefer", None)
        resp = httpx.post(
            f"{db['base_url']}/pipeline_logs",
            headers=headers,
            json={
                "run_type": run_type,
                "status": status,
                "symbols_processed": symbols_processed,
                "rows_written": rows_written,
                "errors": errors,
                "notes": notes,
            },
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to log pipeline run: {e}")
