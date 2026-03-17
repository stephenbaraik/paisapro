"""
AI-powered portfolio builder.

Uses Groq LLM + live market intelligence to suggest stocks and quantities
based on the user's investment amount and risk tolerance.
"""

import json
import logging
import httpx
from ..core.config import get_settings

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


def _market_snapshot() -> str:
    """Build a concise market snapshot for the LLM from the analytics cache."""
    try:
        from .analytics import get_cached_report, _get_cached_df

        cached = get_cached_report()
        if cached is None:
            return "No market data available."

        lines = []

        # All stocks with BUY signal, sorted by confidence
        buy_stocks = [
            a for a in cached.stock_analyses
            if a.technical_signals.composite_signal.value == "BUY"
        ]
        buy_stocks.sort(key=lambda a: a.technical_signals.confidence_score, reverse=True)

        hold_stocks = [
            a for a in cached.stock_analyses
            if a.technical_signals.composite_signal.value == "HOLD"
        ]
        hold_stocks.sort(key=lambda a: a.technical_signals.confidence_score, reverse=True)

        lines.append("=== STOCKS WITH BUY SIGNAL ===")
        for a in buy_stocks:
            sym = a.symbol.replace(".NS", "")
            rm = a.risk_metrics
            price = a.technical_signals.current_price
            lines.append(
                f"- {sym} ({a.company_name}) | Sector: {a.sector} | "
                f"Price: {price:.2f} | Confidence: {a.technical_signals.confidence_score:.0f}% | "
                f"Sharpe: {rm.sharpe_ratio:.2f} | MaxDD: {rm.max_drawdown:.1%} | "
                f"Beta: {rm.beta:.2f} | Vol: {rm.volatility:.1%}"
            )

        lines.append("\n=== STOCKS WITH HOLD SIGNAL ===")
        for a in hold_stocks[:10]:
            sym = a.symbol.replace(".NS", "")
            rm = a.risk_metrics
            price = a.technical_signals.current_price
            lines.append(
                f"- {sym} ({a.company_name}) | Sector: {a.sector} | "
                f"Price: {price:.2f} | Confidence: {a.technical_signals.confidence_score:.0f}% | "
                f"Sharpe: {rm.sharpe_ratio:.2f} | MaxDD: {rm.max_drawdown:.1%} | "
                f"Beta: {rm.beta:.2f} | Vol: {rm.volatility:.1%}"
            )

        # Sector performance
        overview = cached.market_overview
        if overview.sector_heatmap:
            lines.append("\n=== SECTOR PERFORMANCE ===")
            for s in sorted(overview.sector_heatmap, key=lambda x: x.avg_change_pct, reverse=True):
                lines.append(f"- {s.sector}: {s.avg_change_pct:+.2f}% ({s.stock_count} stocks)")

        # Anomalies as warnings
        if overview.anomaly_alerts:
            lines.append("\n=== ANOMALY WARNINGS ===")
            for a in overview.anomaly_alerts[:5]:
                lines.append(f"- {a.symbol.replace('.NS','')}: {a.description} [{a.severity}]")

        return "\n".join(lines)
    except Exception as e:
        logger.warning("Failed to build market snapshot: %s", e)
        return "Market data temporarily unavailable."


SYSTEM_PROMPT = """You are an expert Indian equity portfolio constructor built into PaisaPro.ai.
Your job: given the user's investment amount and risk profile, select the best stocks and allocate quantities to build an optimal portfolio.

Rules:
- ONLY pick from the stocks listed in the market data provided. Do NOT invent symbols.
- For conservative: prefer high-Sharpe, low-volatility, low-beta stocks. Pick 8-12 stocks. Diversify broadly across sectors.
- For moderate: balanced mix of growth and value. Pick 7-10 stocks. Diversify across at least 4 sectors.
- For aggressive: high-confidence BUY signals with strong momentum. Pick 5-8 stocks. At least 3 sectors.
- IMPORTANT: You MUST pick at least 5 stocks. Spread the allocation, do not over-concentrate.
- Allocate rupee amounts per stock, then calculate quantity = floor(allocation / current_price).
- No single stock should exceed 20% of total investment.
- Use current market prices from the data provided.
- The sum of all allocations must be between 90% and 98% of the investment amount.
- Prioritize stocks with BUY signal first, then HOLD stocks with high Sharpe ratios.

You MUST respond with ONLY valid JSON in this exact format — no markdown, no explanation outside JSON:
{
  "picks": [
    {
      "symbol": "RELIANCE",
      "company_name": "Reliance Industries",
      "sector": "Energy",
      "current_price": 1234.56,
      "quantity": 10,
      "allocation": 12345.60,
      "weight_pct": 12.3,
      "reason": "Strong BUY signal with 78% confidence, low volatility, sector leader"
    }
  ],
  "strategy_summary": "Brief 2-3 sentence summary of the portfolio strategy",
  "risk_notes": "Key risks to be aware of",
  "expected_sectors": {"Energy": 25.0, "IT": 20.0},
  "total_allocated": 95000,
  "cash_remaining": 5000
}"""


async def ai_build_portfolio(
    investment_amount: float,
    risk_profile: str = "moderate",
) -> dict:
    """Call the LLM with market data to generate stock picks."""
    settings = get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("Groq API key is not configured.")

    snapshot = _market_snapshot()

    user_prompt = f"""Build me a portfolio with these parameters:
- Investment Amount: Rs {investment_amount:,.0f}
- Risk Profile: {risk_profile.upper()}

Here is the current market data for Indian stocks:

{snapshot}

Respond with ONLY the JSON object. No markdown fences, no extra text."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": messages,
                    "max_tokens": 4096,
                    "temperature": 0.3,  # lower temp for structured output
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            raise RuntimeError("Rate limited by Groq. Please wait a moment.")
        raise RuntimeError(f"Groq API error: {exc.response.status_code}")
    except httpx.RequestError:
        raise RuntimeError("Could not reach Groq API. Please try again.")

    raw = (data["choices"][0]["message"].get("content") or "").strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3].rstrip()
    if raw.startswith("json"):
        raw = raw[4:].lstrip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                result = json.loads(raw[start:end])
            except json.JSONDecodeError:
                raise RuntimeError("AI returned invalid JSON. Please try again.")
        else:
            raise RuntimeError("AI returned invalid response format. Please try again.")

    # Validate and enrich picks with live prices
    from .portfolio import _get_latest_price, _get_stock_meta

    picks = result.get("picks", [])
    validated_picks = []
    for pick in picks:
        sym = pick.get("symbol", "").upper().replace(".NS", "")
        if not sym:
            continue
        price, change = _get_latest_price(sym)
        name, sector = _get_stock_meta(sym)

        if price <= 0:
            price = pick.get("current_price", 0)

        qty = int(pick.get("quantity", 0))
        if qty <= 0 and price > 0:
            alloc = pick.get("allocation", 0)
            qty = int(alloc / price) if alloc > 0 else 0

        if qty <= 0 or price <= 0:
            continue

        validated_picks.append({
            "symbol": sym,
            "company_name": name or pick.get("company_name", ""),
            "sector": sector or pick.get("sector", ""),
            "current_price": round(price, 2),
            "daily_change_pct": change,
            "quantity": qty,
            "allocation": round(price * qty, 2),
            "weight_pct": 0,  # recalculated below
            "reason": pick.get("reason", ""),
        })

    # Post-process: scale down if total exceeds budget
    total_allocated = sum(p["allocation"] for p in validated_picks)
    if total_allocated > investment_amount and validated_picks:
        scale = investment_amount * 0.97 / total_allocated  # 3% cash buffer
        for p in validated_picks:
            new_qty = max(1, int(p["quantity"] * scale))
            p["quantity"] = new_qty
            p["allocation"] = round(p["current_price"] * new_qty, 2)
        total_allocated = sum(p["allocation"] for p in validated_picks)

    # Cap any single stock at 25% of total
    for p in validated_picks:
        max_alloc = investment_amount * 0.25
        if p["allocation"] > max_alloc and p["current_price"] > 0:
            p["quantity"] = max(1, int(max_alloc / p["current_price"]))
            p["allocation"] = round(p["current_price"] * p["quantity"], 2)
    total_allocated = sum(p["allocation"] for p in validated_picks)

    # Recalculate weights
    for p in validated_picks:
        p["weight_pct"] = round(p["allocation"] / investment_amount * 100, 1) if investment_amount > 0 else 0

    return {
        "picks": validated_picks,
        "strategy_summary": result.get("strategy_summary", ""),
        "risk_notes": result.get("risk_notes", ""),
        "total_allocated": round(total_allocated, 2),
        "cash_remaining": round(investment_amount - total_allocated, 2),
        "investment_amount": investment_amount,
        "risk_profile": risk_profile,
    }
