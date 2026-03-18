---
title: PaisaPro
emoji: 💰
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

<div align="center">

<br />

```
██████╗  █████╗ ██╗███████╗ █████╗ ██████╗ ██████╗  ██████╗
██╔══██╗██╔══██╗██║██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔═══██╗
██████╔╝███████║██║███████╗███████║██████╔╝██████╔╝██║   ██║
██╔═══╝ ██╔══██║██║╚════██║██╔══██║██╔═══╝ ██╔══██╗██║   ██║
██║     ██║  ██║██║███████║██║  ██║██║     ██║  ██║╚██████╔╝
╚═╝     ╚═╝  ╚═╝╚═╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝ ╚═════╝
```

### ◈ Institutional-grade quantitative finance. For everyone. ◈

<br />

[![Live Demo](https://img.shields.io/badge/◉_LIVE-paisapro.netlify.app-00C7B7?style=for-the-badge&logoColor=white)](https://paisapro.netlify.app)
[![Backend API](https://img.shields.io/badge/⚡_API-HuggingFace_Spaces-FFD21E?style=for-the-badge&logoColor=black)](https://stephenbaraik-paisapro.hf.space/health)

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-F55036?style=for-the-badge&logoColor=white)](https://groq.com)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)

<br />

> *Hedge-fund-level analytics. Agentic AI advisory. Real-time Indian equity intelligence.*
> *ARIMA · GARCH · Fama-French · Monte Carlo · Random Forest · GARCH · Llama 3.3 70B*

<br />

</div>

---

## ◈ What is PaisaPro?

PaisaPro brings **institutional-grade quantitative finance** to Indian retail investors — the kind of analytics that typically lives behind Bloomberg terminals and quant desks, now accessible through a clean, real-time web application.

The platform combines **classical econometrics** (ARIMA, GARCH, Fama-French 4-factor), **machine learning** (Random Forest, Gradient Boosting, Isolation Forest, K-Means), and an **agentic LLM advisor** (Llama 3.3 70B with live tool-use) — fully integrated, no PhD required.

<br />

---

## ◈ Feature Matrix

<table>
<tr>
<td width="50%" valign="top">

### ⚡ Agentic AI Advisor
- **Llama 3.3 70B** via Groq with SSE streaming
- **Live tool-use** — LLM calls 4 real-time tools mid-conversation: `get_stock_analysis`, `get_macro_dashboard`, `get_news_sentiment`, `run_screener`
- **Portfolio context injection** — your holdings and watchlist fed directly into the system prompt
- **Market intelligence injection** — live signals, anomalies, sector data, macro regime
- Multi-turn tool loop (up to 3 rounds) with graceful fallback
- 30-message conversation history window

</td>
<td width="50%" valign="top">

### 📊 ML Regression Engine
- **Ridge, Random Forest, Gradient Boosting** — 3-model ensemble with cross-validated RMSE
- **Feature engineering** — 20+ OHLCV-aware features: returns, log-price, RSI, MACD, rolling stats, lag features
- **Walk-forward evaluation** — train on 80%, test on 20% with time-series splits
- **MLOps Dashboard** — per-model RMSE, MAE, R², train/test scores, feature importance
- 30-day forward price forecasting with confidence intervals

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 📈 Time-Series & Volatility
- **ARIMA** — auto-differencing via ADF/KPSS stationarity tests, AIC model selection
- **Holt-Winters ETS** — damped additive trend with scipy optimization
- **GARCH(1,1)** — conditional heteroskedasticity with volatility cone term-structure
- **Regime detection** — LOW / NORMAL / HIGH / EXTREME volatility classification
- 95% confidence intervals on all forecasts

</td>
<td width="50%" valign="top">

### 🔬 Risk & Factor Analysis
- **Fama-French 4-Factor** — OLS decomposition: Market (β), Size (SMB), Value (HML), Momentum (WML)
- **Alpha, R², factor contribution** — full attribution breakdown
- **Markowitz MVO** — 2,000 random portfolios, efficient frontier, min-variance + max-Sharpe
- **Composite technical signal** — 7-indicator weighted ensemble (RSI, MACD, BB, ATR, ADX, VWAP, OBV)
- **Isolation Forest** anomaly detection on returns + volume

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🌐 Market Intelligence
- **Stock Screener** — filter by signal, sector, Sharpe ratio, drawdown; composite scoring
- **Sector Rotation** — multi-horizon momentum (1M/3M/6M/12M), market phase (EXPANSION/PEAK/CONTRACTION/TROUGH)
- **Macro Dashboard** — India VIX, USD/INR, Gold, Crude Oil, Nifty 50, Bank Nifty; regime: RISK_ON / RISK_OFF / NEUTRAL
- **News Sentiment** — keyword lexicon scoring across 25 major stocks via Google News RSS
- **Anomaly alerts** — real-time flagging of unusual price/volume behaviour

</td>
<td width="50%" valign="top">

### 💼 Portfolio & Planning
- **Portfolio Tracker** — holdings management, real-time P&L, sector breakdown, watchlist
- **AI Portfolio Builder** — LLM-powered stock selection with budget capping and diversification guardrails
- **Monte Carlo Wealth Planner** — 1,000 simulations with SIP step-up, P10–P90 probability bands
- **Goal-Based Planner** — reverse-solve for required monthly SIP with ±2%/±4% sensitivity analysis
- **K-Means clustering (k=4)** — Defensive / Value / Momentum / High-Volatility stock segments

</td>
</tr>
</table>

<br />

---

## ◈ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USER (Browser)                             │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │
                  ┌─────────────────┴──────────────────┐
                  │                                     │
                  ▼                                     ▼
   ┌──────────────────────────┐         ┌──────────────────────────────┐
   │      NETLIFY CDN         │         │   HUGGING FACE SPACES        │
   │  ─────────────────────   │         │   (Docker · cpu-basic)       │
   │  React 19 + TypeScript   │  REST   │  ──────────────────────────  │
   │  Recharts · Tailwind 4   │◀──JSON──│  FastAPI 0.111 + Pydantic v2 │
   │  TanStack Query v5       │───SSE──▶│  APScheduler (daily 18:00 IST│
   │  Zustand                 │         │  CacheManager (TTL singleton) │
   │  18 pages                │         │  19 service modules          │
   │                          │         │  6 API routers · 35 endpoints│
   │  paisapro.netlify.app    │         │  stephenbaraik-paisapro      │
   └──────────────────────────┘         │        .hf.space             │
                                        └────────┬──────┬──────┬───────┘
                                                 │      │      │
                              ┌──────────────────┘      │      └───────────────────┐
                              ▼                          ▼                          ▼
               ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
               │      SUPABASE        │  │        GROQ          │  │      YFINANCE        │
               │   PostgreSQL         │  │   Llama 3.3 70B      │  │   NSE/BSE OHLCV      │
               │  ─────────────────   │  │  ─────────────────   │  │  ─────────────────   │
               │  stock_prices        │  │  Function calling    │  │  502 stocks          │
               │  stocks (universe)   │  │  SSE streaming       │  │  Daily refresh       │
               │  portfolio_holdings  │  │  Tool-use loop       │  │  ^NSEI · ^BSESN      │
               │  watchlist           │  │  4 live tools        │  │  Google News RSS     │
               └──────────────────────┘  └──────────────────────┘  └──────────────────────┘
```

<br />

---

## ◈ Backend Architecture

The backend is structured in clean, decoupled layers:

```
backend/app/
│
├── api/routes/              ◈ 6 API routers — 35+ endpoints
│   ├── advisor.py           → /advisor/chat  /advisor/chat/stream
│   ├── analytics.py         → /analytics/report  screener  backtest  timeseries  model-health
│   ├── advanced_analytics.py→ /advanced/sector-rotation  volatility  macro  risk-factors  ml-prediction
│   ├── portfolio.py         → /portfolio/holdings  watchlist  ai-build  news-sentiment
│   ├── stocks.py            → /stocks/search  history  indices  sectors
│   └── planner.py           → /planner/forward  /planner/goal
│
├── core/
│   ├── config.py            ◈ Pydantic Settings — env vars, secrets
│   ├── cache.py             ◈ CacheManager — TTL in-memory singleton (shared by all services)
│   ├── database.py          ◈ Supabase httpx REST client
│   └── errors.py            ◈ Global exception handlers
│
├── data/                    ◈ Data access layer (Supabase I/O)
│   ├── stock_repository.py  → load_universe · get_prices · save_prices · bulk_load
│   └── macro_repository.py  → macro indicator persistence
│
├── services/                ◈ 19 domain service modules
│   ├── universe.py          → Stock symbol list, names, sectors (loaded from Supabase)
│   ├── market_data.py       → yfinance fetch · Supabase cache · OHLCV normalisation
│   ├── technical.py         → 7-indicator composite signal engine
│   ├── risk.py              → Sharpe, beta, VaR, max drawdown, annualised return
│   ├── analytics.py         → ML orchestration: RF classifier · Isolation Forest · K-Means
│   ├── ml_regression.py     → Ridge · Random Forest · GBM ensemble with walk-forward eval
│   ├── timeseries.py        → ARIMA · Holt-Winters ETS · ADF/KPSS · decomposition
│   ├── volatility.py        → GARCH(1,1) · volatility cone · regime classification
│   ├── risk_factors.py      → Fama-French 4-factor OLS decomposition
│   ├── sector_rotation.py   → Multi-horizon momentum · market phase detection
│   ├── macro.py             → VIX · USD/INR · Gold · Crude · regime classification
│   ├── news_sentiment.py    → Google News RSS · keyword lexicon · per-stock sentiment
│   ├── ai_advisor.py        → Groq LLM · agentic tool-use loop · SSE streaming
│   ├── ai_portfolio.py      → LLM-driven portfolio construction with guardrails
│   ├── portfolio_optimizer.py → Markowitz MVO · efficient frontier · scipy optimise
│   ├── portfolio_backtester.py→ Historical strategy backtesting
│   ├── portfolio.py         → Holdings & watchlist CRUD (Supabase)
│   ├── financial_engine.py  → SIP calculator · goal solver · asset allocation
│   └── monte_carlo.py       → 1,000-simulation wealth projection · P10–P90 bands
│
├── schemas/                 ◈ Pydantic v2 request/response models
├── main.py                  ◈ FastAPI app · lifespan · CORS · pre-warm cache
└── scheduler.py             ◈ APScheduler — daily 18:00 IST data refresh + cache rebuild
```

<br />

---

## ◈ Quantitative Models

| Model | Algorithm | Application |
|-------|-----------|-------------|
| **ARIMA** | ADF/KPSS stationarity test → auto-differencing → AIC grid search p,q ∈ [0,3] | 30-day price forecast + CI |
| **Holt-Winters ETS** | Damped additive trend, scipy Nelder-Mead optimisation | Alternative forecast model |
| **GARCH(1,1)** | Conditional heteroskedasticity via `arch` library | 30-day volatility forecast + regime |
| **Fama-French 4-Factor** | OLS: Rᵢ − Rf = α + β₁MKT + β₂SMB + β₃HML + β₄WML | Risk decomposition + alpha |
| **Random Forest Classifier** | 252-day training window, 6 technical features, OOB score | 5-day directional prediction |
| **ML Regression Ensemble** | Ridge + RF + GBM, 20+ OHLCV features, walk-forward CV | 30-day price regression |
| **Isolation Forest** | Auto-contamination on log-returns + volume z-scores | Price/volume anomaly detection |
| **K-Means (k=4)** | Features: annualised vol, 3M momentum, beta | Stock universe segmentation |
| **Markowitz MVO** | 2,000 random portfolios + scipy `minimize` (SLSQP) | Efficient frontier construction |
| **Monte Carlo** | 1,000 sims, normal returns, monthly compounding, SIP step-up | Probabilistic wealth projection |
| **Composite Signal** | Weighted ensemble: RSI(.25) MACD(.20) BB(.20) ATR(.15) ADX(.10) VWAP(.05) OBV(.05) | BUY / HOLD / SELL classification |

<br />

---

## ◈ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 19, TypeScript 5.9, Vite 8, Tailwind CSS 4 | 18-page SPA, dark/light theme |
| **Charts** | Recharts (Line, Bar, Area, Scatter, Pie, Radar, Composed) | Interactive financial visualisation |
| **State** | TanStack React Query v5, Zustand | Server-state caching, persisted client state |
| **Backend** | Python 3.12, FastAPI 0.111, Pydantic v2 | REST + SSE API, request validation |
| **Cache** | In-memory CacheManager (TTL singleton) | Sub-millisecond cache reads across all services |
| **ML / Stats** | scikit-learn, statsmodels, scipy, arch, numpy, pandas | RF, IF, K-Means, ARIMA, GARCH, OLS, Monte Carlo |
| **AI / LLM** | Groq API — Llama 3.3 70B Versatile | Agentic advisor with function calling + SSE |
| **Database** | Supabase (PostgreSQL) via httpx PostgREST | Stock prices, holdings, watchlist |
| **Market Data** | yfinance, Google News RSS | NSE/BSE OHLCV, news sentiment |
| **Scheduling** | APScheduler (CronTrigger) | Daily 18:00 IST refresh + cache rebuild |
| **Deployment** | Netlify (frontend) · Hugging Face Spaces Docker (backend) | CDN SPA + containerised API |

<br />

---

## ◈ Agentic AI Advisor — How It Works

The AI advisor uses **Groq function-calling** to give the LLM access to live platform data mid-conversation:

```
User message
     │
     ▼
┌─────────────────────────────────────────────────┐
│              System Prompt                       │
│  + User financial profile                        │
│  + Portfolio holdings & watchlist                │
│  + Live market signals (from analytics cache)    │
│  + Macro regime (from macro cache)               │
│  + News sentiment (from news cache)              │
└─────────────────────────┬───────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Groq Llama 3.3 70B  │  ◀── tool_choice: auto
              │   (Tool-Use Round 1)  │
              └─────────┬─────────────┘
                        │  tool_calls?
            ┌───────────┴──────────────┐
            │  YES                     │  NO → stream reply
            ▼                          ▼
   ┌─────────────────┐         ┌───────────────┐
   │  Execute Tool   │         │  [DONE]       │
   │  ─────────────  │         └───────────────┘
   │  get_stock_     │
   │  analysis       │  ← queries analytics cache / yfinance
   │  get_macro_     │  ← queries macro service
   │  dashboard      │
   │  get_news_      │  ← queries news sentiment service
   │  sentiment      │
   │  run_screener   │  ← queries screener with filters
   └────────┬────────┘
            │  append tool results
            ▼
     Round 2 / Round 3  (MAX_TOOL_ROUNDS = 3)
            │
            ▼
   Final non-streaming request → word-by-word SSE stream
```

<br />

---

## ◈ Caching Architecture

| Service | Cache Key | TTL | Notes |
|---------|-----------|-----|-------|
| Stock DataFrames | `stock:df:{symbol}:{period}` | 24 h | Refreshed by APScheduler after market close |
| Analytics Report | `analytics:report` | 2 h | Full ML compute — RF, IF, K-Means, signals |
| ML Regression | `ml:regression:{symbol}` | 2 h | Ridge + RF + GBM ensemble |
| Time-Series | `timeseries:{symbol}:{horizon}` | 2 h | ARIMA + ETS fit |
| GARCH Forecast | `volatility:{symbol}` | 1 h | Model re-fit on stale data |
| Sector Rotation | `sector:rotation` | 1 h | Multi-horizon momentum |
| Risk Factors | `risk:factors:{symbols}` | 1 h | Factor loadings are stable intraday |
| Macro Dashboard | `macro:dashboard` | 30 min | Regime can shift intraday |
| News Sentiment | `news:sentiment` | 30 min | Continuous news flow |

<br />

---

## ◈ API Reference

<details>
<summary><b>▶ Expand — 35+ endpoints</b></summary>

<br />

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/advisor/chat` | AI advisor — non-streaming |
| `POST` | `/api/v1/advisor/chat/stream` | AI advisor — SSE token stream |
| `GET` | `/api/v1/analytics/report` | Full ML analytics report |
| `GET` | `/api/v1/analytics/market-overview` | Market breadth + sector heatmap |
| `GET` | `/api/v1/analytics/stock-signals` | BUY/HOLD/SELL signals |
| `GET` | `/api/v1/analytics/stock/{symbol}` | Full stock analysis |
| `GET` | `/api/v1/analytics/screener` | Screener with filters |
| `POST` | `/api/v1/analytics/portfolio-optimize` | Efficient frontier |
| `GET` | `/api/v1/analytics/correlation` | Correlation matrix |
| `GET` | `/api/v1/analytics/backtest/{symbol}` | Strategy backtest |
| `POST` | `/api/v1/analytics/smart-portfolio` | Auto-optimised portfolio |
| `GET` | `/api/v1/analytics/timeseries/{symbol}` | ARIMA/ETS forecast |
| `GET` | `/api/v1/analytics/model-health` | MLOps — per-model RMSE, R², MAE |
| `GET` | `/api/v1/advanced/ml-prediction/{symbol}` | ML regression forecast |
| `GET` | `/api/v1/advanced/sector-rotation` | Sector momentum + phase |
| `GET` | `/api/v1/advanced/volatility/{symbol}` | GARCH forecast + vol cone |
| `GET` | `/api/v1/advanced/macro` | Macro indicators + regime |
| `POST` | `/api/v1/advanced/risk-factors` | Fama-French decomposition |
| `GET` | `/api/v1/stocks/search` | Search stocks by name/symbol |
| `GET` | `/api/v1/stocks/{symbol}/history` | OHLCV history |
| `GET` | `/api/v1/stocks/indices/summary` | Nifty 50, Sensex, Bank Nifty |
| `GET` | `/api/v1/stocks/sectors/performance` | Sector-wise returns |
| `GET` | `/api/v1/portfolio/holdings` | Portfolio + P&L |
| `POST` | `/api/v1/portfolio/holdings` | Add holding |
| `DELETE` | `/api/v1/portfolio/holdings/{id}` | Remove holding |
| `GET` | `/api/v1/portfolio/watchlist` | Watchlist |
| `POST` | `/api/v1/portfolio/watchlist` | Add to watchlist |
| `DELETE` | `/api/v1/portfolio/watchlist/{id}` | Remove from watchlist |
| `POST` | `/api/v1/portfolio/ai-build` | LLM portfolio builder |
| `GET` | `/api/v1/portfolio/news-sentiment` | News sentiment |
| `POST` | `/api/v1/planner/forward` | Monte Carlo wealth projection |
| `POST` | `/api/v1/planner/goal` | Goal-based SIP solver |
| `GET` | `/health` | Health check |

</details>

<br />

---

## ◈ Project Structure

```
PaisaPro/
│
├── backend/                 ◈ Python 3.12 · FastAPI backend
│   ├── app/
│   │   ├── api/routes/      → 6 routers · 35+ endpoints
│   │   ├── core/            → config · cache · database · errors
│   │   ├── data/            → Supabase data access layer
│   │   ├── schemas/         → Pydantic v2 models
│   │   ├── services/        → 19 domain service modules
│   │   ├── main.py          → FastAPI app + pre-warm + CORS
│   │   └── scheduler.py     → APScheduler daily refresh
│   ├── scripts/
│   │   ├── backfill_nifty500.py   → one-time historical data load
│   │   └── backfill_macro.py      → one-time macro data load
│   ├── Dockerfile           → HF Spaces deployment
│   └── requirements.txt
│
├── frontend/                ◈ React 19 · TypeScript 5.9 SPA
│   └── src/
│       ├── pages/           → 18 page components
│       │   ├── Landing.tsx         → animated hero, ticker tape
│       │   ├── Dashboard.tsx       → KPI cards, indices, profile
│       │   ├── AIAdvisor.tsx       → streaming LLM chat
│       │   ├── Portfolio.tsx       → holdings, P&L, AI builder
│       │   ├── StockScreener.tsx   → filter & rank
│       │   ├── PortfolioOptimizer.tsx → efficient frontier
│       │   ├── TimeSeriesAnalysis.tsx → ARIMA/ETS forecast
│       │   ├── VolatilityForecast.tsx → GARCH + vol cone
│       │   ├── MLPrediction.tsx    → ML regression forecast
│       │   ├── ModelHealth.tsx     → MLOps dashboard
│       │   ├── SectorRotation.tsx  → momentum rankings
│       │   ├── RiskFactors.tsx     → factor decomposition
│       │   ├── MacroDashboard.tsx  → macro indicators
│       │   ├── NewsSentiment.tsx   → news analysis
│       │   ├── AnalyticsReport.tsx → full ML report
│       │   ├── ScenarioComparison.tsx → side-by-side planning
│       │   ├── ForwardPlanner.tsx  → Monte Carlo projection
│       │   └── GoalPlanner.tsx     → SIP goal solver
│       ├── api/client.ts    → Axios + SSE client (35+ functions)
│       ├── types/index.ts   → TypeScript interfaces
│       └── store/           → Zustand persisted state
│
├── scripts/
│   └── remove_bad_symbols.py  → utility: prune delisted stocks from Supabase
│
└── Dockerfile               → root HF Spaces container
```

<br />

---

## ◈ Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Supabase project (free tier works)
- Groq API key — free at [console.groq.com](https://console.groq.com)

### 1 — Clone & configure

```bash
git clone https://github.com/StephenBaraik/PaisaPro.git
cd PaisaPro
```

Create `.env` in the project root:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
GROQ_API_KEY=gsk_your-groq-key
FRONTEND_URL=http://localhost:5173
APP_ENV=development
```

### 2 — Run the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3 — Backfill historical data (one-time)

```bash
python -m scripts.backfill_nifty500
```

### 4 — Run the frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

<br />

---

## ◈ Deployment

| Component | Platform | URL |
|-----------|----------|-----|
| Frontend | Netlify CDN | [paisapro.netlify.app](https://paisapro.netlify.app) |
| Backend | Hugging Face Spaces — Docker | [stephenbaraik-paisapro.hf.space](https://stephenbaraik-paisapro.hf.space/health) |
| Database | Supabase (PostgreSQL) | Managed cloud |

<br />

---

## ◈ Disclaimer

> PaisaPro is an analytical and educational tool. It is **not** a SEBI-registered investment advisor. All signals, forecasts, and AI-generated recommendations are for **informational purposes only** and do not constitute financial advice. Past performance does not guarantee future results. Always consult a qualified financial advisor before making investment decisions.

<br />

---

<div align="center">

**[◉ Live Demo](https://paisapro.netlify.app)** · **[⚡ API](https://stephenbaraik-paisapro.hf.space/health)** · **[⚠ Issues](https://github.com/StephenBaraik/PaisaPro/issues)**

<br />

<sub>Built by <a href="https://github.com/StephenBaraik">Stephen Baraik</a> · Python · React · Quantitative Finance</sub>

</div>
