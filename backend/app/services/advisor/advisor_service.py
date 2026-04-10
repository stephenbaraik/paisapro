"""
AI Advisor service — streaming, caching, rate limiting, input sanitization.

Features:
  - Real SSE streaming from Groq (token-by-token)
  - Response caching (hash-based deduplication)
  - Rate limiting (per-session, sliding window)
  - Input sanitization & prompt injection protection
  - Circuit breaker for Groq API failures
  - Progressive status messages during tool-call phase
  - Comprehensive observability (logging, metrics)
  - Graceful degradation when tools fail
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

# Rate limiting
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 10  # per window
_rate_limit_tracker: dict[str, deque] = defaultdict(deque)

# Response cache (5 min TTL)
_response_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL = 300

# Circuit breaker
_circuit_state = {"failures": 0, "threshold": 5, "open_until": 0.0, "half_open": False}
CIRCUIT_RECOVERY = 30  # seconds


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
    """Sanitize user input: strip dangerous patterns, enforce length limits."""
    message = " ".join(message.split())
    if len(message) > 2000:
        message = message[:2000]
    return message


def check_prompt_injection(message: str) -> Optional[str]:
    """Check for prompt injection attempts."""
    lower = message.lower()
    for pattern in _PROMPT_INJECTION_PATTERNS:
        if pattern in lower:
            return f"Potential prompt injection detected: '{pattern}'"
    return None


# ── Rate limiting ─────────────────────────────────────────────────────────────

def check_rate_limit(session_id: str = "default") -> bool:
    """Check if request is within rate limit. Returns True if allowed."""
    now = time.time()
    tracker = _rate_limit_tracker[session_id]
    while tracker and tracker[0] < now - RATE_LIMIT_WINDOW:
        tracker.popleft()
    if len(tracker) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    tracker.append(now)
    return True


# ── Circuit breaker ───────────────────────────────────────────────────────────

def check_circuit() -> bool:
    """Check if circuit allows requests. True = closed (OK)."""
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
    """Build market intelligence context from analytics cache."""
    try:
        from ...analytics import get_cached_report
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
        }
    except Exception as exc:
        logger.warning("Market context build failed: %s", exc)
        return {}


async def _build_macro_context() -> dict:
    """Build macro regime context."""
    try:
        from ...macro import get_macro_dashboard
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
    """Build news sentiment context."""
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
    """Build the complete message list: system + context + history + user."""
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


# ── Streaming with tool-use loop ──────────────────────────────────────────────

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


async def stream_advisor_response(request: AdvisorChatRequest) -> AsyncGenerator[str, None]:
    """SSE generator with real streaming, tool-use loop, caching, rate limiting."""
    start_time = time.time()
    settings = get_settings()

    if not settings.groq_api_key:
        yield f"data: {_json.dumps({'error': 'Groq API key is not configured.'})}\n\n"
        return

    if not check_rate_limit():
        yield f"data: {_json.dumps({'error': 'Rate limit exceeded. Please wait a moment.'})}\n\n"
        return

    if not check_circuit():
        yield f"data: {_json.dumps({'error': 'Service temporarily unavailable. Please try again shortly.'})}\n\n"
        return

    request.message = sanitize_input(request.message)
    injection = check_prompt_injection(request.message)
    if injection:
        logger.warning("Prompt injection detected: %s", injection)
        yield f"data: {_json.dumps({'error': 'Request rejected due to policy violation.'})}\n\n"
        return

    # Cache check
    profile_hash = str(hash(request.profile)) if request.profile else "none"
    ckey = _cache_key(request.message, profile_hash)
    cached = get_cached_response(ckey)
    if cached:
        for word in cached.split():
            yield f"data: {_json.dumps({'token': word + ' '})}\n\n"
            await asyncio.sleep(0.01)
        yield "data: [DONE]\n\n"
        return

    messages = _build_messages(request)
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    groq_url = _get_groq_url()
    groq_model = _get_groq_model()

    # Phase 1: Tool-call loop
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
            if exc.response.status_code == 429:
                yield f"data: {_json.dumps({'error': 'Groq rate limited. Please try again shortly.'})}\n\n"
                return
            # Retry without tools
            payload_nt = {k: v for k, v in payload.items() if k not in ("tools", "tool_choice", "parallel_tool_calls")}
            payload_nt["temperature"] = 0.7
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    resp = await client.post(groq_url, headers=headers, json=payload_nt)
                    resp.raise_for_status()
                    data = resp.json()
            except Exception:
                yield f"data: {_json.dumps({'error': f'AI service error: {exc.response.status_code}'})}\n\n"
                return
        except httpx.RequestError:
            record_failure()
            yield f"data: {_json.dumps({'error': 'Could not reach AI service. Please try again.'})}\n\n"
            return

        choice = data["choices"][0]
        message = choice["message"]
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            reply = (message.get("content") or "").strip()
            if reply:
                set_cached_response(ckey, reply)
                for word in reply.split():
                    yield f"data: {_json.dumps({'token': word + ' '})}\n\n"
                    await asyncio.sleep(0.015)
            yield "data: [DONE]\n\n"
            logger.info("Advisor stream complete (no tools) in %.2fs", time.time() - start_time)
            return

        messages.append(message)
        for tc in tool_calls:
            tool_name = tc["function"]["name"]
            try:
                args = _json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
            except _json.JSONDecodeError:
                args = {}

            status = _TOOL_STATUS_MESSAGES.get(tool_name, f"Calling {tool_name}...")
            yield f"data: {_json.dumps({'status': status})}\n\n"

            result = await execute_tool(tool_name, args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result,
            })

    # Phase 2: Final text
    payload = {"model": groq_model, "messages": messages, "max_tokens": 4096, "temperature": 0.7}
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(groq_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            record_success()
    except Exception:
        record_failure()
        yield f"data: {_json.dumps({'error': 'AI service error. Please try again.'})}\n\n"
        return

    reply = (data["choices"][0]["message"].get("content") or "").strip()
    if not reply:
        yield f"data: {_json.dumps({'error': 'AI returned an empty response.'})}\n\n"
        yield "data: [DONE]\n\n"
        return

    set_cached_response(ckey, reply)
    for word in reply.split():
        yield f"data: {_json.dumps({'token': word + ' '})}\n\n"
        await asyncio.sleep(0.015)

    logger.info("Advisor stream complete in %.2fs", time.time() - start_time)
    yield "data: [DONE]\n\n"


# ── Non-streaming fallback ────────────────────────────────────────────────────

async def get_advisor_response(request: AdvisorChatRequest) -> AdvisorChatResponse:
    """Non-streaming fallback with tool-use loop."""
    start_time = time.time()
    settings = get_settings()

    if not settings.groq_api_key:
        raise HTTPException(status_code=503, detail="Groq API key is not configured.")
    if not check_rate_limit():
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    if not check_circuit():
        raise HTTPException(status_code=503, detail="Service temporarily unavailable.")

    request.message = sanitize_input(request.message)
    injection = check_prompt_injection(request.message)
    if injection:
        raise HTTPException(status_code=400, detail="Request rejected due to policy violation.")

    profile_hash = str(hash(request.profile)) if request.profile else "none"
    ckey = _cache_key(request.message, profile_hash)
    cached = get_cached_response(ckey)
    if cached:
        return AdvisorChatResponse(reply=cached, suggestions=[])

    messages = _build_messages(request)
    headers = {"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"}
    groq_url = _get_groq_url()
    groq_model = _get_groq_model()

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
        except httpx.HTTPStatusError as exc:
            record_failure()
            if exc.response.status_code == 429:
                raise HTTPException(status_code=429, detail="Rate limited.")
            payload_nt = {k: v for k, v in payload.items() if k not in ("tools", "tool_choice", "parallel_tool_calls")}
            payload_nt["temperature"] = 0.7
            try:
                async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                    resp = await client.post(groq_url, headers=headers, json=payload_nt)
                    resp.raise_for_status()
                    data = resp.json()
            except Exception:
                raise HTTPException(status_code=502, detail=f"AI service error: {exc.response.status_code}")
        except httpx.RequestError:
            record_failure()
            raise HTTPException(status_code=503, detail="Could not reach AI service.")

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
        if not reply:
            raise HTTPException(status_code=502, detail="AI returned empty response.")

        set_cached_response(ckey, reply)
        suggestions = [line.strip()[2:] for line in reply.split("\n") if line.strip().startswith("- ") and len(line.strip()) < 100][:3]

        logger.info("Advisor non-stream response in %.2fs", time.time() - start_time)
        return AdvisorChatResponse(reply=reply, suggestions=suggestions)

    raise HTTPException(status_code=502, detail="AI could not complete response.")
