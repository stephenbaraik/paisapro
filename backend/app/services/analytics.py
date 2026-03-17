"""
Analytics engine — orchestrates all ML and financial analysis modules.

This module is the public API surface. It delegates to focused sub-modules:
  - market_data      — price DataFrames (cache → Supabase → yfinance)
  - technical        — RSI/MACD/BB/SMA signal computation
  - risk             — Sharpe, drawdown, VaR, anomaly detection
  - ml.classifier    — Random Forest BUY/HOLD/SELL classifier
  - ml.clustering    — KMeans stock grouping
  - portfolio.optimizer  — Monte Carlo + scipy portfolio optimisation
  - portfolio.backtester — Strategy vs benchmark backtesting

Legacy names (NIFTY_INDEX, _get_cached_df, _report_cache, _df_cache) are kept
as re-exports / shims so existing consumers don't need immediate updates.
"""

from __future__ import annotations

import logging
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message=".*sklearn.utils.parallel.delayed.*")

from ..core.cache import cache

# ── Sub-module imports (public API re-exports) ────────────────────────────────
from .universe import (
    get_symbols as get_stock_universe,
    get_name as get_stock_name,
    get_sector as get_stock_sector,
    NIFTY_INDEX,
)
from .market_data import (
    get_price_df as _get_cached_df,   # legacy name kept for existing consumers
    get_nifty_df,
    preload_all as preload_stock_data,
    invalidate_all as _clear_price_cache,
)
from .technical import compute_technical_signals
from .risk import compute_risk_metrics, detect_anomalies, compute_correlation_matrix, RISK_FREE_RATE
from .ml.classifier import train_rf_classifier, invalidate_all_models
from .ml.clustering import cluster_stocks
from .portfolio_optimizer import optimize_portfolio
from .portfolio_backtester import backtest_strategy

# Schemas
from ..schemas.analytics import (
    SignalDirection,
    StockAnalysis,
    AnalyticsReport,
    MarketOverview,
    SectorHeatmapItem,
    TrendingStock,
    ScreenerStock,
    ScreenerResponse,
    ForecastPoint,
    StockForecast,
    SmartPortfolioResponse,
    PortfolioOptimizationResult,
    PortfolioStats,
)

logger = logging.getLogger(__name__)

REPORT_CACHE_KEY = "analytics:report"
ANALYSIS_CACHE_PREFIX = "analytics:stock:"
REPORT_TTL = 7200   # 2 h

# Single-flight lock: prevents N concurrent cold-cache requests from each
# triggering a full rebuild. Only one build runs; the others wait and share
# the result.
_build_lock = threading.Lock()

# ── Legacy shims ──────────────────────────────────────────────────────────────
# ai_advisor.py and ai_portfolio.py import _report_cache as a tuple.
# We keep this module-level variable and sync it whenever the cache changes.
_report_cache: tuple[Optional[AnalyticsReport], float] = (None, 0.0)

# Kept for scheduler.py which clears it directly.
# After the scheduler is updated, these can be removed.
_df_cache: dict = {}   # no longer used — delegated to CacheManager


# ── Per-stock analysis cache (populated during report build) ──────────────────

def _get_analysis(symbol: str) -> Optional[dict]:
    return cache.get(f"{ANALYSIS_CACHE_PREFIX}{symbol}")


def _set_analysis(symbol: str, data: dict) -> None:
    cache.set(f"{ANALYSIS_CACHE_PREFIX}{symbol}", data, REPORT_TTL)


def _analysis_cache_valid() -> bool:
    """True if at least one stock analysis exists in cache."""
    return bool(cache.keys_with_prefix(ANALYSIS_CACHE_PREFIX))


# ── Report building ───────────────────────────────────────────────────────────

def _analyze_stock_worker(symbol: str, nifty_df: pd.DataFrame) -> Optional[dict]:
    try:
        df = _get_cached_df(symbol, "1y")
        if df is None or df.empty:
            return None
        signals = compute_technical_signals(symbol, df)
        risk = compute_risk_metrics(symbol, df, nifty_df)
        prob_up, rf_sig = train_rf_classifier(df, symbol=symbol)
        anomalies = detect_anomalies(symbol, df)
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) >= 2 else last
        chg = float((last["close"] - prev["close"]) / prev["close"] * 100) if prev["close"] > 0 else 0.0
        result = {
            "symbol": symbol,
            "signals": signals,
            "risk": risk,
            "rf_probability": prob_up,
            "rf_signal": rf_sig,
            "anomalies": anomalies,
            "daily_change_pct": chg,
        }
        _set_analysis(symbol, result)
        return result
    except Exception as exc:
        logger.warning("Worker failed for %s: %s", symbol, exc)
        return None


def get_analytics_report(force_refresh: bool = False) -> AnalyticsReport:
    global _report_cache

    # Fast path — no lock needed
    cached_report: Optional[AnalyticsReport] = cache.get(REPORT_CACHE_KEY)
    if not force_refresh and cached_report is not None:
        return cached_report

    # Single-flight: only one thread builds at a time.
    # All other threads wait here and receive the freshly built result.
    with _build_lock:
        # Re-check after acquiring lock — another thread may have just finished
        cached_report = cache.get(REPORT_CACHE_KEY)
        if not force_refresh and cached_report is not None:
            return cached_report

        universe = get_stock_universe()
        logger.info("Building full analytics report for %d stocks…", len(universe))
    nifty_df = get_nifty_df("1y") or pd.DataFrame()

    results: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        fmap = {pool.submit(_analyze_stock_worker, sym, nifty_df): sym for sym in universe}
        for fut in as_completed(fmap):
            sym = fmap[fut]
            try:
                res = fut.result()
                if res:
                    results[sym] = res
            except Exception as exc:
                logger.warning("Report worker error for %s: %s", sym, exc)

    buy_count = sum(1 for r in results.values() if r["signals"].composite_signal == SignalDirection.BUY)
    sell_count = sum(1 for r in results.values() if r["signals"].composite_signal == SignalDirection.SELL)
    hold_count = len(results) - buy_count - sell_count

    sector_data: dict[str, list[float]] = {}
    for r in results.values():
        sec = get_stock_sector(r["symbol"])
        sector_data.setdefault(sec, []).append(r["daily_change_pct"])

    sector_heatmap = [
        SectorHeatmapItem(sector=s, avg_change_pct=round(sum(v) / len(v), 2), stock_count=len(v))
        for s, v in sector_data.items()
    ]

    by_chg = sorted(results.values(), key=lambda r: r["daily_change_pct"], reverse=True)
    top_gainers = [
        TrendingStock(symbol=r["symbol"], company_name=get_stock_name(r["symbol"]), change_pct=round(r["daily_change_pct"], 2))
        for r in by_chg[:5]
    ]
    top_losers = [
        TrendingStock(symbol=r["symbol"], company_name=get_stock_name(r["symbol"]), change_pct=round(r["daily_change_pct"], 2))
        for r in by_chg[-5:]
    ]

    all_anomalies = [a for r in results.values() for a in r["anomalies"]]

    stock_analyses = [
        StockAnalysis(
            symbol=r["symbol"],
            company_name=get_stock_name(r["symbol"]),
            sector=get_stock_sector(r["symbol"]),
            technical_signals=r["signals"],
            risk_metrics=r["risk"],
            rf_probability=r["rf_probability"],
            rf_signal=r["rf_signal"],
            anomalies=r["anomalies"],
        )
        for r in results.values()
    ]

    clustering = cluster_stocks(list(results.keys()))
    correlation = compute_correlation_matrix(list(results.keys())[:15])

    market_overview = MarketOverview(
        sector_heatmap=sector_heatmap,
        top_gainers=top_gainers,
        top_losers=top_losers,
        anomaly_alerts=all_anomalies[:10],
        market_breadth={"buy": buy_count, "hold": hold_count, "sell": sell_count},
    )

    report = AnalyticsReport(
        generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        stocks_analyzed=len(results),
        stock_analyses=stock_analyses,
        market_overview=market_overview,
        clustering=clustering,
        correlation=correlation,
        buy_count=buy_count,
        sell_count=sell_count,
        hold_count=hold_count,
        anomaly_count=len(all_anomalies),
    )

    cache.set(REPORT_CACHE_KEY, report, REPORT_TTL)
    _report_cache = (report, time.time())  # keep legacy tuple in sync

    logger.info(
        "Analytics report built: %d stocks, %d BUY, %d SELL",
        len(results), buy_count, sell_count,
    )
    return report


def get_cached_report() -> Optional[AnalyticsReport]:
    """Return the cached report without triggering a rebuild. Returns None if not ready."""
    return cache.get(REPORT_CACHE_KEY)


def get_market_overview() -> MarketOverview:
    """Fast market overview — uses cached report or per-stock analysis cache."""
    cached_report = cache.get(REPORT_CACHE_KEY)
    if cached_report is not None:
        return cached_report.market_overview

    # Fall back to per-stock analysis cache populated during last report build
    if _analysis_cache_valid():
        quick_results = [cache.get(k) for k in cache.keys_with_prefix(ANALYSIS_CACHE_PREFIX) if cache.get(k)]
    else:
        quick_results = []
        for sym in get_stock_universe():
            try:
                df = _get_cached_df(sym, "1y")
                if df is None or df.empty:
                    quick_results.append({"symbol": sym, "daily_change_pct": 0.0, "signals": None, "anomalies": []})
                    continue
                prev = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
                chg = float((df.iloc[-1]["close"] - prev["close"]) / prev["close"] * 100) if prev["close"] > 0 else 0.0
                signals = compute_technical_signals(sym, df)
                anomalies = detect_anomalies(sym, df)
                quick_results.append({"symbol": sym, "daily_change_pct": chg, "signals": signals, "anomalies": anomalies})
            except Exception:
                pass

    sector_data: dict[str, list[float]] = {}
    for r in quick_results:
        sec = get_stock_sector(r["symbol"])
        sector_data.setdefault(sec, []).append(r.get("daily_change_pct", 0.0))

    sector_heatmap = [
        SectorHeatmapItem(sector=s, avg_change_pct=round(sum(v) / len(v), 2), stock_count=len(v))
        for s, v in sector_data.items()
    ]

    by_chg = sorted(quick_results, key=lambda r: r.get("daily_change_pct", 0.0), reverse=True)
    top_gainers = [
        TrendingStock(symbol=r["symbol"], company_name=get_stock_name(r["symbol"]), change_pct=round(r.get("daily_change_pct", 0.0), 2))
        for r in by_chg[:5]
    ]
    top_losers = [
        TrendingStock(symbol=r["symbol"], company_name=get_stock_name(r["symbol"]), change_pct=round(r.get("daily_change_pct", 0.0), 2))
        for r in by_chg[-5:]
    ]

    all_anomalies = [a for r in quick_results for a in r.get("anomalies", [])]
    buy = sum(1 for r in quick_results if r.get("signals") and r["signals"].composite_signal == SignalDirection.BUY)
    sell = sum(1 for r in quick_results if r.get("signals") and r["signals"].composite_signal == SignalDirection.SELL)
    hold = len(quick_results) - buy - sell

    return MarketOverview(
        sector_heatmap=sector_heatmap,
        top_gainers=top_gainers,
        top_losers=top_losers,
        anomaly_alerts=all_anomalies[:10],
        market_breadth={"buy": buy, "hold": hold, "sell": sell},
    )


# ── Screener ──────────────────────────────────────────────────────────────────

def screen_stocks(
    sector: Optional[str] = None,
    signal: Optional[str] = None,
    min_sharpe: Optional[float] = None,
    max_drawdown_threshold: Optional[float] = None,
    sort_by: str = "composite_score",
    limit: int = 30,
) -> ScreenerResponse:
    stocks: list[ScreenerStock] = []
    cache_keys = cache.keys_with_prefix(ANALYSIS_CACHE_PREFIX)

    if cache_keys:
        # Fast path: use pre-computed analysis from last report build
        for key in cache_keys:
            cached = cache.get(key)
            if not cached:
                continue
            try:
                sym = cached["symbol"]
                sig = cached["signals"]
                risk = cached["risk"]
                df = _get_cached_df(sym, "1y")
                current_price = float(df.iloc[-1]["close"]) if df is not None and not df.empty else 0.0
                rsi_val = float(df.iloc[-1].get("rsi_14", 50)) if df is not None and not df.empty else 50.0
                if np.isnan(rsi_val):
                    rsi_val = 50.0

                stock = ScreenerStock(
                    symbol=sym,
                    company_name=get_stock_name(sym),
                    sector=get_stock_sector(sym),
                    current_price=round(current_price, 2),
                    daily_change_pct=round(cached["daily_change_pct"], 2),
                    composite_signal=sig.composite_signal,
                    confidence_score=sig.confidence_score,
                    composite_score=sig.composite_score,
                    rsi=round(rsi_val, 1),
                    sharpe_ratio=risk.sharpe_ratio,
                    max_drawdown=risk.max_drawdown,
                    volatility=risk.volatility,
                    beta=risk.beta,
                )

                if sector and stock.sector != sector:
                    continue
                if signal and stock.composite_signal.value != signal:
                    continue
                if min_sharpe is not None and stock.sharpe_ratio < min_sharpe:
                    continue
                if max_drawdown_threshold is not None and stock.max_drawdown < -abs(max_drawdown_threshold):
                    continue

                stocks.append(stock)
            except Exception as exc:
                logger.warning("Screener (cached) failed for %s: %s", cached.get("symbol", "?"), exc)
    else:
        # Slow path: compute on first load before report is built
        nifty_df = get_nifty_df("1y") or pd.DataFrame()
        for sym in get_stock_universe():
            try:
                df = _get_cached_df(sym, "1y")
                if df is None or df.empty:
                    continue
                sig = compute_technical_signals(sym, df)
                risk = compute_risk_metrics(sym, df, nifty_df)
                current_price = float(df.iloc[-1]["close"])
                prev = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]
                change_pct = float((df.iloc[-1]["close"] - prev["close"]) / prev["close"] * 100) if prev["close"] > 0 else 0.0
                rsi_val = float(df.iloc[-1].get("rsi_14", 50))
                if np.isnan(rsi_val):
                    rsi_val = 50.0

                stock = ScreenerStock(
                    symbol=sym,
                    company_name=get_stock_name(sym),
                    sector=get_stock_sector(sym),
                    current_price=round(current_price, 2),
                    daily_change_pct=round(change_pct, 2),
                    composite_signal=sig.composite_signal,
                    confidence_score=sig.confidence_score,
                    composite_score=sig.composite_score,
                    rsi=round(rsi_val, 1),
                    sharpe_ratio=risk.sharpe_ratio,
                    max_drawdown=risk.max_drawdown,
                    volatility=risk.volatility,
                    beta=risk.beta,
                )

                if sector and stock.sector != sector:
                    continue
                if signal and stock.composite_signal.value != signal:
                    continue
                if min_sharpe is not None and stock.sharpe_ratio < min_sharpe:
                    continue
                if max_drawdown_threshold is not None and stock.max_drawdown < -abs(max_drawdown_threshold):
                    continue

                stocks.append(stock)
            except Exception as exc:
                logger.warning("Screener failed for %s: %s", sym, exc)

    reverse = sort_by not in ["max_drawdown", "volatility"]
    stocks.sort(key=lambda s: getattr(s, sort_by, 0), reverse=reverse)
    stocks = stocks[:limit]

    buy = sum(1 for s in stocks if s.composite_signal == SignalDirection.BUY)
    sell = sum(1 for s in stocks if s.composite_signal == SignalDirection.SELL)
    return ScreenerResponse(stocks=stocks, total=len(stocks), buy_count=buy, sell_count=sell, hold_count=len(stocks) - buy - sell)


# ── Forecast ──────────────────────────────────────────────────────────────────

def forecast_stock(symbol: str, horizon: int = 30) -> Optional[StockForecast]:
    df = _get_cached_df(symbol, "2y")
    if df is None or len(df) < 120:
        return None

    close = df["close"].values.astype(float)
    dates = pd.to_datetime(df["date"].values)

    alpha, beta_hl = 0.3, 0.1
    level = close[0]
    trend = 0.0
    for p in close[1:]:
        prev_level = level
        level = alpha * p + (1 - alpha) * (level + trend)
        trend = beta_hl * (level - prev_level) + (1 - beta_hl) * trend

    forecast_prices = [level + trend * h for h in range(1, horizon + 1)]

    # Residual sigma for confidence bands
    fitted = []
    lv, tr = close[0], 0.0
    for p in close[1:]:
        prev_l = lv
        lv = alpha * p + (1 - alpha) * (lv + tr)
        tr = beta_hl * (lv - prev_l) + (1 - beta_hl) * tr
        fitted.append(lv)
    residuals = close[1:] - np.array(fitted)
    sigma = float(np.std(residuals))

    last_date = dates[-1]
    forecast_points: list[ForecastPoint] = []
    for h in range(1, horizon + 1):
        d = last_date + pd.Timedelta(days=h)
        band = 1.96 * sigma * np.sqrt(h)
        forecast_points.append(ForecastPoint(
            date=d.strftime("%Y-%m-%d"),
            price=round(forecast_prices[h - 1], 2),
            lower=round(forecast_prices[h - 1] - band, 2),
            upper=round(forecast_prices[h - 1] + band, 2),
        ))

    current_price = float(close[-1])
    predicted_price = forecast_prices[-1]
    predicted_return = (predicted_price - current_price) / current_price * 100

    if predicted_return > 3:
        trend_label = "BULLISH"
    elif predicted_return < -3:
        trend_label = "BEARISH"
    else:
        trend_label = "NEUTRAL"

    recent_60 = close[-60:]
    x_idx = np.arange(len(recent_60))
    corr_coef = np.corrcoef(x_idx, recent_60)[0, 1]
    r_squared = corr_coef ** 2
    vol_30 = float(np.std(np.diff(np.log(close[-30:]))) * np.sqrt(252) * 100)
    confidence = min(95, max(15, r_squared * 80 + (1 - min(vol_30, 60) / 60) * 20))

    recent_90 = close[-90:]
    support = float(np.min(recent_90))
    resistance = float(np.max(recent_90))

    return StockForecast(
        symbol=symbol,
        company_name=get_stock_name(symbol),
        sector=get_stock_sector(symbol),
        current_price=round(current_price, 2),
        forecast_30d=forecast_points,
        predicted_return_pct=round(predicted_return, 2),
        confidence=round(confidence, 1),
        trend=trend_label,
        support_level=round(support, 2),
        resistance_level=round(resistance, 2),
        volatility_30d=round(vol_30, 2),
    )


# ── Smart portfolio ───────────────────────────────────────────────────────────

def build_smart_portfolio(
    risk_profile: str = "moderate",
    top_n: int = 15,
    n_portfolios: int = 2000,
) -> SmartPortfolioResponse:
    from ..schemas.analytics import StockAnalysis as SA

    report = get_analytics_report(force_refresh=False)
    analyses = report.stock_analyses

    scored: list[tuple[float, SA, str]] = []
    for a in analyses:
        sig_score = a.technical_signals.composite_score
        conf = a.technical_signals.confidence_score / 100
        sharpe = a.risk_metrics.sharpe_ratio
        rf_prob = a.rf_probability
        vol = a.risk_metrics.volatility / 100

        selection = (
            sig_score * 2.0
            + conf * 3.0
            + sharpe * 2.0
            + (rf_prob - 0.5) * 6.0
            - vol * 3.0
        )

        if risk_profile == "conservative":
            selection += (1 - vol) * 2 + min(sharpe, 2) * 1.5
            reason = f"Sharpe {sharpe:.2f}, Vol {a.risk_metrics.volatility:.1f}%, Signal {a.technical_signals.composite_signal.value}"
        elif risk_profile == "aggressive":
            selection += sig_score * 1.5 + rf_prob * 3
            reason = f"RF prob {rf_prob:.0%} up, Signal {sig_score:+.1f}, Confidence {conf:.0%}"
        else:
            reason = f"Score {sig_score:+.1f}, Sharpe {sharpe:.2f}, RF {rf_prob:.0%} bullish"

        scored.append((selection, a, reason))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected: list[SA] = []
    reasons: list[str] = []
    sector_count: dict[str, int] = {}
    max_per_sector = max(3, top_n // 4)

    for score_val, analysis, reason in scored:
        sec = analysis.sector
        if sector_count.get(sec, 0) >= max_per_sector:
            continue
        selected.append(analysis)
        reasons.append(f"{get_stock_name(analysis.symbol).split(' ')[0]} — {reason}")
        sector_count[sec] = sector_count.get(sec, 0) + 1
        if len(selected) >= top_n:
            break

    symbols = [a.symbol for a in selected]

    opt_result = optimize_portfolio(symbols, risk_profile, n_portfolios)
    if opt_result is None:
        eq_w = {s: round(1.0 / len(symbols), 4) for s in symbols}
        opt_result = PortfolioOptimizationResult(
            symbols=symbols,
            min_variance_weights=eq_w,
            max_sharpe_weights=eq_w,
            risk_profile_weights=eq_w,
            risk_profile=risk_profile,
            efficient_frontier=[],
            correlation_matrix=[],
            mc_results=[],
            min_variance_stats=PortfolioStats(expected_return=0, volatility=0, sharpe=0),
            max_sharpe_stats=PortfolioStats(expected_return=0, volatility=0, sharpe=0),
            risk_profile_stats=PortfolioStats(expected_return=0, volatility=0, sharpe=0),
        )

    forecasts = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        fmap = {pool.submit(forecast_stock, sym): sym for sym in symbols}
        for fut in as_completed(fmap):
            try:
                fc = fut.result()
                if fc is not None:
                    forecasts.append(fc)
            except Exception as exc:
                logger.warning("Forecast failed for %s: %s", fmap[fut], exc)

    fc_map = {f.symbol: f for f in forecasts}
    forecasts = [fc_map[s] for s in symbols if s in fc_map]

    weights = opt_result.risk_profile_weights
    total_weight = sum(weights.get(s, 0) for s in symbols if s in fc_map)

    portfolio_return = 0.0
    portfolio_risk = 0.0
    for fc in forecasts:
        w = weights.get(fc.symbol, 0)
        w_norm = w / total_weight if total_weight > 0 else 1.0 / len(forecasts)
        portfolio_return += fc.predicted_return_pct * w_norm
        portfolio_risk += fc.volatility_30d * w_norm

    risk_score = min(100, max(0, portfolio_risk * 1.5))

    return SmartPortfolioResponse(
        selected_symbols=symbols,
        selection_reasoning=reasons,
        optimization=opt_result,
        forecasts=forecasts,
        portfolio_predicted_return=round(portfolio_return, 2),
        portfolio_risk_score=round(risk_score, 1),
    )
