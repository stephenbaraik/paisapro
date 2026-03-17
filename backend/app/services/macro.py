"""
Macro Dashboard — India VIX, USD/INR, Nifty 50, Gold, Crude Oil, Bank Nifty.

Data pipeline:
  1. yfinance → Supabase macro_prices table  (ingest, runs locally or on schedule)
  2. Supabase → API response                 (serve, works on HF Spaces)
  3. yfinance direct as fallback             (if Supabase is empty)
"""

import asyncio
import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

from ..core.cache import cache
from ..data.macro_repository import get_macro_prices, save_macro_prices
from ..schemas.advanced_analytics import (
    MacroIndicator, MacroTimeSeries, MacroTimeSeriesPoint,
    MacroCorrelation, MacroDashboardResponse,
)

logger = logging.getLogger(__name__)

_CACHE_KEY = "macro:dashboard"
_CACHE_TTL = 1800   # 30 min

# ── Ticker config ─────────────────────────────────────────────────────────────

MACRO_TICKERS = {
    "India VIX":  "^INDIAVIX",
    "USD/INR":    "INR=X",
    "Nifty 50":   "^NSEI",
    "Gold (INR)": "GC=F",
    "Crude Oil":  "CL=F",
    "Bank Nifty": "^NSEBANK",
}

DESCRIPTIONS = {
    "India VIX":  "Volatility index — fear gauge for Indian markets",
    "USD/INR":    "Dollar-Rupee exchange rate — rupee strength indicator",
    "Nifty 50":   "Benchmark Indian equity index — 50 large caps",
    "Gold (INR)": "Gold futures — safe-haven proxy (USD, converted mentally)",
    "Crude Oil":  "WTI crude oil — import cost driver for India",
    "Bank Nifty": "Banking sector index — financial sector health",
}


# ── yfinance fetch ────────────────────────────────────────────────────────────

def _batch_download(tickers: list[str], period: str = "1y") -> dict[str, pd.DataFrame]:
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


# ── Ingest pipeline ───────────────────────────────────────────────────────────

def refresh_macro_data() -> int:
    """
    Fetch macro data from yfinance and save to Supabase.
    Returns number of tickers successfully ingested.
    """
    tickers = list(MACRO_TICKERS.values())
    ticker_dfs = _batch_download(tickers, "1y")

    success = 0
    for name, ticker in MACRO_TICKERS.items():
        df = ticker_dfs.get(ticker)
        if df is None or len(df) < 5:
            logger.warning("Macro refresh: no data for %s (%s)", name, ticker)
            continue
        save_macro_prices(ticker, df)
        success += 1

    # Invalidate cache so next request gets fresh data
    cache.invalidate(_CACHE_KEY)

    logger.info("Macro refresh complete: %d/%d tickers ingested.", success, len(MACRO_TICKERS))
    return success


# ── Response builders ─────────────────────────────────────────────────────────

def _trend(change_pct: float) -> str:
    if change_pct > 0.5:
        return "UP"
    elif change_pct < -0.5:
        return "DOWN"
    return "FLAT"


def _determine_regime(indicators: list[MacroIndicator]) -> tuple[str, str]:
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

    if oil and oil.change_pct > 5:
        risk_score -= 1

    if risk_score >= 2:
        return "RISK_ON", "Macro conditions favor equities — low VIX, positive market momentum. Consider increasing equity allocation."
    elif risk_score <= -2:
        return "RISK_OFF", "Elevated uncertainty — high VIX or falling markets. Consider defensive positioning with gold and debt."
    return "NEUTRAL", "Mixed signals — VIX and market trends are not strongly directional. Maintain balanced allocation."


def _build_response(ticker_dfs: dict[str, pd.DataFrame]) -> MacroDashboardResponse:
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
            MacroTimeSeriesPoint(date=row["date"].strftime("%Y-%m-%d"), value=round(float(row["close"]), 2))
            for _, row in df.iterrows()
        ]
        all_series.append(MacroTimeSeries(name=name, data=ts_points))

        ret = df.set_index("date")["close"].pct_change().dropna()
        ret.name = name
        returns_dict[name] = ret

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


# ── Main API function ─────────────────────────────────────────────────────────

async def get_macro_dashboard(force: bool = False) -> MacroDashboardResponse:
    if not force:
        cached = cache.get(_CACHE_KEY)
        if cached is not None:
            return cached

    tickers = list(MACRO_TICKERS.values())
    ticker_dfs: dict[str, pd.DataFrame] = {}

    # 1. Try Supabase first (works on HF Spaces where yfinance is blocked)
    supabase_dfs = await asyncio.to_thread(
        lambda: {t: get_macro_prices(t) for t in tickers}
    )
    for ticker, df in supabase_dfs.items():
        if not df.empty and len(df) >= 5:
            ticker_dfs[ticker] = df

    if len(ticker_dfs) >= 3:
        logger.info("Macro: serving %d/%d tickers from Supabase", len(ticker_dfs), len(tickers))
    else:
        # 2. Fallback: yfinance (works locally, may fail on cloud)
        logger.info("Macro: Supabase has %d tickers, trying yfinance fallback…", len(ticker_dfs))
        yf_dfs = await asyncio.to_thread(_batch_download, tickers, "1y")
        for ticker, df in yf_dfs.items():
            if ticker not in ticker_dfs:
                ticker_dfs[ticker] = df
        if yf_dfs:
            await asyncio.to_thread(
                lambda: [save_macro_prices(t, df) for t, df in yf_dfs.items()]
            )

    result = _build_response(ticker_dfs)
    cache.set(_CACHE_KEY, result, _CACHE_TTL)
    return result
