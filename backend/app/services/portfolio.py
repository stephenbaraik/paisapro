"""
Watchlist & Portfolio Tracker service.

CRUD operations on Supabase watchlist + portfolio_holdings tables,
enriched with live prices from the analytics cache.
"""

import asyncio
import httpx
from datetime import date

from ..core.config import get_settings
from ..core.database import get_db
from ..schemas.portfolio import (
    WatchlistItem, WatchlistResponse, WatchlistAddRequest,
    HoldingInput, PortfolioHolding, PortfolioSummary, PortfolioResponse,
)

USER_ID = "default"  # single-user for now


def _sb_headers(prefer: str = "return=representation"):
    key = get_settings().supabase_service_role_key
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": prefer,
    }


def _sb_url(table: str) -> str:
    return f"{get_settings().supabase_url}/rest/v1/{table}"


def _sb_get(url: str, headers: dict, params: dict) -> list:
    resp = httpx.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _sb_post(url: str, headers: dict, payload: dict) -> dict:
    resp = httpx.post(url, headers=headers, json=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()[0]


def _sb_delete(url: str, headers: dict, params: dict) -> int:
    resp = httpx.delete(url, headers=headers, params=params, timeout=10)
    return resp.status_code


def _batch_latest_prices(symbols: list[str]) -> dict[str, tuple[float, float]]:
    """
    Return {symbol: (price, change_pct)} for all symbols in a single Supabase query.
    Falls back to per-symbol cache lookup first, only queries Supabase for misses.
    """
    result: dict[str, tuple[float, float]] = {}
    missing: list[str] = []

    try:
        from .analytics import _get_cached_df
        for sym in symbols:
            yf_sym = f"{sym}.NS" if not sym.endswith(".NS") else sym
            df = _get_cached_df(yf_sym, "1y")
            if df is not None and len(df) >= 2:
                current = float(df["close"].iloc[-1])
                prev = float(df["close"].iloc[-2])
                change = (current - prev) / prev * 100 if prev > 0 else 0
                result[sym] = (current, round(change, 2))
            else:
                missing.append(sym)
    except Exception:
        missing = list(symbols)

    if not missing:
        return result

    # Batch fetch all missing symbols in one Supabase request using `in.(...)` filter
    try:
        db_syms = [s.replace(".NS", "") for s in missing]
        in_filter = f"in.({','.join(db_syms)})"
        rows = _sb_get(
            _sb_url("stock_prices"),
            _sb_headers(""),
            {"symbol": in_filter, "select": "symbol,close,date", "order": "date.desc"},
        )
        # Keep only the latest 2 rows per symbol
        seen: dict[str, list[float]] = {}
        for row in rows:
            sym = row["symbol"]
            if len(seen.get(sym, [])) < 2:
                seen.setdefault(sym, []).append(float(row["close"]))
        for sym, closes in seen.items():
            if len(closes) >= 2:
                change = (closes[0] - closes[1]) / closes[1] * 100 if closes[1] > 0 else 0
                result[sym] = (closes[0], round(change, 2))
            elif len(closes) == 1:
                result[sym] = (closes[0], 0.0)
    except Exception:
        pass

    return result


def _get_latest_price(symbol: str) -> tuple[float, float]:
    """Single-symbol price lookup (used by add_to_watchlist / add_holding)."""
    return _batch_latest_prices([symbol]).get(symbol, (0.0, 0.0))


def _get_stock_meta(symbol: str) -> tuple[str, str]:
    """Return (company_name, sector) from cache or Supabase."""
    try:
        from .analytics import get_stock_name, get_stock_sector
        yf_sym = f"{symbol}.NS" if not symbol.endswith(".NS") else symbol
        name = get_stock_name(yf_sym)
        sector = get_stock_sector(yf_sym)
        if name:
            return name, sector
    except Exception:
        pass

    try:
        db_sym = symbol.replace(".NS", "")
        db = get_db()
        result = db.table("stocks").select("company_name,sector").eq("symbol", db_sym).limit(1).execute()
        if result.data:
            return result.data[0].get("company_name", ""), result.data[0].get("sector", "")
    except Exception:
        pass
    return "", ""


# ── Watchlist CRUD ───────────────────────────────────────────────────────────

async def get_watchlist() -> WatchlistResponse:
    rows = await asyncio.to_thread(
        _sb_get,
        _sb_url("watchlist"),
        _sb_headers(""),
        {"user_id": f"eq.{USER_ID}", "select": "id,symbol,added_at,notes", "order": "added_at.desc"},
    )

    symbols = [r["symbol"] for r in rows]
    prices = await asyncio.to_thread(_batch_latest_prices, symbols)

    items: list[WatchlistItem] = []
    for row in rows:
        sym = row["symbol"]
        price, change = prices.get(sym, (0.0, 0.0))
        name, sector = _get_stock_meta(sym)
        items.append(WatchlistItem(
            id=row["id"],
            symbol=sym,
            company_name=name,
            sector=sector,
            current_price=round(price, 2),
            daily_change_pct=change,
            added_at=row["added_at"],
            notes=row.get("notes"),
        ))

    return WatchlistResponse(items=items, total=len(items))


async def add_to_watchlist(req: WatchlistAddRequest) -> WatchlistItem:
    sym = req.symbol.upper().replace(".NS", "")
    row = await asyncio.to_thread(
        _sb_post,
        _sb_url("watchlist"),
        _sb_headers("return=representation"),
        {"user_id": USER_ID, "symbol": sym, "notes": req.notes},
    )
    price, change = _get_latest_price(sym)
    name, sector = _get_stock_meta(sym)
    return WatchlistItem(
        id=row["id"], symbol=sym, company_name=name, sector=sector,
        current_price=round(price, 2), daily_change_pct=change,
        added_at=row["added_at"], notes=row.get("notes"),
    )


async def remove_from_watchlist(item_id: int) -> bool:
    status = await asyncio.to_thread(
        _sb_delete,
        _sb_url("watchlist"),
        _sb_headers(""),
        {"id": f"eq.{item_id}", "user_id": f"eq.{USER_ID}"},
    )
    return status in (200, 204)


# ── Portfolio CRUD ───────────────────────────────────────────────────────────

async def get_portfolio() -> PortfolioResponse:
    rows = await asyncio.to_thread(
        _sb_get,
        _sb_url("portfolio_holdings"),
        _sb_headers(""),
        {
            "user_id": f"eq.{USER_ID}",
            "select": "id,symbol,quantity,buy_price,buy_date,notes,created_at",
            "order": "created_at.desc",
        },
    )

    symbols = [r["symbol"] for r in rows]
    prices = await asyncio.to_thread(_batch_latest_prices, symbols)

    holdings: list[PortfolioHolding] = []
    total_invested = 0.0
    total_market = 0.0
    best: tuple[str, float] = ("", -999)
    worst: tuple[str, float] = ("", 999)

    for row in rows:
        sym = row["symbol"]
        qty = float(row["quantity"])
        buy_px = float(row["buy_price"])
        price, change = prices.get(sym, (0.0, 0.0))
        name, sector = _get_stock_meta(sym)

        invested = buy_px * qty
        market = price * qty
        pnl = market - invested
        pnl_pct = (pnl / invested * 100) if invested > 0 else 0

        total_invested += invested
        total_market += market

        if pnl_pct > best[1]:
            best = (sym, pnl_pct)
        if pnl_pct < worst[1]:
            worst = (sym, pnl_pct)

        holdings.append(PortfolioHolding(
            id=row["id"], symbol=sym, company_name=name, sector=sector,
            quantity=qty, buy_price=buy_px,
            buy_date=str(row["buy_date"]),
            current_price=round(price, 2), daily_change_pct=change,
            pnl=round(pnl, 2), pnl_pct=round(pnl_pct, 2),
            market_value=round(market, 2), invested_value=round(invested, 2),
            notes=row.get("notes"),
        ))

    total_pnl = total_market - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    summary = PortfolioSummary(
        total_invested=round(total_invested, 2),
        total_market_value=round(total_market, 2),
        total_pnl=round(total_pnl, 2),
        total_pnl_pct=round(total_pnl_pct, 2),
        holdings_count=len(holdings),
        best_performer=best[0] if best[0] else None,
        worst_performer=worst[0] if worst[0] else None,
    )

    return PortfolioResponse(holdings=holdings, summary=summary)


async def add_holding(req: HoldingInput) -> PortfolioHolding:
    sym = req.symbol.upper().replace(".NS", "")
    buy_date = req.buy_date if req.buy_date else str(date.today())

    row = await asyncio.to_thread(
        _sb_post,
        _sb_url("portfolio_holdings"),
        _sb_headers("return=representation"),
        {
            "user_id": USER_ID,
            "symbol": sym,
            "quantity": req.quantity,
            "buy_price": req.buy_price,
            "buy_date": buy_date,
            "notes": req.notes,
        },
    )

    price, change = _get_latest_price(sym)
    name, sector = _get_stock_meta(sym)
    invested = req.buy_price * req.quantity
    market = price * req.quantity
    pnl = market - invested

    return PortfolioHolding(
        id=row["id"], symbol=sym, company_name=name, sector=sector,
        quantity=req.quantity, buy_price=req.buy_price, buy_date=buy_date,
        current_price=round(price, 2), daily_change_pct=change,
        pnl=round(pnl, 2), pnl_pct=round(pnl / invested * 100 if invested > 0 else 0, 2),
        market_value=round(market, 2), invested_value=round(invested, 2),
        notes=req.notes,
    )


async def remove_holding(holding_id: int) -> bool:
    status = await asyncio.to_thread(
        _sb_delete,
        _sb_url("portfolio_holdings"),
        _sb_headers(""),
        {"id": f"eq.{holding_id}", "user_id": f"eq.{USER_ID}"},
    )
    return status in (200, 204)
