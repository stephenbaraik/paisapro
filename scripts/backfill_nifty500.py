"""
Nifty 500 Full-History Backfill
================================
Downloads complete daily OHLCV history for every Nifty 500 stock from
Yahoo Finance and persists it to Supabase stock_prices.

Run from the project root:
    python -m backend.scripts.backfill_nifty500

Features:
  - Fetches live Nifty 500 constituent list from NSE India CSV
  - period="max" → full history from listing date (typically 15-25 yrs)
  - Skips symbols that already have ≥ 200 rows in Supabase (resume-safe)
  - Batch-downloads 50 symbols at a time via yfinance for speed
  - Streams rows to Supabase in 1 000-row chunks
  - Populates stocks metadata table before writing prices (FK safe)
"""

from __future__ import annotations

import os
import sys
import time
import logging
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed

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
log = logging.getLogger("backfill")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    log.error("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set in .env")
    sys.exit(1)


# ── Supabase helpers ───────────────────────────────────────────────────────────

def _sb_headers(prefer: str = "resolution=merge-duplicates") -> dict:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }

def _sb(table: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{table}"


def sb_upsert(table: str, rows: list[dict], conflict_cols: str = "") -> bool:
    url = _sb(table) + (f"?on_conflict={conflict_cols}" if conflict_cols else "")
    try:
        r = httpx.post(url, headers=_sb_headers(), json=rows, timeout=60)
        r.raise_for_status()
        return True
    except Exception as e:
        log.warning(f"  Supabase write error ({table}): {e}")
        return False


def sb_has_sufficient_data(sym: str, min_rows: int = 200) -> bool:
    """Return True if stock_prices already has >= min_rows for this symbol."""
    try:
        r = httpx.get(
            _sb("stock_prices"),
            headers={**_sb_headers(), "Prefer": "count=exact"},
            params={"symbol": f"eq.{sym}", "select": "symbol", "limit": "1"},
            timeout=15,
        )
        content_range = r.headers.get("content-range", "")
        if "/" in content_range:
            total = int(content_range.split("/")[1])
            return total >= min_rows
    except Exception:
        pass
    return False


def sb_get_symbol_counts(symbols: list[str]) -> dict[str, int]:
    """Return {bare_symbol: row_count} checked concurrently for speed."""
    counts: dict[str, int] = {}
    def _check(sym: str):
        try:
            r = httpx.get(
                _sb("stock_prices"),
                headers={**_sb_headers(), "Prefer": "count=exact"},
                params={"symbol": f"eq.{sym}", "select": "symbol", "limit": "1"},
                timeout=15,
            )
            cr = r.headers.get("content-range", "")
            if "/" in cr:
                counts[sym] = int(cr.split("/")[1])
        except Exception:
            pass

    with ThreadPoolExecutor(max_workers=20) as ex:
        list(ex.map(_check, symbols))
    return counts


# ── NSE 500 constituent list ───────────────────────────────────────────────────

NSE_CSV_URL = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"

# Fallback: top ~100 liquid NSE stocks if NSE CSV is unreachable
FALLBACK_SYMBOLS = [
    "RELIANCE","TCS","HDFCBANK","INFY","ICICIBANK","HINDUNILVR","SBIN",
    "BHARTIARTL","KOTAKBANK","AXISBANK","BAJFINANCE","LT","WIPRO","HCLTECH",
    "ASIANPAINT","MARUTI","SUNPHARMA","ULTRACEMCO","TITAN","POWERGRID",
    "NTPC","ONGC","JSWSTEEL","ADANIENT","TATAMOTORS","HDFCLIFE","BAJAJFINSV",
    "TECHM","MM","NESTLEIND","CIPLA","DRREDDY","DIVISLAB","BRITANNIA","HEROMOTOCO",
    "EICHERMOT","INDUSINDBK","APOLLOHOSP","TATACONSUM","SBILIFE","PIDILITIND",
    "HAVELLS","BERGEPAINT","MUTHOOTFIN","COLPAL","DABUR","MARICO","GODREJCP",
    "LUPIN","TORNTPHARM","AUROPHARMA","BIOCON","ALKEM","ABBOTINDIA","PFIZER",
    "GLAXO","TATACHEM","AMBUJACEM","ACCGRI","SHREECEM","GRASIM","HINDZINC",
    "VEDL","HINDALCO","NATIONALUM","SAIL","JSWENERGY","TATAPOWER","ADANIGREEN",
    "ADANIPORTS","ADANITRANS","ITC","COALINDIA","BPCL","IOC","HINDPETRO","GAIL",
    "PETRONET","MGL","IGL","CONCOR","IRCTC","PFC","RECLTD","IRFC","NHPC",
    "SJVN","TORNTPOWER","CESC","TRENT","DMART","NYKAA","ZOMATO","PAYTM",
    "POLICYBZR","NAUKRI","JUSTDIAL","INDIAMART","HAPPSTMNDS","COFORGE",
    "MPHASIS","PERSISTENT","LTIM","KPITTECH","TATAELXSI","SONATSOFTW",
]


def fetch_nifty500_list() -> list[dict]:
    """
    Returns list of {symbol_ns, company_name, sector} dicts.
    symbol_ns = bare NSE ticker + ".NS"  e.g. "RELIANCE.NS"
    """
    log.info("Fetching Nifty 500 constituent list from NSE India…")
    try:
        r = httpx.get(
            NSE_CSV_URL,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=20,
            follow_redirects=True,
        )
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text))
        # NSE CSV columns: Company Name, Industry, Symbol, Series, ISIN Code
        df.columns = [c.strip() for c in df.columns]
        sym_col  = next(c for c in df.columns if "symbol" in c.lower())
        name_col = next(c for c in df.columns if "company" in c.lower())
        ind_col  = next((c for c in df.columns if "industry" in c.lower()), None)

        results = []
        for _, row in df.iterrows():
            sym = str(row[sym_col]).strip()
            if not sym or sym == "nan":
                continue
            results.append({
                "symbol_ns":    sym + ".NS",
                "bare":         sym,
                "company_name": str(row[name_col]).strip(),
                "sector":       str(row[ind_col]).strip() if ind_col else "Unknown",
            })
        log.info(f"  Got {len(results)} symbols from NSE CSV")
        return results

    except Exception as e:
        log.warning(f"NSE CSV fetch failed ({e}), using fallback list")
        return [
            {"symbol_ns": s + ".NS", "bare": s, "company_name": s, "sector": "Unknown"}
            for s in FALLBACK_SYMBOLS
        ]


# ── yfinance download ──────────────────────────────────────────────────────────

def download_batch(symbols_ns: list[str]) -> dict[str, pd.DataFrame]:
    """
    Download full daily history for a batch of symbols.
    Returns {symbol_ns: DataFrame(date, open, high, low, close, volume)}.
    """
    if not symbols_ns:
        return {}

    try:
        raw = yf.download(
            symbols_ns,
            period="max",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as e:
        log.warning(f"  yfinance batch error: {e}")
        return {}

    if raw is None or raw.empty:
        return {}

    result: dict[str, pd.DataFrame] = {}

    # Single symbol → flat columns
    if len(symbols_ns) == 1:
        df = raw.reset_index()
        df.rename(columns={"Date": "date", "Open": "open", "High": "high",
                            "Low": "low", "Close": "close", "Volume": "volume"}, inplace=True)
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        df = df[["date", "open", "high", "low", "close", "volume"]].dropna(subset=["close"])
        df = df[df["close"] > 0].reset_index(drop=True)
        if not df.empty:
            result[symbols_ns[0]] = df
        return result

    # Multiple symbols → MultiIndex columns (Price, Ticker)
    for sym in symbols_ns:
        try:
            sym_data = raw.xs(sym, axis=1, level=1) if sym in raw.columns.get_level_values(1) else None
            if sym_data is None or sym_data.empty:
                continue
            df = sym_data.reset_index()
            df.rename(columns={"Date": "date", "Open": "open", "High": "high",
                                "Low": "low", "Close": "close", "Volume": "volume"}, inplace=True)
            df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
            df = df[["date", "open", "high", "low", "close", "volume"]].dropna(subset=["close"])
            df = df[df["close"] > 0].reset_index(drop=True)
            if not df.empty:
                result[sym] = df
        except Exception:
            continue

    return result


# ── Supabase row builder ───────────────────────────────────────────────────────

def _f(v) -> float | None:
    try:
        x = float(v)
        return None if x != x else round(x, 6)   # NaN → None
    except (TypeError, ValueError):
        return None


def df_to_rows(bare_sym: str, df: pd.DataFrame) -> list[dict]:
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "symbol":           bare_sym,
            "date":             str(r["date"].date()),
            "open":             _f(r.get("open")),
            "high":             _f(r.get("high")),
            "low":              _f(r.get("low")),
            "close":            _f(r.get("close")),
            "volume":           int(r["volume"]) if r.get("volume") and r["volume"] == r["volume"] else None,
        })
    return rows


def write_to_supabase(bare_sym: str, df: pd.DataFrame) -> int:
    """Write all rows for one symbol to Supabase. Returns rows written."""
    rows = df_to_rows(bare_sym, df)
    written = 0
    for i in range(0, len(rows), 1000):
        chunk = rows[i : i + 1000]
        if sb_upsert("stock_prices", chunk, conflict_cols="symbol,date"):
            written += len(chunk)
    return written


# ── Main backfill logic ────────────────────────────────────────────────────────

BATCH_SIZE   = 50    # symbols per yfinance download call
SKIP_IF_ROWS = 200   # skip symbol if Supabase already has this many rows


def run_backfill():
    t_start = time.time()

    # 1. Get Nifty 500 list
    constituents = fetch_nifty500_list()
    total = len(constituents)
    log.info(f"Total symbols to process: {total}")

    # 2. Check existing Supabase data (resume support)
    log.info("Checking existing Supabase data…")
    all_bare = [c["bare"] for c in constituents]
    existing = sb_get_symbol_counts(all_bare)
    to_process = [c for c in constituents if existing.get(c["bare"], 0) < SKIP_IF_ROWS]
    skipped = total - len(to_process)
    log.info(f"  Already populated: {skipped}  |  Need to fetch: {len(to_process)}")

    if not to_process:
        log.info("All symbols already have sufficient data. Nothing to do.")
        return

    # 3. Populate stocks metadata (FK requirement)
    log.info("Upserting stocks metadata…")
    stock_meta = [
        {
            "symbol":       c["bare"],
            "company_name": c["company_name"] or c["bare"],
            "exchange":     "NSE",
            "sector":       c["sector"] or "Unknown",
        }
        for c in constituents
    ]
    # Batch upsert in groups of 200
    for i in range(0, len(stock_meta), 200):
        sb_upsert("stocks", stock_meta[i : i + 200])
    log.info(f"  Upserted {len(stock_meta)} stock metadata rows")

    # 4. Download + write in batches
    symbols_ns = [c["symbol_ns"] for c in to_process]
    bare_map   = {c["symbol_ns"]: c["bare"] for c in to_process}

    total_rows = 0
    done = 0
    errors = 0

    for batch_start in range(0, len(symbols_ns), BATCH_SIZE):
        batch = symbols_ns[batch_start : batch_start + BATCH_SIZE]
        log.info(
            f"Batch {batch_start // BATCH_SIZE + 1}/{(len(symbols_ns) + BATCH_SIZE - 1) // BATCH_SIZE}"
            f"  ({batch_start + 1}–{min(batch_start + BATCH_SIZE, len(symbols_ns))} of {len(symbols_ns)})"
            f"  symbols: {', '.join(s.replace('.NS','') for s in batch[:5])}{'…' if len(batch) > 5 else ''}"
        )

        dfs = download_batch(batch)

        for sym_ns in batch:
            bare = bare_map[sym_ns]
            df   = dfs.get(sym_ns)
            if df is None or df.empty:
                log.warning(f"  No data for {sym_ns}")
                errors += 1
                done   += 1
                continue

            n  = write_to_supabase(bare, df)
            total_rows += n
            done       += 1
            log.info(f"  [{done}/{len(symbols_ns)}] {bare:<18} {len(df)} rows  → Supabase {n} upserted")

        # Brief pause between batches to be polite to Yahoo Finance
        time.sleep(1)

    elapsed = time.time() - t_start
    log.info(
        f"\n{'='*60}\n"
        f"  Backfill complete in {elapsed:.0f}s\n"
        f"  Symbols processed : {done}\n"
        f"  Rows written       : {total_rows:,}\n"
        f"  Errors / no data   : {errors}\n"
        f"{'='*60}"
    )


if __name__ == "__main__":
    run_backfill()
