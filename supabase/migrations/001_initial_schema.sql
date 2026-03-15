-- =============================================================
-- AI Investment Advisor — Supabase Schema
-- Run this in: Supabase Dashboard > SQL Editor
-- =============================================================

SET search_path TO public;

-- -------------------------------------------------------
-- CLEAN SLATE (safe on fresh project — drops if exists)
-- -------------------------------------------------------
DROP FUNCTION IF EXISTS get_sector_performance() CASCADE;
DROP TABLE IF EXISTS pipeline_logs    CASCADE;
DROP TABLE IF EXISTS chat_history     CASCADE;
DROP TABLE IF EXISTS saved_plans      CASCADE;
DROP TABLE IF EXISTS user_profiles    CASCADE;
DROP TABLE IF EXISTS stock_prices     CASCADE;
DROP TABLE IF EXISTS market_indices   CASCADE;
DROP TABLE IF EXISTS stocks           CASCADE;

-- -------------------------------------------------------
-- 1. STOCKS — Indian market stock metadata
-- -------------------------------------------------------
CREATE TABLE stocks (
  symbol            VARCHAR(20) PRIMARY KEY,
  company_name      VARCHAR(200) NOT NULL,
  exchange          VARCHAR(10) NOT NULL DEFAULT 'NSE' CHECK (exchange IN ('NSE', 'BSE')),
  sector            VARCHAR(100),
  industry          VARCHAR(100),
  current_price     DECIMAL(12, 4),
  previous_close    DECIMAL(12, 4),
  daily_change_pct  DECIMAL(8, 4),
  market_cap        BIGINT,
  pe_ratio          DECIMAL(10, 4),
  pb_ratio          DECIMAL(10, 4),
  dividend_yield    DECIMAL(8, 6),
  week_52_high      DECIMAL(12, 4),
  week_52_low       DECIMAL(12, 4),
  avg_volume        BIGINT,
  beta              DECIMAL(8, 4),
  price_updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------
-- 2. STOCK PRICES — Daily OHLCV + technical indicators
-- -------------------------------------------------------
CREATE TABLE stock_prices (
  id               BIGSERIAL PRIMARY KEY,
  symbol           VARCHAR(20) NOT NULL REFERENCES stocks(symbol) ON DELETE CASCADE,
  date             DATE NOT NULL,
  open             DECIMAL(12, 4) NOT NULL,
  high             DECIMAL(12, 4) NOT NULL,
  low              DECIMAL(12, 4) NOT NULL,
  close            DECIMAL(12, 4) NOT NULL,
  volume           BIGINT,
  sma_20           DECIMAL(12, 4),
  sma_50           DECIMAL(12, 4),
  sma_200          DECIMAL(12, 4),
  ema_12           DECIMAL(12, 4),
  ema_26           DECIMAL(12, 4),
  macd             DECIMAL(12, 4),
  macd_signal      DECIMAL(12, 4),
  macd_histogram   DECIMAL(12, 4),
  rsi_14           DECIMAL(8, 4),
  bb_upper         DECIMAL(12, 4),
  bb_mid           DECIMAL(12, 4),
  bb_lower         DECIMAL(12, 4),
  bb_width         DECIMAL(10, 6),
  atr_14           DECIMAL(12, 4),
  vol_sma_20       DECIMAL(16, 2),
  vol_ratio        DECIMAL(10, 4),
  daily_return_pct DECIMAL(8, 4),
  UNIQUE(symbol, date)
);

-- -------------------------------------------------------
-- 3. MARKET INDICES — Nifty, Sensex, etc.
-- -------------------------------------------------------
CREATE TABLE market_indices (
  symbol         VARCHAR(30) PRIMARY KEY,
  name           VARCHAR(100) NOT NULL,
  current_value  DECIMAL(12, 2),
  previous_close DECIMAL(12, 2),
  change_pct     DECIMAL(8, 4),
  updated_at     TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------
-- 4. USER PROFILES
-- -------------------------------------------------------
CREATE TABLE user_profiles (
  id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id                  UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  monthly_income           DECIMAL(15, 2),
  monthly_expenses         DECIMAL(15, 2),
  current_savings          DECIMAL(15, 2) DEFAULT 0,
  age                      SMALLINT,
  risk_profile             VARCHAR(20) DEFAULT 'moderate' CHECK (risk_profile IN ('conservative', 'moderate', 'aggressive')),
  annual_income_growth_pct DECIMAL(5, 2) DEFAULT 5.0,
  created_at               TIMESTAMPTZ DEFAULT NOW(),
  updated_at               TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------
-- 5. SAVED PLANS
-- -------------------------------------------------------
CREATE TABLE saved_plans (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  plan_type           VARCHAR(20) NOT NULL CHECK (plan_type IN ('forward', 'goal')),
  name                VARCHAR(100),
  input_params        JSONB NOT NULL,
  result_summary      JSONB NOT NULL,
  monte_carlo_result  JSONB,
  created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------
-- 6. CHAT HISTORY
-- -------------------------------------------------------
CREATE TABLE chat_history (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role       VARCHAR(10) NOT NULL CHECK (role IN ('user', 'assistant')),
  content    TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------
-- 7. PIPELINE LOGS
-- -------------------------------------------------------
CREATE TABLE pipeline_logs (
  id                BIGSERIAL PRIMARY KEY,
  run_type          VARCHAR(20) NOT NULL,
  status            VARCHAR(20) NOT NULL,
  symbols_processed INT DEFAULT 0,
  rows_written      INT DEFAULT 0,
  errors            INT DEFAULT 0,
  notes             TEXT,
  started_at        TIMESTAMPTZ DEFAULT NOW()
);

-- -------------------------------------------------------
-- INDEXES
-- -------------------------------------------------------
CREATE INDEX idx_stock_prices_symbol      ON stock_prices(symbol);
CREATE INDEX idx_stock_prices_date        ON stock_prices(date DESC);
CREATE INDEX idx_stock_prices_symbol_date ON stock_prices(symbol, date DESC);
CREATE INDEX idx_stocks_sector            ON stocks(sector);
CREATE INDEX idx_stocks_exchange          ON stocks(exchange);
CREATE INDEX idx_saved_plans_user_id      ON saved_plans(user_id);
CREATE INDEX idx_chat_history_user_id     ON chat_history(user_id, created_at DESC);

-- -------------------------------------------------------
-- ROW LEVEL SECURITY
-- -------------------------------------------------------
ALTER TABLE user_profiles  ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_plans    ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_history   ENABLE ROW LEVEL SECURITY;
ALTER TABLE stocks         ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_prices   ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_indices ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Own profile only" ON user_profiles FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Own plans only"   ON saved_plans   FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Own chat only"    ON chat_history  FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Public read stocks"  ON stocks        FOR SELECT USING (true);
CREATE POLICY "Public read prices"  ON stock_prices  FOR SELECT USING (true);
CREATE POLICY "Public read indices" ON market_indices FOR SELECT USING (true);

-- -------------------------------------------------------
-- HELPER FUNCTION: Sector performance summary
-- -------------------------------------------------------
CREATE OR REPLACE FUNCTION get_sector_performance()
RETURNS TABLE (
  sector_name      TEXT,
  stock_count      BIGINT,
  avg_daily_change NUMERIC,
  avg_pe_ratio     NUMERIC,
  total_market_cap BIGINT
)
LANGUAGE plpgsql STABLE
SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT
    s.sector::TEXT,
    COUNT(*)::BIGINT,
    ROUND(AVG(s.daily_change_pct)::NUMERIC, 4),
    ROUND(AVG(s.pe_ratio)::NUMERIC, 2),
    SUM(s.market_cap)::BIGINT
  FROM public.stocks s
  WHERE s.sector IS NOT NULL AND s.sector != 'Unknown'
  GROUP BY s.sector
  ORDER BY AVG(s.daily_change_pct) DESC;
END;
$$;
