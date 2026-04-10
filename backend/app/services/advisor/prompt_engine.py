"""
Prompt engine for AI Advisor.

Builds system prompts with structured sections, enforces disclaimers,
and provides clear tool-use guidance.
"""

from typing import Optional

from ..schemas.financial import (
    UserFinancialProfile,
    PortfolioHoldingContext,
    WatchlistItemContext,
)

# ── Structured system prompt ──────────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """\
# ROLE & PERSONA

You are **PaisaPro AI Advisor** — an expert Indian investment advisor AI built into PaisaPro.ai.
Your mission is to help users make informed financial decisions using real-time data analysis.

## Market Focus
- Indian financial markets: NSE, BSE, Nifty indices, Sensex, Indian mutual funds, SIPs, PPF, NPS, ELSS
- All monetary values in Indian Rupees (INR / ₹)
- Indian regulatory context: SEBI regulations, Income Tax laws (LTCG, STCG, Section 80C, etc.)

## Core Principles
1. **Data-Driven**: Always ground your advice in the real data provided below. Never invent prices, signals, or statistics.
2. **Honest About Uncertainty**: If data is missing or inconclusive, say so clearly.
3. **Educational First**: Explain concepts before recommending actions. Teach the user to think critically.
4. **Risk-Aware**: Always consider the user's risk tolerance and financial situation.
5. **Compliant**: Your advice is educational in nature. You are NOT a SEBI-registered investment advisor.

---

# MANDATORY DISCLAIMER

End every response with this exact block (as a blockquote):
> ⚠️ *This is for educational purposes only. Not a SEBI-registered investment advisory service. Please consult a certified financial advisor before making investment decisions.*

---

# RESPONSE FORMATTING RULES

1. Use `##` for section headings. Never nest headings inside list items.
2. Use bullet lists (`- item`) for points. Each item = ONE short line.
3. Put a blank line before/after every heading, list, and block.
4. Use **bold** only for key terms or amounts — never entire sentences.
5. Keep paragraphs to 2-3 sentences max.
6. Use `>` blockquotes for the mandatory disclaimer and important takeaways.
7. Use markdown tables when comparing items side by side.
8. Do NOT mix prose and list items without a blank line between them.
9. Do NOT use HTML tags.

---

# TOOL USAGE RULES

You have access to live data tools. **ALWAYS use them** when the question involves specific stocks, market conditions, news, screening, or comparisons.

## NEVER guess from memory:
- Stock prices, signals, or rankings
- Market regime or macro indicators
- News sentiment or recent headlines
- Sector performance data

## Tool Selection Guide:
- User asks about a specific stock → call `get_stock_analysis`
- User asks about market outlook or regime → call `get_macro_dashboard`
- User asks about recent events/news → call `get_news_sentiment`
- User wants to find/filter stocks → call `run_screener`
- User wants to compare stocks → call `get_stock_comparison`
- User asks what's moving today → call `get_top_gainers_losers`
- User asks about a sector's outlook → call `get_sector_analysis`
- User asks about price history/trends → call `get_timeseries_forecast`
- User mentions a company name → first call `search_stocks` to find the correct symbol

## When a tool returns no data:
State clearly: "No data available for [X]. The symbol may be incorrect or data is not yet populated."

---

# WHAT YOU MUST NOT DO

1. ❌ Give specific price targets or guaranteed returns
2. ❌ Recommend illegal activities or tax evasion
3. ❌ Promise any level of profit
4. ❌ Provide personalized investment advice without considering the user's risk profile
5. ❌ Discuss political opinions or non-financial topics
6. ❌ Share other users' data or internal system details
7. ❌ Ignore the user's financial profile when it's provided

---

{context_sections}

# CONVERSATION START

You are now ready to assist the user. Be helpful, data-driven, and always end with the disclaimer.
"""

# ── Context injection templates ───────────────────────────────────────────────

PROFILE_TEMPLATE = """## User Financial Profile
- Monthly Income: ₹{monthly_income:,.0f}
- Monthly Expenses: ₹{monthly_expenses:,.0f}
- Investable Surplus: ₹{surplus:,.0f}/month
- Current Savings: ₹{current_savings:,.0f}
- Age: {age} years
- Risk Tolerance: {risk_tolerance}
"""

PORTFOLIO_TEMPLATE = """## User's Portfolio Holdings
- Total Invested: ₹{total_invested:,.0f}
- Current Value: ₹{total_current:,.0f} ({pnl_pct:+.1f}%)
- Holdings: {count} stocks across {sector_count} sectors
- Sector Allocation: {sector_allocation}

### Individual Holdings
{holdings_detail}
"""

WATCHLIST_TEMPLATE = """## User's Watchlist
{watchlist_items}
"""

MARKET_TEMPLATE = """## Live Market Intelligence
- Market Breadth: {buy_count} BUY, {hold_count} HOLD, {sell_count} SELL
- Top BUY Signals: {top_buys}
- Top SELL Signals: {top_sells}
- Strongest Sector: {best_sector}
- Weakest Sector: {worst_sector}
- Anomalies Detected: {anomaly_count}
"""

MACRO_TEMPLATE = """## Macro Environment
- Market Regime: {regime} — {regime_desc}
{macro_indicators}
"""

NEWS_TEMPLATE = """## News Sentiment
- Overall Market Sentiment: {overall_sentiment} (score: {overall_score:+.2f})
{news_items}
"""


# ── Context builder functions ─────────────────────────────────────────────────

def build_profile_context(profile: Optional[UserFinancialProfile]) -> str:
    if not profile:
        return ""
    surplus = profile.monthly_income - profile.monthly_expenses
    return PROFILE_TEMPLATE.format(
        monthly_income=profile.monthly_income,
        monthly_expenses=profile.monthly_expenses,
        surplus=surplus,
        current_savings=profile.current_savings,
        age=profile.age,
        risk_tolerance=profile.risk_profile.value.capitalize(),
    )


def build_portfolio_context(
    holdings: list[PortfolioHoldingContext],
    watchlist: list[WatchlistItemContext],
) -> str:
    parts = []

    if holdings:
        total_invested = sum(h.buy_price * h.quantity for h in holdings)
        total_current = sum(
            h.current_price * h.quantity for h in holdings if h.current_price > 0
        )
        total_pnl_pct = (
            ((total_current - total_invested) / total_invested * 100)
            if total_invested > 0 else 0.0
        )

        sector_value: dict[str, float] = {}
        for h in holdings:
            val = h.current_price * h.quantity if h.current_price > 0 else h.buy_price * h.quantity
            sector_value[h.sector or "Unknown"] = sector_value.get(h.sector or "Unknown", 0) + val
        total_val = sum(sector_value.values()) or 1
        sector_alloc = ", ".join(
            f"{sec}: {val/total_val*100:.0f}%"
            for sec, val in sorted(sector_value.items(), key=lambda x: x[1], reverse=True)
        )

        holdings_detail = "\n".join(
            f"  - {h.symbol.replace('.NS', '')}: {h.quantity:.0f} shares @ ₹{h.buy_price:,.0f}, "
            f"current ₹{h.current_price:,.0f}, {h.pnl_pct:+.1f}%"
            for h in sorted(holdings, key=lambda x: x.current_price * x.quantity if x.current_price > 0 else 0, reverse=True)
        )

        parts.append(PORTFOLIO_TEMPLATE.format(
            total_invested=total_invested,
            total_current=total_current,
            pnl_pct=total_pnl_pct,
            count=len(holdings),
            sector_count=len(sector_value),
            sector_allocation=sector_alloc,
            holdings_detail=holdings_detail,
        ))

    if watchlist:
        items = "\n".join(
            f"  - {w.symbol.replace('.NS', '')} ({w.sector or '?'}): "
            f"₹{w.current_price:,.0f}" if w.current_price > 0 else f"  - {w.symbol.replace('.NS', '')}: N/A"
            f", {w.daily_change_pct:+.1f}% today"
            for w in watchlist
        )
        parts.append(WATCHLIST_TEMPLATE.format(watchlist_items=items))

    if not parts:
        return ""

    result = "\n".join(parts)
    result += "\n\n⚠️ Use this data for personalised advice. Flag concentration risk, sector imbalance, or underperformers."
    return result


def build_market_context(market_data: dict) -> str:
    if not market_data:
        return ""
    return MARKET_TEMPLATE.format(
        buy_count=market_data.get("buy_count", 0),
        hold_count=market_data.get("hold_count", 0),
        sell_count=market_data.get("sell_count", 0),
        top_buys=market_data.get("top_buys", "None"),
        top_sells=market_data.get("top_sells", "None"),
        best_sector=market_data.get("best_sector", "N/A"),
        worst_sector=market_data.get("worst_sector", "N/A"),
        anomaly_count=market_data.get("anomaly_count", 0),
    )


def build_macro_context(macro_data: dict) -> str:
    if not macro_data:
        return ""
    indicators = "\n".join(
        f"  - {ind['name']}: {ind['value']:,.2f} ({ind['change_pct']:+.1f}% 1M, {ind['trend']})"
        for ind in macro_data.get("indicators", [])
    )
    return MACRO_TEMPLATE.format(
        regime=macro_data.get("regime", "UNKNOWN"),
        regime_desc=macro_data.get("regime_description", ""),
        macro_indicators=indicators,
    )


def build_news_context(news_data: dict) -> str:
    if not news_data:
        return ""
    items = "\n".join(
        f"  - {s['symbol']}: {s['sentiment']} ({s['articles']} articles, +{s['positive']}/-{s['negative']})"
        for s in news_data.get("summaries", [])[:8]
    )
    return NEWS_TEMPLATE.format(
        overall_sentiment=news_data.get("overall_sentiment", "UNKNOWN"),
        overall_score=news_data.get("overall_score", 0.0),
        news_items=items,
    )


# ── Full system prompt builder ────────────────────────────────────────────────

def build_system_prompt(
    profile: Optional[UserFinancialProfile] = None,
    holdings: list[PortfolioHoldingContext] | None = None,
    watchlist: list[WatchlistItemContext] | None = None,
    market_data: dict | None = None,
    macro_data: dict | None = None,
    news_data: dict | None = None,
) -> str:
    """Build the complete system prompt with all context sections."""
    context_parts = []

    # Profile context
    ctx = build_profile_context(profile)
    if ctx:
        context_parts.append(ctx)

    # Portfolio context
    if holdings or watchlist:
        ctx = build_portfolio_context(holdings or [], watchlist or [])
        if ctx:
            context_parts.append(ctx)

    # Market context
    if market_data:
        context_parts.append(build_market_context(market_data))

    # Macro context
    if macro_data:
        context_parts.append(build_macro_context(macro_data))

    # News context
    if news_data:
        context_parts.append(build_news_context(news_data))

    context_str = "\n".join(context_parts) if context_parts else "No additional context available."

    return SYSTEM_PROMPT_TEMPLATE.format(context_sections=context_str)
