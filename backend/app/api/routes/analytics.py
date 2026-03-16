"""Analytics API routes — thin controllers delegating to the analytics service."""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException

from ...schemas.analytics import (
    MarketOverview,
    TechnicalSignal,
    StockAnalysis,
    PortfolioOptimizationResult,
    PortfolioOptimizeRequest,
    CorrelationMatrix,
    ScreenerResponse,
    AnalyticsReport,
    BacktestResult,
    SmartPortfolioRequest,
    SmartPortfolioResponse,
    TimeSeriesAnalysisResult,
)
from ...services import analytics as svc
from ...services import timeseries as ts_svc

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/market-overview", response_model=MarketOverview)
def market_overview():
    """Sector heatmap, top gainers/losers, anomaly alerts, market breadth."""
    return svc.get_market_overview()


@router.get("/stock-signals", response_model=list[TechnicalSignal])
def stock_signals(
    direction: Optional[str] = Query(None, description="BUY | HOLD | SELL"),
    limit: int = Query(10, ge=1, le=30),
):
    """Return technical signals for tracked stocks, optionally filtered by direction."""
    signals = []
    for sym in svc.get_stock_universe():
        df = svc._get_cached_df(sym, "1y")
        if df is None or df.empty:
            continue
        sig = svc.compute_technical_signals(sym, df)
        if direction and sig.composite_signal.value != direction:
            continue
        signals.append(sig)

    signals.sort(key=lambda s: s.confidence_score, reverse=True)
    return signals[:limit]


@router.get("/stock/{symbol}", response_model=StockAnalysis)
def stock_analysis(symbol: str):
    """On-demand full analysis for a single stock."""
    import pandas as pd
    df = svc._get_cached_df(symbol, "1y")
    if df is None or df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for symbol: {symbol}")
    _nifty = svc._get_cached_df(svc.NIFTY_INDEX, "1y")
    nifty_df = _nifty if _nifty is not None else pd.DataFrame()
    signals = svc.compute_technical_signals(symbol, df)
    risk = svc.compute_risk_metrics(symbol, df, nifty_df)
    prob_up, rf_sig = svc.train_rf_classifier(df, symbol=symbol)
    anomalies = svc.detect_anomalies(symbol, df)
    return StockAnalysis(
        symbol=symbol,
        company_name=svc.get_stock_name(symbol),
        sector=svc.get_stock_sector(symbol),
        technical_signals=signals,
        risk_metrics=risk,
        rf_probability=prob_up,
        rf_signal=rf_sig,
        anomalies=anomalies,
    )


@router.post("/portfolio-optimize", response_model=PortfolioOptimizationResult)
def portfolio_optimize(body: PortfolioOptimizeRequest):
    """Run Monte Carlo + scipy portfolio optimisation for a set of symbols."""
    result = svc.optimize_portfolio(body.symbols, body.risk_profile, body.n_portfolios)
    if result is None:
        raise HTTPException(status_code=422, detail="Not enough valid data for optimisation")
    return result


@router.get("/correlation", response_model=CorrelationMatrix)
def correlation(
    symbols: Optional[str] = Query(None, description="Comma-separated symbols; defaults to top 15"),
):
    """Pearson correlation matrix for daily returns."""
    sym_list = [s.strip() for s in symbols.split(",")] if symbols else svc.get_stock_universe()[:15]
    return svc.compute_correlation_matrix(sym_list)


@router.get("/screener", response_model=ScreenerResponse)
def screener(
    sector: Optional[str] = Query(None),
    signal: Optional[str] = Query(None, description="BUY | HOLD | SELL"),
    min_sharpe: Optional[float] = Query(None),
    max_drawdown: Optional[float] = Query(None, description="Max acceptable drawdown magnitude (e.g. 20 means -20%)"),
    sort_by: str = Query("composite_score"),
    limit: int = Query(50, ge=1, le=500),
):
    """Filter and sort tracked stocks by signal, risk metrics and fundamentals."""
    return svc.screen_stocks(sector, signal, min_sharpe, max_drawdown, sort_by, limit)


@router.get("/report", response_model=AnalyticsReport)
def analytics_report(force_refresh: bool = Query(False)):
    """Full ML analytics report covering all stocks. First call may take a few minutes."""
    return svc.get_analytics_report(force_refresh)


@router.get("/backtest/{symbol}", response_model=BacktestResult)
def backtest(symbol: str):
    """Backtest the technical-signal strategy vs Nifty 50 benchmark."""
    return svc.backtest_strategy(symbol)


@router.post("/smart-portfolio", response_model=SmartPortfolioResponse)
def smart_portfolio(body: SmartPortfolioRequest):
    """Auto-select best stocks, optimise portfolio, and forecast each pick."""
    return svc.build_smart_portfolio(body.risk_profile, body.top_n, body.n_portfolios)


@router.get("/timeseries/{symbol}", response_model=TimeSeriesAnalysisResult)
def timeseries_analysis(symbol: str, horizon: int = Query(30, ge=7, le=90)):
    """ARIMA + ETS time-series analysis with decomposition and stationarity tests."""
    result = ts_svc.run_timeseries_analysis(symbol, horizon)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Not enough data for {symbol} (need ≥120 observations)")
    return result


@router.get("/timeseries-symbols")
def timeseries_symbols():
    """Return list of symbols available for time-series analysis."""
    return ts_svc.get_available_symbols()


