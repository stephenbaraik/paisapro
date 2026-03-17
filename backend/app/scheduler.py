"""
Daily data refresh scheduler.

Runs at 6 PM IST (12:30 UTC) on weekdays to:
  1. Invalidate in-memory price cache
  2. Re-fetch latest prices for all tracked stocks (yfinance → Supabase → cache)
  3. Refresh macro indicators
  4. Invalidate report + ML model caches
  5. Pre-warm the report cache for next request
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _daily_refresh():
    """Invalidate all caches, re-fetch prices, rebuild report."""
    try:
        from .core.cache import cache
        from .services.universe import get_symbols
        from .services.market_data import get_price_df, invalidate_all
        from .services.ml.classifier import invalidate_all_models
        from .services.analytics import get_analytics_report, REPORT_CACHE_KEY

        universe = get_symbols()
        logger.info("Daily refresh: invalidating caches for %d stocks…", len(universe))

        # 1. Clear all price DataFrames so they're re-fetched from yfinance
        invalidate_all()

        # 2. Clear per-stock ML models, report, and per-stock analysis caches
        invalidate_all_models()
        cache.invalidate(REPORT_CACHE_KEY)
        cache.invalidate_prefix("analytics:stock:")

        # 3. Re-fetch latest prices for each stock (writes back to Supabase)
        success = 0
        for sym in universe:
            try:
                df = get_price_df(sym, "1y")
                if df is not None and not df.empty:
                    success += 1
            except Exception as exc:
                logger.warning("Refresh failed for %s: %s", sym, exc)

        logger.info("Daily refresh: %d/%d stocks updated.", success, len(universe))

        # 4. Refresh macro data
        try:
            from .services.macro import refresh_macro_data
            logger.info("Daily refresh: updating macro indicators…")
            macro_count = refresh_macro_data()
            logger.info("Daily refresh: %d macro tickers updated.", macro_count)
        except Exception as exc:
            logger.warning("Macro refresh failed: %s", exc)

        # 5. Pre-warm the report cache
        logger.info("Daily refresh: rebuilding analytics report…")
        get_analytics_report(force_refresh=True)
        logger.info("Daily refresh complete.")

    except Exception as exc:
        logger.error("Daily refresh error: %s", exc, exc_info=True)


def start_scheduler():
    """Start the background scheduler. Safe to call multiple times."""
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler(daemon=True)
    # 6 PM IST = 12:30 UTC, weekdays only
    _scheduler.add_job(
        _daily_refresh,
        trigger=CronTrigger(hour=12, minute=30, day_of_week="mon-fri"),
        id="daily_price_refresh",
        name="Daily price refresh (6 PM IST)",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler started — daily refresh at 6 PM IST (12:30 UTC) on weekdays.")


def stop_scheduler():
    """Shutdown the scheduler gracefully."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
