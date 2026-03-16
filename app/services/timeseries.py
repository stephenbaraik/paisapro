"""
Time-series analysis service — ARIMA, ETS, decomposition, stationarity tests.

Uses statsmodels for proper econometric modelling. Models are cached per symbol
so repeat requests are instant after the first computation.
"""

from __future__ import annotations

import logging
import time
import warnings
from typing import Optional

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller, kpss, acf, pacf

from ..schemas.analytics import (
    ForecastPoint,
    ModelForecast,
    SeasonalDecomposition,
    StationarityTest,
    AutocorrelationPoint,
    TimeSeriesAnalysisResult,
)
from .analytics import (
    _get_cached_df,
    get_stock_name,
    get_stock_sector,
    get_stock_universe,
)

logger = logging.getLogger(__name__)

# Suppress convergence warnings from statsmodels
warnings.filterwarnings("ignore", category=UserWarning, module="statsmodels")
warnings.filterwarnings("ignore", category=FutureWarning, module="statsmodels")

# ── Cache for computed results ────────────────────────────────────────────────
_ts_cache: dict[str, tuple[TimeSeriesAnalysisResult, float]] = {}
_TS_CACHE_TTL = 7200  # 2 hours


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_forecast_points(
    last_date: pd.Timestamp, values: np.ndarray, lower: np.ndarray, upper: np.ndarray
) -> list[ForecastPoint]:
    points = []
    for h in range(len(values)):
        d = last_date + pd.Timedelta(days=h + 1)
        points.append(ForecastPoint(
            date=d.strftime("%Y-%m-%d"),
            price=round(float(values[h]), 2),
            lower=round(float(lower[h]), 2),
            upper=round(float(upper[h]), 2),
        ))
    return points


def _determine_differencing_order(series: np.ndarray, max_d: int = 2) -> int:
    """Determine optimal differencing order using ADF test.

    Repeatedly differences until stationary (p < 0.05) or max_d reached.
    """
    current = series.copy()
    for d in range(max_d + 1):
        try:
            _, p_value, *_ = adfuller(current, maxlag=20, autolag="AIC")
            if p_value < 0.05:
                return d
        except Exception:
            return 1  # safe default
        if d < max_d:
            current = np.diff(current)
    return max_d


# ── Core analysis ─────────────────────────────────────────────────────────────

def run_timeseries_analysis(symbol: str, horizon: int = 30) -> Optional[TimeSeriesAnalysisResult]:
    """Full time-series analysis for a single stock."""

    # Check cache
    if symbol in _ts_cache:
        cached, ts = _ts_cache[symbol]
        if time.time() - ts < _TS_CACHE_TTL:
            return cached

    df = _get_cached_df(symbol, "2y")
    if df is None or len(df) < 120:
        return None

    close = df["close"].values.astype(float)
    dates = pd.to_datetime(df["date"].values)
    last_date = dates[-1]
    n = len(close)

    # ── 1. Seasonal Decomposition ─────────────────────────────────────────
    decomp_data: list[SeasonalDecomposition] = []
    try:
        # Use 5-day period (trading week) for decomposition
        series = pd.Series(close, index=dates)
        result = seasonal_decompose(series, model="additive", period=5, extrapolate_trend="freq")

        # Sample every 5th point to keep payload manageable
        step = max(1, n // 100)
        for i in range(0, n, step):
            decomp_data.append(SeasonalDecomposition(
                date=dates[i].strftime("%Y-%m-%d"),
                observed=round(float(close[i]), 2),
                trend=round(float(result.trend.iloc[i]), 2) if not np.isnan(result.trend.iloc[i]) else None,
                seasonal=round(float(result.seasonal.iloc[i]), 2) if not np.isnan(result.seasonal.iloc[i]) else None,
                residual=round(float(result.resid.iloc[i]), 2) if not np.isnan(result.resid.iloc[i]) else None,
            ))
    except Exception as exc:
        logger.warning(f"Decomposition failed for {symbol}: {exc}")

    # ── 2. Stationarity Tests + Optimal Differencing ──────────────────────
    stationarity_tests: list[StationarityTest] = []

    # Determine optimal differencing order from the data
    optimal_d = _determine_differencing_order(close)

    # ADF test on raw series
    try:
        adf_stat, adf_p, *_ = adfuller(close, maxlag=20, autolag="AIC")
        stationarity_tests.append(StationarityTest(
            test_name="Augmented Dickey-Fuller",
            statistic=round(float(adf_stat), 4),
            p_value=round(float(adf_p), 4),
            is_stationary=adf_p < 0.05,
            interpretation="Stationary (reject unit root)" if adf_p < 0.05
                else f"Non-stationary — auto-differencing with d={optimal_d} applied",
        ))
    except Exception as exc:
        logger.debug(f"ADF test failed for {symbol}: {exc}")

    # KPSS test on raw series
    try:
        kpss_stat, kpss_p, *_ = kpss(close, regression="ct", nlags="auto")
        stationarity_tests.append(StationarityTest(
            test_name="KPSS",
            statistic=round(float(kpss_stat), 4),
            p_value=round(float(kpss_p), 4),
            is_stationary=kpss_p > 0.05,
            interpretation="Stationary (fail to reject)" if kpss_p > 0.05
                else f"Non-stationary — auto-differencing with d={optimal_d} applied",
        ))
    except Exception as exc:
        logger.debug(f"KPSS test failed for {symbol}: {exc}")

    # If differenced, also run ADF on the differenced series to confirm
    if optimal_d > 0:
        try:
            diffed = close.copy()
            for _ in range(optimal_d):
                diffed = np.diff(diffed)
            adf_stat_d, adf_p_d, *_ = adfuller(diffed, maxlag=20, autolag="AIC")
            stationarity_tests.append(StationarityTest(
                test_name=f"ADF (after d={optimal_d} differencing)",
                statistic=round(float(adf_stat_d), 4),
                p_value=round(float(adf_p_d), 4),
                is_stationary=adf_p_d < 0.05,
                interpretation=f"Stationary after {optimal_d}x differencing (p={adf_p_d:.4f})"
                    if adf_p_d < 0.05 else f"Still non-stationary after d={optimal_d}",
            ))
        except Exception as exc:
            logger.debug(f"Post-differencing ADF failed for {symbol}: {exc}")

    # Log-transform check — useful for variance stationarity
    use_log = False
    try:
        if np.all(close > 0):
            log_close = np.log(close)
            log_d = _determine_differencing_order(log_close)
            if log_d < optimal_d:
                use_log = True
                optimal_d = log_d
                logger.info(f"{symbol}: log-transform reduces d from {optimal_d} to {log_d}")
    except Exception:
        pass

    # ── 3. ACF / PACF ────────────────────────────────────────────────────
    autocorrelation: list[AutocorrelationPoint] = []
    try:
        returns = np.diff(np.log(close))
        nlags = min(30, len(returns) // 3)
        acf_vals = acf(returns, nlags=nlags, fft=True)
        pacf_vals = pacf(returns, nlags=nlags)
        for lag in range(nlags + 1):
            autocorrelation.append(AutocorrelationPoint(
                lag=lag,
                acf=round(float(acf_vals[lag]), 4),
                pacf=round(float(pacf_vals[lag]), 4),
            ))
    except Exception as exc:
        logger.debug(f"ACF/PACF failed for {symbol}: {exc}")

    # ── 4. Model Forecasts ────────────────────────────────────────────────
    # Split: last 30 days for validation, rest for training
    val_size = min(30, n // 5)
    train = close[:-val_size]
    val = close[-val_size:]
    model_forecasts: list[ModelForecast] = []

    # --- ARIMA (with data-driven d) ---
    # Prepare data: optionally log-transform for variance stationarity
    arima_data_train = np.log(train) if use_log and np.all(train > 0) else train
    arima_data_full = np.log(close) if use_log and np.all(close > 0) else close

    try:
        # Build order grid using the optimal d
        d = optimal_d
        order_grid = [
            (1, d, 1), (2, d, 1), (1, d, 2), (2, d, 2), (0, d, 1), (1, d, 0),
            (3, d, 1), (1, d, 3),
        ]

        best_arima = None
        best_aic = float("inf")
        best_order = (1, d, 1)

        for order in order_grid:
            try:
                model = ARIMA(arima_data_train, order=order)
                fit = model.fit()
                if fit.aic < best_aic:
                    best_aic = fit.aic
                    best_arima = fit
                    best_order = order
            except Exception:
                continue

        if best_arima is not None:
            # Validation RMSE (compare on original scale)
            val_pred = best_arima.forecast(steps=val_size)
            if use_log:
                val_pred = np.exp(val_pred)
            rmse = float(np.sqrt(np.mean((val - val_pred) ** 2)))

            # Refit on full data for final forecast
            full_model = ARIMA(arima_data_full, order=best_order).fit()
            fc = full_model.get_forecast(steps=horizon)
            fc_mean = fc.predicted_mean
            fc_ci = fc.conf_int(alpha=0.05)

            # Invert log transform if used
            if use_log:
                fc_mean = np.exp(fc_mean)
                fc_ci = np.exp(fc_ci)

            points = _make_forecast_points(
                last_date, fc_mean, fc_ci[:, 0], fc_ci[:, 1]
            )
            label = f"ARIMA{'(log)' if use_log else ''}"
            model_forecasts.append(ModelForecast(
                model_name=label,
                forecast=points,
                rmse=round(rmse, 2),
                aic=round(best_aic, 2),
                order=str(best_order),
            ))
    except Exception as exc:
        logger.warning(f"ARIMA failed for {symbol}: {exc}")

    # --- ETS (Holt-Winters Exponential Smoothing) ---
    ets_train = np.log(train) if use_log and np.all(train > 0) else train
    ets_full = np.log(close) if use_log and np.all(close > 0) else close

    try:
        model = ExponentialSmoothing(
            ets_train, trend="add", seasonal=None, damped_trend=True,
        )
        fit = model.fit(optimized=True)

        val_pred = fit.forecast(steps=val_size)
        if use_log:
            val_pred = np.exp(val_pred)
        rmse = float(np.sqrt(np.mean((val - val_pred) ** 2)))

        # Refit on full data
        full_fit = ExponentialSmoothing(
            ets_full, trend="add", seasonal=None, damped_trend=True,
        ).fit(optimized=True)

        fc_mean = full_fit.forecast(steps=horizon)

        # Approximate confidence intervals using residual std
        resid_std = float(np.std(full_fit.resid.dropna()))
        h_arr = np.arange(1, horizon + 1)
        band = 1.96 * resid_std * np.sqrt(h_arr)

        fc_vals = fc_mean.values
        fc_lower = fc_vals - band
        fc_upper = fc_vals + band

        # Invert log transform
        if use_log:
            fc_vals = np.exp(fc_vals)
            fc_lower = np.exp(fc_lower)
            fc_upper = np.exp(fc_upper)

        label = f"Exponential Smoothing{'(log)' if use_log else ''}"
        points = _make_forecast_points(last_date, fc_vals, fc_lower, fc_upper)
        model_forecasts.append(ModelForecast(
            model_name=label,
            forecast=points,
            rmse=round(rmse, 2),
            aic=round(float(fit.aic), 2) if hasattr(fit, "aic") else None,
            order="Holt (damped)",
        ))
    except Exception as exc:
        logger.warning(f"ETS failed for {symbol}: {exc}")

    # --- Linear Trend (simple baseline) ---
    try:
        x = np.arange(len(train))
        coeffs = np.polyfit(x, train, 1)
        trend_pred = np.polyval(coeffs, np.arange(len(train), len(train) + val_size))
        rmse = float(np.sqrt(np.mean((val - trend_pred) ** 2)))

        x_full = np.arange(n)
        coeffs_full = np.polyfit(x_full, close, 1)
        fc_x = np.arange(n, n + horizon)
        fc_mean = np.polyval(coeffs_full, fc_x)

        resid = close - np.polyval(coeffs_full, x_full)
        resid_std = float(np.std(resid))
        h_arr = np.arange(1, horizon + 1)
        band = 1.96 * resid_std * np.sqrt(1 + h_arr / n)

        points = _make_forecast_points(last_date, fc_mean, fc_mean - band, fc_mean + band)
        model_forecasts.append(ModelForecast(
            model_name="Linear Trend",
            forecast=points,
            rmse=round(rmse, 2),
            aic=None,
            order="degree=1",
        ))
    except Exception as exc:
        logger.warning(f"Linear trend failed for {symbol}: {exc}")

    # ── 5. Pick best model ────────────────────────────────────────────────
    if model_forecasts:
        best = min(model_forecasts, key=lambda m: m.rmse)
        best_model = best.model_name
        best_fc = best.forecast
        predicted_price = best_fc[-1].price
    else:
        best_model = "None"
        predicted_price = float(close[-1])

    current_price = float(close[-1])
    predicted_return = (predicted_price - current_price) / current_price * 100

    if predicted_return > 3:
        trend_label = "BULLISH"
    elif predicted_return < -3:
        trend_label = "BEARISH"
    else:
        trend_label = "NEUTRAL"

    vol_30 = float(np.std(np.diff(np.log(close[-30:]))) * np.sqrt(252) * 100)
    recent_90 = close[-90:] if len(close) >= 90 else close
    support = float(np.min(recent_90))
    resistance = float(np.max(recent_90))

    result = TimeSeriesAnalysisResult(
        symbol=symbol,
        company_name=get_stock_name(symbol),
        sector=get_stock_sector(symbol),
        current_price=round(current_price, 2),
        data_points=n,
        decomposition=decomp_data,
        stationarity_tests=stationarity_tests,
        autocorrelation=autocorrelation,
        model_forecasts=model_forecasts,
        best_model=best_model,
        predicted_return_pct=round(predicted_return, 2),
        trend=trend_label,
        volatility_30d=round(vol_30, 2),
        support_level=round(support, 2),
        resistance_level=round(resistance, 2),
    )

    _ts_cache[symbol] = (result, time.time())
    return result


def get_available_symbols() -> list[dict]:
    """Return list of symbols available for analysis."""
    symbols = []
    for sym in get_stock_universe():
        df = _get_cached_df(sym, "1y")
        if df is not None and len(df) >= 120:
            symbols.append({
                "symbol": sym,
                "company_name": get_stock_name(sym),
                "sector": get_stock_sector(sym),
                "data_points": len(df),
            })
    return symbols
