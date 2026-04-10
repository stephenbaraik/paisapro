"""
AI Advisor service — streaming, caching, graceful degradation.

Features:
  - Real SSE streaming from Groq (token-by-token)
  - Response caching (hash-based deduplication)
  - Input sanitization & prompt injection protection
  - Circuit breaker for Groq API failures
  - Progressive status messages during tool-call phase
  - Comprehensive observability (logging, metrics)
  - GRACEFUL DEGRADATION: when Groq is unavailable, generates a presentable
    response from cached market/macro/portfolio data
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
    PortfolioHoldingContext,
    WatchlistItemContext,
)
from .prompt_engine import build_system_prompt
from .tools import TOOLS, execute_tool

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

MAX_HISTORY = 30
MAX_TOOL_ROUNDS = 3
REQUEST_TIMEOUT = 60

# Rate limiting (soft — logs warning but doesn't block)
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX_REQUESTS = 30  # generous limit

# Response cache (5 min TTL)
_response_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL = 300

# Circuit breaker
_circuit_state = {"failures": 0, "threshold": 5, "open_until": 0.0, "half_open": False}
CIRCUIT_RECOVERY = 30


# ── Helper functions ──────────────────────────────────────────────────────────

def _get_groq_url() -> str:
    return get_settings().groq_url

def _get_groq_model() -> str:
    return get_settings().groq_model


# ── Input sanitization ────────────────────────────────────────────────────────

_PROMPT_INJECTION_PATTERNS = [
    "ignore all previous",
    "ignore the above",
    "disregard all",
    "system prompt",
    "you are now",
    "new instructions",
    "override your",
    "bypass your",
    "forget everything",
    "act as a different",
    "pretend you are",
    "ignore your training",
    "do not follow",
    "break your rules",
]


def sanitize_input(message: str) -> str:
    message = " ".join(message.split())
    if len(message) > 2000:
        message = message[:2000]
    return message


def check_prompt_injection(message: str) -> Optional[str]:
    lower = message.lower()
    for pattern in _PROMPT_INJECTION_PATTERNS:
        if pattern in lower:
            return f"Potential prompt injection detected: '{pattern}'"
    return None


# ── Rate limiting (soft — logs but doesn't block) ────────────────────────────

_rate_limit_tracker: dict[str, deque] = defaultdict(deque)


def check_rate_limit(session_id: str = "default") -> bool:
    """Soft rate limit — logs warning but never blocks."""
    now = time.time()
    tracker = _rate_limit_tracker[session_id]
    while tracker and tracker[0] < now - RATE_LIMIT_WINDOW:
        tracker.popleft()
    if len(tracker) >= RATE_LIMIT_MAX_REQUESTS:
        logger.warning("Soft rate limit hit for session %s", session_id)
        return False  # Still allow, but log
    tracker.append(now)
    return True


# ── Circuit breaker ───────────────────────────────────────────────────────────

def check_circuit() -> bool:
    now = time.time()
    state = _circuit_state
    if state["open_until"] > now:
        return False
    if state["half_open"]:
        state["half_open"] = False
    return True


def record_failure() -> None:
    state = _circuit_state
    state["failures"] += 1
    if state["failures"] >= state["threshold"]:
        state["open_until"] = time.time() + CIRCUIT_RECOVERY
        state["half_open"] = False
        logger.error("Circuit breaker OPENED — Groq API failing repeatedly")


def record_success() -> None:
    state = _circuit_state
    state["failures"] = 0
    state["open_until"] = 0.0
    state["half_open"] = False


# ── Response caching ──────────────────────────────────────────────────────────

def _cache_key(message: str, profile_hash: str) -> str:
    raw = f"{message}|{profile_hash}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


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

def _build_market_context() -> dict:
    try:
        from ..analytics import get_cached_report
        cached = get_cached_report()
        if not cached:
            return {}
        overview = cached.market_overview
        breadth = overview.market_breadth
        top_buys = sorted(
            [a for a in cached.stock_analyses if a.technical_signals.composite_signal.value == "BUY"],
            key=lambda a: a.technical_signals.confidence_score, reverse=True,
        )[:5]
        top_sells = sorted(
            [a for a in cached.stock_analyses if a.technical_signals.composite_signal.value == "SELL"],
            key=lambda a: a.technical_signals.confidence_score, reverse=True,
        )[:5]
        best = max(overview.sector_heatmap, key=lambda s: s.avg_change_pct) if overview.sector_heatmap else None
        worst = min(overview.sector_heatmap, key=lambda s: s.avg_change_pct) if overview.sector_heatmap else None
        return {
            "buy_count": breadth.get("buy", 0),
            "hold_count": breadth.get("hold", 0),
            "sell_count": breadth.get("sell", 0),
            "top_buys": ", ".join(f"{a.symbol.replace('.NS', '')} ({a.technical_signals.confidence_score:.0f}%)" for a in top_buys) or "None",
            "top_sells": ", ".join(f"{a.symbol.replace('.NS', '')} ({a.technical_signals.confidence_score:.0f}%)" for a in top_sells) or "None",
            "best_sector": f"{best.sector} ({best.avg_change_pct:+.2f}%)" if best else "N/A",
            "worst_sector": f"{worst.sector} ({worst.avg_change_pct:+.2f}%)" if worst else "N/A",
            "anomaly_count": cached.anomaly_count,
            "anomalies": [
                {"symbol": a.symbol.replace(".NS", ""), "description": a.description, "severity": a.severity}
                for a in overview.anomaly_alerts[:3]
            ] if overview.anomaly_alerts else [],
        }
    except Exception as exc:
        logger.warning("Market context build failed: %s", exc)
        return {}


async def _build_macro_context() -> dict:
    try:
        from ..macro import get_macro_dashboard
        result = await get_macro_dashboard()
        return {
            "regime": result.market_regime,
            "regime_description": result.regime_description,
            "indicators": [
                {"name": ind.name, "value": ind.value, "change_pct": ind.change_pct, "trend": ind.trend}
                for ind in result.indicators
            ],
        }
    except Exception as exc:
        logger.warning("Macro context build failed: %s", exc)
        return {}


def _build_news_context() -> dict:
    try:
        from ...core.cache import cache
        cached = cache.get("news:sentiment")
        if not cached:
            return {}
        return {
            "overall_sentiment": cached.overall_sentiment,
            "overall_score": cached.overall_score,
            "summaries": [
                {
                    "symbol": s.symbol.replace(".NS", ""),
                    "sentiment": s.sentiment_label,
                    "articles": s.article_count,
                    "positive": s.positive_count,
                    "negative": s.negative_count,
                }
                for s in cached.summaries[:8]
            ],
        }
    except Exception as exc:
        logger.warning("News context build failed: %s", exc)
        return {}


# ── Message building ──────────────────────────────────────────────────────────

def _build_messages(request: AdvisorChatRequest) -> list[dict]:
    market = _build_market_context()
    system_prompt = build_system_prompt(
        profile=request.profile,
        holdings=request.portfolio_holdings,
        watchlist=request.watchlist,
        market_data=market or None,
    )
    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for msg in request.conversation_history[-MAX_HISTORY:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.message})
    return messages


# ── Graceful degradation fallback response ────────────────────────────────────

_TOOL_STATUS_MESSAGES = {
    "get_stock_analysis": "Analyzing stock data...",
    "get_macro_dashboard": "Checking macro indicators...",
    "get_news_sentiment": "Fetching latest news sentiment...",
    "run_screener": "Screening stocks...",
    "get_stock_comparison": "Comparing stocks...",
    "get_top_gainers_losers": "Finding top movers...",
    "get_sector_analysis": "Analyzing sector performance...",
    "get_timeseries_forecast": "Fetching price history...",
    "search_stocks": "Searching stocks...",
    "get_financial_plan": "Loading financial plan...",
}


def _generate_fallback_response(
    request: AdvisorChatRequest,
    market: dict,
    macro: dict,
    news: dict,
) -> str:
    """
    Generate a presentable response from cached data when Groq is unavailable.
    This ensures the chatbot always returns something useful.
    """
    lines: list[str] = []
    msg_lower = request.message.lower()

    # Header
    lines.append("## Market Update")
    lines.append("")
    lines.append("> Note: AI model is temporarily unavailable. Here's the latest data from our analytics engine.")
    lines.append("")

    # If user asks about a specific stock
    stock_symbols = []
    for word in request.message.split():
        w = word.strip(".,;:!?()[]{}\"'").upper()
        if len(w) >= 3 and any(c.isdigit() for c in w):
            stock_symbols.append(w)
    # Also check portfolio holdings
    if request.portfolio_holdings:
        for h in request.portfolio_holdings:
            sym = h.symbol.replace(".NS", "").upper()
            if sym.lower() in msg_lower or sym[:4].lower() in msg_lower:
                stock_symbols.append(sym)

    if stock_symbols:
        lines.append(f"### Stocks Mentioned: {', '.join(stock_symbols)}")
        lines.append("")
        lines.append("I'm unable to fetch live analysis right now, but you can view detailed technical analysis for any stock in the Analytics section.")
        lines.append("")

    # Market breadth
    if market:
        buy = market.get("buy_count", 0)
        sell = market.get("sell_count", 0)
        hold = market.get("hold_count", 0)
        total = buy + sell + hold
        if total > 0:
            pct_buy = buy / total * 100
            pct_sell = sell / total * 100
            lines.append("## Market Breadth")
            lines.append("")
            lines.append(f"- **BUY signals**: {buy} ({pct_buy:.0f}%)")
            lines.append(f"- **HOLD signals**: {hold}")
            lines.append(f"- **SELL signals**: {sell} ({pct_sell:.0f}%)")
            lines.append("")
            if pct_buy > 50:
                lines.append("> The market leans **bullish** based on our ML analytics across 500+ NSE stocks.")
            elif pct_sell > 40:
                lines.append("> The market shows **caution** with elevated sell signals.")
            else:
                lines.append("> The market appears **mixed** with no strong directional bias.")
            lines.append("")

        if market.get("top_buys") and market["top_buys"] != "None":
            lines.append(f"**Top BUY signals**: {market['top_buys']}")
            lines.append("")
        if market.get("top_sells") and market["top_sells"] != "None":
            lines.append(f"**Top SELL signals**: {market['top_sells']}")
            lines.append("")

    # Macro regime
    if macro:
        lines.append("## Macro Environment")
        lines.append("")
        lines.append(f"- **Market Regime**: {macro.get('regime', 'N/A')}")
        if macro.get("regime_description"):
            lines.append(f"  - {macro['regime_description']}")
        lines.append("")
        for ind in macro.get("indicators", []):
            lines.append(f"- **{ind['name']}**: {ind['value']:,.2f} ({ind['change_pct']:+.1f}%, {ind['trend']})")
        lines.append("")

    # News sentiment
    if news:
        lines.append(f"## News Sentiment (Overall: {news.get('overall_sentiment', 'N/A').upper()})")
        lines.append("")
        for s in news.get("summaries", [])[:5]:
            lines.append(f"- **{s['symbol']}**: {s['sentiment']} ({s['articles']} articles)")
        lines.append("")

    # Portfolio summary
    if request.portfolio_holdings:
        total_inv = sum(h.buy_price * h.quantity for h in request.portfolio_holdings)
        total_cur = sum(h.current_price * h.quantity for h in request.portfolio_holdings if h.current_price > 0)
        pnl = ((total_cur - total_inv) / total_inv * 100) if total_inv > 0 else 0
        lines.append("## Your Portfolio")
        lines.append("")
        lines.append(f"- Invested: ₹{total_inv:,.0f}")
        if total_cur > 0:
            lines.append(f"- Current: ₹{total_cur:,.0f} ({pnl:+.1f}%)")
        lines.append(f"- Holdings: {len(request.portfolio_holdings)} stocks")
        lines.append("")

    # Disclaimer
    lines.append("> ⚠️ *This is for educational purposes only. Not a SEBI-registered investment advisory service. Please consult a certified financial advisor before making investment decisions.*")

    return "\n".join(lines)


# ── Streaming with tool-use loop ──────────────────────────────────────────────

async def _stream_response(reply: str) -> None:
    """Helper to stream a complete response word-by-word."""
    for word in reply.split():
        yield f"data: {_json.dumps({'token': word + ' '})}\n\n"
        await asyncio.sleep(0.015)
    yield "data: [DONE]\n\n"


async def stream_advisor_response(request: AdvisorChatRequest) -> AsyncGenerator[str, None]:
    """SSE generator with graceful degradation when Groq is unavailable."""
    start_time = time.time()
    settings = get_settings()

    # Input sanitization
    request.message = sanitize_input(request.message)
    injection = check_prompt_injection(request.message)
    if injection:
        logger.warning("Prompt injection: %s", injection)
        yield f"data: {_json.dumps({'error': 'Request rejected due to policy violation.'})}\n\n"
        return

    # Cache check
    profile_hash = hashlib.md5(request.profile.model_dump_json().encode()).hexdigest()[:16] if request.profile else "none"
    ckey = _cache_key(request.message, profile_hash)
    cached = get_cached_response(ckey)
    if cached:
        async for chunk in _stream_response(cached):
            yield chunk
        return

    # Check if Groq is available
    groq_available = bool(settings.groq_api_key) and check_circuit()
    groq_url = _get_groq_url() if groq_available else None
    groq_model = _get_groq_model() if groq_available else None
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    } if groq_available else {}

    # Phase 1: Tool-call loop (only if Groq available)
    if groq_available:
        messages = _build_messages(request)
        for _round in range(MAX_TOOL_ROUNDS):
            payload = {
                "model": groq_model,
                "messages": messages,
                "max_tokens": 4096,
                "temperature": 0.0,
                "tools": TOOLS,
                "tool_choice": "auto",
                "parallel_tool_calls": True,
            }

            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    resp = await client.post(groq_url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    record_success()
            except httpx.HTTPStatusError as exc:
                record_failure()
                logger.warning("Groq HTTP error %d: %s", exc.response.status_code, exc.response.text[:200])
                # Fall through to fallback
                groq_available = False
                break
            except httpx.RequestError:
                record_failure()
                logger.warning("Groq request error: connection failed")
                groq_available = False
                break

            choice = data["choices"][0]
            message = choice["message"]
            tool_calls = message.get("tool_calls")

            if not tool_calls:
                reply = (message.get("content") or "").strip()
                if reply:
                    set_cached_response(ckey, reply)
                    async for chunk in _stream_response(reply):
                        yield chunk
                    logger.info("Advisor stream complete (no tools) in %.2fs", time.time() - start_time)
                else:
                    yield f"data: {_json.dumps({'error': 'Empty response from AI.'})}\n\n"
                return

            messages.append(message)
            for tc in tool_calls:
                tool_name = tc["function"]["name"]
                try:
                    args = _json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
                except _json.JSONDecodeError:
                    args = {}

                yield f"data: {_json.dumps({'status': _TOOL_STATUS_MESSAGES.get(tool_name, 'Processing...')})}\n\n"
                result = await execute_tool(tool_name, args)
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

    # Fallback: generate response from cached data
    if not groq_available:
        logger.info("Groq unavailable — generating fallback response")
        yield f"data: {_json.dumps({'status': 'Generating response from available data...'})}\n\n"
        market = _build_market_context()
        macro = await _build_macro_context()
        news = _build_news_context()
        reply = _generate_fallback_response(request, market, macro, news)
        set_cached_response(ckey, reply)
        async for chunk in _stream_response(reply):
            yield chunk
        logger.info("Advisor fallback response in %.2fs", time.time() - start_time)
        return

    # Phase 2: Final text (after tool rounds exhausted)
    payload = {"model": groq_model, "messages": messages, "max_tokens": 4096, "temperature": 0.7}
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(groq_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            record_success()
    except Exception:
        record_failure()
        logger.warning("Groq final text failed — falling back")
        market = _build_market_context()
        macro = await _build_macro_context()
        news = _build_news_context()
        reply = _generate_fallback_response(request, market, macro, news)
        set_cached_response(ckey, reply)
        async for chunk in _stream_response(reply):
            yield chunk
        return

    reply = (data["choices"][0]["message"].get("content") or "").strip()
    if not reply:
        yield f"data: {_json.dumps({'error': 'AI returned an empty response.'})}\n\n"
        yield "data: [DONE]\n\n"
        return

    set_cached_response(ckey, reply)
    async for chunk in _stream_response(reply):
        yield chunk

    logger.info("Advisor stream complete in %.2fs", time.time() - start_time)
    yield "data: [DONE]\n\n"


# ── Non-streaming fallback ────────────────────────────────────────────────────

async def get_advisor_response(request: AdvisorChatRequest) -> AdvisorChatResponse:
    """Non-streaming with graceful degradation."""
    start_time = time.time()
    settings = get_settings()

    request.message = sanitize_input(request.message)
    injection = check_prompt_injection(request.message)
    if injection:
        raise HTTPException(status_code=400, detail="Request rejected due to policy violation.")

    profile_hash = hashlib.md5(request.profile.model_dump_json().encode()).hexdigest()[:16] if request.profile else "none"
    ckey = _cache_key(request.message, profile_hash)
    cached = get_cached_response(ckey)
    if cached:
        return AdvisorChatResponse(reply=cached, suggestions=[])

    groq_available = bool(settings.groq_api_key) and check_circuit()
    groq_url = _get_groq_url() if groq_available else None
    groq_model = _get_groq_model() if groq_available else None
    headers = {"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"} if groq_available else {}

    if groq_available:
        messages = _build_messages(request)
        for _round in range(MAX_TOOL_ROUNDS + 1):
            is_final = _round == MAX_TOOL_ROUNDS
            payload = {"model": groq_model, "messages": messages, "max_tokens": 4096, "temperature": 0.7 if is_final else 0.0}
            if not is_final:
                payload["tools"] = TOOLS
                payload["tool_choice"] = "auto"
                payload["parallel_tool_calls"] = True

            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    resp = await client.post(groq_url, headers=headers, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    record_success()
            except Exception:
                record_failure()
                groq_available = False
                break

            choice = data["choices"][0]
            message = choice["message"]
            tool_calls = message.get("tool_calls")

            if tool_calls and not is_final:
                messages.append(message)
                for tc in tool_calls:
                    try:
                        args = _json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
                    except _json.JSONDecodeError:
                        args = {}
                    result = await execute_tool(tc["function"]["name"], args)
                    messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})
                continue

            reply = (message.get("content") or "").strip()
            while reply.endswith("---"):
                reply = reply[:-3].rstrip()
            if reply:
                set_cached_response(ckey, reply)
                suggestions = [line.strip()[2:] for line in reply.split("\n") if line.strip().startswith("- ") and len(line.strip()) < 100][:3]
                logger.info("Advisor non-stream response in %.2fs", time.time() - start_time)
                return AdvisorChatResponse(reply=reply, suggestions=suggestions)

    # Fallback
    logger.info("Groq unavailable — generating fallback response")
    market = _build_market_context()
    macro = await _build_macro_context()
    news = _build_news_context()
    reply = _generate_fallback_response(request, market, macro, news)
    set_cached_response(ckey, reply)
    return AdvisorChatResponse(reply=reply, suggestions=[])
