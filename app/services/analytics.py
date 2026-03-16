"""
Core ML analytics engine for Indian stock market analysis.

Data source:
  - Yahoo Finance (yfinance) — NSE-listed stocks, 1-day interval, 1-year history.
      No API key required, no rate limits.
      Results persisted to Supabase (stock_prices table) so restarts are instant.
      24-hour in-memory cache on top of Supabase for hot-path performance.

ML: scikit-learn RandomForest, IsolationForest, KMeans; scipy optimisation.
"""

from __future__ import annotations

import os
import time
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
import yfinance as yf
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from scipy.optimize import minimize

from ..schemas.analytics import (
    SignalDirection,
    IndicatorSignal,
    TechnicalSignal,
    RiskMetrics,
    AnomalyAlert,
    AnomalyType,
    AnomalySeverity,
    StockAnalysis,
    PortfolioOptimizationResult,
    PortfolioStats,
    EfficientFrontierPoint,
    StockCluster,
    ClusteringResult,
    ClusterLabel,
    CorrelationMatrix,
    CorrelationPair,
    ScreenerStock,
    ScreenerResponse,
    EquityPoint,
    BacktestResult,
    SectorHeatmapItem,
    TrendingStock,
    MarketOverview,
    AnalyticsReport,
    ForecastPoint,
    StockForecast,
    SmartPortfolioResponse,
)

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

RISK_FREE_RATE = 0.065  # Indian 10-yr gilt
NIFTY_INDEX = "^NSEI"

# ── Dynamic stock universe (loaded from Supabase stocks table) ────────────────

_stock_universe: list[str] = []           # ["RELIANCE.NS", "TCS.NS", ...]
_stock_names: dict[str, str] = {}         # {"RELIANCE.NS": "Reliance Industries"}
_stock_sectors: dict[str, str] = {}       # {"RELIANCE.NS": "Energy"}
_universe_loaded = False


def _load_stock_universe() -> None:
    """Fetch all stocks from Supabase stocks table and populate the universe."""
    global _stock_universe, _stock_names, _stock_sectors, _universe_loaded

    from ..core.config import get_settings
    settings = get_settings()

    try:
        url = f"{settings.supabase_url}/rest/v1/stocks"
        headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }
        resp = httpx.get(
            url,
            headers=headers,
            params={
                "select": "symbol,company_name,sector",
                "order": "symbol.asc",
                "limit": "1000",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning(f"Failed to load stock universe from Supabase: {exc}")
        _universe_loaded = True
        return

    symbols = []
    names = {}
    sectors = {}
    for row in data:
        bare = row["symbol"]
        ns = f"{bare}.NS"
        symbols.append(ns)
        names[ns] = row.get("company_name") or bare
        sectors[ns] = row.get("sector") or "Unknown"

    _stock_universe = symbols
    _stock_names = names
    _stock_sectors = sectors
    _universe_loaded = True
    logger.info(f"Loaded stock universe: {len(symbols)} stocks from Supabase")


def get_stock_universe() -> list[str]:
    """Return the full list of stock symbols (lazy-loaded from DB)."""
    if not _universe_loaded:
        _load_stock_universe()
    return _stock_universe


def get_stock_name(symbol: str) -> str:
    if not _universe_loaded:
        _load_stock_universe()
    return _stock_names.get(symbol, symbol)


def get_stock_sector(symbol: str) -> str:
    if not _universe_loaded:
        _load_stock_universe()
    return _stock_sectors.get(symbol, "Unknown")

# ── In-memory caches ───────────────────────────────────────────────────────────

_df_cache: dict[str, tuple[pd.DataFrame, float]] = {}       # historical OHLCV
_report_cache: tuple[Optional[AnalyticsReport], float] = (None, 0.0)

# Per-stock ML model + prediction cache (trained once per report build)
# { symbol: (RandomForestClassifier, prob_up, signal_direction) }
_rf_model_cache: dict[str, tuple[object, float, SignalDirection]] = {}

# Per-stock pre-computed analysis cache (built during report generation)
# { symbol: { "signals": TechnicalSignal, "risk": RiskMetrics, "rf_probability": float, ... } }
_analysis_cache: dict[str, dict] = {}
_analysis_cache_ts: float = 0.0

HIST_CACHE_TTL = 86400    # 24 hr — yfinance (once-a-day re-fetch)
REPORT_TTL     = 7200     # 2 hr  — full analytics report

# ── Supabase REST helpers ──────────────────────────────────────────────────────

def _db_symbol(symbol: str) -> str:
    """Strip exchange suffix for DB storage: RELIANCE.NS → RELIANCE, ^NSEI → NSEI."""
    return symbol.replace(".NS", "").replace(".BO", "").replace("^", "")


def _sb_headers() -> dict:
    from ..core.config import get_settings
    key = get_settings().supabase_service_role_key
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }


def _sb_url(table: str) -> str:
    from ..core.config import get_settings
    return f"{get_settings().supabase_url}/rest/v1/{table}"


def _safe_f(v) -> Optional[float]:
    try:
        f = float(v)
        return None if (f != f) else round(f, 6)   # NaN → None
    except (TypeError, ValueError):
        return None


def _upsert_stocks_meta(symbols: list[str]) -> None:
    """Ensure every symbol has a row in the stocks table."""
    rows = [
        {
            "symbol":       _db_symbol(sym),
            "company_name": get_stock_name(sym) or _db_symbol(sym),
            "exchange":     "NSE",
            "sector":       get_stock_sector(sym),
        }
        for sym in symbols
    ]
    try:
        resp = httpx.post(_sb_url("stocks"), headers=_sb_headers(), json=rows, timeout=15)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning(f"Supabase stocks meta upsert failed: {exc}")


def _save_to_supabase(symbol: str, df: pd.DataFrame) -> None:
    """Bulk-upsert OHLCV data to stock_prices (upsert on symbol+date)."""
    db_sym = _db_symbol(symbol)
    rows = []
    for _, row in df.iterrows():
        rows.append({
            "symbol":         db_sym,
            "date":           str(row["date"].date()),
            "open":           _safe_f(row.get("open")),
            "high":           _safe_f(row.get("high")),
            "low":            _safe_f(row.get("low")),
            "close":          _safe_f(row.get("close")),
            "volume":         int(row["volume"]) if row.get("volume") and not (row["volume"] != row["volume"]) else None,
        })

    for i in range(0, len(rows), 500):
        batch = rows[i : i + 500]
        try:
            resp = httpx.post(
                _sb_url("stock_prices") + "?on_conflict=symbol,date",
                headers=_sb_headers(), json=batch, timeout=30,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning(f"Supabase write failed for {symbol} batch {i}: {exc}")

    logger.info(f"Saved {len(rows)} rows for {symbol} to Supabase")


def _load_from_supabase(symbol: str) -> pd.DataFrame:
    """Load recent OHLCV rows from stock_prices (last 750 rows ≈ 3 years)."""
    db_sym = _db_symbol(symbol)
    try:
        resp = httpx.get(
            _sb_url("stock_prices"),
            headers=_sb_headers(),
            params={
                "symbol": f"eq.{db_sym}",
                "select": "date,open,high,low,close,volume",
                "order": "date.desc",
                "limit": "750",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning(f"Supabase read failed for {symbol}: {exc}")
        return pd.DataFrame()

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    for col in df.columns:
        if col != "date":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)

    logger.debug(f"Loaded {len(df)} rows for {symbol} from Supabase")
    return df



# ── Data fetching & indicators ─────────────────────────────────────────────────

def _add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    df["sma_20"] = close.rolling(20).mean()
    df["sma_50"] = close.rolling(50).mean()
    df["sma_200"] = close.rolling(200).mean()
    df["ema_12"] = close.ewm(span=12, adjust=False).mean()
    df["ema_26"] = close.ewm(span=26, adjust=False).mean()
    df["macd"] = df["ema_12"] - df["ema_26"]
    df["macd_signal"]    = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_histogram"] = df["macd"] - df["macd_signal"]

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    df["bb_mid"]   = bb_mid
    df["bb_upper"] = bb_mid + 2 * bb_std
    df["bb_lower"] = bb_mid - 2 * bb_std
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / bb_mid

    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    df["atr_14"] = tr.rolling(14).mean()

    df["vol_sma_20"] = volume.rolling(20).mean()
    df["vol_ratio"] = volume / df["vol_sma_20"].replace(0, np.nan)
    df["daily_return"] = close.pct_change()
    df["price_vs_sma20"] = (close / df["sma_20"]) - 1
    df["price_vs_sma50"] = (close / df["sma_50"]) - 1
    df["atr_normalized"] = df["atr_14"] / close
    df["return_5d"] = close.pct_change(5)
    df["return_20d"] = close.pct_change(20)

    return df


# ── Yahoo Finance data fetching ────────────────────────────────────────────────

def _fetch_yfinance(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    Fetch daily OHLCV from Yahoo Finance (1d interval).
    Returns DataFrame with columns: date, open, high, low, close, volume.
    Returns empty DataFrame on any error.
    """
    try:
        raw = yf.Ticker(symbol).history(period=period, interval="1d", auto_adjust=True)
        if raw is None or raw.empty:
            logger.warning(f"yfinance: no data for {symbol}")
            return pd.DataFrame()
        df = raw.reset_index()
        df.rename(columns={"Date": "date", "Open": "open", "High": "high",
                            "Low": "low", "Close": "close", "Volume": "volume"}, inplace=True)
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
        df = df[["date", "open", "high", "low", "close", "volume"]].copy()
        df = df[df["close"] > 0].reset_index(drop=True)
        logger.info(f"yfinance: fetched {len(df)} rows for {symbol}")
        return df
    except Exception as exc:
        logger.error(f"yfinance error for {symbol}: {exc}")
        return pd.DataFrame()


def _get_cached_df(symbol: str, period: str = "1y") -> Optional[pd.DataFrame]:
    """
    Return a DataFrame of historical OHLCV + indicators for the requested period.

    Fetch priority:
      1. In-memory cache (24 hr TTL) — zero network cost.
      2. Supabase stock_prices (persistent across restarts) — zero network cost
         if latest row is within 3 calendar days and ≥ 50 rows.
      3. Yahoo Finance — free, no rate limits.  Result saved to Supabase.
    """
    raw_key = f"{symbol}_raw"
    now = time.time()

    # 1. In-memory cache
    if raw_key in _df_cache:
        raw_df, ts = _df_cache[raw_key]
        if now - ts < HIST_CACHE_TTL:
            return _trim_period(raw_df, period)

    # 2. Supabase
    sb_df = _load_from_supabase(symbol)
    if not sb_df.empty:
        latest_date = sb_df["date"].max()
        days_stale = (pd.Timestamp.now() - latest_date).days
        if days_stale <= 3 and len(sb_df) >= 50:
            sb_df = _add_indicators(sb_df)
            _df_cache[raw_key] = (sb_df, now)
            return _trim_period(sb_df, period)

    # 3. Yahoo Finance (full history)
    raw_df = _fetch_yfinance(symbol, period="max")
    if raw_df.empty:
        if not sb_df.empty:          # stale Supabase is better than nothing
            sb_df = _add_indicators(sb_df)
            _df_cache[raw_key] = (sb_df, now)
            return _trim_period(sb_df, period)
        return None

    raw_df = _add_indicators(raw_df)
    _upsert_stocks_meta([symbol])
    _save_to_supabase(symbol, raw_df)
    _df_cache[raw_key] = (raw_df, now)
    return _trim_period(raw_df, period)


def _trim_period(df: pd.DataFrame, period: str) -> Optional[pd.DataFrame]:
    """Trim a full-history DataFrame to the requested period."""
    period_days = {"1mo": 30, "3mo": 92, "6mo": 183, "1y": 365, "2y": 730, "5y": 1825}
    n_days = period_days.get(period, 365)
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=n_days)
    trimmed = df[df["date"] >= cutoff].copy().reset_index(drop=True)
    return trimmed if len(trimmed) >= 20 else None


def preload_stock_data() -> int:
    """Bulk-load ALL stock price data from Supabase in one query, then split per symbol."""
    universe = get_stock_universe()
    if not universe:
        return 0

    already = sum(1 for sym in universe if f"{sym}_raw" in _df_cache)
    if already == len(universe):
        return already

    logger.info(f"Bulk-loading stock prices from Supabase…")

    # Single query: fetch last 750 rows per stock using a window function via RPC,
    # or just fetch all recent data. With 500 stocks × 750 rows = 375K rows max.
    # Supabase REST has no window function, so we fetch the last 3 years of data
    # for ALL stocks in one paginated call.
    from ..core.config import get_settings
    settings = get_settings()
    url = f"{settings.supabase_url}/rest/v1/stock_prices"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
    }

    cutoff = (pd.Timestamp.now() - pd.Timedelta(days=750)).strftime("%Y-%m-%d")
    all_data: list[dict] = []
    page_size = 10000
    offset = 0

    while True:
        try:
            resp = httpx.get(
                url, headers=headers,
                params={
                    "select": "symbol,date,open,high,low,close,volume",
                    "date": f"gte.{cutoff}",
                    "order": "symbol.asc,date.asc",
                    "limit": str(page_size),
                    "offset": str(offset),
                },
                timeout=30,
            )
            resp.raise_for_status()
            page = resp.json()
        except Exception as exc:
            logger.warning(f"Bulk load page failed at offset {offset}: {exc}")
            break

        if not page:
            break
        all_data.extend(page)
        logger.info(f"  Fetched {len(all_data)} rows so far…")
        if len(page) < page_size:
            break
        offset += page_size

    if not all_data:
        logger.warning("Bulk load returned no data")
        return already

    logger.info(f"Bulk load complete: {len(all_data)} rows. Splitting per symbol…")

    # Build one big DataFrame, split by symbol
    big_df = pd.DataFrame(all_data)
    big_df["date"] = pd.to_datetime(big_df["date"])
    for col in ["open", "high", "low", "close", "volume"]:
        big_df[col] = pd.to_numeric(big_df[col], errors="coerce")

    now = time.time()
    loaded = 0

    def _process_group(sym_bare: str, group_df: pd.DataFrame) -> bool:
        ns = f"{sym_bare}.NS"
        key = f"{ns}_raw"
        if key in _df_cache:
            return False
        df = group_df.drop(columns=["symbol"]).reset_index(drop=True)
        if len(df) < 20:
            return False
        df = _add_indicators(df)
        _df_cache[key] = (df, now)
        return True

    # Process in parallel (indicator computation is CPU-bound)
    groups = {sym: grp.copy() for sym, grp in big_df.groupby("symbol")}
    with ThreadPoolExecutor(max_workers=16) as pool:
        futs = {pool.submit(_process_group, sym, grp): sym for sym, grp in groups.items()}
        for fut in as_completed(futs):
            try:
                if fut.result():
                    loaded += 1
            except Exception:
                pass

    total = already + loaded
    logger.info(f"Preload done: {loaded} newly cached, {total} total in cache")
    return total


# ── 1. Technical signals ───────────────────────────────────────────────────────

def compute_technical_signals(symbol: str, df: pd.DataFrame) -> TechnicalSignal:
    last = df.iloc[-1]
    signals: list[IndicatorSignal] = []
    score = 0.0

    def _safe(col: str):
        v = last.get(col, np.nan)
        return float(v) if not (isinstance(v, float) and np.isnan(v)) else np.nan

    # RSI
    rsi = _safe("rsi_14")
    if not np.isnan(rsi):
        if rsi < 30:
            d, s = SignalDirection.BUY, 2.0
        elif rsi > 70:
            d, s = SignalDirection.SELL, -2.0
        else:
            d, s = SignalDirection.HOLD, 0.0
        signals.append(IndicatorSignal(name="RSI", direction=d, score=s, value=round(rsi, 2)))
        score += s

    # MACD
    macd, macd_sig = _safe("macd"), _safe("macd_signal")
    if not np.isnan(macd) and not np.isnan(macd_sig):
        if macd > macd_sig:
            d, s = SignalDirection.BUY, 1.5
        else:
            d, s = SignalDirection.SELL, -1.5
        signals.append(IndicatorSignal(name="MACD", direction=d, score=s, value=round(macd, 4)))
        score += s

    # SMA crossover
    sma20, sma50 = _safe("sma_20"), _safe("sma_50")
    if not np.isnan(sma20) and not np.isnan(sma50):
        if sma20 > sma50:
            d, s = SignalDirection.BUY, 1.0
        else:
            d, s = SignalDirection.SELL, -1.0
        signals.append(IndicatorSignal(name="SMA_Cross", direction=d, score=s, value=round(sma20, 2)))
        score += s

    # Bollinger Bands
    close, bb_upper, bb_lower = _safe("close"), _safe("bb_upper"), _safe("bb_lower")
    if not np.isnan(close) and not np.isnan(bb_upper) and not np.isnan(bb_lower):
        if close < bb_lower:
            d, s = SignalDirection.BUY, 1.5
        elif close > bb_upper:
            d, s = SignalDirection.SELL, -1.5
        else:
            d, s = SignalDirection.HOLD, 0.0
        signals.append(IndicatorSignal(name="BB", direction=d, score=s, value=round(close, 2)))
        score += s

    if score > 0.5:
        direction = SignalDirection.BUY
    elif score < -0.5:
        direction = SignalDirection.SELL
    else:
        direction = SignalDirection.HOLD

    confidence = min(abs(score) / 6.0 * 100, 100)

    return TechnicalSignal(
        symbol=symbol,
        company_name=get_stock_name(symbol),
        sector=get_stock_sector(symbol),
        current_price=round(close, 2) if not np.isnan(close) else 0.0,
        composite_signal=direction,
        composite_score=round(score, 2),
        confidence_score=round(confidence, 1),
        signals=signals,
    )


# ── 2. Risk metrics ────────────────────────────────────────────────────────────

def compute_risk_metrics(
    symbol: str, df: pd.DataFrame, nifty_df: pd.DataFrame
) -> RiskMetrics:
    returns = df["daily_return"].dropna()
    ann_return = float(returns.mean() * 252)
    ann_vol = float(returns.std() * np.sqrt(252))

    sharpe = (ann_return - RISK_FREE_RATE) / ann_vol if ann_vol > 0 else 0.0
    neg_ret = returns[returns < 0]
    down_vol = float(neg_ret.std() * np.sqrt(252)) if len(neg_ret) > 1 else ann_vol
    sortino = (ann_return - RISK_FREE_RATE) / down_vol if down_vol > 0 else 0.0

    cum = (1 + returns).cumprod()
    roll_max = cum.cummax()
    drawdown = (cum - roll_max) / roll_max
    max_dd = float(drawdown.min()) * 100

    var_95 = float(np.percentile(returns, 5)) * 100

    beta, alpha = 1.0, 0.0
    if nifty_df is not None and not nifty_df.empty and "daily_return" in nifty_df.columns:
        stock_s = df.set_index("date")["daily_return"].dropna()
        nifty_s = nifty_df.set_index("date")["daily_return"].dropna()
        common = stock_s.index.intersection(nifty_s.index)
        if len(common) > 30:
            s_vals = stock_s[common].values
            n_vals = nifty_s[common].values
            cov_mat = np.cov(s_vals, n_vals)
            if cov_mat[1, 1] > 0:
                beta = float(cov_mat[0, 1] / cov_mat[1, 1])
            nifty_ann = float(n_vals.mean() * 252)
            alpha = (ann_return - (RISK_FREE_RATE + beta * (nifty_ann - RISK_FREE_RATE))) * 100

    return RiskMetrics(
        symbol=symbol,
        sharpe_ratio=round(sharpe, 3),
        sortino_ratio=round(sortino, 3),
        max_drawdown=round(max_dd, 2),
        var_95=round(var_95, 3),
        beta=round(beta, 3),
        volatility=round(ann_vol * 100, 2),
        alpha=round(alpha, 2),
        annualized_return=round(ann_return * 100, 2),
    )


# ── 3. Random Forest classifier ────────────────────────────────────────────────

_FEATURES = [
    "rsi_14", "macd", "macd_signal", "bb_width", "vol_ratio",
    "price_vs_sma20", "price_vs_sma50", "return_5d", "return_20d", "atr_normalized",
]


def train_rf_classifier(df: pd.DataFrame, symbol: str = "") -> tuple[float, SignalDirection]:
    # Use cached model if available (models are trained once per report build)
    if symbol and symbol in _rf_model_cache:
        clf, cached_prob, cached_sig = _rf_model_cache[symbol]
        # Re-predict with latest features if model exists
        try:
            df_c = df.dropna(subset=_FEATURES + ["close"])
            if len(df_c) >= 1:
                prob_up = float(clf.predict_proba(df_c[_FEATURES].values[-1:, :])[0][1])
                sig = SignalDirection.BUY if prob_up > 0.6 else (SignalDirection.SELL if prob_up < 0.4 else SignalDirection.HOLD)
                return round(prob_up, 3), sig
        except Exception:
            pass
        return cached_prob, cached_sig

    df_c = df.dropna(subset=_FEATURES + ["close"]).copy()
    if len(df_c) < 40:
        return 0.5, SignalDirection.HOLD

    df_c["target"] = (df_c["close"].shift(-5) > df_c["close"]).astype(int)
    df_c = df_c.dropna(subset=["target"])

    X = df_c[_FEATURES].values
    y = df_c["target"].values.astype(int)

    split = int(len(X) * 0.8)
    X_train, y_train = X[:split], y[:split]

    if len(X_train) < 30 or len(set(y_train)) < 2:
        return 0.5, SignalDirection.HOLD

    clf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42, n_jobs=1)
    clf.fit(X_train, y_train)

    prob_up = float(clf.predict_proba(df_c[_FEATURES].values[-1:, :])[0][1])

    if prob_up > 0.6:
        sig = SignalDirection.BUY
    elif prob_up < 0.4:
        sig = SignalDirection.SELL
    else:
        sig = SignalDirection.HOLD

    # Cache the trained model
    if symbol:
        _rf_model_cache[symbol] = (clf, round(prob_up, 3), sig)

    return round(prob_up, 3), sig


# ── 4. Portfolio optimisation ──────────────────────────────────────────────────

def optimize_portfolio(
    symbols: list[str], risk_profile: str = "moderate", n_portfolios: int = 2000
) -> Optional[PortfolioOptimizationResult]:
    series_list: list[pd.Series] = []
    valid: list[str] = []

    for sym in symbols:
        df = _get_cached_df(sym, "2y")
        if df is not None and len(df) > 50:
            s = df.set_index("date")["daily_return"].dropna()
            s.name = sym
            series_list.append(s)
            valid.append(sym)

    if len(valid) < 2:
        return None

    rets_df = pd.concat(series_list, axis=1).dropna()
    n = len(valid)
    mu = rets_df.mean().values * 252          # annualised mean returns
    cov = rets_df.cov().values * 252          # annualised cov matrix

    # Monte Carlo
    mc: list[dict] = []
    for _ in range(n_portfolios):
        w = np.random.dirichlet(np.ones(n))
        r = float(w @ mu)
        v = float(np.sqrt(w @ cov @ w))
        sh = (r - RISK_FREE_RATE) / v if v > 0 else 0.0
        mc.append({"vol": v, "ret": r, "sharpe": sh, "w": w})

    # scipy helpers
    def port_vol(w: np.ndarray) -> float:
        return float(np.sqrt(w @ cov @ w))

    def neg_sharpe(w: np.ndarray) -> float:
        r = float(w @ mu)
        v = port_vol(w)
        return -(r - RISK_FREE_RATE) / v if v > 0 else 0.0

    cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bnds = [(0.0, 1.0)] * n
    w0 = np.ones(n) / n

    res_minv = minimize(port_vol, w0, method="SLSQP", bounds=bnds, constraints=cons)
    res_maxs = minimize(neg_sharpe, w0, method="SLSQP", bounds=bnds, constraints=cons)

    def w_to_dict(w_arr: np.ndarray) -> dict[str, float]:
        return {sym: round(float(w), 4) for sym, w in zip(valid, w_arr)}

    min_var_w = w_to_dict(res_minv.x if res_minv.success else w0)
    max_shr_w = w_to_dict(res_maxs.x if res_maxs.success else w0)

    # Risk-profile weights (minimise distance to target vol)
    target_vols = {"conservative": 0.12, "moderate": 0.18, "aggressive": 0.25}
    tv = target_vols.get(risk_profile, 0.18)

    def vol_dist(w: np.ndarray) -> float:
        return (port_vol(w) - tv) ** 2

    res_rp = minimize(vol_dist, w0, method="SLSQP", bounds=bnds, constraints=cons)
    rp_w = w_to_dict(res_rp.x if res_rp.success else w0)

    # Efficient frontier: 50 vol bins
    all_vols = [p["vol"] for p in mc]
    v_bins = np.linspace(min(all_vols), max(all_vols), 51)
    frontier: list[EfficientFrontierPoint] = []
    for i in range(50):
        bucket = [p for p in mc if v_bins[i] <= p["vol"] < v_bins[i + 1]]
        if bucket:
            best = max(bucket, key=lambda p: p["ret"])
            frontier.append(
                EfficientFrontierPoint(
                    vol=round(best["vol"] * 100, 2),
                    ret=round(best["ret"] * 100, 2),
                    sharpe=round(best["sharpe"], 3),
                )
            )

    # Correlation matrix
    corr = rets_df.corr()
    corr_matrix = [[round(float(corr.iloc[i, j]), 3) for j in range(n)] for i in range(n)]

    def port_stats(wd: dict) -> PortfolioStats:
        w = np.array([wd[s] for s in valid])
        r = float(w @ mu) * 100
        v = port_vol(w) * 100
        sh = (r / 100 - RISK_FREE_RATE) / (v / 100) if v > 0 else 0.0
        return PortfolioStats(expected_return=round(r, 2), volatility=round(v, 2), sharpe=round(sh, 3))

    mc_out = [
        EfficientFrontierPoint(vol=round(p["vol"] * 100, 2), ret=round(p["ret"] * 100, 2), sharpe=round(p["sharpe"], 3))
        for p in mc[:500]  # cap response size
    ]

    return PortfolioOptimizationResult(
        symbols=valid,
        min_variance_weights=min_var_w,
        max_sharpe_weights=max_shr_w,
        risk_profile_weights=rp_w,
        risk_profile=risk_profile,
        efficient_frontier=frontier,
        correlation_matrix=corr_matrix,
        mc_results=mc_out,
        min_variance_stats=port_stats(min_var_w),
        max_sharpe_stats=port_stats(max_shr_w),
        risk_profile_stats=port_stats(rp_w),
    )


# ── 5. Clustering ──────────────────────────────────────────────────────────────

def cluster_stocks(symbols: list[str]) -> ClusteringResult:
    nifty_df = _get_cached_df(NIFTY_INDEX, "1y")
    feat_rows: list[list[float]] = []
    valid: list[str] = []

    for sym in symbols:
        df = _get_cached_df(sym, "1y")
        if df is None or len(df) < 30:
            continue

        rets = df["daily_return"].dropna()
        ann_vol = float(rets.std() * np.sqrt(252))
        mom30 = float((df["close"].iloc[-1] / df["close"].iloc[-30]) - 1)

        beta = 1.0
        if nifty_df is not None and not nifty_df.empty:
            s_s = df.set_index("date")["daily_return"].dropna()
            n_s = nifty_df.set_index("date")["daily_return"].dropna()
            common = s_s.index.intersection(n_s.index)
            if len(common) > 30:
                c = np.cov(s_s[common].values, n_s[common].values)
                if c[1, 1] > 0:
                    beta = float(c[0, 1] / c[1, 1])

        feat_rows.append([ann_vol, mom30, beta])
        valid.append(sym)

    if len(valid) < 4:
        return ClusteringResult(clusters=[])

    X = np.array(feat_rows)
    X_sc = StandardScaler().fit_transform(X)
    km = KMeans(n_clusters=4, random_state=42, n_init=10)
    labels = km.fit_predict(X_sc)

    # Label clusters by centroid volatility (ascending)
    vol_order = np.argsort(km.cluster_centers_[:, 0])
    label_map = {
        vol_order[0]: ClusterLabel.DEFENSIVE,
        vol_order[1]: ClusterLabel.VALUE,
        vol_order[2]: ClusterLabel.MOMENTUM,
        vol_order[3]: ClusterLabel.HIGH_VOLATILITY,
    }

    clusters = [
        StockCluster(
            symbol=valid[i],
            cluster_id=int(labels[i]),
            cluster_label=label_map[int(labels[i])],
            volatility=round(feat_rows[i][0] * 100, 2),
            momentum_30d=round(feat_rows[i][1] * 100, 2),
            beta=round(feat_rows[i][2], 3),
        )
        for i in range(len(valid))
    ]
    return ClusteringResult(clusters=clusters)


# ── 6. Anomaly detection ───────────────────────────────────────────────────────

def detect_anomalies(symbol: str, df: pd.DataFrame) -> list[AnomalyAlert]:
    alerts: list[AnomalyAlert] = []
    if len(df) < 60:
        return alerts

    recent = df.iloc[-60:].copy()
    recent["abs_return"] = recent["daily_return"].abs()

    # Volume z-score
    vol_mean, vol_std = recent["volume"].mean(), recent["volume"].std()
    last_vol = recent["volume"].iloc[-1]
    vol_z = (last_vol - vol_mean) / vol_std if vol_std > 0 else 0.0
    if abs(vol_z) > 2.5:
        sev = AnomalySeverity.HIGH if abs(vol_z) > 3.5 else AnomalySeverity.MEDIUM
        alerts.append(AnomalyAlert(
            symbol=symbol, anomaly_type=AnomalyType.VOLUME_SPIKE, severity=sev,
            z_score=round(float(vol_z), 2),
            description=f"Unusual volume: {abs(vol_z):.1f}σ from 60-day mean",
        ))

    # Return z-score
    ret_mean, ret_std = recent["abs_return"].mean(), recent["abs_return"].std()
    last_ret = recent["abs_return"].iloc[-1]
    ret_z = (last_ret - ret_mean) / ret_std if ret_std > 0 else 0.0
    if abs(ret_z) > 2.5:
        sev = AnomalySeverity.HIGH if abs(ret_z) > 3.5 else AnomalySeverity.MEDIUM
        alerts.append(AnomalyAlert(
            symbol=symbol, anomaly_type=AnomalyType.PRICE_SPIKE, severity=sev,
            z_score=round(float(ret_z), 2),
            description=f"Unusual price move: {abs(ret_z):.1f}σ from 60-day mean",
        ))

    # IsolationForest
    try:
        feat_df = recent[["daily_return", "vol_ratio", "bb_width"]].dropna()
        if len(feat_df) >= 20:
            arr = feat_df.values
            iso = IsolationForest(contamination=0.05, random_state=42)
            preds = iso.fit_predict(arr)
            scores = iso.decision_function(arr)
            for i in range(-5, 0):
                if preds[i] == -1 and scores[i] < -0.15:
                    sev = AnomalySeverity.HIGH if scores[i] < -0.25 else AnomalySeverity.MEDIUM
                    alerts.append(AnomalyAlert(
                        symbol=symbol, anomaly_type=AnomalyType.ISOLATION_FOREST, severity=sev,
                        z_score=round(float(abs(scores[i]) * 10), 2),
                        description=f"IsolationForest anomaly (score={scores[i]:.3f})",
                    ))
                    break
    except Exception as exc:
        logger.debug(f"IsolationForest skipped for {symbol}: {exc}")

    return alerts


# ── 7. Correlation matrix ──────────────────────────────────────────────────────

def compute_correlation_matrix(symbols: list[str]) -> CorrelationMatrix:
    series_list: list[pd.Series] = []
    valid: list[str] = []

    for sym in symbols:
        df = _get_cached_df(sym, "1y")
        if df is not None and len(df) > 50:
            s = df.set_index("date")["daily_return"].dropna()
            s.name = sym
            series_list.append(s)
            valid.append(sym)

    if len(valid) < 2:
        return CorrelationMatrix(symbols=[], matrix=[], high_correlation_pairs=[])

    rets_df = pd.concat(series_list, axis=1).dropna()
    corr = rets_df.corr()
    n = len(valid)
    matrix = [[round(float(corr.iloc[i, j]), 3) for j in range(n)] for i in range(n)]

    pairs = [
        CorrelationPair(symbol1=valid[i], symbol2=valid[j], correlation=round(float(corr.iloc[i, j]), 3))
        for i in range(n)
        for j in range(i + 1, n)
        if abs(float(corr.iloc[i, j])) > 0.8
    ]

    return CorrelationMatrix(symbols=valid, matrix=matrix, high_correlation_pairs=pairs)


# ── 8. Screener ────────────────────────────────────────────────────────────────

def screen_stocks(
    sector: Optional[str] = None,
    signal: Optional[str] = None,
    min_sharpe: Optional[float] = None,
    max_drawdown_threshold: Optional[float] = None,
    sort_by: str = "composite_score",
    limit: int = 30,
) -> ScreenerResponse:
    stocks: list[ScreenerStock] = []

    # Fast path: use pre-computed analysis cache from report build
    use_cache = bool(_analysis_cache) and time.time() - _analysis_cache_ts < REPORT_TTL

    if use_cache:
        for sym, cached in _analysis_cache.items():
            try:
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
                logger.warning(f"Screener (cached) failed for {sym}: {exc}")
    else:
        # Slow path: compute from scratch (only on first load before report is built)
        _nifty = _get_cached_df(NIFTY_INDEX, "1y")
        nifty_df = _nifty if _nifty is not None else pd.DataFrame()

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
                logger.warning(f"Screener failed for {sym}: {exc}")

    # Sort — most fields descending, volatility/drawdown ascending
    reverse = sort_by not in ["max_drawdown", "volatility"]
    stocks.sort(key=lambda s: getattr(s, sort_by, 0), reverse=reverse)
    stocks = stocks[:limit]

    buy = sum(1 for s in stocks if s.composite_signal == SignalDirection.BUY)
    sell = sum(1 for s in stocks if s.composite_signal == SignalDirection.SELL)
    return ScreenerResponse(stocks=stocks, total=len(stocks), buy_count=buy, sell_count=sell, hold_count=len(stocks) - buy - sell)


# ── 9. Backtest ────────────────────────────────────────────────────────────────

def backtest_strategy(symbol: str) -> BacktestResult:
    df = _get_cached_df(symbol, "2y")
    nifty_df = _get_cached_df(NIFTY_INDEX, "2y")

    if df is None or len(df) < 100:
        return BacktestResult(
            symbol=symbol, equity_curve=[], total_return=0.0,
            benchmark_return=0.0, alpha=0.0, sharpe_ratio=0.0, num_trades=0, win_rate=0.0,
        )

    df = df.copy()

    # Compute composite score per row (vectorised approximation)
    rsi = df["rsi_14"].fillna(50)
    macd = df["macd"].fillna(0)
    macd_sig = df["macd_signal"].fillna(0)
    sma20 = df["sma_20"].fillna(df["close"])
    sma50 = df["sma_50"].fillna(df["close"])
    close = df["close"]
    bb_upper = df["bb_upper"].fillna(close * 1.1)
    bb_lower = df["bb_lower"].fillna(close * 0.9)

    score = (
        np.where(rsi < 30, 2.0, np.where(rsi > 70, -2.0, 0.0))
        + np.where(macd > macd_sig, 1.5, -1.5)
        + np.where(sma20 > sma50, 1.0, -1.0)
        + np.where(close < bb_lower, 1.5, np.where(close > bb_upper, -1.5, 0.0))
    )

    df["composite_score"] = score
    df["position"] = (score > 0.5).astype(float)
    df["position_lag"] = df["position"].shift(1).fillna(0)
    df["strategy_return"] = df["position_lag"] * df["daily_return"]

    clean = df.dropna(subset=["strategy_return", "daily_return"]).copy()
    if len(clean) < 20:
        return BacktestResult(
            symbol=symbol, equity_curve=[], total_return=0.0,
            benchmark_return=0.0, alpha=0.0, sharpe_ratio=0.0, num_trades=0, win_rate=0.0,
        )

    strat_eq = (1 + clean["strategy_return"]).cumprod()
    bench_eq = (1 + clean["daily_return"]).cumprod()

    # Align benchmark to Nifty if available
    if nifty_df is not None and not nifty_df.empty:
        nifty_s = nifty_df.set_index("date")["daily_return"].dropna()
        aligned = nifty_s.reindex(clean["date"].values).fillna(0)
        bench_eq = (1 + aligned.values).cumprod()

    # Normalise to start at 100
    strat_eq = strat_eq / strat_eq.iloc[0] * 100
    bench_eq_vals = (bench_eq / bench_eq[0] * 100) if hasattr(bench_eq, "iloc") else (bench_eq / bench_eq[0] * 100)

    total_return = float(strat_eq.iloc[-1] - 100)
    bench_return = float(bench_eq_vals[-1] - 100) if not hasattr(bench_eq_vals, "iloc") else float(bench_eq_vals.iloc[-1] - 100)

    strat_ann_ret = float(clean["strategy_return"].mean() * 252)
    strat_ann_vol = float(clean["strategy_return"].std() * np.sqrt(252))
    sharpe = (strat_ann_ret - RISK_FREE_RATE) / strat_ann_vol if strat_ann_vol > 0 else 0.0

    bench_ann_ret = float(clean["daily_return"].mean() * 252)
    alpha = (strat_ann_ret - bench_ann_ret) * 100

    num_trades = int(clean["position_lag"].diff().abs().sum())
    active = clean["strategy_return"] != 0
    win_rate = float((clean.loc[active, "strategy_return"] > 0).mean() * 100) if active.any() else 0.0

    # Equity curve (every 5 days)
    dates = clean["date"].values
    bench_arr = bench_eq_vals if not hasattr(bench_eq_vals, "values") else bench_eq_vals.values
    strat_arr = strat_eq.values

    equity_curve = [
        EquityPoint(
            date=str(dates[i])[:10],
            strategy=round(float(strat_arr[i]), 2),
            benchmark=round(float(bench_arr[i]), 2),
        )
        for i in range(0, len(clean), 5)
    ]

    return BacktestResult(
        symbol=symbol,
        equity_curve=equity_curve,
        total_return=round(total_return, 2),
        benchmark_return=round(bench_return, 2),
        alpha=round(alpha, 2),
        sharpe_ratio=round(sharpe, 3),
        num_trades=num_trades,
        win_rate=round(win_rate, 1),
    )


# ── 10. Full analytics report ──────────────────────────────────────────────────

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
        # Cache per-stock analysis for fast access by screener / smart portfolio
        _analysis_cache[symbol] = result
        return result
    except Exception as exc:
        logger.warning(f"Worker failed for {symbol}: {exc}")
        return None


def get_analytics_report(force_refresh: bool = False) -> AnalyticsReport:
    global _report_cache
    cached, ts = _report_cache
    if not force_refresh and cached is not None and time.time() - ts < REPORT_TTL:
        return cached

    logger.info("Building full analytics report for %d stocks…", len(get_stock_universe()))
    _nifty = _get_cached_df(NIFTY_INDEX, "1y")
    nifty_df = _nifty if _nifty is not None else pd.DataFrame()

    results: dict[str, dict] = {}
    universe = get_stock_universe()
    with ThreadPoolExecutor(max_workers=20) as pool:
        fmap = {pool.submit(_analyze_stock_worker, sym, nifty_df): sym for sym in universe}
        for fut in as_completed(fmap):
            sym = fmap[fut]
            try:
                res = fut.result()
                if res:
                    results[sym] = res
            except Exception as exc:
                logger.warning(f"Report worker error for {sym}: {exc}")

    # Market breadth
    buy_count = sum(1 for r in results.values() if r["signals"].composite_signal == SignalDirection.BUY)
    sell_count = sum(1 for r in results.values() if r["signals"].composite_signal == SignalDirection.SELL)
    hold_count = len(results) - buy_count - sell_count

    # Sector heatmap
    sector_data: dict[str, list[float]] = {}
    for r in results.values():
        sec = get_stock_sector(r["symbol"])
        sector_data.setdefault(sec, []).append(r["daily_change_pct"])
    sector_heatmap = [
        SectorHeatmapItem(sector=s, avg_change_pct=round(sum(v) / len(v), 2), stock_count=len(v))
        for s, v in sector_data.items()
    ]

    # Top gainers / losers
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

    _report_cache = (report, time.time())
    global _analysis_cache_ts
    _analysis_cache_ts = time.time()
    logger.info("Analytics report built: %d stocks, %d BUY, %d SELL, %d models cached",
                len(results), buy_count, sell_count, len(_rf_model_cache))
    return report


def get_market_overview() -> MarketOverview:
    """
    Fast market overview — uses cached report or analysis cache.
    """
    cached, ts = _report_cache
    if cached is not None and time.time() - ts < REPORT_TTL:
        return cached.market_overview

    # Use analysis cache if available (faster than recomputing)
    if _analysis_cache and time.time() - _analysis_cache_ts < REPORT_TTL:
        quick_results = list(_analysis_cache.values())
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
    top_gainers = [TrendingStock(symbol=r["symbol"], company_name=get_stock_name(r["symbol"]), change_pct=round(r.get("daily_change_pct", 0.0), 2)) for r in by_chg[:5]]
    top_losers = [TrendingStock(symbol=r["symbol"], company_name=get_stock_name(r["symbol"]), change_pct=round(r.get("daily_change_pct", 0.0), 2)) for r in by_chg[-5:]]

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


# ── 12. Time-series forecasting ──────────────────────────────────────────────

def forecast_stock(symbol: str, horizon: int = 30) -> Optional[StockForecast]:
    """
    30-day price forecast using exponential smoothing + linear trend.
    Returns ForecastPoints with confidence bands.
    """
    df = _get_cached_df(symbol, "2y")
    if df is None or len(df) < 120:
        return None

    close = df["close"].values.astype(float)
    dates = pd.to_datetime(df["date"].values)

    # --- Exponential smoothing (Holt's linear trend) ---
    alpha, beta_hl = 0.3, 0.1
    level = close[0]
    trend = 0.0
    for p in close[1:]:
        prev_level = level
        level = alpha * p + (1 - alpha) * (level + trend)
        trend = beta_hl * (level - prev_level) + (1 - beta_hl) * trend

    # Generate forecast
    forecast_prices: list[float] = []
    for h in range(1, horizon + 1):
        forecast_prices.append(level + trend * h)

    # Confidence bands based on recent residual volatility
    fitted = []
    l, t = close[0], 0.0
    for p in close[1:]:
        prev_l = l
        l = alpha * p + (1 - alpha) * (l + t)
        t = beta_hl * (l - prev_l) + (1 - beta_hl) * t
        fitted.append(l)
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

    # Trend classification
    if predicted_return > 3:
        trend_label = "BULLISH"
    elif predicted_return < -3:
        trend_label = "BEARISH"
    else:
        trend_label = "NEUTRAL"

    # Confidence: based on R² of recent trend + volatility
    recent_60 = close[-60:]
    x_idx = np.arange(len(recent_60))
    corr_coef = np.corrcoef(x_idx, recent_60)[0, 1]
    r_squared = corr_coef ** 2
    vol_30 = float(np.std(np.diff(np.log(close[-30:]))) * np.sqrt(252) * 100)
    confidence = min(95, max(15, r_squared * 80 + (1 - min(vol_30, 60) / 60) * 20))

    # Support / resistance from recent 90 days
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


# ── 13. Smart portfolio builder ──────────────────────────────────────────────

def build_smart_portfolio(
    risk_profile: str = "moderate",
    top_n: int = 15,
    n_portfolios: int = 2000,
) -> SmartPortfolioResponse:
    """
    Auto-select the best stocks, optimise the portfolio, then forecast each pick.
    Selection uses the cached analytics report (signals + risk + RF scores).
    """
    report = get_analytics_report(force_refresh=False)
    analyses = report.stock_analyses

    # ── Score each stock for selection ──
    scored: list[tuple[float, StockAnalysis, str]] = []
    for a in analyses:
        # Composite selection score
        sig_score = a.technical_signals.composite_score  # -6 to +6
        conf = a.technical_signals.confidence_score / 100  # 0-1
        sharpe = a.risk_metrics.sharpe_ratio
        rf_prob = a.rf_probability  # 0-1, higher = more bullish
        vol = a.risk_metrics.volatility / 100  # annualised as decimal

        # Risk-adjusted selection score
        selection = (
            sig_score * 2.0
            + conf * 3.0
            + sharpe * 2.0
            + (rf_prob - 0.5) * 6.0  # center on 0, scale up
            - vol * 3.0  # penalise high vol
        )

        # Risk profile adjustments
        if risk_profile == "conservative":
            selection += (1 - vol) * 2  # reward low vol
            selection += min(sharpe, 2) * 1.5  # extra reward for good risk-adjusted returns
            reason = f"Sharpe {sharpe:.2f}, Vol {a.risk_metrics.volatility:.1f}%, Signal {a.technical_signals.composite_signal.value}"
        elif risk_profile == "aggressive":
            selection += sig_score * 1.5  # extra weight on momentum signals
            selection += rf_prob * 3  # extra weight on ML bullish probability
            reason = f"RF prob {rf_prob:.0%} up, Signal {sig_score:+.1f}, Confidence {conf:.0%}"
        else:
            reason = f"Score {sig_score:+.1f}, Sharpe {sharpe:.2f}, RF {rf_prob:.0%} bullish"

        scored.append((selection, a, reason))

    # Sort descending and pick top_n, ensuring sector diversity
    scored.sort(key=lambda x: x[0], reverse=True)
    selected: list[StockAnalysis] = []
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

    # ── Optimise portfolio ──
    opt_result = optimize_portfolio(symbols, risk_profile, n_portfolios)
    if opt_result is None:
        # Fallback: equal weight
        from ..schemas.analytics import PortfolioOptimizationResult, PortfolioStats, EfficientFrontierPoint
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

    # ── Forecast each selected stock ──
    forecasts: list[StockForecast] = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        fmap = {pool.submit(forecast_stock, sym): sym for sym in symbols}
        for fut in as_completed(fmap):
            try:
                fc = fut.result()
                if fc is not None:
                    forecasts.append(fc)
            except Exception as exc:
                logger.warning(f"Forecast failed for {fmap[fut]}: {exc}")

    # Sort forecasts to match symbols order
    fc_map = {f.symbol: f for f in forecasts}
    forecasts = [fc_map[s] for s in symbols if s in fc_map]

    # ── Aggregate portfolio-level metrics ──
    weights = opt_result.risk_profile_weights
    total_weight = sum(weights.get(s, 0) for s in symbols if s in fc_map)

    portfolio_return = 0.0
    portfolio_risk = 0.0
    for fc in forecasts:
        w = weights.get(fc.symbol, 0)
        if total_weight > 0:
            w_norm = w / total_weight
        else:
            w_norm = 1.0 / len(forecasts)
        portfolio_return += fc.predicted_return_pct * w_norm
        portfolio_risk += fc.volatility_30d * w_norm

    # Risk score: 0-100 (higher = riskier)
    risk_score = min(100, max(0, portfolio_risk * 1.5))

    return SmartPortfolioResponse(
        selected_symbols=symbols,
        selection_reasoning=reasons,
        optimization=opt_result,
        forecasts=forecasts,
        portfolio_predicted_return=round(portfolio_return, 2),
        portfolio_risk_score=round(risk_score, 1),
    )
