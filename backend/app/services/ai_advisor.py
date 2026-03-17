"""
AI advisor service powered by Groq (Llama 3.3 70B).
Uses the OpenAI-compatible /chat/completions endpoint.
"""

import httpx
from fastapi import HTTPException
from ..core.config import get_settings
from ..schemas.financial import UserFinancialProfile, AdvisorChatRequest, AdvisorChatResponse

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are an expert Indian investment advisor AI assistant built into a personal finance planning tool.
Your role is to help users understand their investment strategy, explain financial concepts, and provide actionable advice.

Key context:
- You are focused on the Indian financial market (NSE/BSE, Nifty, Sensex, Indian mutual funds, SIPs, PPF, NPS, ELSS)
- All monetary values are in Indian Rupees (INR / ₹)
- Regulatory context: SEBI regulations, Indian tax laws (LTCG, STCG, Section 80C)
- Be clear that your advice is educational and not a registered financial advisory service

Tone: Professional yet approachable. Use simple language. Avoid jargon unless explaining it.

Formatting rules (STRICT — your output is rendered as Markdown):
- Use ## for section headings. Never put headings inside list items.
- Use bullet lists (- item) for points. Use numbered lists (1. item) only for sequential steps.
- Each list item must be ONE short line. Never put multiple sentences or sub-points on a single list item.
- Put a blank line before and after every heading, list, and block.
- Use **bold** sparingly — only for key terms or amounts, never for entire sentences.
- Keep paragraphs to 2-3 sentences max.
- Use > blockquote for important callouts or final takeaways.
- Use markdown tables when comparing multiple items side by side. Keep columns concise.
- Do NOT mix prose paragraphs and list items without a blank line between them.

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
        from .analytics import get_market_overview, get_cached_report
        cached = get_cached_report()
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


def _build_messages(request: AdvisorChatRequest) -> list[dict]:
    system = SYSTEM_PROMPT
    if request.profile:
        system += "\n" + _profile_context(request.profile)
    system += _market_context()

    messages = [{"role": "system", "content": system}]
    for msg in request.conversation_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": request.message})
    return messages


async def stream_advisor_response(request: AdvisorChatRequest):
    """SSE generator — streams tokens from Groq to the client."""
    import json as _json

    settings = get_settings()
    if not settings.groq_api_key:
        yield f"data: {_json.dumps({'error': 'Groq API key is not configured.'})}\n\n"
        return

    messages = _build_messages(request)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            async with client.stream(
                "POST",
                GROQ_URL,
                headers={
                    "Authorization": f"Bearer {settings.groq_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": messages,
                    "max_tokens": 4096,
                    "temperature": 0.7,
                    "stream": True,
                },
            ) as resp:
                if resp.status_code != 200:
                    yield f"data: {_json.dumps({'error': f'Groq error: {resp.status_code}'})}\n\n"
                    return

                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload.strip() == "[DONE]":
                        yield "data: [DONE]\n\n"
                        return
                    try:
                        chunk = _json.loads(payload)
                        delta = chunk["choices"][0].get("delta", {})
                        token = delta.get("content")
                        if token:
                            yield f"data: {_json.dumps({'token': token})}\n\n"
                    except (KeyError, _json.JSONDecodeError):
                        continue
    except httpx.RequestError:
        yield f"data: {_json.dumps({'error': 'Could not reach Groq. Please try again.'})}\n\n"


async def get_advisor_response(request: AdvisorChatRequest) -> AdvisorChatResponse:
    """Non-streaming fallback."""
    settings = get_settings()

    if not settings.groq_api_key:
        raise HTTPException(status_code=503, detail="Groq API key is not configured.")

    messages = _build_messages(request)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
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
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            raise HTTPException(status_code=429, detail="Rate limited. Please wait a moment and try again.")
        raise HTTPException(status_code=502, detail=f"Groq error: {exc.response.status_code}")
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Could not reach Groq. Please try again.")

    reply = (data["choices"][0]["message"].get("content") or "").strip()
    while reply.endswith("---"):
        reply = reply[:-3].rstrip()
    if not reply:
        raise HTTPException(status_code=502, detail="AI returned an empty response. Please try again.")

    suggestions = []
    for line in reply.split("\n"):
        line = line.strip()
        if line.startswith("- ") and len(line) < 100:
            suggestions.append(line[2:])
        if len(suggestions) >= 3:
            break

    return AdvisorChatResponse(reply=reply, suggestions=suggestions)
