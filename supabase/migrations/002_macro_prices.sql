-- =============================================================
-- Macro Prices table — stores daily close prices for macro
-- indicators (India VIX, USD/INR, Nifty 50, Gold, Oil, Bank Nifty)
-- Run this in: Supabase Dashboard > SQL Editor
-- =============================================================

SET search_path TO public;

CREATE TABLE IF NOT EXISTS macro_prices (
  id      BIGSERIAL PRIMARY KEY,
  ticker  VARCHAR(20) NOT NULL,      -- e.g. "^NSEI", "INR=X", "GC=F"
  date    DATE NOT NULL,
  close   DECIMAL(16, 4) NOT NULL,
  UNIQUE(ticker, date)
);

CREATE INDEX idx_macro_prices_ticker      ON macro_prices(ticker);
CREATE INDEX idx_macro_prices_ticker_date ON macro_prices(ticker, date DESC);

-- Allow service role to read/write, public read
ALTER TABLE macro_prices ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read macro" ON macro_prices FOR SELECT USING (true);
CREATE POLICY "Service write macro" ON macro_prices FOR ALL USING (true);
