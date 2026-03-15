import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import get_settings
from .api.routes import planner, advisor, stocks, analytics

logger = logging.getLogger(__name__)
settings = get_settings()


def _prewarm_cache():
    """Pre-warm: load all stock data from Supabase, then build analytics report."""
    try:
        from .services.analytics import preload_stock_data, get_analytics_report
        logger.info("Pre-warming: loading stock data from Supabase…")
        count = preload_stock_data()
        logger.info("Loaded %d stocks into cache. Building analytics report…", count)
        get_analytics_report(force_refresh=False)
        logger.info("Analytics cache pre-warmed successfully.")
    except Exception as exc:
        logger.warning("Cache pre-warm failed (non-fatal): %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from .scheduler import start_scheduler, stop_scheduler

    # Startup: cache warm + scheduler
    thread = threading.Thread(target=_prewarm_cache, daemon=True)
    thread.start()
    start_scheduler()

    yield

    # Shutdown
    stop_scheduler()


app = FastAPI(
    title="AI Investment Advisor",
    description="Indian market investment planning with Monte Carlo simulations and AI advisory",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(planner.router, prefix="/api/v1")
app.include_router(advisor.router, prefix="/api/v1")
app.include_router(stocks.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok", "service": "AI Investment Advisor Backend"}
