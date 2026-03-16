"""API routes for Watchlist, Portfolio Tracker, and News Sentiment."""

from fastapi import APIRouter, HTTPException, Query

from ...schemas.portfolio import (
    WatchlistResponse, WatchlistAddRequest, WatchlistItem,
    PortfolioResponse, HoldingInput, PortfolioHolding,
    NewsSentimentResponse,
    AIBuildRequest, AIBuildResponse,
)
from ...services.portfolio import (
    get_watchlist, add_to_watchlist, remove_from_watchlist,
    get_portfolio, add_holding, remove_holding,
)
from ...services.news_sentiment import get_news_sentiment

router = APIRouter(prefix="/portfolio", tags=["Portfolio & Watchlist"])


# ── Watchlist ────────────────────────────────────────────────────────────────

@router.get("/watchlist", response_model=WatchlistResponse)
async def list_watchlist():
    """Get all watchlist items with live prices."""
    try:
        return await get_watchlist()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/watchlist", response_model=WatchlistItem)
async def add_watchlist(req: WatchlistAddRequest):
    """Add a stock to the watchlist."""
    try:
        return await add_to_watchlist(req)
    except Exception as e:
        detail = str(e)
        if "duplicate" in detail.lower() or "unique" in detail.lower() or "409" in detail:
            raise HTTPException(status_code=409, detail="Stock already in watchlist")
        raise HTTPException(status_code=500, detail=detail)


@router.delete("/watchlist/{item_id}")
async def delete_watchlist(item_id: int):
    """Remove a stock from the watchlist."""
    ok = await remove_from_watchlist(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"ok": True}


# ── Portfolio Holdings ───────────────────────────────────────────────────────

@router.get("/holdings", response_model=PortfolioResponse)
async def list_holdings():
    """Get all portfolio holdings with live P&L."""
    try:
        return await get_portfolio()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/holdings", response_model=PortfolioHolding)
async def create_holding(req: HoldingInput):
    """Add a new holding to the portfolio."""
    try:
        return await add_holding(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/holdings/{holding_id}")
async def delete_holding(holding_id: int):
    """Remove a holding from the portfolio."""
    ok = await remove_holding(holding_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Holding not found")
    return {"ok": True}


# ── AI Portfolio Builder ─────────────────────────────────────────────────────

@router.post("/ai-build", response_model=AIBuildResponse)
async def ai_build(req: AIBuildRequest):
    """Use AI to select stocks and allocate quantities for a portfolio."""
    from ...services.ai_portfolio import ai_build_portfolio
    try:
        return await ai_build_portfolio(req.investment_amount, req.risk_profile)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── News Sentiment ───────────────────────────────────────────────────────────

@router.get("/news-sentiment", response_model=NewsSentimentResponse)
async def news_sentiment(force: bool = Query(False)):
    """Aggregated news sentiment for Indian stocks."""
    try:
        return await get_news_sentiment(force=force)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
