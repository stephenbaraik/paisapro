"""
AI Advisor service — simple, reliable, beautiful.

Strategy:
  1. Inject ALL live data (market, macro, news, portfolio) directly into system prompt
  2. Make ONE Groq call — no tool calling, no multi-turn loops
  3. Stream response word-by-word
  4. If Groq fails, fall back to a well-formatted cached-data response
"""

import asyncio
import hashlib
import json as _json
import logging
import time
from collections import defaultdict, deque
from typing import AsyncGenerator, Optional

import httpx
from fastapi import HTTPException

from ...core.config import get_settings
from ...schemas.financial import (
    UserFinancialProfile,
    AdvisorChatRequest,
    AdvisorChatResponse,
)

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

MAX_HISTORY = 30
REQUEST_TIMEOUT = 90

# Response cache (5 min TTL)
_response_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL = 300

# ── Input sanitization ────────────────────────────────────────────────────────

def sanitize_input(message: str) -> str:
    message = " ".join(message.split())
    if len(message) > 2000:
        message = message[:2000]
    return message


# ── Response caching ──────────────────────────────────────────────────────────

def _cache_key(message: str, profile_hash: str) -> str:
    return hashlib.sha256(f"{message}|{profile_hash}".encode()).hexdigest()[:16]

def get_cached_response(key: str) -> Optional[str]:
    if key in _response_cache:
        reply, ts = _response_cache[key]
        if time.time() - ts < CACHE_TTL:
            return reply
        del _response_cache[key]
    return None

def set_cached_response(key: str, reply: str) -> None:
    _response_cache[key] = (reply, time.time())


# ── Context builders ──────────────────────────────────────────────────────────

def _build_full_context(request: AdvisorChatRequest) -> str:
    """Build a rich system prompt with ALL live data injected."""
    parts: list[str] = []

    # ── Role ──────────────────────────────────────────────────────────
    parts.append("""# ROLE

You are **PaisaPro AI Advisor** — an expert Indian investment advisor built into PaisaPro.ai.
Help users make informed financial decisions using the real-time data below.

## Rules
- Indian markets: NSE, BSE, Nifty, Sensex, Indian mutual funds, SIPs, PPF, NPS, ELSS
- All values in INR (₹)
- Ground your advice in the data provided. Never invent prices or signals.
- If data is missing, say so.
- Educational first — explain concepts, don't just give answers.
- Consider the user's risk profile and portfolio.
- End every response with this exact blockquote:

> ⚠️ *This is for educational purposes only. Not a SEBI-registered investment advisory service.*
""")

    # ── User profile ──────────────────────────────────────────────────
    profile = request.profile
    if profile:
        surplus = profile.monthly_income - profile.monthly_expenses
        parts.append(f"""## User Financial Profile
- Monthly Income: ₹{profile.monthly_income:,.0f}
- Monthly Expenses: ₹{profile.monthly_expenses:,.0f}
- Investable Surplus: ₹{surplus:,.0f}/month
- Current Savings: ₹{profile.current_savings:,.0f}
- Age: {profile.age} years
- Risk Tolerance: {profile.risk_profile.value.capitalize()}
""")

    # ── Portfolio ─────────────────────────────────────────────────────
    if request.portfolio_holdings:
        total_inv = sum(h.buy_price * h.quantity for h in request.portfolio_holdings)
        total_cur = sum(h.current_price * h.quantity for h in request.portfolio_holdings if h.current_price > 0)
        pnl = ((total_cur - total_inv) / total_inv * 100) if total_inv > 0 else 0
        sectors: dict[str, float] = {}
        for h in request.portfolio_holdings:
            v = h.current_price * h.quantity if h.current_price > 0 else h.buy_price * h.quantity
            sectors[h.sector or "Unknown"] = sectors.get(h.sector or "Unknown", 0) + v
        total_val = sum(sectors.values()) or 1
        holdings_lines = "\n".join(
            f"  - {h.symbol.replace('.NS', '')}: {h.quantity:.0f} shares, ₹{h.current_price:,.0f} ({h.pnl_pct:+.1f}%)"
            for h in sorted(request.portfolio_holdings, key=lambda x: x.pnl_pct, reverse=True)
        )
        sector_lines = "\n".join(
            f"  - {sec}: {val/total_val*100:.0f}%"
            for sec, val in sorted(sectors.items(), key=lambda x: x[1], reverse=True)
        )
        parts.append(f"""## User's Portfolio
- Total Invested: ₹{total_inv:,.0f}
- Current Value: ₹{total_cur:,.0f} ({pnl:+.1f}%)
- Holdings: {len(request.portfolio_holdings)} stocks

{holdings_lines}

### Sector Allocation
{sector_lines}
""")

    # ── Watchlist ─────────────────────────────────────────────────────
    if request.watchlist:
        wl_lines = "\n".join(
            f"  - {w.symbol.replace('.NS', '')}: ₹{w.current_price:,.0f} ({w.daily_change_pct:+.1f}%)"
            for w in request.watchlist
        )
        parts.append(f"""## Watchlist
{wl_lines}
""")

    # ── Market intelligence ───────────────────────────────────────────
    try:
        from ..analytics import get_cached_report
        cached = get_cached_report()
        if cached:
            ov = cached.market_overview
            br = ov.market_breadth
            top_buys = sorted(
                [a for a in cached.stock_analyses if a.technical_signals.composite_signal.value == "BUY"],
                key=lambda a: a.technical_signals.confidence_score, reverse=True,
            )[:5]
            top_sells = sorted(
                [a for a in cached.stock_analyses if a.technical_signals.composite_signal.value == "SELL"],
                key=lambda a: a.technical_signals.confidence_score, reverse=True,
            )[:5]
            best = max(ov.sector_heatmap, key=lambda s: s.avg_change_pct) if ov.sector_heatmap else None
            worst = min(ov.sector_heatmap, key=lambda s: s.avg_change_pct) if ov.sector_heatmap else None
            buys_str = "\n".join(f"  - {a.symbol.replace('.NS', '')} ({a.technical_signals.confidence_score:.0f}%)" for a in top_buys) or "None"
            sells_str = "\n".join(f"  - {a.symbol.replace('.NS', '')} ({a.technical_signals.confidence_score:.0f}%)" for a in top_sells) or "None"
            best_sector = f"{best.sector} ({best.avg_change_pct:+.2f}%)" if best else "N/A"
            worst_sector = f"{worst.sector} ({worst.avg_change_pct:+.2f}%)" if worst else "N/A"
            parts.append(f"""## Live Market Intelligence
- Market Breadth: {br.get('buy', 0)} BUY | {br.get('hold', 0)} HOLD | {br.get('sell', 0)} SELL
- Strongest Sector: {best_sector}
- Weakest Sector: {worst_sector}

### Top BUY Signals
{buys_str}

### Top SELL Signals
{sells_str}
""")
    except Exception as e:
        logger.warning("Market context failed: %s", e)

    # ── Macro ─────────────────────────────────────────────────────────
    try:
        from ...core.cache import cache
        macro = cache.get("macro:dashboard")
        if macro:
            ind_lines = "\n".join(
                f"  - **{ind.name}**: {ind.value:,.2f} ({ind.change_pct:+.1f}%, {ind.trend})"
                for ind in macro.indicators
            )
            parts.append(f"""## Macro Environment
- **Market Regime**: {macro.market_regime}
- {macro.regime_description}

{ind_lines}
""")
    except Exception as e:
        logger.warning("Macro context failed: %s", e)

    # ── News ──────────────────────────────────────────────────────────
    try:
        from ...core.cache import cache
        news = cache.get("news:sentiment")
        if news:
            news_lines = "\n".join(
                f"  - **{s.symbol}**: {s.sentiment_label} ({s.article_count} articles, +{s.positive_count}/-{s.negative_count})"
                for s in news.summaries[:8]
            )
            parts.append(f"""## News Sentiment
- Overall: {news.overall_sentiment.upper()} (score: {news.overall_score:+.2f})

{news_lines}
""")
    except Exception as e:
        logger.warning("News context failed: %s", e)

    return "\n".join(parts)


# ── Fallback response ─────────────────────────────────────────────────────────

def _generate_fallback_response(request: AdvisorChatRequest) -> str:
    """Generate a beautiful markdown response from cached data when Groq is down."""
    lines: list[str] = []

    lines.append("## Market Update")
    lines.append("")
    lines.append("*AI model is temporarily unavailable. Here's the latest data available:*")
    lines.append("")

    # Portfolio
    if request.portfolio_holdings:
        total_inv = sum(h.buy_price * h.quantity for h in request.portfolio_holdings)
        total_cur = sum(h.current_price * h.quantity for h in request.portfolio_holdings if h.current_price > 0)
        pnl = ((total_cur - total_inv) / total_inv * 100) if total_inv > 0 else 0
        lines.append(f"**Portfolio**: ₹{total_inv:,.0f} invested → ₹{total_cur:,.0f} ({pnl:+.1f}%)")
        lines.append("")

    # Macro
    try:
        from ...core.cache import cache
        macro = cache.get("macro:dashboard")
        if macro:
            lines.append("### Macro Environment")
            lines.append(f"- **Regime**: {macro.market_regime}")
            for ind in macro.indicators:
                lines.append(f"- {ind.name}: {ind.value:,.2f} ({ind.change_pct:+.1f}%, {ind.trend})")
            lines.append("")
    except Exception:
        pass

    # Disclaimer
    lines.append("> ⚠️ *This is for educational purposes only. Not a SEBI-registered investment advisory service.*")

    return "\n".join(lines)


# ── Streaming ─────────────────────────────────────────────────────────────────

async def stream_advisor_response(request: AdvisorChatRequest) -> AsyncGenerator[str, None]:
    """Stream AI response. ONE Groq call. Fallback if Groq fails."""
    start = time.time()
    settings = get_settings()

    request.message = sanitize_input(request.message)

    # Cache
    phash = hashlib.md5(request.profile.model_dump_json().encode()).hexdigest()[:16] if request.profile else "none"
    ckey = _cache_key(request.message, phash)
    cached = get_cached_response(ckey)
    if cached:
        for word in cached.split():
            yield f"data: {_json.dumps({'token': word + ' '})}\n\n"
            await asyncio.sleep(0.015)
        yield "data: [DONE]\n\n"
        return

    # Build system prompt with ALL data
    system_prompt = _build_full_context(request)
    messages = [
        {"role": "system", "content": system_prompt},
    ]
    # Add conversation history
    if request.conversation_history:
        for msg in request.conversation_history[-MAX_HISTORY:]:
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})

    headers = {"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"}
    groq_url = settings.groq_url
    groq_model = settings.groq_model

    if not settings.groq_api_key:
        reply = _generate_fallback_response(request)
        set_cached_response(ckey, reply)
        for word in reply.split():
            yield f"data: {_json.dumps({'token': word + ' '})}\n\n"
            await asyncio.sleep(0.015)
        yield "data: [DONE]\n\n"
        return

    # ONE Groq call — no tools, no loops
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(groq_url, headers=headers, json={
                "model": groq_model,
                "messages": messages,
                "max_tokens": 4096,
                "temperature": 0.7,
            })
            resp.raise_for_status()
            data = resp.json()

        reply = (data["choices"][0]["message"].get("content") or "").strip()
        if not reply:
            raise ValueError("Empty response")

        set_cached_response(ckey, reply)
        for word in reply.split():
            yield f"data: {_json.dumps({'token': word + ' '})}\n\n"
            await asyncio.sleep(0.015)

        logger.info("Advisor response in %.2fs", time.time() - start)
        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.warning("Groq failed (%s), using fallback", e)
        reply = _generate_fallback_response(request)
        set_cached_response(ckey, reply)
        for word in reply.split():
            yield f"data: {_json.dumps({'token': word + ' '})}\n\n"
            await asyncio.sleep(0.015)
        yield "data: [DONE]\n\n"


# ── Non-streaming ─────────────────────────────────────────────────────────────

async def get_advisor_response(request: AdvisorChatRequest) -> AdvisorChatResponse:
    """Non-streaming — ONE Groq call."""
    start = time.time()
    settings = get_settings()

    request.message = sanitize_input(request.message)

    phash = hashlib.md5(request.profile.model_dump_json().encode()).hexdigest()[:16] if request.profile else "none"
    ckey = _cache_key(request.message, phash)
    cached = get_cached_response(ckey)
    if cached:
        return AdvisorChatResponse(reply=cached, suggestions=[])

    system_prompt = _build_full_context(request)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in request.conversation_history[-MAX_HISTORY:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})

    headers = {"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"}

    if not settings.groq_api_key:
        reply = _generate_fallback_response(request)
        return AdvisorChatResponse(reply=reply, suggestions=[])

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(settings.groq_url, headers=headers, json={
                "model": settings.groq_model,
                "messages": messages,
                "max_tokens": 4096,
                "temperature": 0.7,
            })
            resp.raise_for_status()
            data = resp.json()

        reply = (data["choices"][0]["message"].get("content") or "").strip()
        if not reply:
            raise ValueError("Empty response")

        set_cached_response(ckey, reply)
        suggestions = [line.strip()[2:] for line in reply.split("\n") if line.strip().startswith("- ") and len(line.strip()) < 100][:3]
        logger.info("Advisor non-stream in %.2fs", time.time() - start)
        return AdvisorChatResponse(reply=reply, suggestions=suggestions)

    except Exception as e:
        logger.warning("Groq failed (%s), fallback", e)
        reply = _generate_fallback_response(request)
        set_cached_response(ckey, reply)
        return AdvisorChatResponse(reply=reply, suggestions=[])
