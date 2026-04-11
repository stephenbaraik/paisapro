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

# Groq models — primary path (ultra-fast streaming, ~300-500ms TTFT)
# llama-3.1-8b-instant has a SEPARATE higher rate-limit quota from the 70B model
GROQ_MODELS = [
    "llama-3.1-8b-instant",      # Primary: fastest, highest rate limits
    "llama-3.3-70b-versatile",   # Secondary: higher quality, lower daily limit
]

# OpenRouter models — fallback when Groq is rate-limited or unavailable
OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct",
    "meta-llama/llama-3.1-8b-instruct",
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

async def _stream_from_provider(
    url: str,
    headers: dict,
    payload: dict,
    model: str,
) -> AsyncGenerator[str, None]:
    """
    Inner generator: streams SSE tokens from any OpenAI-compatible endpoint.
    Yields token strings. Raises on HTTP error or request failure.
    """
    client = httpx.AsyncClient(timeout=httpx.Timeout(REQUEST_TIMEOUT, connect=10.0))
    try:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            if resp.status_code != 200:
                await resp.aread()
                raise httpx.HTTPStatusError(
                    f"HTTP {resp.status_code}", request=resp.request, response=resp
                )
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
                        return
                    try:
                        obj = _json.loads(raw)
                        token = (obj["choices"][0]["delta"].get("content") or "")
                        if token:
                            yield token
                    except (_json.JSONDecodeError, KeyError, IndexError):
                        pass
    finally:
        await client.aclose()


async def stream_advisor_response(request: AdvisorChatRequest) -> AsyncGenerator[str, None]:
    """
    Stream AI response — Groq first (ultra-fast), OpenRouter as fallback.
    Time-to-first-token: ~300-500ms via Groq, ~3-5s via OpenRouter.

    - Cache hit  → send full reply instantly as one token.
    - Cache miss → try Groq models, then OpenRouter models.
    - All fail   → stream fallback response from cached market data.
    """
    start = time.time()
    settings = get_settings()
    request.message = sanitize_input(request.message)

    # ── Cache hit ─────────────────────────────────────────────────────────────
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

    base_payload = {"messages": messages, "max_tokens": 2048, "temperature": 0.7, "stream": True}

    # ── Build provider list: Groq first, then OpenRouter ─────────────────────
    providers: list[tuple[str, str, dict]] = []  # (url, model, headers)

    if settings.groq_api_key:
        groq_headers = {
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        for model in GROQ_MODELS:
            providers.append((settings.groq_url, model, groq_headers))

    if settings.openrouter_api_key:
        or_headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://stephenbaraik-paisapro.hf.space",
            "X-Title": "PaisaPro AI Advisor",
        }
        for model in OPENROUTER_MODELS:
            providers.append((settings.openrouter_url, model, or_headers))

    if not providers:
        reply = _generate_fallback_response(request)
        yield f"data: {_json.dumps({'token': reply})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # ── Try each provider/model in order ─────────────────────────────────────
    reply_chunks: list[str] = []

    for url, model, headers in providers:
        reply_chunks = []
        payload = {**base_payload, "model": model}
        try:
            async for token in _stream_from_provider(url, headers, payload, model):
                reply_chunks.append(token)
                yield f"data: {_json.dumps({'token': token})}\n\n"

            if reply_chunks:
                provider_name = "Groq" if "groq" in url else "OpenRouter"
                logger.info("%s (%s) streamed in %.2fs", provider_name, model, time.time() - start)
                break

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Rate limited by %s (%s) — trying next", url, model)
            else:
                logger.warning("HTTP %d from %s (%s) — trying next", e.response.status_code, url, model)
        except httpx.RequestError as e:
            logger.warning("Request error from %s (%s): %s — trying next", url, model, e)
        except Exception as e:
            logger.warning("Unexpected error from %s (%s): %s — trying next", url, model, e)

    # ── Fallback if all providers failed ──────────────────────────────────────
    if not reply_chunks:
        logger.warning("All providers failed — using cached data fallback")
        reply = _generate_fallback_response(request)
        yield f"data: {_json.dumps({'token': reply})}\n\n"
    else:
        set_cached_response(ckey, "".join(reply_chunks))

    logger.info("Advisor stream done in %.2fs", time.time() - start)
    yield "data: [DONE]\n\n"


# ── Non-streaming ─────────────────────────────────────────────────────────────

async def get_advisor_response(request: AdvisorChatRequest) -> AdvisorChatResponse:
    """Non-streaming — Groq first, OpenRouter fallback."""
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

    # Try Groq first, then OpenRouter
    reply = None
    if settings.groq_api_key:
        for model in GROQ_MODELS:
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    resp = await client.post(
                        settings.groq_url,
                        headers={"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"},
                        json={"model": model, "messages": messages, "max_tokens": 2048, "temperature": 0.7},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                reply = (data["choices"][0]["message"].get("content") or "").strip() or None
                if reply:
                    break
            except Exception as e:
                logger.warning("Groq (%s) non-stream failed: %s", model, e)

    if not reply and settings.openrouter_api_key:
        for model in OPENROUTER_MODELS:
            reply = await _call_openrouter(settings, messages, model)
            if reply:
                break

    if not reply:
        logger.warning("All LLMs failed, using fallback")
        reply = _generate_fallback_response(request)

    set_cached_response(ckey, reply)
    suggestions = [line.strip()[2:] for line in reply.split("\n") if line.strip().startswith("- ") and len(line.strip()) < 100][:3]
    logger.info("Advisor non-stream in %.2fs", time.time() - start)
    return AdvisorChatResponse(reply=reply, suggestions=suggestions)
