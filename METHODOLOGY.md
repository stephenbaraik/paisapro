# PaisaPro.ai — Methodology

## 1. Introduction

PaisaPro.ai is an AI-powered investment advisory platform designed for Indian retail investors. It combines quantitative finance models, machine learning algorithms, and large language models to provide data-driven investment insights on NSE-listed stocks. This document details the methodology behind every analytical component of the system.

---

## 2. System Architecture

### 2.1 High-Level Design

The platform follows a three-tier architecture:

| Layer | Technology | Deployment |
|-------|-----------|------------|
| **Frontend** | React 19, TypeScript, Vite, TailwindCSS | Netlify CDN |
| **Backend** | FastAPI (Python 3.12), 12 specialized services | HuggingFace Spaces (Docker) |
| **Database** | PostgreSQL (Supabase managed) | Supabase Cloud |

### 2.2 Service-Oriented Backend

The backend is decomposed into 12 independent services, each responsible for a specific analytical domain:

- **Analytics** — Technical indicators, composite signals, anomaly detection, clustering
- **Time-Series** — ARIMA, Exponential Smoothing, seasonal decomposition
- **Volatility** — GARCH forecasting, volatility cones, regime classification
- **Risk Factors** — Fama-French 4-factor model decomposition
- **Sector Rotation** — Multi-horizon momentum analysis, market phase detection
- **Macro** — Macroeconomic indicator tracking and regime classification
- **AI Advisor** — LLM-powered conversational investment guidance
- **AI Portfolio** — LLM-driven portfolio construction
- **Portfolio** — Holdings management, watchlists, P&L tracking
- **Monte Carlo** — Probabilistic wealth projection simulations
- **Financial Engine** — SIP calculations, goal planning, asset allocation
- **News Sentiment** — Keyword-based sentiment scoring from news feeds

---

## 3. Data Acquisition & Pipeline

### 3.1 Data Sources

| Source | Data Provided | Frequency | Method |
|--------|--------------|-----------|--------|
| **yfinance** | Daily OHLCV for 500+ NSE stocks | Daily | Batch API (`yf.download`) |
| **yfinance (Macro)** | Nifty 50, Bank Nifty, India VIX, USD/INR, Gold, Crude Oil | Daily | Batch API |
| **Google News RSS** | Headlines for 25+ major Indian stocks | On-demand | RSS feed parsing |
| **NSE India** | Index constituents (Nifty 50, Nifty Next 50, etc.) | Static | Web scraping |

### 3.2 Stock Universe

The stock universe consists of 500+ NSE-listed equities sourced from major indices: Nifty 50, Nifty Next 50, Nifty Midcap 150, and Nifty Smallcap 250. Symbols are automatically suffixed with `.NS` for yfinance compatibility.

### 3.3 Ingestion Pipeline

```
Daily Scheduler (6:00 PM IST / 12:30 UTC, weekdays only)
│
├── Phase 1: Cache Invalidation
│   └── Clear in-memory caches (_df_cache, _report_cache)
│
├── Phase 2: Stock Price Ingestion
│   ├── Fetch latest OHLCV for all 500+ symbols via yfinance batch API
│   ├── Use ThreadPoolExecutor for concurrent downloads
│   └── Upsert into Supabase `stock_prices` table (ON CONFLICT symbol+date)
│
├── Phase 3: Technical Indicator Calculation
│   ├── Compute SMA (20, 50, 200), EMA (12, 26)
│   ├── Compute MACD, RSI (14), Bollinger Bands (20, 2σ)
│   ├── Compute ATR (14), VWAP, OBV
│   └── Store indicators alongside price data in `stock_prices`
│
├── Phase 4: Macro Data Ingestion
│   ├── Fetch ^NSEI, ^NSEBANK, ^INDIAVIX, INR=X, GC=F, CL=F
│   └── Upsert into Supabase `macro_prices` table
│
├── Phase 5: Report Pre-Warming
│   └── Rebuild full analytics report (ML models + signals)
│
└── Phase 6: Audit Logging
    └── Write run metadata to `pipeline_logs` table
```

### 3.4 Caching Strategy

Multi-level caching minimizes latency and API load:

| Cache Layer | TTL | Purpose |
|-------------|-----|---------|
| Stock DataFrames | 24 hours | Raw OHLCV data reuse across services |
| Analytics Report | 2 hours | Full ML pipeline output |
| Time-Series Models | 2 hours | ARIMA/ETS parameters |
| GARCH Forecasts | 1 hour | Volatility shifts faster than price trends |
| Sector Rotation | 1 hour | Momentum recalculation |
| Risk Factor Models | 1 hour | Factor exposure stability |
| Macro Indicators | 30 minutes | Intraday regime sensitivity |
| News Sentiment | 30 minutes | Headline freshness |

---

## 4. Technical Analysis

### 4.1 Indicator Suite

All technical indicators are computed from daily OHLCV data using a 1-year lookback window.

#### Simple Moving Averages (SMA)
$$SMA_n = \frac{1}{n} \sum_{i=0}^{n-1} C_{t-i}$$

Periods: 20 (short-term trend), 50 (medium-term), 200 (long-term). Crossovers between SMA-50 and SMA-200 generate golden cross / death cross signals.

#### Exponential Moving Averages (EMA)
$$EMA_t = \alpha \cdot C_t + (1 - \alpha) \cdot EMA_{t-1}, \quad \alpha = \frac{2}{n+1}$$

Periods: 12 and 26, used as inputs to the MACD calculation.

#### MACD (Moving Average Convergence Divergence)
$$MACD = EMA_{12} - EMA_{26}$$
$$Signal = EMA_9(MACD)$$
$$Histogram = MACD - Signal$$

**Signal Logic:** MACD above signal line → bullish; below → bearish. Histogram divergence indicates momentum acceleration.

#### RSI (Relative Strength Index)
$$RSI = 100 - \frac{100}{1 + RS}, \quad RS = \frac{\text{Avg Gain}_{14}}{\text{Avg Loss}_{14}}$$

**Signal Logic:** RSI < 30 → oversold (BUY); RSI > 70 → overbought (SELL); 30–70 → neutral (HOLD).

#### Bollinger Bands
$$\text{Upper} = SMA_{20} + 2\sigma_{20}$$
$$\text{Lower} = SMA_{20} - 2\sigma_{20}$$
$$\text{Width} = \frac{\text{Upper} - \text{Lower}}{SMA_{20}}$$

**Signal Logic:** Price below lower band → oversold; above upper band → overbought. Band squeeze (narrowing width) indicates impending volatility expansion.

#### ATR (Average True Range)
$$TR = \max(H_t - L_t, |H_t - C_{t-1}|, |L_t - C_{t-1}|)$$
$$ATR_{14} = EMA_{14}(TR)$$

Used to assess current volatility relative to historical norms. High ATR relative to price → elevated risk.

#### VWAP (Volume-Weighted Average Price)
$$VWAP = \frac{\sum (Price_i \times Volume_i)}{\sum Volume_i}$$

Calculated on the most recent trading session. Price above VWAP → bullish intraday bias.

#### OBV (On-Balance Volume)
$$OBV_t = OBV_{t-1} + \begin{cases} V_t & \text{if } C_t > C_{t-1} \\ -V_t & \text{if } C_t < C_{t-1} \\ 0 & \text{otherwise} \end{cases}$$

Measures buying/selling pressure through cumulative volume flow. Rising OBV with rising price confirms trend strength.

### 4.2 Composite Signal Generation

Individual indicator signals are combined into a single BUY/HOLD/SELL classification using a weighted ensemble:

| Indicator | Weight | Signal Mapping |
|-----------|--------|----------------|
| RSI | 25% | <30 → BUY, >70 → SELL, else HOLD |
| MACD | 20% | Above signal → BUY, below → SELL |
| Bollinger Bands | 20% | Below lower → BUY, above upper → SELL |
| ATR | 15% | Low relative ATR → BUY, high → SELL |
| ADX | 10% | >25 with +DI > -DI → BUY, else bearish |
| VWAP | 5% | Price > VWAP → BUY, < VWAP → SELL |
| OBV | 5% | Rising → BUY, falling → SELL |

Each indicator contributes a directional vote (+1 for BUY, 0 for HOLD, -1 for SELL), scaled by its weight. The weighted sum determines the composite signal:

- **Score > +0.3** → BUY
- **Score < -0.3** → SELL
- **Otherwise** → HOLD

**Confidence Score** = percentage of indicators agreeing with the composite direction (0–100%).

---

## 5. Machine Learning Models

### 5.1 Random Forest Classifier — Directional Prediction

**Objective:** Predict whether a stock's price will be higher or lower in 5 trading days.

**Feature Engineering:**
| Feature | Description |
|---------|-------------|
| `rsi_14` | 14-day Relative Strength Index |
| `macd` | MACD line value |
| `bb_width` | Bollinger Band width (normalized) |
| `atr_14` | 14-day Average True Range |
| `vol_ratio` | Volume / 20-day volume SMA |
| `daily_return_pct` | Most recent daily return |

**Training Configuration:**
- Training window: 252 trading days (1 year)
- Target: Binary (1 if price 5 days ahead > current price, else 0)
- Estimators: 100 decision trees
- Split: 80/20 train/test
- Library: scikit-learn `RandomForestClassifier`

**Output:** Probability of upward movement (0.0–1.0) and direction label (BUY if >0.5, SELL otherwise).

### 5.2 Isolation Forest — Anomaly Detection

**Objective:** Detect unusual price movements and volume spikes that may indicate significant market events.

**Features:**
- Absolute daily return percentage
- Volume ratio (current vs 20-day average)

**Configuration:**
- Contamination: auto (algorithm determines outlier threshold)
- Library: scikit-learn `IsolationForest`

**Supplementary Rules:**
- **Price Spike:** |daily return| > 2 standard deviations from mean
- **Volume Spike:** Volume > 3× the 20-day average

Anomalies flagged by either the model or the rules are surfaced in the market overview dashboard.

### 5.3 K-Means Clustering — Stock Segmentation

**Objective:** Group stocks into behaviorally similar clusters for portfolio diversification insights.

**Features (per stock):**
| Feature | Calculation |
|---------|-------------|
| Annualized Volatility | std(daily returns) × √252 |
| Momentum | Cumulative return over trailing 3 months |
| Beta | Covariance with Nifty 50 / Variance of Nifty 50 |

**Configuration:**
- Clusters: k = 4
- Feature scaling: StandardScaler (zero mean, unit variance)
- Library: scikit-learn `KMeans`

**Cluster Labels (assigned heuristically):**

| Cluster | Characteristics |
|---------|----------------|
| **Defensive** | Low volatility, low beta, modest momentum |
| **Value** | Moderate volatility, near-market beta, mixed momentum |
| **Momentum** | High recent returns, moderate-to-high volatility |
| **High-Volatility** | Highest volatility and beta, unstable returns |

---

## 6. Time-Series Forecasting

### 6.1 Stationarity Testing

Before fitting ARIMA models, the series is tested for stationarity:

1. **ADF Test (Augmented Dickey-Fuller):** Null hypothesis = unit root present. If p-value > 0.05, the series is non-stationary.
2. **KPSS Test:** Null hypothesis = series is stationary. Used as counter-validation.
3. **Auto-Differencing:** If ADF fails, apply first differencing (d=1). If still non-stationary, apply second differencing (d=2). Maximum d=2.

### 6.2 ARIMA (AutoRegressive Integrated Moving Average)

$$\phi(B)(1-B)^d X_t = \theta(B)\epsilon_t$$

Where:
- $\phi(B)$ = autoregressive polynomial of order $p$
- $(1-B)^d$ = differencing operator
- $\theta(B)$ = moving average polynomial of order $q$
- $\epsilon_t$ = white noise

**Parameter Selection:**
- Grid search over p ∈ {0, 1, 2, 3}, d ∈ {0, 1, 2}, q ∈ {0, 1, 2, 3}
- Selection criterion: Akaike Information Criterion (AIC) — lower is better
- Fitting library: `statsmodels.tsa.arima.model.ARIMA`

**Forecast Horizon:** 30 trading days with 95% confidence intervals.

### 6.3 Holt-Winters Exponential Smoothing (ETS)

$$\hat{y}_{t+h} = l_t + \phi_h b_t$$

Where:
- $l_t$ = level (smoothed value)
- $b_t$ = trend (slope)
- $\phi$ = damping parameter (0 < φ < 1)

**Configuration:**
- Trend: additive with damping
- Seasonal: none (daily stock data lacks strong seasonality)
- Optimization: scipy minimize (MSE objective)
- Library: `statsmodels.tsa.holtwinters.ExponentialSmoothing`

Provides an alternative forecast alongside ARIMA for model comparison and ensemble potential.

### 6.4 Seasonal Decomposition

$$X_t = T_t + S_t + R_t$$

Additive decomposition using STL (Seasonal and Trend decomposition using LOESS):
- **Trend ($T_t$):** Long-term direction, extracted via LOESS smoothing
- **Seasonal ($S_t$):** Repeating patterns (period = 5 trading days / weekly)
- **Residual ($R_t$):** Remaining noise after removing trend and seasonality

Used for visual analysis rather than direct forecasting.

---

## 7. Volatility Modeling

### 7.1 GARCH(1,1) — Generalized Autoregressive Conditional Heteroskedasticity

**Objective:** Model and forecast time-varying volatility (volatility clustering).

**Mean Equation:**
$$r_t = \mu + \epsilon_t, \quad \epsilon_t = \sigma_t z_t, \quad z_t \sim N(0,1)$$

**Variance Equation:**
$$\sigma_t^2 = \omega + \alpha \epsilon_{t-1}^2 + \beta \sigma_{t-1}^2$$

**Constraints:**
- $\omega > 0$, $\alpha \geq 0$, $\beta \geq 0$
- $\alpha + \beta < 1$ (stationarity)

**Configuration:**
- Distribution: Normal
- Input: Daily log returns (scaled by 100 for numerical stability)
- Fitting library: `arch` package
- Forecast horizon: 30 trading days

**Output:**
- Annualized volatility forecast (daily σ × √252)
- Conditional variance path over forecast horizon

### 7.2 Volatility Cone

Realized volatility is computed across multiple lookback windows to construct a volatility cone:

| Window | Purpose |
|--------|---------|
| 10 days | Very short-term |
| 21 days | 1 month |
| 63 days | 3 months |
| 126 days | 6 months |
| 252 days | 1 year |

For each window, the percentile distribution (min, 25th, 50th, 75th, max) of rolling realized volatility is computed. The current realized volatility is plotted against the cone to assess whether current conditions are historically elevated or depressed.

### 7.3 Volatility Regime Classification

Current annualized volatility is classified into regimes based on percentile thresholds:

| Regime | Condition |
|--------|-----------|
| **LOW** | Volatility < 25th percentile of 1-year history |
| **NORMAL** | 25th ≤ Volatility < 75th percentile |
| **HIGH** | 75th ≤ Volatility < 95th percentile |
| **EXTREME** | Volatility ≥ 95th percentile |

---

## 8. Risk Analytics

### 8.1 Risk Metrics Suite

For each stock, the following risk metrics are computed from 1-year daily return data:

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **Annualized Volatility** | $\sigma_{daily} \times \sqrt{252}$ | Total risk |
| **Sharpe Ratio** | $(R_p - R_f) / \sigma_p$, $R_f = 6\%$ | Risk-adjusted return |
| **Sortino Ratio** | $(R_p - R_f) / \sigma_{downside}$ | Downside risk-adjusted return |
| **Max Drawdown** | $\max\left(\frac{Peak - Trough}{Peak}\right)$ | Worst peak-to-trough decline |
| **Value at Risk (95%)** | 5th percentile of daily returns | Maximum expected daily loss |
| **Beta** | $\frac{Cov(R_i, R_m)}{Var(R_m)}$ | Systematic risk vs Nifty 50 |
| **Alpha (Jensen's)** | $R_i - [R_f + \beta(R_m - R_f)]$ | Excess return vs CAPM |

Risk-free rate is assumed at 6% annualized (approximate Indian government bond yield).

### 8.2 Fama-French 4-Factor Model

**Objective:** Decompose stock returns into systematic risk factors to identify true alpha.

$$R_i - R_f = \alpha + \beta_1(R_m - R_f) + \beta_2 \cdot SMB + \beta_3 \cdot HML + \beta_4 \cdot MOM + \epsilon$$

| Factor | Proxy Construction |
|--------|-------------------|
| **Market (Rm - Rf)** | Nifty 50 excess returns over risk-free rate |
| **SMB (Small Minus Big)** | Return of small-cap stocks minus large-cap stocks (from portfolio universe) |
| **HML (High Minus Low)** | Return of high-P/E stocks minus low-P/E stocks (value proxy) |
| **MOM (Momentum)** | Return of top-momentum stocks minus bottom-momentum stocks |

**Estimation:**
- Method: OLS regression (`numpy.linalg.lstsq`)
- Window: 252 trading days
- Output: Alpha (annualized), factor betas, t-statistics, p-values, R-squared

**Interpretation:**
- Statistically significant positive alpha → genuine stock-picking skill or mispricing
- High market beta → stock amplifies market moves
- Positive SMB beta → behaves like small-cap stock
- Positive HML beta → behaves like value stock
- Positive MOM beta → exhibits momentum characteristics

---

## 9. Portfolio Optimization

### 9.1 Markowitz Mean-Variance Optimization (MVO)

**Objective:** Find the portfolio allocation that maximizes return for a given level of risk (or minimizes risk for a given return).

**Mathematical Framework:**

Given $n$ assets with expected return vector $\mu$ and covariance matrix $\Sigma$:

$$\min_w \quad w^T \Sigma w$$
$$\text{s.t.} \quad w^T \mu = \mu_{\text{target}}, \quad \sum w_i = 1, \quad w_i \geq 0$$

**Implementation:**

1. **Expected Returns:** Annualized mean of daily historical returns
2. **Covariance Matrix:** Sample covariance of daily returns, annualized (×252)
3. **Efficient Frontier:** 2,000 random portfolio simulations + scipy constrained optimization
4. **Key Portfolios:**
   - **Minimum Variance:** Lowest possible volatility
   - **Maximum Sharpe:** Highest risk-adjusted return (tangency portfolio)
   - **Risk-Profile Allocation:** Target volatility based on user's risk profile

**Constraints:**
- Long-only (no short selling): $w_i \geq 0$
- Fully invested: $\sum w_i = 1$
- Per-stock maximum: $w_i \leq 0.4$ (40% concentration limit)

**Solver:** `scipy.optimize.minimize` with SLSQP method.

### 9.2 Correlation Analysis

Pearson correlation coefficients are computed for all stock pairs in a portfolio:

$$\rho_{i,j} = \frac{Cov(R_i, R_j)}{\sigma_i \sigma_j}$$

High-correlation pairs ($|\rho| > 0.7$) are flagged as diversification risks. The correlation matrix is visualized as a heatmap for portfolio construction decisions.

---

## 10. Wealth Planning & Monte Carlo Simulation

### 10.1 Forward Planner — Monte Carlo Engine

**Objective:** Project future wealth given a monthly SIP (Systematic Investment Plan) amount, investment horizon, and risk profile.

**Simulation Parameters:**

| Parameter | Source |
|-----------|--------|
| Expected annual return ($\mu$) | Risk-profile-based (Conservative: 9%, Moderate: 12%, Aggressive: 15%) |
| Annual standard deviation ($\sigma$) | Risk-profile-based (Conservative: 4%, Moderate: 8%, Aggressive: 14%) |
| Monthly SIP amount | User input |
| Annual SIP step-up | User input (default 10%) |
| Investment horizon | User input (years) |
| Number of simulations | 1,000 |

**Simulation Algorithm:**

For each simulation $s = 1, \ldots, 1000$ and each month $t$:

$$R_t^{(s)} \sim N\left(\frac{\mu}{12}, \frac{\sigma}{\sqrt{12}}\right)$$

$$W_t^{(s)} = W_{t-1}^{(s)} \times (1 + R_t^{(s)}) + SIP_t$$

Where $SIP_t$ increases annually by the step-up percentage.

**Output:**
- Percentile wealth trajectories: P10 (pessimistic), P25, P50 (median), P75, P90 (optimistic)
- Probability of achieving target amount
- Year-by-year statistics (mean, std, min, max)
- Probability of loss (% of simulations ending below total invested)

### 10.2 Goal Planner — Reverse Solver

**Objective:** Given a target wealth amount and horizon, calculate the required monthly SIP.

**Method:** Binary search over SIP amounts, running Monte Carlo at each step, until the median (P50) outcome converges to the target within 1% tolerance.

**Output:**
- Required monthly SIP
- Sensitivity analysis: how SIP changes with ±1-2% return variation
- Probability distribution of outcomes at the solved SIP level

### 10.3 Asset Allocation

Risk-profile-based recommended asset allocation:

| Asset Class | Conservative | Moderate | Aggressive |
|-------------|-------------|----------|------------|
| Large Cap Equity | 20% | 40% | 40% |
| Mid Cap Equity | 0% | 15% | 25% |
| Small Cap Equity | 0% | 0% | 20% |
| Debt / Fixed Income | 50% | 30% | 10% |
| Gold | 15% | 10% | 5% |
| Liquid / Cash | 15% | 5% | 0% |

**Expected Return Assumptions:**
- Conservative: 9% ± 4% annual
- Moderate: 12% ± 8% annual
- Aggressive: 15% ± 14% annual

These are calibrated to long-term Indian market performance (Nifty 50 ~12% CAGR, mid/small cap ~15-18% with higher variance).

---

## 11. Sector Rotation Analysis

### 11.1 Multi-Horizon Momentum

Sector momentum is computed across four time horizons:

| Horizon | Window | Weight in Composite |
|---------|--------|-------------------|
| 1 Month | 21 trading days | 10% |
| 3 Months | 63 trading days | 20% |
| 6 Months | 126 trading days | 30% |
| 12 Months | 252 trading days | 40% |

Momentum for each sector = average return of constituent stocks over each window. The composite momentum score weights longer horizons more heavily (consistent with academic momentum factor literature).

### 11.2 Market Phase Detection

Market phase is determined by Nifty 50 behavior:

| Phase | Condition |
|-------|-----------|
| **EXPANSION** | 3M return > 0 AND 12M return > 0 |
| **PEAK** | 3M return < 0 AND 12M return > 0 |
| **CONTRACTION** | 3M return < 0 AND 12M return < 0 |
| **TROUGH** | 3M return > 0 AND 12M return < 0 |

This simple heuristic maps to the classic business/market cycle for sector rotation guidance.

---

## 12. Macroeconomic Dashboard

### 12.1 Tracked Indicators

| Indicator | Ticker | Significance |
|-----------|--------|-------------|
| **Nifty 50** | ^NSEI | Broad market benchmark |
| **Bank Nifty** | ^NSEBANK | Financial sector health |
| **India VIX** | ^INDIAVIX | Market fear gauge |
| **USD/INR** | INR=X | Currency risk, FII flow indicator |
| **Gold** | GC=F | Safe haven, inflation hedge |
| **Crude Oil** | CL=F | Input cost, current account impact |

### 12.2 Macro Regime Classification

The macro environment is classified as RISK_ON or RISK_OFF based on a composite of indicator trends:

- **VIX falling** + **Nifty rising** + **INR stable/strengthening** → RISK_ON
- **VIX rising** + **Nifty falling** + **INR weakening** → RISK_OFF

This classification is injected into the AI Advisor's context to inform recommendations.

---

## 13. News Sentiment Analysis

### 13.1 Data Collection

News headlines are fetched from Google News RSS feeds using keyword queries for 25+ major Indian stocks (e.g., "Reliance Industries NSE", "TCS stock market").

### 13.2 Sentiment Scoring

A keyword-based lexicon approach is used:

1. **Positive Keywords:** "surge", "rally", "growth", "profit", "upgrade", "bullish", "record high", "outperform"
2. **Negative Keywords:** "crash", "fall", "loss", "downgrade", "bearish", "decline", "sell-off", "default"
3. **Scoring:** Each headline receives a score from -1 to +1 based on keyword matches
4. **Aggregation:** Mean sentiment score per stock across recent headlines

**Output:** Per-stock sentiment score, headline count, and trend direction.

---

## 14. AI Advisory System

### 14.1 LLM Integration

| Component | Detail |
|-----------|--------|
| **Provider** | Groq Cloud |
| **Model** | Llama 3.3 70B Versatile |
| **Interface** | OpenAI-compatible chat completions API |
| **Streaming** | Server-Sent Events (SSE) for token-by-token delivery |

### 14.2 Context Injection

The AI advisor receives rich context with every query:

1. **User Financial Profile:** Monthly income, expenses, savings, age, risk profile
2. **Market Snapshot:** Top BUY/SELL signals, current anomalies, sector performance
3. **Macro Conditions:** VIX level, market regime (RISK_ON/RISK_OFF)
4. **Conversation History:** Prior messages for continuity

### 14.3 System Prompt Design

The advisor is configured as an expert Indian investment advisor with:
- Educational (non-advisory) tone with explicit disclaimers
- Markdown formatting for structured responses
- Awareness of Indian tax implications (LTCG, STCG, Section 80C)
- Focus on NSE-listed securities and Indian mutual funds

### 14.4 AI Portfolio Builder

Given a user's investment amount and risk profile, the LLM generates a diversified portfolio:

**Constraints enforced via prompt engineering:**
- 5–15 stocks
- Maximum 20% allocation per stock
- Sector diversification (no more than 30% in one sector)
- Budget constraint (total ≤ investment amount)
- JSON-structured output for programmatic parsing

---

## 15. Database Design

### 15.1 Schema Overview

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│   stocks     │────<│  stock_prices    │     │ macro_prices  │
│ (500+ rows)  │     │ (daily OHLCV +   │     │ (6 tickers)  │
│              │     │  10 indicators)  │     │              │
└──────────────┘     └──────────────────┘     └──────────────┘

┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│user_profiles │────<│  saved_plans     │     │ chat_history  │
│ (RLS)        │     │ (JSONB results)  │     │ (RLS)        │
└──────────────┘     └──────────────────┘     └──────────────┘

┌──────────────┐     ┌──────────────────┐
│market_indices│     │ pipeline_logs    │
│              │     │ (audit trail)    │
└──────────────┘     └──────────────────┘
```

### 15.2 Security

- **Row-Level Security (RLS):** Enabled on all user-facing tables
- **Policy:** `auth.uid() = user_id` — users can only access their own data
- **Public Tables:** `stocks`, `stock_prices`, `macro_prices`, `market_indices` are read-accessible
- **Service Role:** Backend uses service-role key for write operations (price ingestion)

### 15.3 Indexing Strategy

| Index | Table | Purpose |
|-------|-------|---------|
| `(symbol, date)` UNIQUE | stock_prices | Fast lookup + upsert deduplication |
| `(symbol)` | stock_prices | Per-stock history queries |
| `(date)` | stock_prices | Cross-stock date range queries |
| `(ticker, date)` UNIQUE | macro_prices | Macro data deduplication |
| `(sector)` | stocks | Sector-based filtering |
| `(user_id)` | user_profiles | RLS policy evaluation |

---

## 16. Frontend Presentation

### 16.1 Visualization Stack

| Library | Use Case |
|---------|----------|
| **Recharts** | Line charts, area charts, bar charts, scatter plots, pie charts, radar charts |
| **react-markdown** | Render LLM responses with tables, lists, code blocks |
| **TailwindCSS** | Responsive layout, dark/light theme via CSS variables |

### 16.2 State Management

| Layer | Library | Purpose |
|-------|---------|---------|
| Server state | TanStack React Query v5 | API response caching (5-min stale time), background refetching |
| Client state | Zustand (persisted) | User preferences, profile data, theme |
| URL state | React Router v7 | Page navigation, query parameters |

---

## 17. Limitations & Disclaimers

1. **Not SEBI-Registered:** PaisaPro.ai provides educational insights only, not registered investment advice.
2. **Historical Data Dependency:** All models are trained on historical data and may not predict future market behavior accurately.
3. **Data Source Limitations:** yfinance data may have occasional gaps or delays; not suitable for real-time trading.
4. **Model Assumptions:** Monte Carlo assumes normally distributed returns; real markets exhibit fat tails and skewness.
5. **Factor Proxies:** Fama-French factors are approximated from the platform's stock universe rather than formal academic factor portfolios.
6. **Sentiment Simplicity:** Keyword-based sentiment analysis is less nuanced than transformer-based NLP models.
7. **LLM Hallucination Risk:** AI advisor responses may occasionally contain inaccurate information; always cross-verify with primary sources.
8. **Indian Market Focus:** All analysis, tax assumptions, and benchmarks are specific to the Indian equity market (NSE).

---

## 18. References

1. Box, G. E. P., & Jenkins, G. M. (1976). *Time Series Analysis: Forecasting and Control*. Holden-Day.
2. Bollerslev, T. (1986). Generalized Autoregressive Conditional Heteroskedasticity. *Journal of Econometrics*, 31(3), 307–327.
3. Markowitz, H. (1952). Portfolio Selection. *The Journal of Finance*, 7(1), 77–91.
4. Fama, E. F., & French, K. R. (1993). Common Risk Factors in the Returns on Stocks and Bonds. *Journal of Financial Economics*, 33(1), 3–56.
5. Carhart, M. M. (1997). On Persistence in Mutual Fund Performance. *The Journal of Finance*, 52(1), 57–82.
6. Breiman, L. (2001). Random Forests. *Machine Learning*, 45(1), 5–32.
7. Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). Isolation Forest. *ICDM*.
8. Hyndman, R. J., & Athanasopoulos, G. (2021). *Forecasting: Principles and Practice*. OTexts.
