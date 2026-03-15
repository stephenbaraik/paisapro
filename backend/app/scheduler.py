"""
Daily data refresh scheduler.

Runs at 6 PM IST (12:30 UTC) on weekdays to:
  1. Fetch today's prices for all tracked stocks via yfinance → Supabase
  2. Clear the analytics in-memory cache so next request rebuilds with fresh data
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _daily_refresh():
    """Fetch latest prices and invalidate analytics cache."""
    try:
        from .services.analytics import (
            get_stock_universe, _get_cached_df, _df_cache, _report_cache,
            get_analytics_report,
        )

        universe = get_stock_universe()
        logger.info("Daily refresh: fetching latest prices for %d stocks…", len(universe))

        # 1. Clear the in-memory cache so _get_cached_df re-fetches from yfinance
        _df_cache.clear()

        # 2. Force-fetch fresh data for each stock (saves to Supabase automatically)
        success = 0
        for sym in universe:
            try:
                df = _get_cached_df(sym, "1y")
                if df is not None and not df.empty:
                    success += 1
            except Exception as exc:
                logger.warning("Refresh failed for %s: %s", sym, exc)

        logger.info("Daily refresh: %d/%d stocks updated.", success, len(universe))

        # 3. Invalidate the report cache so next request rebuilds
        import app.services.analytics as svc
        svc._report_cache = (None, 0.0)

        # 4. Pre-warm the report cache
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
