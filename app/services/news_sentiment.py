"""
News Sentiment Analysis service.

Fetches financial headlines from Google News RSS (free, no API key),
scores sentiment using a keyword-based approach, and aggregates by stock.
"""

import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from .analytics import get_stock_universe, get_stock_name, get_stock_sector
from ..schemas.portfolio import (
    NewsArticle, SentimentSummary, NewsSentimentResponse,
)

_cache: tuple[NewsSentimentResponse | None, float] = (None, 0.0)
_CACHE_TTL = 1800  # 30 minutes

# ── Sentiment keyword lists ──────────────────────────────────────────────────

POSITIVE_WORDS = {
    "surge", "surges", "surging", "rally", "rallies", "rallied", "gain", "gains",
    "jump", "jumps", "jumped", "rise", "rises", "rose", "soar", "soars",
    "bullish", "upgrade", "upgraded", "outperform", "buy", "growth", "profit",
    "profitable", "positive", "boost", "boosted", "record", "high", "strong",
    "strength", "recovery", "recover", "recovered", "beat", "beats", "exceeds",
    "dividend", "bonus", "breakout", "uptick", "uptrend", "optimistic",
    "momentum", "expand", "expansion", "robust",
}

NEGATIVE_WORDS = {
    "crash", "crashes", "crashed", "fall", "falls", "fell", "drop", "drops",
    "dropped", "plunge", "plunges", "plunged", "decline", "declines", "declined",
    "bearish", "downgrade", "downgraded", "sell", "loss", "losses", "negative",
    "weak", "weakness", "slump", "slumps", "slumped", "cut", "cuts",
    "concern", "risk", "risky", "warning", "warn", "warns", "crisis",
    "default", "fraud", "scam", "penalty", "fine", "fined", "debt",
    "downturn", "recession", "volatility", "correction", "tank", "tanks",
    "underperform", "miss", "misses", "missed", "disappointing",
}

# Top Indian stocks to track news for
TOP_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "AXISBANK", "BAJFINANCE", "MARUTI", "TITAN",
    "SUNPHARMA", "TATAMOTORS", "WIPRO", "ADANIENT", "HCLTECH",
    "NTPC", "POWERGRID", "ONGC", "TATASTEEL", "JSWSTEEL",
]

SYMBOL_ALIASES = {
    "RELIANCE": ["reliance", "reliance industries", "ril"],
    "TCS": ["tcs", "tata consultancy"],
    "HDFCBANK": ["hdfc bank", "hdfc"],
    "INFY": ["infosys", "infy"],
    "ICICIBANK": ["icici bank", "icici"],
    "HINDUNILVR": ["hindustan unilever", "hul"],
    "ITC": ["itc"],
    "SBIN": ["sbi", "state bank"],
    "BHARTIARTL": ["bharti airtel", "airtel"],
    "KOTAKBANK": ["kotak", "kotak mahindra"],
    "LT": ["larsen", "l&t"],
    "AXISBANK": ["axis bank"],
    "BAJFINANCE": ["bajaj finance", "bajaj finserv"],
    "MARUTI": ["maruti", "maruti suzuki"],
    "TITAN": ["titan"],
    "SUNPHARMA": ["sun pharma", "sun pharmaceutical"],
    "TATAMOTORS": ["tata motors"],
    "WIPRO": ["wipro"],
    "ADANIENT": ["adani", "adani enterprises"],
    "HCLTECH": ["hcl tech", "hcl technologies"],
    "NTPC": ["ntpc"],
    "POWERGRID": ["power grid"],
    "ONGC": ["ongc"],
    "TATASTEEL": ["tata steel"],
    "JSWSTEEL": ["jsw steel", "jsw"],
}


def _score_sentiment(text: str) -> tuple[str, float]:
    """Score sentiment of a text using keyword matching. Returns (label, score)."""
    words = set(re.findall(r'[a-z]+', text.lower()))
    pos = len(words & POSITIVE_WORDS)
    neg = len(words & NEGATIVE_WORDS)

    if pos == 0 and neg == 0:
        return "NEUTRAL", 0.0

    total = pos + neg
    score = (pos - neg) / total  # -1.0 to 1.0

    if score > 0.15:
        return "POSITIVE", round(score, 3)
    elif score < -0.15:
        return "NEGATIVE", round(score, 3)
    return "NEUTRAL", round(score, 3)


def _match_symbols(text: str) -> list[str]:
    """Match stock symbols mentioned in text."""
    text_lower = text.lower()
    matched = []
    for sym, aliases in SYMBOL_ALIASES.items():
        for alias in aliases:
            if alias in text_lower:
                matched.append(sym)
                break
    return matched


def _fetch_google_news_rss(query: str, num: int = 15) -> list[dict]:
    """Fetch news from Google News RSS (free, no API key)."""
    url = f"https://news.google.com/rss/search?q={quote(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True)
        if resp.status_code != 200:
            return []

        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
        articles = []

        for item in items[:num]:
            title = item.findtext("title", "")
            source = item.findtext("source", "Unknown")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")

            if title:
                articles.append({
                    "title": title,
                    "source": source,
                    "url": link,
                    "published_at": pub_date,
                })
        return articles
    except Exception:
        return []


async def get_news_sentiment(force: bool = False) -> NewsSentimentResponse:
    global _cache
    cached, ts = _cache
    if cached and not force and time.time() - ts < _CACHE_TTL:
        return cached

    all_articles: list[NewsArticle] = []
    seen_titles: set[str] = set()

    # Fetch news for Indian stock market + individual top stocks
    queries = [
        "Indian stock market Nifty BSE NSE",
        "Nifty 50 Sensex today",
        "Indian stocks earnings results",
    ]
    # Add top 10 stocks individually
    for sym in TOP_SYMBOLS[:10]:
        aliases = SYMBOL_ALIASES.get(sym, [sym.lower()])
        queries.append(f"{aliases[0]} stock NSE")

    for query in queries:
        raw_articles = _fetch_google_news_rss(query, num=10)
        for art in raw_articles:
            title = art["title"]
            if title in seen_titles:
                continue
            seen_titles.add(title)

            sentiment, score = _score_sentiment(title)
            symbols = _match_symbols(title)

            all_articles.append(NewsArticle(
                title=title,
                source=art["source"],
                url=art["url"],
                published_at=art["published_at"],
                sentiment=sentiment,
                sentiment_score=score,
                symbols=symbols,
            ))

    # Sort by recency (most recent first)
    all_articles.sort(key=lambda a: a.published_at, reverse=True)

    # Limit to 50 articles
    all_articles = all_articles[:50]

    # Build per-symbol sentiment summaries
    sym_articles: dict[str, list[NewsArticle]] = {}
    for art in all_articles:
        for sym in art.symbols:
            sym_articles.setdefault(sym, []).append(art)

    summaries: list[SentimentSummary] = []
    for sym in TOP_SYMBOLS:
        arts = sym_articles.get(sym, [])
        if not arts:
            continue

        pos = sum(1 for a in arts if a.sentiment == "POSITIVE")
        neg = sum(1 for a in arts if a.sentiment == "NEGATIVE")
        neu = sum(1 for a in arts if a.sentiment == "NEUTRAL")
        avg_score = sum(a.sentiment_score for a in arts) / len(arts)

        label = "BULLISH" if avg_score > 0.1 else "BEARISH" if avg_score < -0.1 else "NEUTRAL"

        name = get_stock_name(f"{sym}.NS") or sym
        summaries.append(SentimentSummary(
            symbol=sym,
            company_name=name,
            article_count=len(arts),
            avg_sentiment=round(avg_score, 3),
            positive_count=pos,
            negative_count=neg,
            neutral_count=neu,
            sentiment_label=label,
        ))

    # Sort by article count (most mentioned first)
    summaries.sort(key=lambda s: s.article_count, reverse=True)

    # Overall sentiment
    if all_articles:
        overall_score = sum(a.sentiment_score for a in all_articles) / len(all_articles)
    else:
        overall_score = 0.0
    overall = "BULLISH" if overall_score > 0.1 else "BEARISH" if overall_score < -0.1 else "NEUTRAL"

    result = NewsSentimentResponse(
        articles=all_articles,
        summaries=summaries,
        overall_sentiment=overall,
        overall_score=round(overall_score, 3),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    _cache = (result, time.time())
    return result
