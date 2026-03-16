"""
Volatility Forecasting — GARCH(1,1) model for 30-day vol prediction.

Provides: realized vol history, GARCH forecast, volatility cones,
vol-regime classification, and low-vol entry signals.
"""

import time
import warnings
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from .analytics import (
    get_stock_universe, _get_cached_df, get_stock_name, get_stock_sector,
)
from ..schemas.advanced_analytics import (
    VolatilityPoint, VolatilityConePoint, VolatilityForecastResponse, VolSymbol,
)

warnings.filterwarnings("ignore", category=FutureWarning)

_cache: dict[str, tuple[VolatilityForecastResponse, float]] = {}
_CACHE_TTL = 3600


def _annualize(daily_vol: float) -> float:
    return daily_vol * np.sqrt(252) * 100


def _vol_regime(vol_percentile: float) -> str:
    if vol_percentile < 20:
        return "LOW"
    elif vol_percentile < 60:
        return "NORMAL"
    elif vol_percentile < 85:
        return "HIGH"
    return "EXTREME"


def _entry_signal(regime: str) -> str:
    if regime == "LOW":
        return "LOW_VOL_ENTRY"
    elif regime in ("HIGH", "EXTREME"):
        return "HIGH_VOL_CAUTION"
    return "NEUTRAL"


async def get_volatility_forecast(symbol: str) -> VolatilityForecastResponse:
    cache_key = symbol.upper()
    if cache_key in _cache:
        cached, ts = _cache[cache_key]
        if time.time() - ts < _CACHE_TTL:
            return cached

    from arch import arch_model

    df = _get_cached_df(symbol, "2y")
    if df is None or len(df) < 200:
        raise ValueError(f"Insufficient data for {symbol}")

    close = df["close"].values
    returns = pd.Series(close).pct_change().dropna().values * 100  # percentage returns
    dates = df["date"].values[1:]  # align with returns

    if len(returns) < 200:
        raise ValueError(f"Insufficient returns data for {symbol}")

    # --- GARCH(1,1) ---
    try:
        model = arch_model(returns, vol="Garch", p=1, q=1, mean="Constant", dist="normal")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = model.fit(disp="off", show_warning=False)

        # Forecast 30 days
        fcast = res.forecast(horizon=30, reindex=False)
        forecast_var = fcast.variance.values[-1]   # 30-day variance array
        forecast_vol_daily = np.sqrt(forecast_var)  # daily vol (% terms)

        omega = float(res.params.get("omega", 0))
        alpha_1 = float(res.params.get("alpha[1]", 0))
        beta_1 = float(res.params.get("beta[1]", 0))
        persistence = alpha_1 + beta_1
        garch_params = {
            "omega": round(omega, 6),
            "alpha": round(alpha_1, 4),
            "beta": round(beta_1, 4),
            "persistence": round(persistence, 4),
        }

        # Annualized GARCH forecast (average over 30 days)
        garch_30d_vol = float(np.mean(forecast_vol_daily)) * np.sqrt(252)
    except Exception:
        # Fallback to simple EWMA vol
        ewma_var = pd.Series(returns).ewm(span=30).var().iloc[-1]
        garch_30d_vol = float(np.sqrt(ewma_var) * np.sqrt(252))
        forecast_vol_daily = np.full(30, np.sqrt(ewma_var))
        garch_params = {"omega": 0, "alpha": 0.06, "beta": 0.94, "persistence": 1.0}

    # --- Realized vol history (30-day rolling, last 6 months) ---
    ret_series = pd.Series(returns, index=pd.to_datetime(dates[:len(returns)]))
    rolling_vol = ret_series.rolling(30).std() * np.sqrt(252)
    hist_6m = rolling_vol.tail(126).dropna()

    history: list[VolatilityPoint] = []
    for dt, rv in hist_6m.items():
        history.append(VolatilityPoint(
            date=pd.Timestamp(dt).strftime("%Y-%m-%d"),
            realized_vol=round(float(rv), 2),
        ))

    # Add 30-day forecast
    last_date = pd.Timestamp(dates[-1])
    for i in range(30):
        fdate = last_date + pd.Timedelta(days=i + 1)
        fv = float(forecast_vol_daily[i]) * np.sqrt(252) if i < len(forecast_vol_daily) else garch_30d_vol
        history.append(VolatilityPoint(
            date=fdate.strftime("%Y-%m-%d"),
            forecast_vol=round(fv, 2),
            lower=round(fv * 0.7, 2),
            upper=round(fv * 1.3, 2),
        ))

    # --- Current realized vol ---
    current_rv = float(rolling_vol.iloc[-1]) if not rolling_vol.empty else garch_30d_vol

    # --- Vol percentile (vs 1yr) ---
    vol_1y = rolling_vol.tail(252).dropna()
    if len(vol_1y) > 10:
        vol_pct = float((vol_1y < current_rv).sum() / len(vol_1y) * 100)
    else:
        vol_pct = 50.0

    regime = _vol_regime(vol_pct)
    entry = _entry_signal(regime)

    # --- Volatility Cone ---
    vol_cone: list[VolatilityConePoint] = []
    for horizon in [5, 10, 21, 63, 126, 252]:
        if len(returns) > horizon + 20:
            h_vols = []
            for start in range(0, len(returns) - horizon, max(1, horizon // 2)):
                chunk = returns[start:start + horizon]
                h_vols.append(float(np.std(chunk) * np.sqrt(252 / horizon)))
            h_vols_arr = np.array(h_vols)

            # Current vol at this horizon
            cur_h_vol = float(np.std(returns[-horizon:]) * np.sqrt(252 / horizon))

            vol_cone.append(VolatilityConePoint(
                horizon_days=horizon,
                current_vol=round(cur_h_vol, 2),
                percentile_10=round(float(np.percentile(h_vols_arr, 10)), 2),
                percentile_25=round(float(np.percentile(h_vols_arr, 25)), 2),
                percentile_50=round(float(np.percentile(h_vols_arr, 50)), 2),
                percentile_75=round(float(np.percentile(h_vols_arr, 75)), 2),
                percentile_90=round(float(np.percentile(h_vols_arr, 90)), 2),
            ))

    result = VolatilityForecastResponse(
        symbol=symbol,
        company_name=get_stock_name(symbol),
        sector=get_stock_sector(symbol),
        current_price=float(close[-1]),
        current_realized_vol=round(current_rv, 2),
        garch_forecast_vol=round(garch_30d_vol, 2),
        vol_regime=regime,
        entry_signal=entry,
        vol_percentile=round(vol_pct, 1),
        history=history,
        vol_cone=vol_cone,
        garch_params=garch_params,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    _cache[cache_key] = (result, time.time())
    return result


async def get_vol_symbols() -> list[VolSymbol]:
    universe = get_stock_universe()
    result = []
    for sym in sorted(universe):
        name = get_stock_name(sym)
        sector = get_stock_sector(sym)
        if name:
            result.append(VolSymbol(symbol=sym, company_name=name, sector=sector))
    return result
