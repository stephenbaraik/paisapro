---
title: PaisaPro
emoji: 📈
colorFrom: indigo
colorTo: green
sdk: docker
pinned: false
---

# PaisaPro.ai — Backend API

AI-powered Indian market investment advisor with analytics, portfolio building, and time-series forecasting.

## Secrets Required

Set these in **Settings → Repository secrets** on Hugging Face Spaces:

| Secret | Description |
|--------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |
| `GROQ_API_KEY` | Groq API key for LLM |
| `ALPHA_VANTAGE_API_KEY` | Alpha Vantage key (optional) |
| `FRONTEND_URL` | Frontend URL for CORS |
| `APP_ENV` | Set to `production` |
