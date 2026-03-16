"""Pydantic schemas for advanced analytics: Sector Rotation, GARCH, Macro, Risk Factors."""

from typing import Optional
from pydantic import BaseModel, Field


# ── Sector Rotation ──────────────────────────────────────────────────────────

class SectorMomentum(BaseModel):
    sector: str
    stock_count: int
    return_1m: float
    return_3m: float
    return_6m: float
    return_12m: float
    momentum_score: float        # composite momentum rank
    relative_strength: float     # vs Nifty 50
    signal: str                  # "OVERWEIGHT" | "UNDERWEIGHT" | "NEUTRAL"
    avg_rsi: float
    avg_volatility: float


class SectorRotationHistory(BaseModel):
    date: str
    sector: str
    cumulative_return: float


class SectorRotationResponse(BaseModel):
    sectors: list[SectorMomentum]
    rotation_history: list[SectorRotationHistory]   # last 12 months
    leading_sectors: list[str]                       # top 3 by momentum
    lagging_sectors: list[str]                       # bottom 3
    market_phase: str                                # "EXPANSION" | "PEAK" | "CONTRACTION" | "TROUGH"
    generated_at: str


# ── Volatility Forecasting (GARCH) ──────────────────────────────────────────

class VolatilityPoint(BaseModel):
    date: str
    realized_vol: Optional[float] = None     # historical
    forecast_vol: Optional[float] = None     # GARCH forecast
    lower: Optional[float] = None
    upper: Optional[float] = None


class VolatilityConePoint(BaseModel):
    horizon_days: int              # 5, 10, 21, 63, 126, 252
    current_vol: float
    percentile_10: float
    percentile_25: float
    percentile_50: float
    percentile_75: float
    percentile_90: float


class VolatilityForecastResponse(BaseModel):
    symbol: str
    company_name: str
    sector: str
    current_price: float
    current_realized_vol: float       # 30-day annualized
    garch_forecast_vol: float         # next 30-day annualized
    vol_regime: str                   # "LOW" | "NORMAL" | "HIGH" | "EXTREME"
    entry_signal: str                 # "LOW_VOL_ENTRY" | "HIGH_VOL_CAUTION" | "NEUTRAL"
    vol_percentile: float             # current vol vs 1yr range (0-100)
    history: list[VolatilityPoint]    # last 6 months realized + 30 day forecast
    vol_cone: list[VolatilityConePoint]
    garch_params: dict                # omega, alpha, beta, persistence
    generated_at: str


class VolSymbol(BaseModel):
    symbol: str
    company_name: str
    sector: str


# ── Macro Dashboard ──────────────────────────────────────────────────────────

class MacroIndicator(BaseModel):
    name: str                    # "India VIX", "USD/INR", "Nifty 50", "10Y Gilt"
    value: float
    change_pct: float
    trend: str                   # "UP" | "DOWN" | "FLAT"
    description: str


class MacroTimeSeriesPoint(BaseModel):
    date: str
    value: float


class MacroTimeSeries(BaseModel):
    name: str
    data: list[MacroTimeSeriesPoint]


class MacroCorrelation(BaseModel):
    indicator1: str
    indicator2: str
    correlation: float


class MacroDashboardResponse(BaseModel):
    indicators: list[MacroIndicator]
    time_series: list[MacroTimeSeries]        # 1 year history for each indicator
    correlations: list[MacroCorrelation]       # pairwise correlations
    market_regime: str                         # "RISK_ON" | "RISK_OFF" | "NEUTRAL"
    regime_description: str
    generated_at: str


# ── Risk Factor Decomposition ────────────────────────────────────────────────

class FactorExposure(BaseModel):
    factor: str              # "Market", "Size", "Value", "Momentum", "Low_Vol", "Quality"
    beta: float              # factor loading / exposure
    t_stat: float
    p_value: float
    contribution_pct: float  # % of return explained by this factor


class FactorTimeSeries(BaseModel):
    date: str
    market: float
    size: float
    value: float
    momentum: float


class StockFactorResult(BaseModel):
    symbol: str
    company_name: str
    sector: str
    factor_exposures: list[FactorExposure]
    r_squared: float                       # model fit (0-1)
    alpha: float                           # unexplained return (annualized %)
    alpha_t_stat: float
    residual_vol: float                    # idiosyncratic risk (annualized %)
    dominant_factor: str


class RiskFactorRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1, max_length=20)


class RiskFactorResponse(BaseModel):
    stocks: list[StockFactorResult]
    factor_returns: list[FactorTimeSeries]   # factor return history
    factor_descriptions: dict[str, str]
    generated_at: str
