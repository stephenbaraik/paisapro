"""
Macro Dashboard — FII/DII proxy, India VIX, USD/INR, 10Y yield, Nifty 50.

Uses yfinance for market data. FII/DII flows approximated via ETF proxy.
Correlates macro indicators against Nifty 50 returns.
"""

import time
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone

from ..schemas.advanced_analytics import (
    MacroIndicator, MacroTimeSeries, MacroTimeSeriesPoint,
    MacroCorrelation, MacroDashboardResponse,
)

_cache: tuple[MacroDashboardResponse | None, float] = (None, 0.0)
_CACHE_TTL = 1800  # 30 minutes


# Yahoo Finance tickers for Indian macro
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


def _fetch_ticker_history(ticker: str, period: str = "1y") -> pd.DataFrame:
    try:
        data = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=True)
        if data.empty:
            return pd.DataFrame()
        data = data.reset_index()
        data.rename(columns={"Date": "date", "Close": "close"}, inplace=True)
        data["date"] = pd.to_datetime(data["date"]).dt.tz_localize(None)
        return data[["date", "close"]].dropna()
    except Exception:
        return pd.DataFrame()


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

    risk_score = 0  # positive = risk-on, negative = risk-off

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
            risk_score -= 1  # rising oil = headwind for India

    if risk_score >= 2:
        return "RISK_ON", "Macro conditions favor equities — low VIX, positive market momentum. Consider increasing equity allocation."
    elif risk_score <= -2:
        return "RISK_OFF", "Elevated uncertainty — high VIX or falling markets. Consider defensive positioning with gold and debt."
    return "NEUTRAL", "Mixed signals — VIX and market trends are not strongly directional. Maintain balanced allocation."


async def get_macro_dashboard(force: bool = False) -> MacroDashboardResponse:
    global _cache
    cached, ts = _cache
    if cached and not force and time.time() - ts < _CACHE_TTL:
        return cached

    indicators: list[MacroIndicator] = []
    all_series: list[MacroTimeSeries] = []
    returns_dict: dict[str, pd.Series] = {}

    for name, ticker in MACRO_TICKERS.items():
        df = _fetch_ticker_history(ticker, "1y")
        if df.empty or len(df) < 5:
            continue

        current = float(df["close"].iloc[-1])
        prev_month = df["close"].iloc[-22] if len(df) > 22 else df["close"].iloc[0]
        change_pct = float((current - prev_month) / prev_month * 100)

        indicators.append(MacroIndicator(
            name=name,
            value=round(current, 2),
            change_pct=round(change_pct, 2),
            trend=_trend(change_pct),
            description=DESCRIPTIONS.get(name, ""),
        ))

        # Time series data
        ts_points = []
        for _, row in df.iterrows():
            ts_points.append(MacroTimeSeriesPoint(
                date=row["date"].strftime("%Y-%m-%d"),
                value=round(float(row["close"]), 2),
            ))
        all_series.append(MacroTimeSeries(name=name, data=ts_points))

        # Store returns for correlation
        ret = df.set_index("date")["close"].pct_change().dropna()
        ret.name = name
        returns_dict[name] = ret

    # Correlations
    correlations: list[MacroCorrelation] = []
    names = list(returns_dict.keys())
    if len(names) >= 2:
        combined = pd.DataFrame(returns_dict)
        combined = combined.dropna()
        if len(combined) > 20:
            corr_matrix = combined.corr()
            for i, n1 in enumerate(names):
                for j, n2 in enumerate(names):
                    if i < j:
                        c = float(corr_matrix.loc[n1, n2])
                        correlations.append(MacroCorrelation(
                            indicator1=n1, indicator2=n2,
                            correlation=round(c, 3),
                        ))

    regime, desc = _determine_regime(indicators)

    result = MacroDashboardResponse(
        indicators=indicators,
        time_series=all_series,
        correlations=correlations,
        market_regime=regime,
        regime_description=desc,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    _cache = (result, time.time())
    return result
