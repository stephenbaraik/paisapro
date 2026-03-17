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
    ModelHealthResponse,
    RegressionModelMetrics,
    CacheStats,
    PKLInventory,
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


@router.get("/model-health", response_model=ModelHealthResponse)
def model_health():
    """MLOps dashboard: regression model eval metrics, RF classifier stats, cache & PKL inventory."""
    from datetime import datetime, timezone
    from pathlib import Path
    import os
    from ...core.cache import cache
    from ...services.ml.model_store import MODEL_DIR

    # ── Regression metrics ────────────────────────────────────────────────────
    reg_keys = cache.keys_with_prefix("mlops:reg:")
    raw_metrics = [cache.get(k) for k in reg_keys]
    raw_metrics = [m for m in raw_metrics if m is not None]

    regression_metrics = [
        RegressionModelMetrics(**m) for m in raw_metrics
    ]

    def _avg(lst, attr):
        vals = [getattr(m, attr) for m in regression_metrics]
        return round(sum(vals) / len(vals), 4) if vals else 0.0

    # ── RF Classifier stats (from cached analytics report) ────────────────────
    report = svc.get_cached_report()
    rf_classifiers_cached = 0
    signal_dist: dict[str, int] = {"BUY": 0, "HOLD": 0, "SELL": 0}
    prob_up_sum = 0.0

    if report:
        rf_classifiers_cached = len(report.stock_analyses)
        for sa in report.stock_analyses:
            sig = sa.rf_signal.value if hasattr(sa.rf_signal, "value") else str(sa.rf_signal)
            signal_dist[sig] = signal_dist.get(sig, 0) + 1
            prob_up_sum += sa.rf_probability
    avg_rf_prob_up = round(prob_up_sum / rf_classifiers_cached, 3) if rf_classifiers_cached else 0.0

    # ── Cache stats ────────────────────────────────────────────────────────────
    all_keys = cache.keys_with_prefix("")
    cs = CacheStats(
        total_entries=len(all_keys),
        stock_dfs=len([k for k in all_keys if k.startswith("stock:df:")]),
        analytics_entries=len([k for k in all_keys if k.startswith("analytics:")]),
        ml_regression_entries=len([k for k in all_keys if k.startswith("ml:regression:")]),
        ml_classifier_entries=len([k for k in all_keys if k.startswith("ml:rf:")]),
        macro_entries=len([k for k in all_keys if k.startswith("macro:")]),
        news_entries=len([k for k in all_keys if k.startswith("news:")]),
        mlops_entries=len([k for k in all_keys if k.startswith("mlops:")]),
        other=len([k for k in all_keys if not any(
            k.startswith(p) for p in
            ("stock:df:", "analytics:", "ml:regression:", "ml:rf:", "macro:", "news:", "mlops:")
        )]),
    )

    # ── PKL inventory ─────────────────────────────────────────────────────────
    rf_count = reg_count = total = 0
    if MODEL_DIR.exists():
        pkls = list(MODEL_DIR.glob("*.pkl"))
        total = len(pkls)
        rf_count = sum(1 for f in pkls if f.name.startswith("rf_"))
        reg_count = sum(1 for f in pkls if f.name.startswith("reg_"))

    pkl = PKLInventory(
        rf_classifiers_today=rf_count,
        regression_bundles_today=reg_count,
        total_pkl_files=total,
        model_dir=str(MODEL_DIR),
    )

    return ModelHealthResponse(
        generated_at=datetime.now(timezone.utc).isoformat(),
        regression_models_evaluated=len(regression_metrics),
        regression_metrics=sorted(regression_metrics, key=lambda m: m.rf_dir_acc, reverse=True),
        avg_rf_r2=_avg(regression_metrics, "rf_r2"),
        avg_rf_dir_acc=_avg(regression_metrics, "rf_dir_acc"),
        avg_ridge_r2=_avg(regression_metrics, "ridge_r2"),
        avg_ridge_dir_acc=_avg(regression_metrics, "ridge_dir_acc"),
        avg_gbm_r2=_avg(regression_metrics, "gbm_r2"),
        avg_gbm_dir_acc=_avg(regression_metrics, "gbm_dir_acc"),
        rf_classifiers_cached=rf_classifiers_cached,
        signal_distribution=signal_dist,
        avg_rf_prob_up=avg_rf_prob_up,
        cache=cs,
        pkl=pkl,
    )


