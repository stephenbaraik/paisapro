"""
Agentic tool definitions and execution for AI Advisor.

Tools available to the LLM:
  1. get_stock_analysis — Technical + risk analysis for a single stock
  2. get_macro_dashboard — Macro indicators + market regime
  3. get_news_sentiment — Recent news sentiment for Indian stocks
  4. run_screener — Filter/sort stocks by criteria
  5. get_stock_comparison — Compare 2-3 stocks side by side
  6. get_top_gainers_losers — Today's biggest movers
  7. get_sector_analysis — Sector-level performance analysis
  8. get_timeseries_forecast — Historical price trends + simple forecast
  9. search_stocks — Search stocks by name/symbol
  10. get_financial_plan — User's financial plan status (if available)
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Tool definitions (Groq / OpenAI function-calling schema) ──────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_analysis",
            "description": "Get detailed technical analysis for a specific NSE stock. Returns composite signal (BUY/HOLD/SELL), confidence %, risk metrics (Sharpe, beta, volatility, max drawdown, VaR), current price, and anomaly alerts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "NSE stock symbol with .NS suffix, e.g. 'RELIANCE.NS', 'TCS.NS'. If user says a company name, convert it to the NSE ticker."
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
            "description": "Get current macro indicators: India VIX, USD/INR, Nifty 50, Gold (INR), Crude Oil, Bank Nifty, plus the market regime (RISK_ON / RISK_OFF / NEUTRAL). Call when user asks about market conditions, macro outlook, or regime.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_news_sentiment",
            "description": "Get recent news headlines and sentiment analysis for top Indian stocks. Returns per-stock sentiment (BULLISH/BEARISH/NEUTRAL) and overall market sentiment.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_screener",
            "description": "Screen/filter stocks by sector, signal direction, minimum Sharpe ratio, or max drawdown. Returns ranked list of stocks matching the criteria.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sector": {"type": "string", "description": "Filter by sector, e.g. 'IT', 'Banking', 'Pharma'."},
                    "signal": {"type": "string", "enum": ["BUY", "HOLD", "SELL"], "description": "Filter by composite signal."},
                    "min_sharpe": {"type": "number", "description": "Minimum Sharpe ratio threshold."},
                    "max_drawdown": {"type": "number", "description": "Maximum drawdown threshold (positive number, e.g. 20 for -20% max)."},
                    "sort_by": {"type": "string", "enum": ["composite_score", "confidence_score", "sharpe_ratio", "volatility", "daily_change_pct", "beta"], "description": "Sort results by this metric. Default: composite_score."},
                    "limit": {"type": "integer", "description": "Max results (1-30). Default: 10."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_comparison",
            "description": "Compare 2-3 stocks side by side: signals, risk metrics, performance. Use when the user asks to compare specific stocks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of 2-3 NSE stock symbols with .NS suffix, e.g. ['RELIANCE.NS', 'TCS.NS']."
                    }
                },
                "required": ["symbols"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_top_gainers_losers",
            "description": "Get today's biggest gainers and losers from the NSE stock universe. Use when the user asks what's moving today, top performers, or worst decliners.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sector_analysis",
            "description": "Get sector-level performance analysis: average returns, signal distribution, top stocks per sector. Use when the user asks about a sector's outlook or which sectors to focus on.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sector": {"type": "string", "description": "Optional: specific sector name to focus on, e.g. 'IT', 'Banking'."}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_timeseries_forecast",
            "description": "Get historical price trends for a stock over a specific period. Returns price history and a simple trend analysis. Use when the user asks about past performance or price trends.",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "NSE stock symbol with .NS suffix."},
                    "period": {"type": "string", "enum": ["1mo", "3mo", "6mo", "1y", "2y"], "description": "Time period for historical data. Default: 6mo."},
                },
                "required": ["symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_stocks",
            "description": "Search for Indian stocks by company name or symbol. Returns matching stocks with current price and sector. Use when the user mentions a company name and you need to find the correct NSE symbol.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Company name or symbol to search for, e.g. 'Reliance', 'Tata', 'INFY'."}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_plan",
            "description": "Get the user's current financial plan status including goals, progress, and recommendations. Use when the user asks about their financial plan, goals, or progress.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# ── Tool execution ────────────────────────────────────────────────────────────

async def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool call and return a JSON string result for the LLM."""
    try:
        handler = _TOOL_HANDLERS.get(name)
        if handler is None:
            return json.dumps({"error": f"Unknown tool: {name}. Available tools: {', '.join(_TOOL_HANDLERS.keys())}"})
        return await handler(arguments)
    except Exception as exc:
        logger.warning("Tool %s failed with exception: %s", name, exc)
        return json.dumps({"error": f"Tool {name} failed: {str(exc)}"})


async def _handle_stock_analysis(args: dict) -> str:
    """Get detailed technical + risk analysis for a single stock."""
    from ..analytics import get_cached_report
    from ..market_data import get_price_df, get_nifty_df
    from ..technical import compute_technical_signals
    from ..risk import compute_risk_metrics
    from ..universe import get_name, get_sector

    symbol = args.get("symbol", "")
    if not symbol.endswith(".NS"):
        symbol = f"{symbol}.NS"

    # Try cached report first
    report = get_cached_report()
    if report:
        for a in report.stock_analyses:
            if a.symbol == symbol:
                return json.dumps({
                    "symbol": a.symbol.replace(".NS", ""),
                    "company_name": a.company_name,
                    "sector": a.sector,
                    "signal": a.technical_signals.composite_signal.value,
                    "confidence": f"{a.technical_signals.confidence_score:.0f}%",
                    "composite_score": round(a.technical_signals.composite_score, 2),
                    "sharpe_ratio": round(a.risk_metrics.sharpe_ratio, 2),
                    "sortino_ratio": round(a.risk_metrics.sortino_ratio, 2),
                    "beta": round(a.risk_metrics.beta, 2),
                    "volatility": f"{a.risk_metrics.volatility:.1f}%",
                    "max_drawdown": f"{a.risk_metrics.max_drawdown:.1f}%",
                    "annualized_return": f"{a.risk_metrics.annualized_return:.1f}%",
                    "var_95": f"{a.risk_metrics.var_95:.2f}%",
                    "alpha": f"{a.risk_metrics.alpha:.2f}%",
                    "rf_probability_up": f"{a.rf_probability:.0%}",
                    "rf_signal": a.rf_signal,
                    "anomalies": [
                        {"type": an.anomaly_type, "description": an.description, "severity": an.severity}
                        for an in a.anomalies
                    ] if a.anomalies else [],
                })

    # Fallback: compute on the fly
    import pandas as pd
    import numpy as np

    df = get_price_df(symbol, "1y")
    if df is None or df.empty:
        return json.dumps({"error": f"No data found for {symbol}. Check if the symbol is correct."})

    signals = compute_technical_signals(symbol, df)
    nifty_df = get_nifty_df("1y")
    risk = compute_risk_metrics(symbol, df, nifty_df if nifty_df is not None else pd.DataFrame())
    current_price = float(df.iloc[-1]["close"])

    return json.dumps({
        "symbol": symbol.replace(".NS", ""),
        "company_name": get_name(symbol) or symbol,
        "sector": get_sector(symbol) or "Unknown",
        "current_price": round(current_price, 2),
        "signal": signals.composite_signal.value,
        "confidence": f"{signals.confidence_score:.0f}%",
        "composite_score": round(signals.composite_score, 2),
        "sharpe_ratio": round(risk.sharpe_ratio, 2),
        "beta": round(risk.beta, 2),
        "volatility": f"{risk.volatility:.1f}%",
        "max_drawdown": f"{risk.max_drawdown:.1f}%",
        "annualized_return": f"{risk.annualized_return:.1f}%",
    })


async def _handle_macro_dashboard(args: dict) -> str:
    """Get macro indicators and market regime."""
    from ..macro import get_macro_dashboard

    result = await get_macro_dashboard()
    return json.dumps({
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
    })


async def _handle_news_sentiment(args: dict) -> str:
    """Get news sentiment for Indian stocks."""
    from ..news_sentiment import get_news_sentiment

    result = await get_news_sentiment()
    return json.dumps({
        "overall_sentiment": result.overall_sentiment,
        "overall_score": result.overall_score,
        "summaries": [
            {
                "symbol": s.symbol.replace(".NS", ""),
                "company_name": s.company_name,
                "sentiment": s.sentiment_label,
                "avg_score": round(s.avg_sentiment, 3),
                "articles": s.article_count,
                "positive": s.positive_count,
                "negative": s.negative_count,
            }
            for s in result.summaries[:15]
        ],
        "recent_headlines": [
            {"title": a.title, "sentiment": a.sentiment, "symbols": a.symbols}
            for a in result.articles[:10]
        ],
    })


async def _handle_screener(args: dict) -> str:
    """Screen/filter stocks."""
    from ..analytics import screen_stocks

    result = screen_stocks(
        sector=args.get("sector"),
        signal=args.get("signal"),
        min_sharpe=args.get("min_sharpe"),
        sort_by=args.get("sort_by", "composite_score"),
        limit=min(args.get("limit", 10), 30),
    )
    return json.dumps({
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
    })


async def _handle_stock_comparison(args: dict) -> str:
    """Compare 2-3 stocks side by side."""
    symbols = args.get("symbols", [])
    if not isinstance(symbols, list) or len(symbols) < 2 or len(symbols) > 3:
        return json.dumps({"error": "Please provide exactly 2-3 stock symbols to compare."})

    # Normalize symbols
    symbols = [s if s.endswith(".NS") else f"{s}.NS" for s in symbols]

    from ..analytics import get_cached_report
    from ..market_data import get_price_df
    from ..technical import compute_technical_signals
    from ..risk import compute_risk_metrics
    from ..universe import get_name, get_sector
    import pandas as pd

    comparison = []
    for symbol in symbols:
        report = get_cached_report()
        found = False
        if report:
            for a in report.stock_analyses:
                if a.symbol == symbol:
                    comparison.append({
                        "symbol": symbol.replace(".NS", ""),
                        "company_name": a.company_name,
                        "sector": a.sector,
                        "signal": a.technical_signals.composite_signal.value,
                        "confidence": f"{a.technical_signals.confidence_score:.0f}%",
                        "sharpe_ratio": round(a.risk_metrics.sharpe_ratio, 2),
                        "beta": round(a.risk_metrics.beta, 2),
                        "volatility": f"{a.risk_metrics.volatility:.1f}%",
                        "max_drawdown": f"{a.risk_metrics.max_drawdown:.1f}%",
                        "annualized_return": f"{a.risk_metrics.annualized_return:.1f}%",
                        "rf_signal": a.rf_signal,
                        "rf_probability": f"{a.rf_probability:.0%}",
                    })
                    found = True
                    break

        if not found:
            df = get_price_df(symbol, "1y")
            if df is None or df.empty:
                comparison.append({"symbol": symbol.replace(".NS", ""), "error": "No data available"})
                continue
            signals = compute_technical_signals(symbol, df)
            nifty_df = get_nifty_df("1y")
            risk = compute_risk_metrics(symbol, df, nifty_df if nifty_df is not None else pd.DataFrame())
            comparison.append({
                "symbol": symbol.replace(".NS", ""),
                "company_name": get_name(symbol) or symbol,
                "sector": get_sector(symbol) or "Unknown",
                "signal": signals.composite_signal.value,
                "confidence": f"{signals.confidence_score:.0f}%",
                "sharpe_ratio": round(risk.sharpe_ratio, 2),
                "beta": round(risk.beta, 2),
                "volatility": f"{risk.volatility:.1f}%",
                "max_drawdown": f"{risk.max_drawdown:.1f}%",
                "annualized_return": f"{risk.annualized_return:.1f}%",
            })

    return json.dumps({"comparison": comparison})


async def _handle_top_gainers_losers(args: dict) -> str:
    """Get today's biggest gainers and losers."""
    from ..analytics import get_cached_report

    report = get_cached_report()
    if not report:
        return json.dumps({"error": "Market analytics not available yet. Please try again later."})

    gainers = sorted(
        [a for a in report.stock_analyses if a.technical_signals.composite_signal.value == "BUY"],
        key=lambda a: a.technical_signals.confidence_score,
        reverse=True,
    )[:10]

    losers = sorted(
        [a for a in report.stock_analyses if a.technical_signals.composite_signal.value == "SELL"],
        key=lambda a: a.technical_signals.confidence_score,
        reverse=True,
    )[:10]

    return json.dumps({
        "top_gainers": [
            {
                "symbol": a.symbol.replace(".NS", ""),
                "company_name": a.company_name,
                "sector": a.sector,
                "confidence": f"{a.technical_signals.confidence_score:.0f}%",
                "composite_score": round(a.technical_signals.composite_score, 2),
            }
            for a in gainers
        ],
        "top_losers": [
            {
                "symbol": a.symbol.replace(".NS", ""),
                "company_name": a.company_name,
                "sector": a.sector,
                "confidence": f"{a.technical_signals.confidence_score:.0f}%",
                "composite_score": round(a.technical_signals.composite_score, 2),
            }
            for a in losers
        ],
    })


async def _handle_sector_analysis(args: dict) -> str:
    """Get sector-level performance analysis."""
    from ..analytics import get_cached_report

    report = get_cached_report()
    if not report:
        return json.dumps({"error": "Market analytics not available yet. Please try again later."})

    overview = report.market_overview
    sector_heatmap = overview.sector_heatmap or []

    # If a specific sector is requested, filter; otherwise return all
    target = args.get("sector")
    if target:
        sector_heatmap = [s for s in sector_heatmap if target.lower() in s.sector.lower()]

    # Per-sector signal distribution
    sector_signals: dict[str, dict[str, int]] = {}
    for a in report.stock_analyses:
        sec = a.sector or "Unknown"
        if sec not in sector_signals:
            sector_signals[sec] = {"BUY": 0, "HOLD": 0, "SELL": 0}
        sig = a.technical_signals.composite_signal.value
        if sig in sector_signals[sec]:
            sector_signals[sec][sig] += 1

    result_sectors = []
    for s in sector_heatmap:
        result_sectors.append({
            "sector": s.sector,
            "avg_change_pct": round(s.avg_change_pct, 2),
            "stock_count": s.stock_count,
            "signal_distribution": sector_signals.get(s.sector, {"BUY": 0, "HOLD": 0, "SELL": 0}),
        })

    result_sectors.sort(key=lambda x: x["avg_change_pct"], reverse=True)

    return json.dumps({
        "sectors": result_sectors,
        "strongest": result_sectors[0] if result_sectors else None,
        "weakest": result_sectors[-1] if result_sectors else None,
    })


async def _handle_timeseries_forecast(args: dict) -> str:
    """Get historical price trends + simple trend analysis."""
    from ..market_data import get_price_df

    symbol = args.get("symbol", "")
    if not symbol.endswith(".NS"):
        symbol = f"{symbol}.NS"
    period = args.get("period", "6mo")

    df = get_price_df(symbol, period)
    if df is None or df.empty or len(df) < 20:
        return json.dumps({"error": f"Insufficient historical data for {symbol}."})

    current = float(df.iloc[-1]["close"])
    first = float(df.iloc[0]["close"])
    change_pct = ((current - first) / first * 100) if first > 0 else 0.0

    # Simple trend analysis
    sma_20 = float(df.iloc[-1].get("sma_20", 0)) if "sma_20" in df.columns else 0
    sma_50 = float(df.iloc[-1].get("sma_50", 0)) if "sma_50" in df.columns else 0

    trend = "UPTREND" if current > sma_20 > sma_50 else ("DOWNTREND" if current < sma_20 < sma_50 else "SIDEWAYS")

    # Return last 30 data points for brevity
    recent = df.tail(30)
    price_history = [
        {"date": row["date"].strftime("%Y-%m-%d"), "close": round(float(row["close"]), 2)}
        for _, row in recent.iterrows()
    ]

    return json.dumps({
        "symbol": symbol.replace(".NS", ""),
        "period": period,
        "current_price": round(current, 2),
        "period_start_price": round(first, 2),
        "period_change_pct": round(change_pct, 2),
        "trend": trend,
        "sma_20": round(sma_20, 2) if sma_20 else None,
        "sma_50": round(sma_50, 2) if sma_50 else None,
        "price_history": price_history,
    })


async def _handle_search_stocks(args: dict) -> str:
    """Search stocks by name or symbol."""
    import httpx
    from ..core.config import get_settings

    query = args.get("query", "").strip()
    if not query:
        return json.dumps({"error": "Please provide a search query."})

    settings = get_settings()
    try:
        url = f"{settings.supabase_url}/rest/v1/stocks"
        headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
        }
        resp = httpx.get(
            url,
            headers=headers,
            params={
                "select": "symbol,company_name,sector,current_price",
                "or": f"symbol.ilike.%{query}%,company_name.ilike.%{query}%",
                "limit": "10",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return json.dumps({"error": f"Search failed: {str(exc)}"})

    if not data:
        return json.dumps({"error": f"No stocks found matching '{query}'. Try a different name or symbol."})

    return json.dumps({
        "query": query,
        "results": [
            {
                "symbol": f"{row['symbol']}.NS",
                "company_name": row["company_name"],
                "sector": row.get("sector", "Unknown"),
                "current_price": row.get("current_price"),
            }
            for row in data
        ],
    })


async def _handle_financial_plan(args: dict) -> str:
    """Get user's financial plan status (if available)."""
    from ..core.cache import cache

    plan = cache.get("user:financial_plan")
    if not plan:
        return json.dumps({"info": "No financial plan found for user. The user can create a plan using the Financial Planner feature."})

    return json.dumps({
        "plan_summary": {
            "goals": plan.get("goals", []),
            "risk_profile": plan.get("risk_profile", "Unknown"),
            "target_corpus": plan.get("target_corpus"),
            "current_savings": plan.get("current_savings"),
            "monthly_investment": plan.get("monthly_investment"),
            "probability_of_success": plan.get("probability_of_success"),
        },
    })


# ── Tool registry ─────────────────────────────────────────────────────────────

_TOOL_HANDLERS = {
    "get_stock_analysis": _handle_stock_analysis,
    "get_macro_dashboard": _handle_macro_dashboard,
    "get_news_sentiment": _handle_news_sentiment,
    "run_screener": _handle_screener,
    "get_stock_comparison": _handle_stock_comparison,
    "get_top_gainers_losers": _handle_top_gainers_losers,
    "get_sector_analysis": _handle_sector_analysis,
    "get_timeseries_forecast": _handle_timeseries_forecast,
    "search_stocks": _handle_search_stocks,
    "get_financial_plan": _handle_financial_plan,
}
