"""
NSE & BSE Indian stock data fetcher using yfinance.
Fetches all Nifty 500 constituents + major indices.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, date
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Major Indian market indices
INDICES = {
    "NIFTY_50": "^NSEI",
    "SENSEX": "^BSESN",
    "NIFTY_BANK": "^NSEBANK",
    "NIFTY_IT": "^CNXIT",
    "NIFTY_MIDCAP_100": "^NSEMDCP100",
    "NIFTY_SMALLCAP_100": "NIFTY_SMLCAP100.NS",
    "NIFTY_FMCG": "^CNXFMCG",
    "NIFTY_PHARMA": "^CNXPHARMA",
    "NIFTY_AUTO": "^CNXAUTO",
    "NIFTY_REALTY": "^CNXREALTY",
}

# Nifty 500 stock symbols (NSE suffix .NS)
NIFTY_500_SYMBOLS = [
    # Nifty 50 (Large Cap)
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BAJFINANCE.NS", "BHARTIARTL.NS",
    "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "NESTLEIND.NS", "WIPRO.NS",
    "HCLTECH.NS", "TECHM.NS", "POWERGRID.NS", "NTPC.NS", "ONGC.NS",
    "COALINDIA.NS", "BAJAJFINSV.NS", "M&M.NS", "TATAMOTORS.NS", "TATASTEEL.NS",
    "JSWSTEEL.NS", "ADANIENT.NS", "ADANIPORTS.NS", "HINDALCO.NS", "DIVISLAB.NS",
    "CIPLA.NS", "DRREDDY.NS", "EICHERMOT.NS", "BPCL.NS", "INDUSINDBK.NS",
    "SBILIFE.NS", "HDFCLIFE.NS", "BRITANNIA.NS", "GRASIM.NS", "APOLLOHOSP.NS",
    "BAJAJ-AUTO.NS", "TATACONSUM.NS", "UPL.NS", "HEROMOTOCO.NS", "SHREECEM.NS",
    # Nifty Next 50 (Large-Mid Cap)
    "AMBUJACEM.NS", "AUROPHARMA.NS", "BANDHANBNK.NS", "BERGEPAINT.NS", "BIOCON.NS",
    "BOSCHLTD.NS", "CHOLAFIN.NS", "COLPAL.NS", "CONCOR.NS", "CUMMINSIND.NS",
    "DABUR.NS", "DMART.NS", "DLF.NS", "GAIL.NS", "GODREJCP.NS",
    "GODREJPROP.NS", "HAL.NS", "HAVELLS.NS", "ICICIGI.NS", "ICICIPRULI.NS",
    "IDFCFIRSTB.NS", "IGL.NS", "INDHOTEL.NS", "INDUSTOWER.NS", "IOC.NS",
    "IRCTC.NS", "JINDALSTEL.NS", "JUBLFOOD.NS", "LICHSGFIN.NS", "LUPIN.NS",
    "MARICO.NS", "MCDOWELL-N.NS", "MFSL.NS", "MOTHERSON.NS", "MPHASIS.NS",
    "MRF.NS", "NAUKRI.NS", "NMDC.NS", "PAGEIND.NS", "PERSISTENT.NS",
    "PETRONET.NS", "PIDILITIND.NS", "PNB.NS", "RECLTD.NS", "SAIL.NS",
    "SIEMENS.NS", "SRF.NS", "TORNTPHARM.NS", "TRENT.NS", "VEDL.NS",
    # Nifty Midcap 100 (selection)
    "AARTIIND.NS", "ABFRL.NS", "ACC.NS", "APLAPOLLO.NS", "APOLLOTYRE.NS",
    "ASTRAL.NS", "ATUL.NS", "AUBANK.NS", "BALKRISIND.NS", "BATAINDIA.NS",
    "BHARATFORG.NS", "BHEL.NS", "CANFINHOME.NS", "CARBORUNIV.NS", "CASTROLIND.NS",
    "CESC.NS", "CROMPTON.NS", "DEEPAKNTR.NS", "DIXON.NS", "ESCORTS.NS",
    "FEDERALBNK.NS", "FINOLEXIND.NS", "GLENMARK.NS", "GNFC.NS", "GRANULES.NS",
    "GSPL.NS", "HFCL.NS", "HONAUT.NS", "IDBI.NS", "IIFL.NS",
    "INDIANB.NS", "INDIGO.NS", "INTELLECT.NS", "IEX.NS", "JKCEMENT.NS",
    "JSWENERGY.NS", "JUBLINGREA.NS", "KAJARIACER.NS", "KANSAINER.NS", "KEC.NS",
    "KMARTNET.NS", "KPITTECH.NS", "LALPATHLAB.NS", "LICI.NS", "LTIM.NS",
    "MANAPPURAM.NS", "MAXHEALTH.NS", "MCX.NS", "METROPOLIS.NS", "MFIN.NS",
]

BSE_SYMBOLS = [s.replace(".NS", ".BO") for s in NIFTY_500_SYMBOLS[:50]]  # Top 50 on BSE


def fetch_stock_info(symbol: str) -> Optional[dict]:
    """Fetch current stock metadata from Yahoo Finance."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        if not info or "regularMarketPrice" not in info:
            return None

        return {
            "symbol": symbol,
            "company_name": info.get("longName") or info.get("shortName", symbol),
            "exchange": "NSE" if symbol.endswith(".NS") else "BSE",
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "current_price": info.get("regularMarketPrice"),
            "previous_close": info.get("regularMarketPreviousClose"),
            "daily_change_pct": _safe_change_pct(
                info.get("regularMarketPrice"),
                info.get("regularMarketPreviousClose"),
            ),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "pb_ratio": info.get("priceToBook"),
            "dividend_yield": info.get("dividendYield"),
            "week_52_high": info.get("fiftyTwoWeekHigh"),
            "week_52_low": info.get("fiftyTwoWeekLow"),
            "avg_volume": info.get("averageVolume"),
            "beta": info.get("beta"),
            "price_updated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.warning(f"Failed to fetch info for {symbol}: {e}")
        return None


def fetch_historical_prices(
    symbol: str,
    start_year: Optional[int] = None,
    end_date: Optional[date] = None,
) -> pd.DataFrame:
    """
    Fetch all available daily OHLCV historical data for a symbol.
    Uses period="max" by default to get the full history yfinance has.
    Returns a DataFrame with columns: date, open, high, low, close, volume, symbol
    """
    try:
        ticker = yf.Ticker(symbol)
        if start_year:
            end = end_date or date.today()
            df = ticker.history(start=f"{start_year}-01-01", end=str(end), auto_adjust=True)
        else:
            df = ticker.history(period="max", auto_adjust=True)

        if df.empty:
            return pd.DataFrame()

        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={"stock splits": "stock_splits", "capital gains": "capital_gains"})
        df["symbol"] = symbol
        df["date"] = pd.to_datetime(df["date"]).dt.date

        # Keep only needed columns
        cols = ["symbol", "date", "open", "high", "low", "close", "volume"]
        df = df[[c for c in cols if c in df.columns]]
        df = df.dropna(subset=["close"])

        return df

    except Exception as e:
        logger.warning(f"Failed to fetch history for {symbol}: {e}")
        return pd.DataFrame()


def fetch_index_data(index_symbol: str) -> Optional[dict]:
    """Fetch current value for a market index."""
    try:
        ticker = yf.Ticker(index_symbol)
        info = ticker.info
        hist = ticker.history(period="2d")

        if hist.empty:
            return None

        current = float(hist["Close"].iloc[-1])
        previous = float(hist["Close"].iloc[-2]) if len(hist) > 1 else current
        change_pct = ((current - previous) / previous * 100) if previous else 0

        return {
            "symbol": index_symbol,
            "name": info.get("shortName", index_symbol),
            "current_value": round(current, 2),
            "previous_close": round(previous, 2),
            "change_pct": round(change_pct, 4),
            "updated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.warning(f"Failed to fetch index {index_symbol}: {e}")
        return None


def _safe_change_pct(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    if current and previous and previous != 0:
        return round((current - previous) / previous * 100, 4)
    return None
