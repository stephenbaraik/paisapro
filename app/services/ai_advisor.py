"""
AI advisor service powered by Groq (Llama 3.3 70B).

Features:
  - Context injection: user profile, portfolio, macro regime, news sentiment
  - Agentic tool-use: LLM can call get_stock_analysis / get_macro_dashboard /
    run_screener / get_news_sentiment on demand via Groq function calling
  - SSE streaming with multi-turn tool loop
  - 30-message conversation history window
"""

import json as _json
import logging
from typing import Optional

import httpx
from fastapi import HTTPException

from ..core.config import get_settings
from ..schemas.financial import (
    UserFinancialProfile,
    AdvisorChatRequest,
    AdvisorChatResponse,
    PortfolioHoldingContext,
    WatchlistItemContext,
)

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_HISTORY = 30
MAX_TOOL_ROUNDS = 3  # prevent infinite loops

# ── Tool definitions (Groq / OpenAI function-calling schema) ──────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_analysis",
            "description": (
                "Get detailed technical analysis for a specific NSE stock. "
                "Returns composite signal (BUY/HOLD/SELL), confidence, risk metrics "
                "(Sharpe, beta, volatility, max drawdown), current price, and anomalies. "
                "Call this when the user asks about a specific stock."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": (
                            "NSE stock symbol with .NS suffix, e.g. 'RELIANCE.NS', 'TCS.NS'. "
                            "If the user says a company name, convert it to the NSE ticker."
                        ),
                    }
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_macro_dashboard",
            "description": (
                "Get current macro indicators: India VIX, USD/INR, Nifty 50, Gold, "
                "Crude Oil, Bank Nifty, plus the market regime (RISK_ON / RISK_OFF / NEUTRAL). "
                "Call this when the user asks about market conditions, macro outlook, or regime."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_news_sentiment",
            "description": (
                "Get recent news headlines and sentiment analysis for top Indian stocks. "
                "Returns per-stock sentiment (BULLISH/BEARISH/NEUTRAL) and overall market sentiment. "
                "Call this when the user asks about news, recent events, or sentiment for a stock."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_screener",
            "description": (
                "Screen stocks by sector, signal direction, minimum Sharpe ratio, or max drawdown. "
                "Returns ranked list of stocks matching the criteria. "
                "Call this when the user asks to find/filter stocks by criteria."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sector": {
                        "type": "string",
                        "description": "Filter by sector name, e.g. 'IT', 'Banking', 'Pharma'. Optional.",
                    },
                    "signal": {
                        "type": "string",
                        "enum": ["BUY", "HOLD", "SELL"],
                        "description": "Filter by composite signal direction. Optional.",
                    },
                    "min_sharpe": {
                        "type": "number",
                        "description": "Minimum Sharpe ratio threshold. Optional.",
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": [
                            "composite_score",
                            "confidence_score",
                            "sharpe_ratio",
                            "volatility",
                            "daily_change_pct",
                        ],
                        "description": "Sort results by this metric. Default: composite_score.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max number of results to return (1-30). Default: 10.",
                    },
                },
            },
        },
    },
]


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert Indian investment advisor AI assistant built into PaisaPro.ai, a personal finance and investment analytics platform.
Your role is to help users understand their investment strategy, explain financial concepts, and provide actionable advice grounded in real-time data.

Key context:
- You are focused on the Indian financial market (NSE/BSE, Nifty, Sensex, Indian mutual funds, SIPs, PPF, NPS, ELSS)
- All monetary values are in Indian Rupees (INR / ₹)
- Regulatory context: SEBI regulations, Indian tax laws (LTCG, STCG, Section 80C)
- Be clear that your advice is educational and not a registered financial advisory service

You have access to live data tools. Use them whenever the question involves specific stocks, market conditions, news, or screening. NEVER guess stock prices or signals from memory — always use your tools to fetch real-time data. Present tool results clearly — don't dump raw data. If a tool returns no data, say so honestly.

Tone: Professional yet approachable. Use simple language. Avoid jargon unless explaining it.

Formatting rules (STRICT — your output is rendered as Markdown):
- Use ## for main section headings. Use ### for sub-section headings. Never put headings inside list items.
- Use bullet lists (- item) for points. Use numbered lists (1. item) only for sequential steps.
- Each list item must be ONE short line. Never put multiple sentences or sub-points on a single list item.
- ALWAYS put a blank line before AND after EVERY heading, list, table, blockquote, and code block. Never skip these blank lines — without them elements won't render correctly.
- Use **bold** sparingly — only for key terms or amounts, never for entire sentences.
- Keep paragraphs to 2-3 sentences max.
- Use > blockquote for important callouts or final takeaways.
- Use markdown tables when comparing multiple items side by side. Keep columns concise. Every table MUST have a header row and a separator row (|---|---|).
- Do NOT mix prose paragraphs and list items without a blank line between them.

When the user provides their financial profile, use it to personalise your response."""


# ── Context builders ──────────────────────────────────────────────────────────


def _profile_context(profile: Optional[UserFinancialProfile]) -> str:
    if not profile:
        return ""
    surplus = profile.monthly_income - profile.monthly_expenses
    return f"""
User Financial Profile:
- Monthly Income: ₹{profile.monthly_income:,.0f}
- Monthly Expenses: ₹{profile.monthly_expenses:,.0f}
- Investable Surplus: ₹{surplus:,.0f}/month
- Current Savings: ₹{profile.current_savings:,.0f}
- Age: {profile.age} years
- Risk Tolerance: {profile.risk_profile.value.capitalize()}
"""


def _portfolio_context(
    holdings: list[PortfolioHoldingContext],
    watchlist: list[WatchlistItemContext],
) -> str:
    """Inject the user's actual portfolio holdings and watchlist."""
    lines: list[str] = []

    if holdings:
        total_invested = sum(h.buy_price * h.quantity for h in holdings)
        total_current = sum(
            h.current_price * h.quantity for h in holdings if h.current_price > 0
        )
        total_pnl_pct = (
            ((total_current - total_invested) / total_invested * 100)
            if total_invested > 0
            else 0.0
        )

        # Sector allocation
        sector_value: dict[str, float] = {}
        for h in holdings:
            val = (
                h.current_price * h.quantity
                if h.current_price > 0
                else h.buy_price * h.quantity
            )
            sector_value[h.sector or "Unknown"] = (
                sector_value.get(h.sector or "Unknown", 0) + val
            )
        total_val = sum(sector_value.values()) or 1

        lines.append("\nUser's Portfolio Holdings:")
        lines.append(f"- Total Invested: ₹{total_invested:,.0f}")
        if total_current > 0:
            lines.append(
                f"- Current Value: ₹{total_current:,.0f} ({total_pnl_pct:+.1f}%)"
            )
        lines.append(f"- Holdings: {len(holdings)} stocks")

        # List each holding
        lines.append("- Stocks held:")
        for h in sorted(
            holdings, key=lambda x: x.current_price * x.quantity, reverse=True
        ):
            sym = h.symbol.replace(".NS", "")
            mv = (
                h.current_price * h.quantity
                if h.current_price > 0
                else h.buy_price * h.quantity
            )
            lines.append(
                f"  - {sym}: {h.quantity:.0f} shares, ₹{mv:,.0f} value, {h.pnl_pct:+.1f}% P&L"
            )

        # Sector breakdown
        lines.append("- Sector allocation:")
        for sec, val in sorted(sector_value.items(), key=lambda x: x[1], reverse=True):
            pct = val / total_val * 100
            lines.append(f"  - {sec}: {pct:.0f}%")

    if watchlist:
        lines.append("\nUser's Watchlist:")
        for w in watchlist:
            sym = w.symbol.replace(".NS", "")
            price_str = f"₹{w.current_price:,.0f}" if w.current_price > 0 else "N/A"
            lines.append(
                f"- {sym} ({w.sector or '?'}): {price_str}, {w.daily_change_pct:+.1f}% today"
            )

    if lines:
        lines.append(
            "\nUse this portfolio data to give personalised advice. Warn about concentration risk, sector imbalance, or underperformers."
        )

    return "\n".join(lines)


def _market_context() -> str:
    """Inject live market intelligence from the analytics cache into the advisor."""
    try:
        from .analytics import _report_cache

        cached, _ = _report_cache
        if cached is None:
            return ""

        overview = cached.market_overview
        breadth = overview.market_breadth
        buy_count = breadth.get("buy", 0)
        sell_count = breadth.get("sell", 0)
        hold_count = breadth.get("hold", 0)

        lines = [
            "\nLive Market Intelligence (from ML analytics engine):",
            f"- Market Breadth: {buy_count} BUY signals, {hold_count} HOLD, {sell_count} SELL",
        ]

        # Top BUY signals
        top_buys = [
            a
            for a in cached.stock_analyses
            if a.technical_signals.composite_signal.value == "BUY"
        ]
        top_buys.sort(key=lambda a: a.technical_signals.confidence_score, reverse=True)
        if top_buys:
            names = [
                f"{a.symbol.replace('.NS', '')} ({a.technical_signals.confidence_score:.0f}%)"
                for a in top_buys[:5]
            ]
            lines.append(f"- Top BUY signals: {', '.join(names)}")

        # Top SELL signals
        top_sells = [
            a
            for a in cached.stock_analyses
            if a.technical_signals.composite_signal.value == "SELL"
        ]
        top_sells.sort(key=lambda a: a.technical_signals.confidence_score, reverse=True)
        if top_sells:
            names = [
                f"{a.symbol.replace('.NS', '')} ({a.technical_signals.confidence_score:.0f}%)"
                for a in top_sells[:5]
            ]
            lines.append(f"- Top SELL signals: {', '.join(names)}")

        # Anomalies
        anomaly_count = cached.anomaly_count
        if anomaly_count > 0:
            lines.append(f"- Anomalies detected: {anomaly_count}")
            for a in overview.anomaly_alerts[:3]:
                lines.append(
                    f"  - {a.symbol.replace('.NS', '')}: {a.description} [{a.severity}]"
                )

        # Sector highlights
        if overview.sector_heatmap:
            best = max(overview.sector_heatmap, key=lambda s: s.avg_change_pct)
            worst = min(overview.sector_heatmap, key=lambda s: s.avg_change_pct)
            lines.append(
                f"- Strongest sector: {best.sector} ({best.avg_change_pct:+.2f}%)"
            )
            lines.append(
                f"- Weakest sector: {worst.sector} ({worst.avg_change_pct:+.2f}%)"
            )

        lines.append(
            "\nUse this data to give informed, current answers about the Indian market."
        )
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("Failed to build market context: %s", exc)
        return ""


def _macro_context() -> str:
    """Inject macro regime summary from the cached macro dashboard."""
    try:
        from .macro import _cache as _macro_cache

        cached, _ts = _macro_cache
        if cached is None:
            return ""

        lines = ["\nMacro Environment:"]
        lines.append(
            f"- Market Regime: {cached.market_regime} — {cached.regime_description}"
        )

        for ind in cached.indicators:
            lines.append(
                f"- {ind.name}: {ind.value:,.2f} ({ind.change_pct:+.1f}% 1M, trend: {ind.trend})"
            )

        return "\n".join(lines)
    except Exception as exc:
        logger.warning("Failed to build macro context: %s", exc)
        return ""


def _news_context() -> str:
    """Inject recent news sentiment summary."""
    try:
        from .news_sentiment import _cache as _news_cache

        cached, _ts = _news_cache
        if cached is None:
            return ""

        lines = [
            f"\nNews Sentiment (overall: {cached.overall_sentiment}, score: {cached.overall_score:+.2f}):"
        ]

        for s in cached.summaries[:8]:
            lines.append(
                f"- {s.symbol}: {s.sentiment_label} ({s.article_count} articles, "
                f"+{s.positive_count}/-{s.negative_count} headlines)"
            )

        return "\n".join(lines)
    except Exception as exc:
        logger.warning("Failed to build news context: %s", exc)
        return ""


# ── Tool execution ────────────────────────────────────────────────────────────


async def _execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool call and return a JSON string result for the LLM."""
    try:
        if name == "get_stock_analysis":
            symbol = arguments.get("symbol", "")
            if not symbol.endswith(".NS"):
                symbol = f"{symbol}.NS"
            from .analytics import (
                _report_cache,
                _get_cached_df,
                get_stock_name,
                get_stock_sector,
            )

            # Try cached report first
            cached, _ = _report_cache
            if cached:
                for a in cached.stock_analyses:
                    if a.symbol == symbol:
                        return _json.dumps(
                            {
                                "symbol": a.symbol.replace(".NS", ""),
                                "company_name": a.company_name,
                                "sector": a.sector,
                                "signal": a.technical_signals.composite_signal.value,
                                "confidence": f"{a.technical_signals.confidence_score:.0f}%",
                                "composite_score": round(
                                    a.technical_signals.composite_score, 2
                                ),
                                "sharpe_ratio": round(a.risk_metrics.sharpe_ratio, 2),
                                "beta": round(a.risk_metrics.beta, 2),
                                "volatility": f"{a.risk_metrics.volatility:.1f}%",
                                "max_drawdown": f"{a.risk_metrics.max_drawdown:.1f}%",
                                "annualized_return": f"{a.risk_metrics.annualized_return:.1f}%",
                                "var_95": f"{a.risk_metrics.var_95:.2f}%",
                                "rf_probability_up": f"{a.rf_probability:.0%}",
                                "rf_signal": a.rf_signal,
                                "anomalies": [
                                    {
                                        "type": an.anomaly_type,
                                        "description": an.description,
                                        "severity": an.severity,
                                    }
                                    for an in a.anomalies
                                ],
                            }
                        )

            # Fallback: compute on the fly
            import pandas as pd

            df = _get_cached_df(symbol, "1y")
            if df is None or df.empty:
                return _json.dumps(
                    {
                        "error": f"No data found for {symbol}. Check if the symbol is correct."
                    }
                )

            from .analytics import compute_technical_signals, compute_risk_metrics
            import numpy as np

            signals = compute_technical_signals(symbol, df)
            nifty_df = _get_cached_df("^NSEI", "1y")
            risk = compute_risk_metrics(
                symbol, df, nifty_df if nifty_df is not None else pd.DataFrame()
            )
            current_price = float(df.iloc[-1]["close"])

            return _json.dumps(
                {
                    "symbol": symbol.replace(".NS", ""),
                    "company_name": get_stock_name(symbol) or symbol,
                    "sector": get_stock_sector(symbol) or "Unknown",
                    "current_price": round(current_price, 2),
                    "signal": signals.composite_signal.value,
                    "confidence": f"{signals.confidence_score:.0f}%",
                    "composite_score": round(signals.composite_score, 2),
                    "sharpe_ratio": round(risk.sharpe_ratio, 2),
                    "beta": round(risk.beta, 2),
                    "volatility": f"{risk.volatility:.1f}%",
                    "max_drawdown": f"{risk.max_drawdown:.1f}%",
                    "annualized_return": f"{risk.annualized_return:.1f}%",
                }
            )

        elif name == "get_macro_dashboard":
            from .macro import get_macro_dashboard

            result = await get_macro_dashboard()
            return _json.dumps(
                {
                    "regime": result.market_regime,
                    "regime_description": result.regime_description,
                    "indicators": [
                        {
                            "name": ind.name,
                            "value": ind.value,
                            "change_pct_1m": ind.change_pct,
                            "trend": ind.trend,
                            "description": ind.description,
                        }
                        for ind in result.indicators
                    ],
                }
            )

        elif name == "get_news_sentiment":
            from .news_sentiment import get_news_sentiment

            result = await get_news_sentiment()
            return _json.dumps(
                {
                    "overall_sentiment": result.overall_sentiment,
                    "overall_score": result.overall_score,
                    "summaries": [
                        {
                            "symbol": s.symbol,
                            "company_name": s.company_name,
                            "sentiment": s.sentiment_label,
                            "avg_score": s.avg_sentiment,
                            "articles": s.article_count,
                            "positive": s.positive_count,
                            "negative": s.negative_count,
                        }
                        for s in result.summaries[:15]
                    ],
                    "recent_headlines": [
                        {
                            "title": a.title,
                            "sentiment": a.sentiment,
                            "symbols": a.symbols,
                        }
                        for a in result.articles[:10]
                    ],
                }
            )

        elif name == "run_screener":
            from .analytics import screen_stocks

            result = screen_stocks(
                sector=arguments.get("sector"),
                signal=arguments.get("signal"),
                min_sharpe=arguments.get("min_sharpe"),
                sort_by=arguments.get("sort_by", "composite_score"),
                limit=min(arguments.get("limit", 10), 30),
            )
            return _json.dumps(
                {
                    "total": result.total,
                    "buy_count": result.buy_count,
                    "sell_count": result.sell_count,
                    "hold_count": result.hold_count,
                    "stocks": [
                        {
                            "symbol": s.symbol.replace(".NS", ""),
                            "company_name": s.company_name,
                            "sector": s.sector,
                            "price": round(s.current_price, 2),
                            "signal": s.composite_signal.value,
                            "confidence": f"{s.confidence_score:.0f}%",
                            "sharpe": round(s.sharpe_ratio, 2),
                            "volatility": f"{s.volatility:.1f}%",
                            "beta": round(s.beta, 2),
                            "daily_change": f"{s.daily_change_pct:+.1f}%",
                        }
                        for s in result.stocks
                    ],
                }
            )

        else:
            return _json.dumps({"error": f"Unknown tool: {name}"})

    except Exception as exc:
        logger.warning("Tool %s failed: %s", name, exc)
        return _json.dumps({"error": f"Tool {name} failed: {str(exc)}"})


# ── Message building ──────────────────────────────────────────────────────────


def _build_messages(request: AdvisorChatRequest) -> list[dict]:
    system = SYSTEM_PROMPT

    if request.profile:
        system += "\n" + _profile_context(request.profile)

    # Portfolio & watchlist context (from frontend)
    portfolio_ctx = _portfolio_context(request.portfolio_holdings, request.watchlist)
    if portfolio_ctx:
        system += "\n" + portfolio_ctx

    # Market intelligence (from analytics cache)
    system += _market_context()

    # Macro regime
    system += _macro_context()

    # News sentiment
    system += _news_context()

    messages: list[dict] = [{"role": "system", "content": system}]

    # Conversation history — last MAX_HISTORY messages
    for msg in request.conversation_history[-MAX_HISTORY:]:
        messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": request.message})
    return messages


# ── Streaming with tool-use loop ──────────────────────────────────────────────


async def stream_advisor_response(request: AdvisorChatRequest):
    """
    SSE generator — streams tokens to the client using TRUE Groq streaming.

    Time-to-first-token: ~500 ms (Groq starts sending tokens immediately).

    Strategy:
      Each round makes a STREAMING request to Groq.
      - If Groq returns content tokens  → forward them to the client live, return.
      - If Groq returns tool calls      → buffer them, execute, loop.
      - On tool_use_failed              → retry once without tools (force_final).

    Works around the old httpx aiter_lines() bug by using aiter_text() with
    manual line splitting — safe to yield inside async-with context managers.
    """
    settings = get_settings()
    if not settings.groq_api_key:
        yield f"data: {_json.dumps({'error': 'Groq API key is not configured.'})}\n\n"
        return

    messages = _build_messages(request)
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    force_final = False  # set True after tool_use_failed to skip tools

    for _round in range(MAX_TOOL_ROUNDS + 1):
        is_final = (_round == MAX_TOOL_ROUNDS) or force_final

        payload: dict = {
            "model": GROQ_MODEL,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7 if is_final else 0.0,
            "stream": True,
        }
        if not is_final:
            payload["tools"] = TOOLS
            payload["tool_choice"] = "auto"
            payload["parallel_tool_calls"] = False

        # tool-call accumulator for this round
        tool_buf: dict[int, dict] = {}
        got_content = False
        http_err = False

        # Use manually managed client so finally-close works in async generators
        client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))
        try:
            async with client.stream("POST", GROQ_URL, headers=headers, json=payload) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    if b"tool_use_failed" in body and not is_final:
                        logger.info("tool_use_failed — retrying without tools")
                        force_final = True
                        http_err = True
                    else:
                        yield f"data: {_json.dumps({'error': f'Groq error: {resp.status_code}'})}\n\n"
                        return
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
                                break
                            try:
                                obj = _json.loads(raw)
                                delta = obj["choices"][0].get("delta", {})

                                # ── Content token → forward immediately ──
                                if delta.get("content"):
                                    got_content = True
                                    yield f"data: {_json.dumps({'token': delta['content']})}\n\n"

                                # ── Tool-call delta → accumulate ──
                                if delta.get("tool_calls"):
                                    for tc in delta["tool_calls"]:
                                        idx = tc["index"]
                                        if idx not in tool_buf:
                                            tool_buf[idx] = {
                                                "id": "",
                                                "type": "function",
                                                "function": {"name": "", "arguments": ""},
                                            }
                                        if tc.get("id"):
                                            tool_buf[idx]["id"] = tc["id"]
                                        fn = tc.get("function") or {}
                                        if fn.get("name"):
                                            tool_buf[idx]["function"]["name"] += fn["name"]
                                        if fn.get("arguments"):
                                            tool_buf[idx]["function"]["arguments"] += fn["arguments"]

                            except (_json.JSONDecodeError, KeyError, IndexError):
                                continue

        except httpx.RequestError:
            yield f"data: {_json.dumps({'error': 'Could not reach Groq. Please try again.'})}\n\n"
            return
        finally:
            await client.aclose()

        if http_err:
            continue  # retry as final round with force_final=True

        # Content was streamed → done
        if got_content or is_final:
            yield "data: [DONE]\n\n"
            return

        # No content and no tool calls → fall through to final round
        if not tool_buf:
            force_final = True
            continue

        # Execute tool calls, append results, loop for next round
        tool_list = [tool_buf[i] for i in sorted(tool_buf)]
        messages.append({"role": "assistant", "content": None, "tool_calls": tool_list})
        for tc in tool_list:
            try:
                args = _json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
            except _json.JSONDecodeError:
                args = {}
            result = await _execute_tool(tc["function"]["name"], args)
            messages.append({"role": "tool", "tool_call_id": tc["id"], "content": result})

    yield "data: [DONE]\n\n"


# ── Non-streaming fallback ────────────────────────────────────────────────────


async def get_advisor_response(request: AdvisorChatRequest) -> AdvisorChatResponse:
    """Non-streaming fallback with tool-use loop."""
    settings = get_settings()

    if not settings.groq_api_key:
        raise HTTPException(status_code=503, detail="Groq API key is not configured.")

    messages = _build_messages(request)
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }

    for _round in range(MAX_TOOL_ROUNDS + 1):
        is_final_round = _round == MAX_TOOL_ROUNDS

        payload: dict = {
            "model": GROQ_MODEL,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.7 if is_final_round else 0.0,
        }
        if not is_final_round:
            payload["tools"] = TOOLS
            payload["tool_choice"] = "auto"
            payload["parallel_tool_calls"] = False

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(GROQ_URL, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            # Retry without tools on tool_use_failed
            if (
                exc.response.status_code == 400
                and "tool_use_failed" in exc.response.text
                and "tools" in payload
            ):
                logger.info("Retrying without tools due to tool_use_failed")
                payload.pop("tools", None)
                payload.pop("tool_choice", None)
                payload.pop("parallel_tool_calls", None)
                try:
                    async with httpx.AsyncClient(timeout=60) as client:
                        resp = await client.post(
                            GROQ_URL, headers=headers, json=payload
                        )
                        resp.raise_for_status()
                        data = resp.json()
                except httpx.HTTPStatusError as inner_exc:
                    raise HTTPException(
                        status_code=502,
                        detail=f"Groq error: {inner_exc.response.status_code}",
                    )
                except httpx.RequestError:
                    raise HTTPException(
                        status_code=503,
                        detail="Could not reach Groq. Please try again.",
                    )
            elif exc.response.status_code == 429:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limited. Please wait a moment and try again.",
                )
            else:
                raise HTTPException(
                    status_code=502, detail=f"Groq error: {exc.response.status_code}"
                )
        except httpx.RequestError:
            raise HTTPException(
                status_code=503, detail="Could not reach Groq. Please try again."
            )

        choice = data["choices"][0]
        message = choice["message"]
        tool_calls = message.get("tool_calls")

        if tool_calls and not is_final_round:
            messages.append(message)
            for tc in tool_calls:
                try:
                    args = (
                        _json.loads(tc["function"]["arguments"])
                        if tc["function"]["arguments"]
                        else {}
                    )
                except _json.JSONDecodeError:
                    args = {}
                result = await _execute_tool(tc["function"]["name"], args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": result,
                    }
                )
            continue

        # Final text response
        reply = (message.get("content") or "").strip()
        while reply.endswith("---"):
            reply = reply[:-3].rstrip()
        if not reply:
            raise HTTPException(
                status_code=502,
                detail="AI returned an empty response. Please try again.",
            )

        suggestions = []
        for line in reply.split("\n"):
            line = line.strip()
            if line.startswith("- ") and len(line) < 100:
                suggestions.append(line[2:])
            if len(suggestions) >= 3:
                break

        return AdvisorChatResponse(reply=reply, suggestions=suggestions)

    raise HTTPException(
        status_code=502, detail="AI could not complete the response. Please try again."
    )
