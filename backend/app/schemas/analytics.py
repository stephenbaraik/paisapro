"""Pydantic schemas for ML analytics endpoints."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────────

class SignalDirection(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


class AnomalyType(str, Enum):
    VOLUME_SPIKE = "VOLUME_SPIKE"
    PRICE_SPIKE = "PRICE_SPIKE"
    ISOLATION_FOREST = "ISOLATION_FOREST"


class AnomalySeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"


class ClusterLabel(str, Enum):
    DEFENSIVE = "DEFENSIVE"
    VALUE = "VALUE"
    MOMENTUM = "MOMENTUM"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"


# ── Technical Signals ──────────────────────────────────────────────────────────

class IndicatorSignal(BaseModel):
    name: str
    direction: SignalDirection
    score: float
    value: float


class TechnicalSignal(BaseModel):
    symbol: str
    company_name: str
    sector: str
    current_price: float
    composite_signal: SignalDirection
    composite_score: float
    confidence_score: float  # 0–100
    signals: list[IndicatorSignal]


# ── Risk Metrics ───────────────────────────────────────────────────────────────

class RiskMetrics(BaseModel):
    symbol: str
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float        # negative percentage, e.g. -15.3
    var_95: float              # daily VaR at 95% confidence, negative percentage
    beta: float
    volatility: float          # annualised, positive percentage
    alpha: float               # annualised Jensen's alpha, percentage
    annualized_return: float   # percentage


# ── Anomaly Detection ──────────────────────────────────────────────────────────

class AnomalyAlert(BaseModel):
    symbol: str
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    z_score: float
    description: str


# ── Per-stock Analysis ─────────────────────────────────────────────────────────

class StockAnalysis(BaseModel):
    symbol: str
    company_name: str
    sector: str
    technical_signals: TechnicalSignal
    risk_metrics: RiskMetrics
    rf_probability: float       # probability price up in 5 days
    rf_signal: SignalDirection
    anomalies: list[AnomalyAlert]


# ── Portfolio Optimisation ─────────────────────────────────────────────────────

class PortfolioStats(BaseModel):
    expected_return: float
    volatility: float
    sharpe: float


class EfficientFrontierPoint(BaseModel):
    vol: float
    ret: float
    sharpe: float


class PortfolioOptimizationResult(BaseModel):
    symbols: list[str]
    min_variance_weights: dict[str, float]
    max_sharpe_weights: dict[str, float]
    risk_profile_weights: dict[str, float]
    risk_profile: str
    efficient_frontier: list[EfficientFrontierPoint]
    correlation_matrix: list[list[float]]
    mc_results: list[EfficientFrontierPoint]
    min_variance_stats: PortfolioStats
    max_sharpe_stats: PortfolioStats
    risk_profile_stats: PortfolioStats


class PortfolioOptimizeRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=2, max_length=20)
    risk_profile: str = "moderate"
    n_portfolios: int = Field(2000, ge=500, le=5000)


# ── Clustering ─────────────────────────────────────────────────────────────────

class StockCluster(BaseModel):
    symbol: str
    cluster_id: int
    cluster_label: ClusterLabel
    volatility: float
    momentum_30d: float
    beta: float


class ClusteringResult(BaseModel):
    clusters: list[StockCluster]


# ── Correlation ────────────────────────────────────────────────────────────────

class CorrelationPair(BaseModel):
    symbol1: str
    symbol2: str
    correlation: float


class CorrelationMatrix(BaseModel):
    symbols: list[str]
    matrix: list[list[float]]
    high_correlation_pairs: list[CorrelationPair]


# ── Screener ───────────────────────────────────────────────────────────────────

class ScreenerStock(BaseModel):
    symbol: str
    company_name: str
    sector: str
    current_price: float
    daily_change_pct: float
    composite_signal: SignalDirection
    confidence_score: float
    composite_score: float
    rsi: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    beta: float


class ScreenerResponse(BaseModel):
    stocks: list[ScreenerStock]
    total: int
    buy_count: int
    sell_count: int
    hold_count: int


# ── Backtest ───────────────────────────────────────────────────────────────────

class EquityPoint(BaseModel):
    date: str
    strategy: float
    benchmark: float


class BacktestResult(BaseModel):
    symbol: str
    equity_curve: list[EquityPoint]
    total_return: float
    benchmark_return: float
    alpha: float
    sharpe_ratio: float
    num_trades: int
    win_rate: float


# ── Market Overview ────────────────────────────────────────────────────────────

class SectorHeatmapItem(BaseModel):
    sector: str
    avg_change_pct: float
    stock_count: int


class TrendingStock(BaseModel):
    symbol: str
    company_name: str
    change_pct: float


class MarketOverview(BaseModel):
    sector_heatmap: list[SectorHeatmapItem]
    top_gainers: list[TrendingStock]
    top_losers: list[TrendingStock]
    anomaly_alerts: list[AnomalyAlert]
    market_breadth: dict[str, int]


# ── Full Analytics Report ──────────────────────────────────────────────────────

class AnalyticsReport(BaseModel):
    generated_at: str
    stocks_analyzed: int
    stock_analyses: list[StockAnalysis]
    market_overview: MarketOverview
    clustering: ClusteringResult
    correlation: CorrelationMatrix
    buy_count: int
    sell_count: int
    hold_count: int
    anomaly_count: int


# ── Smart Portfolio + Forecast ────────────────────────────────────────────────

class ForecastPoint(BaseModel):
    date: str
    price: float
    lower: float
    upper: float


class StockForecast(BaseModel):
    symbol: str
    company_name: str
    sector: str
    current_price: float
    forecast_30d: list[ForecastPoint]
    predicted_return_pct: float       # expected 30-day return
    confidence: float                 # 0-100
    trend: str                        # "BULLISH" | "BEARISH" | "NEUTRAL"
    support_level: float
    resistance_level: float
    volatility_30d: float             # annualised vol


class SmartPortfolioRequest(BaseModel):
    risk_profile: str = "moderate"
    top_n: int = Field(15, ge=5, le=30)
    n_portfolios: int = Field(2000, ge=500, le=5000)


class SmartPortfolioResponse(BaseModel):
    # Auto-selected stocks
    selected_symbols: list[str]
    selection_reasoning: list[str]      # why each stock was picked

    # Portfolio optimisation (same as before)
    optimization: PortfolioOptimizationResult

    # Forecasts for each stock in the portfolio
    forecasts: list[StockForecast]

    # Aggregate stats
    portfolio_predicted_return: float   # weighted 30-day forecast
    portfolio_risk_score: float         # 0-100
