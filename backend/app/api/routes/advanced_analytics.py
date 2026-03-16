"""API routes for advanced analytics: Sector Rotation, GARCH, Macro, Risk Factors, ML Regression."""

from fastapi import APIRouter, HTTPException, Query

from ...schemas.advanced_analytics import (
    SectorRotationResponse,
    VolatilityForecastResponse,
    VolSymbol,
    MacroDashboardResponse,
    RiskFactorRequest,
    RiskFactorResponse,
)
from ...schemas.ml_regression import MLPredictionResponse
from ...services.sector_rotation import get_sector_rotation
from ...services.volatility import get_volatility_forecast, get_vol_symbols
from ...services.macro import get_macro_dashboard
from ...services.risk_factors import get_risk_factors
from ...services.ml_regression import get_ml_prediction

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


# ── ML Regression Predictions ────────────────────────────────────────────────

@router.get("/ml-prediction/{symbol}", response_model=MLPredictionResponse)
def ml_prediction(
    symbol: str,
    horizon: int = Query(30, ge=7, le=90, description="Forecast horizon in days"),
):
    """
    Multi-model ML return forecast (RF, Ridge, GBM) with full evaluation metrics.
    Returns per-model MAE, RMSE, R², directional accuracy, CV MAE, ensemble prediction,
    80% confidence interval, and RF feature importances.
    """
    result = get_ml_prediction(symbol.upper(), horizon)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Insufficient data for {symbol} — need at least 120 trading days",
        )
    return result
