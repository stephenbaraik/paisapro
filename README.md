---
title: PaisaPro
emoji: 💰
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

<div align="center">

# <img src="https://img.icons8.com/fluency/48/rupee.png" width="36" align="center" /> PaisaPro.ai

### AI-Powered Investment Advisory Platform for the Indian Equity Market

[![Live Demo](https://img.shields.io/badge/Live_Demo-paisapro.netlify.app-00C7B7?style=for-the-badge&logo=netlify&logoColor=white)](https://paisapro.netlify.app)
[![Backend API](https://img.shields.io/badge/API-HuggingFace_Spaces-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://stephenbaraik-paisapro.hf.space/health)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)

<br />

*Institutional-grade analytics meets AI — built for Indian retail investors.*

*ARIMA forecasting · GARCH volatility · Fama-French factors · Monte Carlo simulations · LLM advisory*

<br />

---

</div>

<br />

## What is PaisaPro.ai?

PaisaPro.ai brings **hedge-fund-level quantitative analytics** to everyday Indian investors. It combines classical econometric models (ARIMA, GARCH, Fama-French), machine learning (Random Forest, Isolation Forest, K-Means), and a conversational AI advisor (Llama 3.3 70B) — all in one beautiful, real-time web application.

> **No PhD required.** The platform automates stationarity testing, model selection, risk decomposition, and portfolio optimization — so you get the insights without the complexity.

<br />

## Key Features

<table>
<tr>
<td width="50%">

### Analytics & Forecasting
- **Time-Series Forecasting** — ARIMA (auto-differencing via ADF), Exponential Smoothing, Linear Trend with 30-day ahead predictions and 95% confidence intervals
- **Volatility Modelling** — GARCH(1,1) with regime detection (LOW/NORMAL/HIGH/EXTREME) and volatility cone term-structure
- **Technical Analysis** — 7 indicators (RSI, MACD, Bollinger, ATR, ADX, VWAP, OBV) synthesized into weighted composite BUY/HOLD/SELL signals
- **Risk Factor Decomposition** — Fama-French 4-factor model (Market, Size, Value, Momentum) with alpha, R-squared, and factor contribution analysis

</td>
<td width="50%">

### Intelligence & Planning
- **AI Financial Advisor** — Streaming chat powered by Llama 3.3 70B with live market context injection (signals, anomalies, sector data)
- **AI Portfolio Builder** — LLM-powered stock selection with budget capping, diversification constraints, and post-processing guardrails
- **Monte Carlo Wealth Planner** — 1,000 simulations with SIP step-up for probabilistic wealth projection (P10–P90 bands)
- **Goal-Based Planning** — Reverse-solve for required monthly SIP with sensitivity analysis at ±2%/±4% return scenarios

</td>
</tr>
<tr>
<td width="50%">

### Market Intelligence
- **Stock Screener** — Filter by signal, sector, Sharpe ratio, max drawdown with composite scoring
- **Sector Rotation** — Multi-horizon momentum (1M/3M/6M/12M) with market phase classification (EXPANSION/PEAK/CONTRACTION/TROUGH)
- **Anomaly Detection** — Isolation Forest + rule-based volume/price spike detection
- **News Sentiment** — Keyword lexicon scoring across 25 major stocks via Google News RSS

</td>
<td width="50%">

### Portfolio & Macro
- **Portfolio Optimizer** — Markowitz mean-variance efficient frontier with min-variance, max-Sharpe, and risk-profile-weighted allocations
- **Portfolio Tracker** — Holdings management with real-time P&L, sector breakdown, and watchlist
- **Macro Dashboard** — India VIX, USD/INR, Gold, Crude Oil, Nifty 50, Bank Nifty with regime classification (RISK_ON/RISK_OFF)
- **ML Clustering** — K-Means (k=4) segmentation: Defensive, Value, Momentum, High-Volatility

</td>
</tr>
</table>

<br />

## Architecture

```
                              ┌──────────┐
                              │   User   │
                              │ (Browser)│
                              └────┬─────┘
                                   │
                    ┌──────────────┴──────────────┐
                    │                             │
                    ▼                             ▼
         ┌───────────────────┐         ┌───────────────────┐
         │   Netlify CDN     │         │  HuggingFace      │
         │                   │  REST   │  Spaces (Docker)   │
         │  React 19 + TS    │──JSON──▶│                   │
         │  Recharts         │◀──SSE───│  FastAPI + Python  │
         │  Tailwind CSS     │         │  12 Service Modules│
         │  React Query      │         │  APScheduler       │
         │                   │         │                   │
         │  paisapro.        │         │  stephenbaraik-   │
         │  netlify.app      │         │  paisapro.hf.space│
         └───────────────────┘         └─────┬───┬───┬─────┘
                                             │   │   │
                                    ┌────────┘   │   └────────┐
                                    ▼            ▼            ▼
                              ┌──────────┐ ┌──────────┐ ┌──────────┐
                              │ Supabase │ │  Groq    │ │ yfinance │
                              │ Postgres │ │ Llama 3.3│ │ NSE Data │
                              │          │ │  70B     │ │ 500 Stocks│
                              └──────────┘ └──────────┘ └──────────┘
```

<br />

## Tech Stack

<table>
<tr>
<th align="left">Layer</th>
<th align="left">Technology</th>
<th align="left">Purpose</th>
</tr>
<tr>
<td><b>Frontend</b></td>
<td>React 19, TypeScript 5.9, Vite 8, Tailwind CSS 4</td>
<td>SPA with 16 interactive pages, dark/light theme</td>
</tr>
<tr>
<td><b>Charts</b></td>
<td>Recharts (Line, Bar, Area, Scatter, Pie, Radar, Composed)</td>
<td>Interactive data visualization</td>
</tr>
<tr>
<td><b>State</b></td>
<td>TanStack React Query v5, Zustand</td>
<td>Server state caching, client state persistence</td>
</tr>
<tr>
<td><b>Backend</b></td>
<td>Python 3.12, FastAPI 0.111, Pydantic v2</td>
<td>REST API + SSE streaming, request validation</td>
</tr>
<tr>
<td><b>ML / Stats</b></td>
<td>scikit-learn, statsmodels, scipy, arch, numpy, pandas</td>
<td>RF, IF, K-Means, ARIMA, GARCH, OLS, Monte Carlo</td>
</tr>
<tr>
<td><b>AI / LLM</b></td>
<td>Groq API (Llama 3.3 70B Versatile)</td>
<td>Conversational advisor, portfolio construction</td>
</tr>
<tr>
<td><b>Database</b></td>
<td>Supabase (PostgreSQL) via httpx PostgREST</td>
<td>Stock prices, holdings, watchlist persistence</td>
</tr>
<tr>
<td><b>Data</b></td>
<td>yfinance, Google News RSS, NSE India</td>
<td>Market OHLCV, news articles, index constituents</td>
</tr>
<tr>
<td><b>Scheduling</b></td>
<td>APScheduler (CronTrigger)</td>
<td>Daily 6 PM IST data refresh + cache rebuild</td>
</tr>
<tr>
<td><b>Deployment</b></td>
<td>Netlify (frontend), Hugging Face Spaces Docker (backend)</td>
<td>CDN-hosted SPA + containerized API</td>
</tr>
</table>

<br />

## Quantitative Models

| Model | Algorithm | Application |
|-------|-----------|-------------|
| **ARIMA** | Auto-differencing (ADF test), AIC grid search over p,d,q | 30-day price forecasting |
| **Holt-Winters ETS** | Damped additive trend, scipy optimization | Alternative forecast model |
| **GARCH(1,1)** | Conditional heteroskedasticity (arch library) | 30-day volatility forecast + regime |
| **Fama-French 4-Factor** | OLS regression: MKT, SMB, HML, WML | Risk decomposition + alpha |
| **Random Forest** | 252-day training, 6 technical features | 5-day directional prediction |
| **Isolation Forest** | Auto-contamination on returns/volume | Anomaly detection |
| **K-Means (k=4)** | Features: volatility, momentum, beta | Stock universe segmentation |
| **Markowitz MVO** | 2,000 random portfolios + scipy optimize | Efficient frontier construction |
| **Monte Carlo** | 1,000 sims, Normal returns, monthly compounding | Probabilistic wealth projection |
| **Composite Signal** | Weighted ensemble: RSI(.25) MACD(.20) BB(.20) ATR(.15) ADX(.10) VWAP(.05) OBV(.05) | BUY/HOLD/SELL classification |

<br />

## Project Structure

```
Ai Advisor/
├── backend/
│   ├── app/
│   │   ├── api/routes/          # 6 API routers (30+ endpoints)
│   │   │   ├── planner.py       # /planner/forward, /planner/goal
│   │   │   ├── advisor.py       # /advisor/chat, /advisor/chat/stream
│   │   │   ├── stocks.py        # /stocks/search, /stocks/{sym}/history
│   │   │   ├── analytics.py     # /analytics/report, screener, backtest, timeseries
│   │   │   ├── advanced_analytics.py  # /advanced/sector-rotation, volatility, macro, risk-factors
│   │   │   └── portfolio.py     # /portfolio/holdings, watchlist, ai-build, news-sentiment
│   │   ├── core/
│   │   │   ├── config.py        # Pydantic Settings (env vars)
│   │   │   └── database.py      # Supabase httpx REST client
│   │   ├── schemas/             # Pydantic request/response models
│   │   ├── services/            # 12 domain service modules
│   │   │   ├── analytics.py     # Core ML engine (67KB) — indicators, RF, IF, KMeans
│   │   │   ├── timeseries.py    # ARIMA, ETS, decomposition, ADF/KPSS
│   │   │   ├── volatility.py    # GARCH(1,1), vol cone, regime detection
│   │   │   ├── risk_factors.py  # Fama-French 4-factor OLS
│   │   │   ├── sector_rotation.py  # Momentum analysis, market phase
│   │   │   ├── macro.py         # VIX, USD/INR, Gold, Oil dashboard
│   │   │   ├── ai_advisor.py    # Groq LLM chat + SSE streaming
│   │   │   ├── ai_portfolio.py  # LLM portfolio construction
│   │   │   ├── news_sentiment.py  # Google News keyword sentiment
│   │   │   ├── financial_engine.py  # SIP calculator, goal solver
│   │   │   ├── monte_carlo.py   # 1000-sim wealth projection
│   │   │   └── portfolio.py     # Holdings & watchlist CRUD
│   │   ├── main.py              # FastAPI app + lifespan + CORS
│   │   └── scheduler.py         # APScheduler daily refresh
│   ├── scripts/
│   │   └── backfill_nifty500.py # One-time historical data loader
│   ├── Dockerfile               # HF Spaces deployment
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/               # 16 page components
│   │   │   ├── Landing.tsx      # Animated landing (ticker tape, SVG chart)
│   │   │   ├── Dashboard.tsx    # KPI cards, profile form, indices
│   │   │   ├── ForwardPlanner.tsx  # Monte Carlo wealth projection
│   │   │   ├── GoalPlanner.tsx  # Target → required SIP
│   │   │   ├── AIAdvisor.tsx    # Streaming LLM chat
│   │   │   ├── Portfolio.tsx    # Holdings, P&L, AI portfolio builder
│   │   │   ├── StockScreener.tsx  # Filter & rank stocks
│   │   │   ├── PortfolioOptimizer.tsx  # Efficient frontier
│   │   │   ├── TimeSeriesAnalysis.tsx  # ARIMA/ETS forecasts
│   │   │   ├── VolatilityForecast.tsx  # GARCH + vol cone
│   │   │   ├── SectorRotation.tsx  # Momentum rankings
│   │   │   ├── RiskFactors.tsx  # Factor decomposition
│   │   │   ├── MacroDashboard.tsx  # Macro indicators
│   │   │   ├── NewsSentiment.tsx  # News sentiment analysis
│   │   │   ├── AnalyticsReport.tsx  # Full ML report
│   │   │   └── ScenarioComparison.tsx  # Side-by-side planning
│   │   ├── components/
│   │   │   ├── Layout.tsx       # Sidebar nav + header + theme toggle
│   │   │   └── ProfileForm.tsx  # Financial profile input
│   │   ├── api/client.ts        # Axios + SSE client (30+ API functions)
│   │   ├── types/index.ts       # TypeScript interfaces
│   │   └── store/profileStore.ts  # Zustand persisted state
│   ├── netlify.toml             # Netlify SPA config
│   ├── .env.production          # VITE_API_URL for production
│   └── package.json
│
└── Draft.MD                     # Academic project report
```

<br />

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Supabase project (free tier works)
- Groq API key (free at [console.groq.com](https://console.groq.com))

### 1. Clone & Setup Backend

```bash
git clone https://github.com/StephenBaraik/PaisaPro.git
cd PaisaPro
```

Create a `.env` file in the project root:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
GROQ_API_KEY=gsk_your-groq-key
FRONTEND_URL=http://localhost:5173
APP_ENV=development
```

Install and run the backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Backfill Stock Data (One-Time)

```bash
python -m scripts.backfill_nifty500
```

### 3. Setup & Run Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

<br />

## API Endpoints

<details>
<summary><b>Expand to see all 30+ endpoints</b></summary>

<br />

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/planner/forward` | Monte Carlo wealth projection |
| `POST` | `/api/v1/planner/goal` | Goal-based SIP solver |
| `POST` | `/api/v1/advisor/chat` | AI advisor (non-streaming) |
| `POST` | `/api/v1/advisor/chat/stream` | AI advisor (SSE streaming) |
| `GET` | `/api/v1/stocks/search?q=` | Search stocks by name/symbol |
| `GET` | `/api/v1/stocks/{symbol}/history` | OHLCV price history |
| `GET` | `/api/v1/stocks/indices/summary` | Nifty 50, Sensex, Bank Nifty |
| `GET` | `/api/v1/stocks/sectors/performance` | Sector-wise average returns |
| `GET` | `/api/v1/analytics/market-overview` | Market breadth + heatmap |
| `GET` | `/api/v1/analytics/stock-signals` | Technical signals (BUY/SELL) |
| `GET` | `/api/v1/analytics/stock/{symbol}` | Full stock analysis |
| `POST` | `/api/v1/analytics/portfolio-optimize` | Efficient frontier |
| `GET` | `/api/v1/analytics/correlation` | Correlation matrix |
| `GET` | `/api/v1/analytics/screener` | Stock screener with filters |
| `GET` | `/api/v1/analytics/report` | Full ML analytics report |
| `GET` | `/api/v1/analytics/backtest/{symbol}` | Strategy backtest |
| `POST` | `/api/v1/analytics/smart-portfolio` | Auto-optimized portfolio |
| `GET` | `/api/v1/analytics/timeseries/{symbol}` | ARIMA/ETS forecast |
| `GET` | `/api/v1/analytics/timeseries-symbols` | Available symbols |
| `GET` | `/api/v1/advanced/sector-rotation` | Sector momentum + phase |
| `GET` | `/api/v1/advanced/volatility/{symbol}` | GARCH forecast + cone |
| `GET` | `/api/v1/advanced/volatility-symbols` | Available symbols |
| `GET` | `/api/v1/advanced/macro` | Macro indicators + regime |
| `POST` | `/api/v1/advanced/risk-factors` | Fama-French decomposition |
| `GET` | `/api/v1/portfolio/watchlist` | Get watchlist |
| `POST` | `/api/v1/portfolio/watchlist` | Add to watchlist |
| `DELETE` | `/api/v1/portfolio/watchlist/{id}` | Remove from watchlist |
| `GET` | `/api/v1/portfolio/holdings` | Get portfolio + P&L |
| `POST` | `/api/v1/portfolio/holdings` | Add holding |
| `DELETE` | `/api/v1/portfolio/holdings/{id}` | Remove holding |
| `POST` | `/api/v1/portfolio/ai-build` | AI portfolio builder |
| `GET` | `/api/v1/portfolio/news-sentiment` | Market news sentiment |
| `GET` | `/health` | Health check |

</details>

<br />

## Caching Strategy

| Service | TTL | Rationale |
|---------|-----|-----------|
| Stock DataFrames | 24 hours | Refreshed daily after market close |
| Analytics Report | 2 hours | Balances freshness with compute cost |
| Time-Series Models | 2 hours | Model parameters change slowly |
| GARCH Forecasts | 1 hour | Volatility shifts faster |
| Sector Rotation | 1 hour | Momentum is medium-frequency |
| Risk Factors | 1 hour | Factor loadings are stable |
| Macro Indicators | 30 minutes | Regime can shift intraday |
| News Sentiment | 30 minutes | News flow is continuous |

<br />

## Deployment

| Component | Platform | URL |
|-----------|----------|-----|
| Frontend | Netlify CDN | [paisapro.netlify.app](https://paisapro.netlify.app) |
| Backend | Hugging Face Spaces (Docker) | [stephenbaraik-paisapro.hf.space](https://stephenbaraik-paisapro.hf.space/health) |
| Database | Supabase (PostgreSQL) | Managed cloud instance |

<br />

## Built By

<table>
<tr>
<td align="center">
<b>Stephen Baraik</b><br />
Full-Stack Developer & Creator<br />
<a href="https://github.com/StephenBaraik">GitHub</a>
</td>
</tr>
</table>

<br />

## Disclaimer

> PaisaPro.ai is an analytical and educational tool. It is **not** a SEBI-registered investment advisor. All signals, forecasts, and AI-generated recommendations are for **informational purposes only** and do not constitute financial advice. Past performance does not guarantee future results. Always consult a qualified financial advisor before making investment decisions.

<br />

---

<div align="center">

**[Live Demo](https://paisapro.netlify.app)** · **[API Health](https://stephenbaraik-paisapro.hf.space/health)** · **[Report an Issue](https://github.com/StephenBaraik/PaisaPro/issues)**

<sub>Built with Python, React, and a lot of math.</sub>

</div>
