"""
AI-powered portfolio builder - OpenRouter primary, Groq fallback.
"""
import json, logging, time, httpx
from ..core.config import get_settings

logger = logging.getLogger(__name__)

OPENROUTER_MODELS = ["meta-llama/llama-3.3-70b-instruct", "meta-llama/llama-3.1-8b-instruct"]
_build_cache: dict = {}
CACHE_TTL = 600

def _cache_key(amt, risk): return f"{round(amt/50000)*50000}:{risk.lower()}"

def _get_cached_build(key):
    if key in _build_cache:
        r, ts = _build_cache[key]
        if time.time()-ts < CACHE_TTL: return r
        del _build_cache[key]

def _set_cached_build(key, r): _build_cache[key] = (r, time.time())

def _market_snapshot():
    try:
        from .analytics import get_cached_report
        cached = get_cached_report()
        if cached is not None:
            lines = []
            buys = sorted([a for a in cached.stock_analyses if a.technical_signals.composite_signal.value=="BUY"], key=lambda a: a.technical_signals.confidence_score, reverse=True)[:20]
            holds = sorted([a for a in cached.stock_analyses if a.technical_signals.composite_signal.value=="HOLD"], key=lambda a: a.technical_signals.confidence_score, reverse=True)[:5]
            if buys:
                lines.append("BUY signals:")
                for a in buys:
                    sym=a.symbol.replace(".NS",""); lines.append(f"  {sym} ({a.company_name}) sector={a.sector} price={a.technical_signals.current_price:.0f} conf={a.technical_signals.confidence_score:.0f}%")
            if holds:
                lines.append("HOLD signals:")
                for a in holds:
                    sym=a.symbol.replace(".NS",""); lines.append(f"  {sym} ({a.company_name}) sector={a.sector} price={a.technical_signals.current_price:.0f}")
            if lines: return "
".join(lines)
    except Exception as e: logger.warning("Analytics cache failed: %s", e)
    try:
        from .analytics import get_stock_universe, get_stock_name, get_stock_sector, _get_cached_df
        syms = get_stock_universe()
        lines = ["Available stocks:"]; count=0
        for s in syms:
            if count>=40: break
            try:
                df=_get_cached_df(s,"1y")
                if df is None or len(df)<2: continue
                price=float(df["close"].iloc[-1])
                if price<=0: continue
                lines.append(f"  {s.replace(chr(46)+'NS','')} ({get_stock_name(s)}) sector={get_stock_sector(s)} price={price:.0f}"); count+=1
            except: continue
        if count>0: return "
".join(lines)
    except Exception as e: logger.warning("Supabase fallback failed: %s", e)
    return ""

SYSTEM_PROMPT = """You are an expert Indian equity portfolio constructor.
Pick stocks from the list below and allocate quantities for the given investment amount and risk profile.
Rules: only use symbols from the list; conservative=8-12 stocks; moderate=7-10 stocks 4+ sectors; aggressive=5-8 stocks 3+ sectors; no single stock >20%; quantity=floor(allocation/price); total=90-98% of budget.
Respond ONLY with valid JSON no markdown:
{"picks":[{"symbol":"X","company_name":"Y","sector":"Z","current_price":100.0,"quantity":10,"allocation":1000.0,"weight_pct":10.0,"reason":"..."}],"strategy_summary":"...","risk_notes":"...","total_allocated":95000,"cash_remaining":5000}"""

async def ai_build_portfolio(investment_amount: float, risk_profile: str="moderate") -> dict:
    settings = get_settings()
    ckey = _cache_key(investment_amount, risk_profile)
    hit = _get_cached_build(ckey)
    if hit: return hit
    snap = _market_snapshot()
    if not snap: raise RuntimeError("Market data not yet loaded. Please try again in a moment.")
    messages = [{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":f"Investment: Rs{investment_amount:,.0f} | Risk: {risk_profile.upper()}

{snap}

Return ONLY the JSON."}]
    providers = []
    if settings.openrouter_api_key:
        h = {"Authorization":f"Bearer {settings.openrouter_api_key}","Content-Type":"application/json","HTTP-Referer":"https://stephenbaraik-paisapro.hf.space","X-Title":"PaisaPro"}
        for m in OPENROUTER_MODELS: providers.append((settings.openrouter_url, h, m))
    if settings.groq_api_key:
        h = {"Authorization":f"Bearer {settings.groq_api_key}","Content-Type":"application/json"}
        providers.append((settings.groq_url, h, "llama-3.1-8b-instant"))
    if not providers: raise RuntimeError("No AI provider configured.")
    data = None
    for url, hdrs, model in providers:
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(url, headers=hdrs, json={"model":model,"messages":messages,"max_tokens":2048,"temperature":0.2})
                r.raise_for_status(); data=r.json()
                logger.info("Portfolio via %s", model); break
        except Exception as e: logger.warning("Provider %s failed: %s — trying next", model, e)
    if data is None: raise RuntimeError("All AI providers failed. Please try again.")
    raw = (data["choices"][0]["message"].get("content") or "").strip()
    if raw.startswith("```"): raw = raw.split("
",1)[1] if "
" in raw else raw[3:]
    if raw.endswith("```"): raw = raw[:-3].rstrip()
    if raw.startswith("json"): raw = raw[4:].lstrip()
    try: result = json.loads(raw)
    except:
        s,e = raw.find("{"), raw.rfind("}")+1
        if s>=0 and e>s:
            try: result=json.loads(raw[s:e])
            except: raise RuntimeError("AI returned invalid JSON.")
        else: raise RuntimeError("AI returned invalid response.")
    from .portfolio import _get_latest_price, _get_stock_meta
    picks=[]
    for p in result.get("picks",[]):
        sym=p.get("symbol","").upper().replace(".NS","")
        if not sym: continue
        price,chg=_get_latest_price(sym); name,sec=_get_stock_meta(sym)
        if price<=0: price=p.get("current_price",0)
        qty=int(p.get("quantity",0))
        if qty<=0 and price>0: qty=int(p.get("allocation",0)/price)
        if qty<=0 or price<=0: continue
        picks.append({"symbol":sym,"company_name":name or p.get("company_name",""),"sector":sec or p.get("sector",""),"current_price":round(price,2),"daily_change_pct":chg,"quantity":qty,"allocation":round(price*qty,2),"weight_pct":0,"reason":p.get("reason","")})
    if not picks: raise RuntimeError("AI could not allocate any stocks. Please try again.")
    total=sum(p["allocation"] for p in picks)
    if total>investment_amount:
        scale=investment_amount*0.97/total
        for p in picks: p["quantity"]=max(1,int(p["quantity"]*scale)); p["allocation"]=round(p["current_price"]*p["quantity"],2)
        total=sum(p["allocation"] for p in picks)
    for p in picks:
        ma=investment_amount*0.25
        if p["allocation"]>ma and p["current_price"]>0: p["quantity"]=max(1,int(ma/p["current_price"])); p["allocation"]=round(p["current_price"]*p["quantity"],2)
    total=sum(p["allocation"] for p in picks)
    for p in picks: p["weight_pct"]=round(p["allocation"]/investment_amount*100,1) if investment_amount>0 else 0
    final={"picks":picks,"strategy_summary":result.get("strategy_summary",""),"risk_notes":result.get("risk_notes",""),"total_allocated":round(total,2),"cash_remaining":round(investment_amount-total,2),"investment_amount":investment_amount,"risk_profile":risk_profile}
    _set_cached_build(ckey, final)
    return final
