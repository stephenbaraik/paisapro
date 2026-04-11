"""
AI-powered portfolio builder — uses OpenRouter (no daily token cap).

Token-budget strategy:
  - Snapshot capped at top 20 BUY + top 5 HOLD stocks
  - LLM response cached 10 min per (amount_bucket, risk_profile)
"""

import json
import logging
import time
import httpx
from ..core.config import get_settings

logger = logging.getLogger(__name__)

OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct",
    "meta-llama/llama-3.1-8b-instruct",
]

# Response cache: key → (result_dict, timestamp)
_build_cache: dict[str, tuple[dict, float]] = {}
CACHE_TTL = 600  # 10 minutes


def _cache_key(investment_amount: float, risk_profile: str) -> str:
    bucket = round(investment_amount / 50_000) * 50_000
    return f"{bucket}:{risk_profile.lower()}"


def _get_cached_build(key: str) -> dict | None:
    if key in _build_cache:
        result, ts = _build_cache[key]
        if time.time() - ts < CACHE_TTL:
            return result
        del _build_cache[key]
    return None


def _set_cached_build(key: str, result: dict) -> None:
    _build_cache[key] = (result, time.time())


def _market_snapshot() -> str:
    """
    Compact snapshot for the LLM.
    Primary: analytics cache (BUY/HOLD signals).
    Fallback: live prices from Supabase when cache is cold (e.g. after Space restart).
    """
    # ── Primary: analytics cache ──────────────────────────────────────────────
    try:
        from .analytics import _report_cache

        cached, _ = _report_cache
        if cached is not None:
            lines = []

            buy_stocks = sorted(
                [a for a in cached.stock_analyses if a.technical_signals.composite_signal.value == "BUY"],
                key=lambda a: a.technical_signals.confidence_score, reverse=True,
            )[:20]

            hold_stocks = sorted(
                [a for a in cached.stock_analyses if a.technical_signals.composite_signal.value == "HOLD"],
                key=lambda a: a.technical_signals.confidence_score, reverse=True,
            )[:5]

            if buy_stocks:
                lines.append("BUY signals:")
                for a in buy_stocks:
                    sym = a.symbol.replace(".NS", "")
                    price = a.technical_signals.current_price
                    lines.append(
                        f"  {sym} ({a.company_name}) sector={a.sector} "
                        f"price={price:.0f} conf={a.technical_signals.confidence_score:.0f}%"
                    )

            if hold_stocks:
                lines.append("HOLD signals (high Sharpe):")
                for a in hold_stocks:
                    sym = a.symbol.replace(".NS", "")
                    price = a.technical_signals.current_price
                    lines.append(
                        f"  {sym} ({a.company_name}) sector={a.sector} "
                        f"price={price:.0f} sharpe={a.risk_metrics.sharpe_ratio:.2f}"
                    )

            if lines:
                return "\n".join(lines)
    except Exception as e:
        logger.warning("Analytics cache snapshot failed: %s", e)

    # ── Fallback: live prices from Supabase ───────────────────────────────────
    try:
        from .analytics import get_stock_universe, get_stock_name, get_stock_sector, _get_cached_df

        symbols_ns = get_stock_universe()
        if not symbols_ns:
            return ""

        lines = ["Available stocks (live prices):"]
        count = 0
        for sym_ns in symbols_ns:
            if count >= 40:
                break
            sym = sym_ns.replace(".NS", "")
            try:
                df = _get_cached_df(sym_ns, "1y")
                if df is None or len(df) < 2:
                    continue
                price = float(df["close"].iloc[-1])
                if price <= 0:
                    continue
                name = get_stock_name(sym_ns) or sym
                sector = get_stock_sector(sym_ns) or "Unknown"
                lines.append(f"  {sym} ({name}) sector={sector} price={price:.0f}")
                count += 1
            except Exception:
                continue

        if count > 0:
            logger.info("Portfolio snapshot: used Supabase fallback (%d stocks)", count)
            return "\n".join(lines)
    except Exception as e:
        logger.warning("Supabase fallback snapshot failed: %s", e)

    return ""


SYSTEM_PROMPT = """You are an expert Indian equity portfolio constructor.
Given an investment amount and risk profile, pick stocks from the provided list and allocate quantities.

Rules:
- Only use symbols from the list. Do not invent symbols.
- Conservative: 8-12 stocks, diversify broadly, prefer stable sectors.
- Moderate: 7-10 stocks, at least 4 sectors, balanced growth/value.
- Aggressive: 5-8 stocks, at least 3 sectors, high-confidence BUY picks.
- No single stock > 20% of total investment.
- quantity = floor(allocation / current_price).
- Total allocations must be 90-98% of investment amount.

Respond with ONLY valid JSON, no markdown:
{"picks":[{"symbol":"X","company_name":"Y","sector":"Z","current_price":100.0,"quantity":10,"allocation":1000.0,"weight_pct":10.0,"reason":"..."}],"strategy_summary":"...","risk_notes":"...","total_allocated":95000,"cash_remaining":5000}"""


async def ai_build_portfolio(
    investment_amount: float,
    risk_profile: str = "moderate",
) -> dict:
    """Build a portfolio using OpenRouter LLM + analytics cache data."""
    settings = get_settings()

    # Serve from cache if available
    ckey = _cache_key(investment_amount, risk_profile)
    cached_result = _get_cached_build(ckey)
    if cached_result:
        logger.info("Portfolio build served from cache")
        return cached_result

    snapshot = _market_snapshot()
    if not snapshot:
        raise RuntimeError(
            "Market analysis data is not yet loaded. "
            "Please wait a moment and try again."
        )

    user_prompt = (
        f"Investment: ₹{investment_amount:,.0f} | Risk: {risk_profile.upper()}\n\n"
        f"Available stocks:\n{snapshot}\n\n"
        "Return ONLY the JSON."
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://stephenbaraik-paisapro.hf.space",
        "X-Title": "PaisaPro AI Advisor",
    }

    # Build ordered provider list: OpenRouter first (no daily cap), Groq as fallback
    providers: list[tuple[str, dict, str]] = []  # (url, headers, model)

    if settings.openrouter_api_key:
        or_headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://stephenbaraik-paisapro.hf.space",
            "X-Title": "PaisaPro AI Advisor",
        }
        for model in OPENROUTER_MODELS:
            providers.append((settings.openrouter_url, or_headers, model))

    # Groq fallback — llama-3.1-8b-instant has a separate quota from 70B
    groq_headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json",
    }
    providers.append(("https://api.groq.com/openai/v1/chat/completions", groq_headers, "llama-3.1-8b-instant"))

    data = None
    for url, req_headers, model in providers:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    url,
                    headers=req_headers,
                    json={"model": model, "messages": messages, "max_tokens": 2048, "temperature": 0.2},
                )
                resp.raise_for_status()
                data = resp.json()
                logger.info("Portfolio built via %s model: %s", "OpenRouter" if "openrouter" in url else "Groq", model)
                break
        except httpx.HTTPStatusError as exc:
            logger.warning("%s %s HTTP %d — trying next", url, model, exc.response.status_code)
            continue
        except httpx.RequestError as exc:
            logger.warning("Request error %s: %s — trying next", model, exc)
            continue

    if data is None:
        raise RuntimeError("All AI providers failed. Please try again in a moment.")

    raw = (data["choices"][0]["message"].get("content") or "").strip()

    # Strip markdown fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3].rstrip()
    if raw.startswith("json"):
        raw = raw[4:].lstrip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                result = json.loads(raw[start:end])
            except json.JSONDecodeError:
                raise RuntimeError("AI returned invalid JSON. Please try again.")
        else:
            raise RuntimeError("AI returned invalid response format. Please try again.")

    from .portfolio import _get_latest_price, _get_stock_meta

    validated_picks = []
    for pick in result.get("picks", []):
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
            "weight_pct": 0,
            "reason": pick.get("reason", ""),
        })

    if not validated_picks:
        raise RuntimeError("AI could not allocate any stocks. Please try again.")

    # Scale down if over budget
    total_allocated = sum(p["allocation"] for p in validated_picks)
    if total_allocated > investment_amount:
        scale = investment_amount * 0.97 / total_allocated
        for p in validated_picks:
            p["quantity"] = max(1, int(p["quantity"] * scale))
            p["allocation"] = round(p["current_price"] * p["quantity"], 2)
        total_allocated = sum(p["allocation"] for p in validated_picks)

    # Cap single stock at 25%
    for p in validated_picks:
        max_alloc = investment_amount * 0.25
        if p["allocation"] > max_alloc and p["current_price"] > 0:
            p["quantity"] = max(1, int(max_alloc / p["current_price"]))
            p["allocation"] = round(p["current_price"] * p["quantity"], 2)
    total_allocated = sum(p["allocation"] for p in validated_picks)

    for p in validated_picks:
        p["weight_pct"] = round(p["allocation"] / investment_amount * 100, 1) if investment_amount > 0 else 0

    final = {
        "picks": validated_picks,
        "strategy_summary": result.get("strategy_summary", ""),
        "risk_notes": result.get("risk_notes", ""),
        "total_allocated": round(total_allocated, 2),
        "cash_remaining": round(investment_amount - total_allocated, 2),
        "investment_amount": investment_amount,
        "risk_profile": risk_profile,
    }

    _set_cached_build(ckey, final)
    return final
