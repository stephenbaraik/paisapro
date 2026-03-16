"""
Risk Factor Decomposition — Fama-French-style factor analysis.

Constructs Market, Size, Value, Momentum factors from the stock universe
and regresses individual stock returns against them.
"""

import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from .analytics import (
    get_stock_universe, _get_cached_df, get_stock_name, get_stock_sector,
    NIFTY_INDEX, RISK_FREE_RATE,
)
from ..schemas.advanced_analytics import (
    FactorExposure, FactorTimeSeries, StockFactorResult,
    RiskFactorResponse,
)

_factor_cache: tuple[pd.DataFrame | None, float] = (None, 0.0)
_CACHE_TTL = 3600


FACTOR_DESCRIPTIONS = {
    "Market": "Excess return of Nifty 50 over risk-free rate. Captures systematic equity risk.",
    "Size": "Small-cap minus large-cap returns. Positive exposure = tilts toward smaller companies.",
    "Value": "High book-yield minus low book-yield proxy (low-price vs high-price stocks). Positive = value tilt.",
    "Momentum": "Past winners minus past losers (6-month return). Positive = trend-following exposure.",
}


def _build_factor_returns() -> pd.DataFrame:
    """Construct daily factor returns from the stock universe."""
    global _factor_cache
    cached, ts = _factor_cache
    if cached is not None and time.time() - ts < _CACHE_TTL:
        return cached

    universe = get_stock_universe()
    nifty_df = _get_cached_df(NIFTY_INDEX, "2y")

    if nifty_df is None or len(nifty_df) < 200:
        raise ValueError("Cannot build factors: Nifty 50 data unavailable")

    # Collect daily returns for all stocks
    stock_returns: dict[str, pd.Series] = {}
    stock_meta: dict[str, dict] = {}  # price level, 6m return for sorting

    for sym in universe:
        df = _get_cached_df(sym, "2y")
        if df is None or len(df) < 200:
            continue
        ret = df.set_index("date")["close"].pct_change().dropna()
        if len(ret) < 200:
            continue
        stock_returns[sym] = ret

        # Metadata for factor construction
        close_vals = df["close"].values
        price = float(close_vals[-1])
        mom_6m = float((close_vals[-1] / close_vals[-126] - 1) * 100) if len(close_vals) > 126 else 0.0
        stock_meta[sym] = {"price": price, "momentum_6m": mom_6m}

    if len(stock_returns) < 20:
        raise ValueError("Too few stocks with sufficient data for factor construction")

    # Align all returns to common date index
    all_ret = pd.DataFrame(stock_returns)
    all_ret = all_ret.dropna(axis=1, thresh=int(len(all_ret) * 0.7))  # drop stocks with >30% missing
    all_ret = all_ret.fillna(0)
    syms = list(all_ret.columns)

    # ── Market Factor ──
    nifty_ret = nifty_df.set_index("date")["close"].pct_change().dropna()
    rf_daily = RISK_FREE_RATE / 252
    market_factor = nifty_ret - rf_daily

    # ── Size Factor (Small minus Big) ──
    prices = {s: stock_meta[s]["price"] for s in syms if s in stock_meta}
    median_price = np.median(list(prices.values())) if prices else 1000
    small = [s for s in syms if s in prices and prices[s] < median_price]
    big = [s for s in syms if s in prices and prices[s] >= median_price]
    smb = all_ret[small].mean(axis=1) - all_ret[big].mean(axis=1) if small and big else pd.Series(0, index=all_ret.index)

    # ── Value Factor (proxy: low-price minus high-price, rebalanced) ──
    sorted_by_price = sorted(prices.items(), key=lambda x: x[1])
    n = len(sorted_by_price)
    value_stocks = [s for s, _ in sorted_by_price[:n // 3]]
    growth_stocks = [s for s, _ in sorted_by_price[-(n // 3):]]
    hml = all_ret[value_stocks].mean(axis=1) - all_ret[growth_stocks].mean(axis=1) if value_stocks and growth_stocks else pd.Series(0, index=all_ret.index)

    # ── Momentum Factor (Winners minus Losers on 6M return) ──
    mom_data = {s: stock_meta[s]["momentum_6m"] for s in syms if s in stock_meta}
    sorted_by_mom = sorted(mom_data.items(), key=lambda x: x[1], reverse=True)
    n_mom = len(sorted_by_mom)
    winners = [s for s, _ in sorted_by_mom[:n_mom // 3]]
    losers = [s for s, _ in sorted_by_mom[-(n_mom // 3):]]
    wml = all_ret[winners].mean(axis=1) - all_ret[losers].mean(axis=1) if winners and losers else pd.Series(0, index=all_ret.index)

    # Combine into factor DataFrame
    factors = pd.DataFrame({
        "Market": market_factor,
        "Size": smb,
        "Value": hml,
        "Momentum": wml,
    }).dropna()

    _factor_cache = (factors, time.time())
    return factors


def _regress_stock(stock_ret: pd.Series, factors: pd.DataFrame) -> StockFactorResult | None:
    """OLS regression of stock returns on factor returns."""
    from scipy import stats as sp_stats

    common_idx = stock_ret.index.intersection(factors.index)
    if len(common_idx) < 60:
        return None

    y = stock_ret.loc[common_idx].values
    X = factors.loc[common_idx].values
    # Add constant (intercept = alpha)
    X_with_const = np.column_stack([np.ones(len(X)), X])

    try:
        # OLS via numpy
        betas, residuals, _, _ = np.linalg.lstsq(X_with_const, y, rcond=None)
        y_hat = X_with_const @ betas
        resid = y - y_hat

        n, k = X_with_const.shape
        ss_res = float(np.sum(resid ** 2))
        ss_tot = float(np.sum((y - y.mean()) ** 2))
        r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0

        # Standard errors
        mse = ss_res / (n - k) if n > k else 1e-10
        var_beta = mse * np.linalg.inv(X_with_const.T @ X_with_const).diagonal()
        se = np.sqrt(np.maximum(var_beta, 1e-12))
        t_stats = betas / se
        p_values = [float(2 * (1 - sp_stats.t.cdf(abs(t), df=n - k))) for t in t_stats]

        alpha = float(betas[0]) * 252 * 100  # annualized alpha in %
        alpha_t = float(t_stats[0])

        factor_names = list(factors.columns)
        exposures = []
        total_var_explained = max(ss_tot - ss_res, 0)

        for i, fname in enumerate(factor_names):
            beta_i = float(betas[i + 1])
            # Factor contribution approximation
            factor_var_contribution = abs(beta_i) * float(np.std(factors[fname])) * np.sqrt(252) * 100
            contribution_pct = (factor_var_contribution / (total_var_explained ** 0.5 * 100 + 1e-6)) * 100

            exposures.append(FactorExposure(
                factor=fname,
                beta=round(beta_i, 4),
                t_stat=round(float(t_stats[i + 1]), 2),
                p_value=round(p_values[i + 1], 4),
                contribution_pct=round(min(contribution_pct, 100), 1),
            ))

        residual_vol = float(np.std(resid) * np.sqrt(252) * 100)
        dominant = max(exposures, key=lambda e: abs(e.beta))

        return {
            "factor_exposures": exposures,
            "r_squared": round(r_squared, 4),
            "alpha": round(alpha, 2),
            "alpha_t_stat": round(alpha_t, 2),
            "residual_vol": round(residual_vol, 2),
            "dominant_factor": dominant.factor,
        }
    except Exception:
        return None


async def get_risk_factors(symbols: list[str]) -> RiskFactorResponse:
    factors = _build_factor_returns()

    results: list[StockFactorResult] = []
    for sym in symbols:
        yf_sym = sym if sym.endswith(".NS") else f"{sym}.NS"
        df = _get_cached_df(yf_sym, "2y")
        if df is None or len(df) < 200:
            continue

        stock_ret = df.set_index("date")["close"].pct_change().dropna()
        reg = _regress_stock(stock_ret, factors)
        if reg is None:
            continue

        results.append(StockFactorResult(
            symbol=sym,
            company_name=get_stock_name(yf_sym),
            sector=get_stock_sector(yf_sym),
            **reg,
        ))

    # Factor return history (monthly)
    factor_ts: list[FactorTimeSeries] = []
    monthly = factors.resample("ME").sum() * 100  # cumulative monthly in %
    for dt, row in monthly.tail(12).iterrows():
        factor_ts.append(FactorTimeSeries(
            date=pd.Timestamp(dt).strftime("%Y-%m-%d"),
            market=round(float(row["Market"]), 2),
            size=round(float(row["Size"]), 2),
            value=round(float(row["Value"]), 2),
            momentum=round(float(row["Momentum"]), 2),
        ))

    return RiskFactorResponse(
        stocks=results,
        factor_returns=factor_ts,
        factor_descriptions=FACTOR_DESCRIPTIONS,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
