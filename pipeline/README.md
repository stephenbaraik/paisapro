# Data Pipeline

Fetches and stores NSE/BSE Indian stock data into Supabase.

## Setup

```bash
cd pipeline
pip install -r ../backend/requirements.txt
cp ../.env.example ../.env
# fill in SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
```

## Run

```bash
# One-time full backfill (2019 → today, ~100 symbols, takes ~20 mins)
python runner.py backfill

# Daily update (run after market close, 6pm IST)
python runner.py daily

# Index-only update (lightweight)
python runner.py indices
```

## What it fetches

- **Stocks**: 100+ NSE-listed stocks (Nifty 50 + Next 50 + Midcap selection)
- **Exchanges**: NSE (.NS suffix) and BSE (.BO suffix) via yfinance
- **History**: Daily OHLCV from 2019 onwards
- **Indicators**: SMA 20/50/200, EMA 12/26, MACD, RSI 14, Bollinger Bands, ATR 14
- **Indices**: Nifty 50, Sensex, Nifty Bank, Nifty IT, Nifty Midcap 100, and more
