---
title: PaisaPro
emoji: 💰
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

<div align="center">

# ⚡ PaisaPro — Backend API

### Quantitative finance engine for the Indian equity market

[![Status](https://img.shields.io/badge/status-live-00C7B7?style=for-the-badge)](https://stephenbaraik-paisapro.hf.space/health)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-F55036?style=for-the-badge)](https://groq.com)

</div>

---

## Services

| Module | Responsibility |
|--------|---------------|
| `market_data` | yfinance fetch · Supabase cache · OHLCV normalisation |
| `technical` | 7-indicator composite signal (RSI · MACD · BB · ATR · ADX · VWAP · OBV) |
| `risk` | Sharpe · beta · VaR · max drawdown · annualised return |
| `analytics` | Random Forest classifier · Isolation Forest · K-Means (k=4) |
| `ml_regression` | Ridge · Random Forest · GBM ensemble with walk-forward evaluation |
| `timeseries` | ARIMA (ADF auto-diff) · Holt-Winters ETS · decomposition |
| `volatility` | GARCH(1,1) · volatility cone · regime classification |
| `risk_factors` | Fama-French 4-factor OLS decomposition |
| `sector_rotation` | Multi-horizon momentum · market phase detection |
| `macro` | India VIX · USD/INR · Gold · Crude · regime: RISK_ON/OFF/NEUTRAL |
| `news_sentiment` | Google News RSS · keyword lexicon · per-stock sentiment |
| `ai_advisor` | Groq Llama 3.3 70B · agentic tool-use loop · SSE streaming |
| `ai_portfolio` | LLM portfolio construction with budget + diversification guardrails |
| `portfolio_optimizer` | Markowitz MVO · efficient frontier · scipy SLSQP |
| `portfolio` | Holdings & watchlist CRUD (Supabase) |
| `financial_engine` | SIP calculator · goal solver · asset allocation |
| `monte_carlo` | 1,000-simulation wealth projection · P10–P90 bands |
| `universe` | Stock symbol list · names · sectors (Supabase) |

---

## Secrets

Set these in **Settings → Repository secrets** on Hugging Face Spaces:

| Secret | Description |
|--------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |
| `GROQ_API_KEY` | Groq API key for Llama 3.3 70B |
| `FRONTEND_URL` | Frontend URL for CORS (e.g. `https://paisapro.netlify.app`) |
| `APP_ENV` | Set to `production` |

---

## Key Endpoints

```
POST /api/v1/advisor/chat/stream    ← agentic AI advisor (SSE)
GET  /api/v1/analytics/report       ← full ML report (cached 2h)
GET  /api/v1/analytics/screener     ← stock screener
GET  /api/v1/advanced/ml-prediction ← ML regression forecast
GET  /api/v1/analytics/model-health ← MLOps dashboard
GET  /api/v1/advanced/macro         ← macro dashboard + regime
GET  /health                        ← health check
```

Full API reference: [github.com/StephenBaraik/PaisaPro](https://github.com/StephenBaraik/PaisaPro)
