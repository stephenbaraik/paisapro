"""
AI Advisor service — beautiful, reliable, OpenRouter-only.

Strategy:
  1. Inject ALL live data (market, macro, news, portfolio) into system prompt
  2. ONE OpenRouter call — no tool calling, no loops
  3. Tries Llama 3.3 70B first, falls back to Gemini 2.0 Flash
  4. If both fail → beautiful cached-data response
  5. Stream response word-by-word
"""

import asyncio
import hashlib
import json as _json
import logging
import time
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

# ── Configuration ────────────────────────────────────────────────────────────

MAX_HISTORY = 30
REQUEST_TIMEOUT = 90
CACHE_TTL = 300

# Response cache
_response_cache: dict[str, tuple[str, float]] = {}

# OpenRouter models (in order of preference)
# NOTE: These model IDs work without the :free suffix on OpenRouter
OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct",      # Best quality Llama
    "meta-llama/llama-3.1-70b-instruct",       # Fallback Llama 70B
    "meta-llama/llama-3.1-8b-instruct",        # Fast fallback Llama 8B
]

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


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_RULES = """\
# ROLE
You are **PaisaPro AI Advisor** — an expert Indian investment advisor inside PaisaPro.ai.
Help users make informed financial decisions using the real-time data provided below.

# CONTEXT
- Markets: NSE, BSE, Nifty, Sensex, Indian mutual funds, SIPs, PPF, NPS, ELSS
- All values in INR (₹)
- Ground every answer in the data provided. Never invent numbers.
- If data is missing, say so honestly.
- Always consider the user's risk profile and portfolio.
- Be educational — explain the "why" behind every suggestion.

# FORMAT — THIS IS CRITICAL
Your output is rendered as Markdown. Follow these rules STRICTLY:

1. **Every section starts with a heading** using `## ` (two hashes + space).
2. **Always use bullet lists** (`- `) for points. Never use numbered lists unless the user explicitly asks for steps.
3. **Each bullet is ONE short line** — max 12-15 words. Never put multiple sentences on one line.
4. **Put one blank line** between every heading, list, paragraph, and blockquote.
5. **Keep paragraphs to 1-2 sentences max.** Break long thoughts into bullets.
6. **Use bold** (`**text**`) only for key terms, amounts, or stock names — never entire sentences.
7. **Use italics** (`*text*`) only for emphasis on single words.
8. **Never use inline code** (backticks) unless showing a specific number or ticker symbol.
9. **End every response** with this exact blockquote on its own line:

> ⚠️ *This is for educational purposes only. Not a SEBI-registered investment advisory service.*

# BAD FORMAT EXAMPLE (never do this)
To determine how much you should invest in ELSS, let's break it down. 1. Section 80C Limit: The total deduction is limited to ₹1.5 lakhs. 2. Your Investable Surplus: You have ₹50,000/month which translates to ₹6 lakhs/year. 3. Tax Savings Goal: Since you want to save tax under 80C, we'll focus on utilizing the ₹1.5 lakhs limit.

# GOOD FORMAT EXAMPLE (always do this)
## How Much to Invest in ELSS

Here is the breakdown:

- **Section 80C limit**: ₹1.5 lakhs per year
- **Your investable surplus**: ₹50,000/month (₹6 lakhs/year)
- **Recommended ELSS investment**: ₹1.5 lakhs (full limit)
- **Monthly SIP equivalent**: ₹12,500/month

## Why ELSS

- Lock-in period of 3 years — shorter than PPF
- Tax deduction under Section 80C
- Equity-linked — higher growth potential
- Matches your **aggressive** risk profile

> ⚠️ *This is for educational purposes only. Not a SEBI-registered investment advisory service.*

# STYLE
- Use simple, clear language. No jargon without explanation.
- Be encouraging but realistic.
- When recommending, explain the reasoning.
- Use tables only when comparing 3+ items side by side.
"""


# ── Context builders ──────────────────────────────────────────────────────────

def _build_full_context(request: AdvisorChatRequest) -> str:
    """Build system prompt: rules + live data."""
    parts: list[str] = [SYSTEM_RULES]

    # User profile
    profile = request.profile
    if profile:
        surplus = profile.monthly_income - profile.monthly_expenses
        parts.append(f"""\n## User Financial Profile

- **Monthly income**: ₹{profile.monthly_income:,.0f}
- **Monthly expenses**: ₹{profile.monthly_expenses:,.0f}
- **Investable surplus**: ₹{surplus:,.0f}/month
- **Current savings**: ₹{profile.current_savings:,.0f}
- **Age**: {profile.age} years
- **Risk tolerance**: {profile.risk_profile.value.capitalize()}
""")

    # Portfolio
    if request.portfolio_holdings:
        total_inv = sum(h.buy_price * h.quantity for h in request.portfolio_holdings)
        total_cur = sum(h.current_price * h.quantity for h in request.portfolio_holdings if h.current_price > 0)
        pnl = ((total_cur - total_inv) / total_inv * 100) if total_inv > 0 else 0
        sectors: dict[str, float] = {}
        for h in request.portfolio_holdings:
            v = h.current_price * h.quantity if h.current_price > 0 else h.buy_price * h.quantity
            sectors[h.sector or "Unknown"] = sectors.get(h.sector or "Unknown", 0) + v
        total_val = sum(sectors.values()) or 1
        holdings = "\n".join(
            f"  - {h.symbol.replace('.NS', '')}: {h.quantity:.0f} shares at ₹{h.current_price:,.0f} ({h.pnl_pct:+.1f}%)"
            for h in sorted(request.portfolio_holdings, key=lambda x: x.pnl_pct, reverse=True)
        )
        sector_alloc = "\n".join(
            f"  - {sec}: {val/total_val*100:.0f}%"
            for sec, val in sorted(sectors.items(), key=lambda x: x[1], reverse=True)
        )
        parts.append(f"""\n## User's Portfolio

- **Total invested**: ₹{total_inv:,.0f}
- **Current value**: ₹{total_cur:,.0f} ({pnl:+.1f}%)
- **Holdings**: {len(request.portfolio_holdings)} stocks

### Stocks Held
{holdings}

### Sector Allocation
{sector_alloc}
""")

    # Watchlist
    if request.watchlist:
        wl = "\n".join(
            f"  - {w.symbol.replace('.NS', '')}: ₹{w.current_price:,.0f} ({w.daily_change_pct:+.1f}%)"
            for w in request.watchlist
        )
        parts.append(f"""\n## Watchlist

{wl}
""")

    # Market intelligence
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
            buys = "\n".join(f"  - {a.symbol.replace('.NS', '')} ({a.technical_signals.confidence_score:.0f}% confidence)" for a in top_buys) or "None"
            sells = "\n".join(f"  - {a.symbol.replace('.NS', '')} ({a.technical_signals.confidence_score:.0f}% confidence)" for a in top_sells) or "None"
            best_sector = f"{best.sector} ({best.avg_change_pct:+.2f}%)" if best else "N/A"
            worst_sector = f"{worst.sector} ({worst.avg_change_pct:+.2f}%)" if worst else "N/A"
            parts.append(f"""\n## Live Market Intelligence

- **Market breadth**: {br.get('buy', 0)} BUY | {br.get('hold', 0)} HOLD | {br.get('sell', 0)} SELL
- **Strongest sector**: {best_sector}
- **Weakest sector**: {worst_sector}

### Top BUY Signals
{buys}

### Top SELL Signals
{sells}
""")
    except Exception as e:
        logger.warning("Market context failed: %s", e)

    # Macro
    try:
        from ...core.cache import cache
        macro = cache.get("macro:dashboard")
        if macro:
            inds = "\n".join(
                f"  - **{ind.name}**: {ind.value:,.2f} ({ind.change_pct:+.1f}%, {ind.trend})"
                for ind in macro.indicators
            )
            parts.append(f"""\n## Macro Environment

- **Market regime**: {macro.market_regime}
- {macro.regime_description}

### Indicators
{inds}
""")
    except Exception as e:
        logger.warning("Macro context failed: %s", e)

    # News
    try:
        from ...core.cache import cache
        news = cache.get("news:sentiment")
        if news:
            nl = "\n".join(
                f"  - **{s.symbol}**: {s.sentiment_label} ({s.article_count} articles)"
                for s in news.summaries[:8]
            )
            parts.append(f"""\n## News Sentiment

- **Overall**: {news.overall_sentiment.upper()} (score: {news.overall_score:+.2f})

{nl}
""")
    except Exception as e:
        logger.warning("News context failed: %s", e)

    return "\n".join(parts)


# ── Fallback response ─────────────────────────────────────────────────────────

def _generate_fallback_response(request: AdvisorChatRequest) -> str:
    """Beautiful markdown from cached data when all LLMs are down."""
    lines: list[str] = []
    lines.append("## Market Update")
    lines.append("")
    lines.append("*AI model is temporarily unavailable. Here's the latest data:*")
    lines.append("")

    if request.portfolio_holdings:
        ti = sum(h.buy_price * h.quantity for h in request.portfolio_holdings)
        tc = sum(h.current_price * h.quantity for h in request.portfolio_holdings if h.current_price > 0)
        pnl = ((tc - ti) / ti * 100) if ti > 0 else 0
        lines.append(f"- **Portfolio**: ₹{ti:,.0f} → ₹{tc:,.0f} ({pnl:+.1f}%)")
        lines.append("")

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

    lines.append("> ⚠️ *This is for educational purposes only. Not a SEBI-registered investment advisory service.*")
    return "\n".join(lines)


# ── OpenRouter call ───────────────────────────────────────────────────────────

async def _call_openrouter(settings, messages: list, model: str) -> Optional[str]:
    """Call OpenRouter with a specific model. Returns reply or None."""
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(
                settings.openrouter_url,
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://stephenbaraik-paisapro.hf.space",
                    "X-Title": "PaisaPro AI Advisor",
                },
                json={"model": model, "messages": messages, "max_tokens": 4096, "temperature": 0.7},
            )
            resp.raise_for_status()
            data = resp.json()
        reply = (data["choices"][0]["message"].get("content") or "").strip()
        return reply if reply else None
    except Exception as e:
        logger.warning("OpenRouter (%s) failed: %s", model, e)
        return None


# ── Streaming ─────────────────────────────────────────────────────────────────

async def stream_advisor_response(request: AdvisorChatRequest) -> AsyncGenerator[str, None]:
    """Stream AI response. OpenRouter only — tries Llama then Gemini."""
    start = time.time()
    settings = get_settings()
    request.message = sanitize_input(request.message)

    # Cache check
    phash = hashlib.md5(request.profile.model_dump_json().encode()).hexdigest()[:16] if request.profile else "none"
    ckey = _cache_key(request.message, phash)
    cached = get_cached_response(ckey)
    if cached:
        for word in cached.split():
            yield f"data: {_json.dumps({'token': word + ' '})}\n\n"
            await asyncio.sleep(0.015)
        yield "data: [DONE]\n\n"
        return

    # Build messages
    system_prompt = _build_full_context(request)
    messages = [{"role": "system", "content": system_prompt}]
    for msg in request.conversation_history[-MAX_HISTORY:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})

    # Try each model in order
    reply = None
    for model in OPENROUTER_MODELS:
        if not settings.openrouter_api_key:
            break
        reply = await _call_openrouter(settings, messages, model)
        if reply:
            logger.info("OpenRouter reply via %s", model)
            break

    # Fallback to cached data
    if not reply:
        logger.warning("All LLMs failed, using fallback")
        reply = _generate_fallback_response(request)

    set_cached_response(ckey, reply)
    for word in reply.split():
        yield f"data: {_json.dumps({'token': word + ' '})}\n\n"
        await asyncio.sleep(0.015)

    logger.info("Advisor response in %.2fs", time.time() - start)
    yield "data: [DONE]\n\n"


# ── Non-streaming ─────────────────────────────────────────────────────────────

async def get_advisor_response(request: AdvisorChatRequest) -> AdvisorChatResponse:
    """Non-streaming — OpenRouter only."""
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

    # Try each model in order
    reply = None
    for model in OPENROUTER_MODELS:
        if not settings.openrouter_api_key:
            break
        reply = await _call_openrouter(settings, messages, model)
        if reply:
            break

    # Fallback to cached data
    if not reply:
        logger.warning("All LLMs failed, using fallback")
        reply = _generate_fallback_response(request)

    set_cached_response(ckey, reply)
    suggestions = [line.strip()[2:] for line in reply.split("\n") if line.strip().startswith("- ") and len(line.strip()) < 100][:3]
    logger.info("Advisor non-stream in %.2fs", time.time() - start)
    return AdvisorChatResponse(reply=reply, suggestions=suggestions)
