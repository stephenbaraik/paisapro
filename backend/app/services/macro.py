"""
Macro Dashboard — India VIX, USD/INR, Nifty 50, Gold, Crude Oil, Bank Nifty.

Data pipeline:
  1. yfinance → Supabase `macro_prices` table  (ingest, runs locally or on schedule)
  2. Supabase → API response                   (serve, runs on HF Spaces)
  3. yfinance direct as fallback                (if Supabase is empty)

Scheduler refreshes daily at 6 PM IST alongside stock prices.
"""

import asyncio
import logging
import time
import numpy as np
import pandas as pd
import httpx
import yfinance as yf
from datetime import datetime, timezone

from ..core.config import get_settings
from ..schemas.advanced_analytics import (
    MacroIndicator, MacroTimeSeries, MacroTimeSeriesPoint,
    MacroCorrelation, MacroDashboardResponse,
)

logger = logging.getLogger(__name__)

_cache: tuple[MacroDashboardResponse | None, float] = (None, 0.0)
_CACHE_TTL = 1800  # 30 minutes


# ── Ticker config ────────────────────────────────────────────────────────────

MACRO_TICKERS = {
    "India VIX":   "^INDIAVIX",
    "USD/INR":     "INR=X",
    "Nifty 50":    "^NSEI",
    "Gold (INR)":  "GC=F",
    "Crude Oil":   "CL=F",
    "Bank Nifty":  "^NSEBANK",
}

DESCRIPTIONS = {
    "India VIX":   "Volatility index — fear gauge for Indian markets",
    "USD/INR":     "Dollar-Rupee exchange rate — rupee strength indicator",
    "Nifty 50":    "Benchmark Indian equity index — 50 large caps",
    "Gold (INR)":  "Gold futures — safe-haven proxy (USD, converted mentally)",
    "Crude Oil":   "WTI crude oil — import cost driver for India",
    "Bank Nifty":  "Banking sector index — financial sector health",
}


# ── Supabase helpers ─────────────────────────────────────────────────────────

def _sb_headers() -> dict:
    settings = get_settings()
    return {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }


def _sb_url(table: str) -> str:
    return f"{get_settings().supabase_url}/rest/v1/{table}"


def _save_macro_to_supabase(ticker: str, df: pd.DataFrame) -> None:
    """Upsert macro price rows to Supabase macro_prices table."""
    rows = []
    for _, row in df.iterrows():
        rows.append({
            "ticker": ticker,
            "date": str(row["date"].date()),
            "close": round(float(row["close"]), 4),
        })

    for i in range(0, len(rows), 500):
        batch = rows[i:i + 500]
        try:
            resp = httpx.post(
                _sb_url("macro_prices") + "?on_conflict=ticker,date",
                headers=_sb_headers(), json=batch, timeout=30,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Supabase macro write failed for %s batch %d: %s", ticker, i, exc)

    logger.info("Saved %d macro rows for %s to Supabase", len(rows), ticker)


def _load_macro_from_supabase(ticker: str) -> pd.DataFrame:
    """Load macro price history from Supabase (last 400 rows ≈ 1.5 years)."""
    try:
        resp = httpx.get(
            _sb_url("macro_prices"),
            headers=_sb_headers(),
            params={
                "ticker": f"eq.{ticker}",
                "select": "date,close",
                "order": "date.desc",
                "limit": "400",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("Supabase macro read failed for %s: %s", ticker, exc)
        return pd.DataFrame()

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)
    return df


# ── yfinance fetch ───────────────────────────────────────────────────────────

def _batch_download(tickers: list[str], period: str = "1y") -> dict[str, pd.DataFrame]:
    """Batch-download all tickers via yf.download."""
    result: dict[str, pd.DataFrame] = {}
    try:
        raw = yf.download(
            tickers, period=period, interval="1d",
            auto_adjust=True, threads=True, progress=False,
        )
        if raw.empty:
            logger.warning("Macro: yf.download returned empty for all tickers")
            return result

        for ticker in tickers:
            try:
                if len(tickers) == 1:
                    df = raw[["Close"]].copy()
                else:
                    df = raw["Close"][[ticker]].copy()
                df = df.dropna().reset_index()
                df.columns = ["date", "close"]
                df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
                if len(df) >= 5:
                    result[ticker] = df
            except Exception as e:
                logger.warning("Macro: failed to extract %s: %s", ticker, e)
    except Exception as e:
        logger.error("Macro: yf.download failed: %s", e)
    return result


# ── Ingest pipeline (called by scheduler + manually) ────────────────────────

def refresh_macro_data() -> int:
    """
    Fetch macro data from yfinance and save to Supabase.
    Returns number of tickers successfully ingested.
    Call this locally or from the scheduler — NOT from HF Spaces.
    """
    tickers = list(MACRO_TICKERS.values())
    ticker_dfs = _batch_download(tickers, "1y")

    success = 0
    for name, ticker in MACRO_TICKERS.items():
        df = ticker_dfs.get(ticker)
        if df is None or len(df) < 5:
            logger.warning("Macro refresh: no data for %s (%s)", name, ticker)
            continue
        _save_macro_to_supabase(ticker, df)
        success += 1

    logger.info("Macro refresh complete: %d/%d tickers ingested.", success, len(MACRO_TICKERS))
    return success


# ── Helpers ──────────────────────────────────────────────────────────────────

def _trend(change_pct: float) -> str:
    if change_pct > 0.5:
        return "UP"
    elif change_pct < -0.5:
        return "DOWN"
    return "FLAT"


def _determine_regime(indicators: list[MacroIndicator]) -> tuple[str, str]:
    """Determine market regime from macro indicators."""
    vix_val = next((i for i in indicators if i.name == "India VIX"), None)
    nifty = next((i for i in indicators if i.name == "Nifty 50"), None)
    oil = next((i for i in indicators if i.name == "Crude Oil"), None)

    risk_score = 0

    if vix_val:
        if vix_val.value < 14:
            risk_score += 2
        elif vix_val.value < 18:
            risk_score += 1
        elif vix_val.value > 22:
            risk_score -= 2
        else:
            risk_score -= 1

    if nifty:
        if nifty.change_pct > 2:
            risk_score += 2
        elif nifty.change_pct > 0:
            risk_score += 1
        elif nifty.change_pct < -2:
            risk_score -= 2
        else:
            risk_score -= 1

    if oil:
        if oil.change_pct > 5:
            risk_score -= 1

    if risk_score >= 2:
        return "RISK_ON", "Macro conditions favor equities — low VIX, positive market momentum. Consider increasing equity allocation."
    elif risk_score <= -2:
        return "RISK_OFF", "Elevated uncertainty — high VIX or falling markets. Consider defensive positioning with gold and debt."
    return "NEUTRAL", "Mixed signals — VIX and market trends are not strongly directional. Maintain balanced allocation."


# ── Build response from DataFrames ──────────────────────────────────────────

def _build_response(ticker_dfs: dict[str, pd.DataFrame]) -> MacroDashboardResponse:
    """Build the API response from a dict of ticker → DataFrame."""
    indicators: list[MacroIndicator] = []
    all_series: list[MacroTimeSeries] = []
    returns_dict: dict[str, pd.Series] = {}

    for name, ticker in MACRO_TICKERS.items():
        df = ticker_dfs.get(ticker)
        if df is None or len(df) < 5:
            continue

        current = float(df["close"].iloc[-1])
        prev_month = float(df["close"].iloc[-22] if len(df) > 22 else df["close"].iloc[0])
        change_pct = (current - prev_month) / prev_month * 100

        indicators.append(MacroIndicator(
            name=name,
            value=round(current, 2),
            change_pct=round(change_pct, 2),
            trend=_trend(change_pct),
            description=DESCRIPTIONS.get(name, ""),
        ))

        ts_points = [
            MacroTimeSeriesPoint(
                date=row["date"].strftime("%Y-%m-%d"),
                value=round(float(row["close"]), 2),
            )
            for _, row in df.iterrows()
        ]
        all_series.append(MacroTimeSeries(name=name, data=ts_points))

        ret = df.set_index("date")["close"].pct_change().dropna()
        ret.name = name
        returns_dict[name] = ret

    # Correlations
    correlations: list[MacroCorrelation] = []
    corr_names = list(returns_dict.keys())
    if len(corr_names) >= 2:
        combined = pd.DataFrame(returns_dict).dropna()
        if len(combined) > 20:
            corr_matrix = combined.corr()
            for i, n1 in enumerate(corr_names):
                for j, n2 in enumerate(corr_names):
                    if i < j:
                        c = float(corr_matrix.loc[n1, n2])
                        correlations.append(MacroCorrelation(
                            indicator1=n1, indicator2=n2, correlation=round(c, 3),
                        ))

    regime, desc = _determine_regime(indicators)

    return MacroDashboardResponse(
        indicators=indicators,
        time_series=all_series,
        correlations=correlations,
        market_regime=regime,
        regime_description=desc,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


# ── Main API function ───────────────────────────────────────────────────────

async def get_macro_dashboard(force: bool = False) -> MacroDashboardResponse:
    global _cache
    cached, ts = _cache
    if cached and not force and time.time() - ts < _CACHE_TTL:
        return cached

    # 1. Try Supabase first (works on HF Spaces where yfinance is blocked)
    ticker_dfs: dict[str, pd.DataFrame] = {}
    tickers = list(MACRO_TICKERS.values())

    supabase_dfs = await asyncio.to_thread(
        lambda: {t: _load_macro_from_supabase(t) for t in tickers}
    )
    for ticker, df in supabase_dfs.items():
        if not df.empty and len(df) >= 5:
            ticker_dfs[ticker] = df

    # 2. If Supabase has data for most tickers, use it
    if len(ticker_dfs) >= 3:
        logger.info("Macro: serving %d/%d tickers from Supabase", len(ticker_dfs), len(tickers))
    else:
        # 3. Fallback: try yfinance directly (works locally, may fail on cloud)
        logger.info("Macro: Supabase has %d tickers, trying yfinance fallback…", len(ticker_dfs))
        yf_dfs = await asyncio.to_thread(_batch_download, tickers, "1y")
        for ticker, df in yf_dfs.items():
            if ticker not in ticker_dfs:
                ticker_dfs[ticker] = df
            # Save to Supabase for next time
        if yf_dfs:
            await asyncio.to_thread(
                lambda: [_save_macro_to_supabase(t, df) for t, df in yf_dfs.items()]
            )

    result = _build_response(ticker_dfs)
    _cache = (result, time.time())
    return result
