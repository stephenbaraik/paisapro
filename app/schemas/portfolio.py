"""Pydantic schemas for Watchlist & Portfolio Tracker."""

from typing import Optional
from pydantic import BaseModel, Field


# ── Watchlist ────────────────────────────────────────────────────────────────

class WatchlistItem(BaseModel):
    id: int
    symbol: str
    company_name: str = ""
    sector: str = ""
    current_price: float = 0
    daily_change_pct: float = 0
    added_at: str
    notes: Optional[str] = None


class WatchlistAddRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    notes: Optional[str] = None


class WatchlistResponse(BaseModel):
    items: list[WatchlistItem]
    total: int


# ── Portfolio Holdings ───────────────────────────────────────────────────────

class HoldingInput(BaseModel):
    symbol: str = Field(..., min_length=1)
    quantity: float = Field(..., gt=0)
    buy_price: float = Field(..., gt=0)
    buy_date: str = ""       # YYYY-MM-DD, defaults to today
    notes: Optional[str] = None


class PortfolioHolding(BaseModel):
    id: int
    symbol: str
    company_name: str = ""
    sector: str = ""
    quantity: float
    buy_price: float
    buy_date: str
    current_price: float = 0
    daily_change_pct: float = 0
    pnl: float = 0              # absolute P&L
    pnl_pct: float = 0          # percentage P&L
    market_value: float = 0     # current_price * quantity
    invested_value: float = 0   # buy_price * quantity
    notes: Optional[str] = None


class PortfolioSummary(BaseModel):
    total_invested: float
    total_market_value: float
    total_pnl: float
    total_pnl_pct: float
    holdings_count: int
    best_performer: Optional[str] = None
    worst_performer: Optional[str] = None


class PortfolioResponse(BaseModel):
    holdings: list[PortfolioHolding]
    summary: PortfolioSummary


# ── News Sentiment ───────────────────────────────────────────────────────────

class NewsArticle(BaseModel):
    title: str
    source: str
    url: str
    published_at: str
    sentiment: str               # "POSITIVE" | "NEGATIVE" | "NEUTRAL"
    sentiment_score: float       # -1.0 to 1.0
    symbols: list[str] = []     # related stock symbols


class SentimentSummary(BaseModel):
    symbol: str
    company_name: str
    article_count: int
    avg_sentiment: float         # -1.0 to 1.0
    positive_count: int
    negative_count: int
    neutral_count: int
    sentiment_label: str         # "BULLISH" | "BEARISH" | "NEUTRAL"


# ── AI Portfolio Builder ─────────────────────────────────────────────────────

class AIBuildRequest(BaseModel):
    investment_amount: float = Field(..., gt=0, description="Total investment in INR")
    risk_profile: str = Field("moderate", pattern="^(conservative|moderate|aggressive)$")


class AIPick(BaseModel):
    symbol: str
    company_name: str = ""
    sector: str = ""
    current_price: float = 0
    daily_change_pct: float = 0
    quantity: int = 0
    allocation: float = 0
    weight_pct: float = 0
    reason: str = ""


class AIBuildResponse(BaseModel):
    picks: list[AIPick]
    strategy_summary: str = ""
    risk_notes: str = ""
    total_allocated: float = 0
    cash_remaining: float = 0
    investment_amount: float = 0
    risk_profile: str = ""


class NewsSentimentResponse(BaseModel):
    articles: list[NewsArticle]
    summaries: list[SentimentSummary]
    overall_sentiment: str       # "BULLISH" | "BEARISH" | "NEUTRAL"
    overall_score: float
    generated_at: str
