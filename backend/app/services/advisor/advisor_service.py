"""
AI Advisor service — beautiful, reliable, OpenRouter-only.

Strategy:
  1. Inject ALL live data (market, macro, news, portfolio) into system prompt
  2. ONE OpenRouter call — no tool calling, no loops
  3. Tries Llama 3.3 70B first, falls back to Gemini 2.0 Flash
  4. If both fail → beautiful cached-data response
  5. Stream response word-by-word
"""

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

# FORMAT — STRICT RULES

## Structure
1. Start with a clear **## heading** that directly answers the user's question.
2. Use **short paragraphs** (1-2 sentences) to introduce concepts.
3. Use **tables** for any comparison, breakdown, or structured data with 2+ rows.
4. Use **bullet lists** (`- `) for simple enumerations.
5. Use **numbered lists** (`1. 2. 3.`) only for sequential steps or ranked priorities.
6. Always put a **blank line** between every heading, paragraph, list, and table.

## Tables
- Use tables for: investment breakdowns, option comparisons, step-by-step plans, portfolio allocations.
- Format: pipe-delimited with header row and separator row.
- Align numbers to the right, text to the left.
- Keep columns concise — one idea per cell.

## Numbers & Math
- Always format currency with commas and symbol: **₹15,000** not "15000" or "15k".
- For large amounts: **₹2,00,00,000** (Indian numbering) or **₹2 crore** — be consistent.
- Percentages: **12%** not "12 percent".
- Show calculations in a clear step-by-step format:
  ```
  Monthly SIP = Target / [((1 + r)^n - 1) / r]
              = ₹2,00,00,000 / [((1.01)^420 - 1) / 0.01]
              = ₹15,000/month
  ```
- Round to sensible precision: ₹15,000 not ₹14,987.32.

## Typography
- Use **bold** for key numbers, amounts, and section labels — never full sentences.
- Use `code blocks` only for formulas or specific calculations.
- Use *italics* sparingly for emphasis.
- Never use inline code for regular text.

## Tone & Style
- Write in clear, simple English. No jargon without explanation.
- Be encouraging but realistic.
- Use active voice.
- Each section should be scannable — a reader should get the gist in 5 seconds.

## Ending
End every response with this exact blockquote:

> ⚠️ *This is for educational purposes only. Not a SEBI-registered investment advisory service.*

---

## GOOD FORMAT EXAMPLE

## Retirement Corpus: ₹2 Crore by Age 60

Here is your personalized plan based on your profile.

### Key Parameters

| Parameter | Value |
|-----------|-------|
| Current age | 25 years |
| Retirement age | 60 years |
| Time horizon | 35 years |
| Monthly surplus | ₹50,000 |
| Risk tolerance | Aggressive |

### Monthly Investment Needed

Assuming **12% annual return** (aggressive equity portfolio):

| Target Corpus | Monthly SIP | Total Invested | Wealth Gained |
|--------------|-------------|----------------|---------------|
| ₹2 crore | ₹15,000 | ₹63 lakh | ₹1.37 crore |
| ₹2.5 crore | ₹19,000 | ₹80 lakh | ₹1.70 crore |

### Recommended Strategy

| Step | Action | Amount | Why |
|------|--------|--------|-----|
| 1 | NPS Tier I | ₹5,000/month | Tax benefit under 80CCD |
| 2 | Equity SIP (large cap) | ₹5,000/month | Core growth engine |
| 3 | Equity SIP (mid/small cap) | ₹5,000/month | Higher growth, higher risk |

### Why This Works

- **Power of compounding**: 35 years gives your money time to grow exponentially
- **₹1.37 crore** of your ₹2 crore comes from investment gains, not your own money
- Starting at 25 vs 35 means you invest **₹15,000/month** instead of **₹50,000/month** for the same goal

### Next Steps

1. Open an NPS account (if you don't have one)
2. Start a ₹10,000 equity SIP split between large-cap and mid-cap funds
3. Review your portfolio every 6 months and rebalance

> ⚠️ *This is for educational purposes only. Not a SEBI-registered investment advisory service.*

---

## BAD FORMAT (never do this)

To determine how much you should invest in ELSS, let's break it down. 1. Section 80C Limit: The total deduction is limited to ₹1.5 lakhs. 2. Your Investable Surplus: You have ₹50,000/month which translates to ₹6 lakhs/year. 3. Tax Savings Goal: Since you want to save tax under 80C, we'll focus on utilizing the ₹1.5 lakhs limit. Considering your aggressive risk tolerance and the fact that ELSS funds have a lock-in period of 3 years, you can invest a significant portion of the ₹1.5 lakhs limit in ELSS.

# ALWAYS FOLLOW THE GOOD FORMAT EXAMPLE. USE TABLES, PROPER NUMBERS, AND CLEAR STRUCTURE.
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
    """
    Stream AI response using TRUE OpenRouter SSE streaming.
    Time-to-first-token: ~500 ms. No artificial delays.

    - Cache hit  → send full reply instantly as one token.
    - Cache miss → stream tokens live from OpenRouter, try each model in order.
    - All fail   → stream fallback response from cached market data.
    """
    start = time.time()
    settings = get_settings()
    request.message = sanitize_input(request.message)

    # ── Cache hit: send instantly ─────────────────────────────────────────────
    phash = hashlib.md5(request.profile.model_dump_json().encode()).hexdigest()[:16] if request.profile else "none"
    ckey = _cache_key(request.message, phash)
    cached = get_cached_response(ckey)
    if cached:
        yield f"data: {_json.dumps({'token': cached})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # ── Build messages ────────────────────────────────────────────────────────
    system_prompt = _build_full_context(request)
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for msg in request.conversation_history[-MAX_HISTORY:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})

    if not settings.openrouter_api_key:
        reply = _generate_fallback_response(request)
        yield f"data: {_json.dumps({'token': reply})}\n\n"
        yield "data: [DONE]\n\n"
        return

    or_headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://stephenbaraik-paisapro.hf.space",
        "X-Title": "PaisaPro AI Advisor",
    }

    # ── Try each model; stream tokens as they arrive ──────────────────────────
    reply_chunks: list[str] = []

    for model in OPENROUTER_MODELS:
        reply_chunks = []
        model_ok = False

        client = httpx.AsyncClient(timeout=httpx.Timeout(REQUEST_TIMEOUT, connect=10.0))
        try:
            async with client.stream(
                "POST",
                settings.openrouter_url,
                headers=or_headers,
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 4096,
                    "temperature": 0.7,
                    "stream": True,
                },
            ) as resp:
                if resp.status_code != 200:
                    await resp.aread()
                    logger.warning("OpenRouter (%s) HTTP %d — trying next", model, resp.status_code)
                else:
                    line_buf = ""
                    async for chunk in resp.aiter_text():
                        line_buf += chunk
                        while "\n" in line_buf:
                            line, line_buf = line_buf.split("\n", 1)
                            line = line.strip()
                            if not line.startswith("data: "):
                                continue
                            raw = line[6:].strip()
                            if raw == "[DONE]":
                                model_ok = True
                                break
                            try:
                                obj = _json.loads(raw)
                                token = (obj["choices"][0]["delta"].get("content") or "")
                                if token:
                                    reply_chunks.append(token)
                                    yield f"data: {_json.dumps({'token': token})}\n\n"
                            except (_json.JSONDecodeError, KeyError, IndexError):
                                pass
                    if reply_chunks:
                        model_ok = True
        except httpx.RequestError as e:
            logger.warning("OpenRouter (%s) request error: %s", model, e)
        finally:
            await client.aclose()

        if model_ok:
            logger.info("OpenRouter streamed via %s in %.2fs", model, time.time() - start)
            break

    # ── Fallback if all models failed ─────────────────────────────────────────
    if not reply_chunks:
        logger.warning("All OpenRouter models failed — using fallback")
        reply = _generate_fallback_response(request)
        yield f"data: {_json.dumps({'token': reply})}\n\n"
    else:
        set_cached_response(ckey, "".join(reply_chunks))

    logger.info("Advisor stream done in %.2fs", time.time() - start)
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
