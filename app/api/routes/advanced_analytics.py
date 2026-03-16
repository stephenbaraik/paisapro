"""API routes for advanced analytics: Sector Rotation, GARCH, Macro, Risk Factors."""

from fastapi import APIRouter, HTTPException, Query

from ...schemas.advanced_analytics import (
    SectorRotationResponse,
    VolatilityForecastResponse,
    VolSymbol,
    MacroDashboardResponse,
    RiskFactorRequest,
    RiskFactorResponse,
)
from ...services.sector_rotation import get_sector_rotation
from ...services.volatility import get_volatility_forecast, get_vol_symbols
from ...services.macro import get_macro_dashboard
from ...services.risk_factors import get_risk_factors

router = APIRouter(prefix="/advanced", tags=["Advanced Analytics"])


# ── Sector Rotation ──────────────────────────────────────────────────────────

@router.get("/sector-rotation", response_model=SectorRotationResponse)
async def sector_rotation(force: bool = Query(False)):
    """Sector momentum rankings, rotation signals, and market phase."""
    try:
        return await get_sector_rotation(force=force)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Volatility Forecasting ───────────────────────────────────────────────────

@router.get("/volatility/{symbol}", response_model=VolatilityForecastResponse)
async def volatility_forecast(symbol: str):
    """GARCH(1,1) volatility forecast with vol cones and regime detection."""
    try:
        return await get_volatility_forecast(symbol)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/volatility-symbols", response_model=list[VolSymbol])
async def volatility_symbols():
    """List available symbols for volatility analysis."""
    return await get_vol_symbols()


# ── Macro Dashboard ──────────────────────────────────────────────────────────

@router.get("/macro", response_model=MacroDashboardResponse)
async def macro_dashboard(force: bool = Query(False)):
    """Macro indicators, correlations, and market regime classification."""
    try:
        return await get_macro_dashboard(force=force)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Risk Factor Decomposition ────────────────────────────────────────────────

@router.post("/risk-factors", response_model=RiskFactorResponse)
async def risk_factors(req: RiskFactorRequest):
    """Fama-French-style factor decomposition for given stocks."""
    try:
        return await get_risk_factors(req.symbols)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
