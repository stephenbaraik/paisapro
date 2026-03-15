"""
AI advisor service powered by OpenRouter (free LLM API).
Uses the OpenAI-compatible /chat/completions endpoint.
"""

import httpx
from ..core.config import get_settings
from ..schemas.financial import UserFinancialProfile, AdvisorChatRequest, AdvisorChatResponse

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "mistralai/mistral-small-3.1-24b-instruct:free"

SYSTEM_PROMPT = """You are an expert Indian investment advisor AI assistant built into a personal finance planning tool.
Your role is to help users understand their investment strategy, explain financial concepts, and provide actionable advice.

Key context:
- You are focused on the Indian financial market (NSE/BSE, Nifty, Sensex, Indian mutual funds, SIPs, PPF, NPS, ELSS)
- All monetary values are in Indian Rupees (INR / ₹)
- Regulatory context: SEBI regulations, Indian tax laws (LTCG, STCG, Section 80C)
- Be clear that your advice is educational and not a registered financial advisory service

Tone: Professional yet approachable. Use simple language. Avoid jargon unless explaining it.
Format: Use bullet points and short paragraphs. Keep answers concise.

When the user provides their financial profile, use it to personalise your response."""


def _profile_context(profile: UserFinancialProfile | None) -> str:
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


def _market_context() -> str:
    """Inject live market intelligence from the analytics cache into the advisor."""
    try:
        from .analytics import get_market_overview, _report_cache
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
            a for a in cached.stock_analyses
            if a.technical_signals.composite_signal.value == "BUY"
        ]
        top_buys.sort(key=lambda a: a.technical_signals.confidence_score, reverse=True)
        if top_buys:
            names = [f"{a.symbol.replace('.NS','')} ({a.technical_signals.confidence_score:.0f}%)" for a in top_buys[:5]]
            lines.append(f"- Top BUY signals: {', '.join(names)}")

        # Top SELL signals
        top_sells = [
            a for a in cached.stock_analyses
            if a.technical_signals.composite_signal.value == "SELL"
        ]
        top_sells.sort(key=lambda a: a.technical_signals.confidence_score, reverse=True)
        if top_sells:
            names = [f"{a.symbol.replace('.NS','')} ({a.technical_signals.confidence_score:.0f}%)" for a in top_sells[:5]]
            lines.append(f"- Top SELL signals: {', '.join(names)}")

        # Anomalies
        anomaly_count = cached.anomaly_count
        if anomaly_count > 0:
            lines.append(f"- Anomalies detected: {anomaly_count}")
            for a in overview.anomaly_alerts[:3]:
                lines.append(f"  - {a.symbol.replace('.NS','')}: {a.description} [{a.severity}]")

        # Sector highlights
        if overview.sector_heatmap:
            best = max(overview.sector_heatmap, key=lambda s: s.avg_change_pct)
            worst = min(overview.sector_heatmap, key=lambda s: s.avg_change_pct)
            lines.append(f"- Strongest sector: {best.sector} ({best.avg_change_pct:+.2f}%)")
            lines.append(f"- Weakest sector: {worst.sector} ({worst.avg_change_pct:+.2f}%)")

        lines.append("\nUse this data to give informed, current answers about the Indian market.")
        return "\n".join(lines)
    except Exception:
        return ""


async def get_advisor_response(request: AdvisorChatRequest) -> AdvisorChatResponse:
    settings = get_settings()

    system = SYSTEM_PROMPT
    if request.profile:
        system += "\n" + _profile_context(request.profile)
    system += _market_context()

    messages = [{"role": "system", "content": system}]
    for msg in request.conversation_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": request.message})

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5173",
                "X-Title": "AI Investment Advisor",
            },
            json={
                "model": MODEL,
                "messages": messages,
                "max_tokens": 1024,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    reply = data["choices"][0]["message"]["content"]

    suggestions = []
    for line in reply.split("\n"):
        line = line.strip()
        if line.startswith("- ") and len(line) < 100:
            suggestions.append(line[2:])
        if len(suggestions) >= 3:
            break

    return AdvisorChatResponse(reply=reply, suggestions=suggestions)
