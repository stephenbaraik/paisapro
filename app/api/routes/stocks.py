import time
import logging
from fastapi import APIRouter, Query, HTTPException
from ...core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stocks", tags=["Stocks"])

# ─── Live indices cache ──────────────────────────────────────────────────────
_indices_cache: tuple[list[dict], float] = ([], 0.0)
_INDICES_TTL = 300  # 5 minutes


@router.get("/search")
def search_stocks(q: str = Query(..., min_length=1)):
    """Search Indian stocks by symbol or company name, with latest prices."""
    db = get_db()
    result = (
        db.table("stocks")
        .select("symbol, company_name, exchange, sector, current_price, daily_change_pct, market_cap")
        .or_(f"symbol.ilike.%{q}%,company_name.ilike.%{q}%")
        .limit(20)
        .execute()
    )
    stocks = result.data or []

    # Enrich with latest prices from stock_prices for any stock missing current_price
    for stock in stocks:
        if stock.get("current_price") is not None:
            continue
        try:
            price_result = (
                db.table("stock_prices")
                .select("close, date")
                .eq("symbol", stock["symbol"])
                .order("date", desc=True)
                .limit(2)
                .execute()
            )
            rows = price_result.data or []
            if rows:
                stock["current_price"] = rows[0]["close"]
                if len(rows) >= 2 and rows[1]["close"] and rows[1]["close"] > 0:
                    change = (rows[0]["close"] - rows[1]["close"]) / rows[1]["close"] * 100
                    stock["daily_change_pct"] = round(change, 2)
                else:
                    stock["daily_change_pct"] = 0.0
        except Exception:
            pass

    return stocks


@router.get("/{symbol}")
def get_stock(symbol: str):
    """Get full details for a stock symbol."""
    db = get_db()
    result = db.table("stocks").select("*").eq("symbol", symbol.upper()).single().execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Stock not found")
    return result.data


@router.get("/{symbol}/history")
def get_stock_history(
    symbol: str,
    period: str = Query("1y", description="1m, 3m, 6m, 1y, 3y, 5y"),
):
    """Get historical OHLCV data for a stock."""
    db = get_db()
    period_days = {"1m": 30, "3m": 90, "6m": 180, "1y": 365, "3y": 1095, "5y": 1825}
    days = period_days.get(period, 365)

    result = (
        db.table("stock_prices")
        .select("date, open, high, low, close, volume")
        .eq("symbol", symbol.upper())
        .order("date", desc=False)
        .limit(days)
        .execute()
    )
    return result.data


@router.get("/indices/summary")
def get_indices_summary():
    """Get current values for major Indian indices (Nifty 50, Sensex, Bank Nifty)."""
    global _indices_cache
    cached, ts = _indices_cache
    if cached and time.time() - ts < _INDICES_TTL:
        return cached

    import yfinance as yf

    INDEX_MAP = {
        "^NSEI": "Nifty 50",
        "^BSESN": "Sensex",
        "^NSEBANK": "Bank Nifty",
    }

    results = []
    for symbol, name in INDEX_MAP.items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")
            if hist.empty:
                continue
            current = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else current
            change = current - prev
            change_pct = (change / prev * 100) if prev > 0 else 0.0
            results.append({
                "symbol": symbol,
                "name": name,
                "current_value": round(current, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
            })
        except Exception as exc:
            logger.warning("Failed to fetch index %s: %s", symbol, exc)

    _indices_cache = (results, time.time())
    return results


@router.get("/sectors/performance")
def get_sector_performance():
    """Get average performance by sector for Indian stocks."""
    db = get_db()
    result = db.rpc("get_sector_performance").execute()
    return result.data
