"""Schemas for ML regression predictions and model evaluations."""

from __future__ import annotations
from pydantic import BaseModel


class FeatureImportance(BaseModel):
    feature: str
    importance: float


class ModelEval(BaseModel):
    mae: float                   # Mean Absolute Error (% return)
    rmse: float                  # Root Mean Square Error (% return)
    r2: float                    # Coefficient of determination
    directional_accuracy: float  # % of correct up/down predictions
    cv_mae: float                # Time-series cross-validated MAE
    sharpe_ratio: float = 0.0    # Annualised Sharpe of signal strategy (sign(pred) * actual return)


class ModelPrediction(BaseModel):
    predicted_return: float   # % return over horizon
    predicted_price: float


class MLPredictionResponse(BaseModel):
    symbol: str
    company_name: str
    current_price: float
    horizon_days: int

    # Per-model predictions and evaluations
    predictions: dict[str, ModelPrediction]   # keys: rf, ridge, gbm
    evaluations: dict[str, ModelEval]         # keys: rf, ridge, gbm

    # Ensemble output
    ensemble_return: float
    ensemble_price: float
    ci_low: float    # 80% confidence interval lower bound (price)
    ci_high: float   # 80% confidence interval upper bound (price)

    # Agreement: lower std = models agree more (0–100 scale)
    model_agreement_score: float

    feature_importances: list[FeatureImportance]
    best_model: str   # model with lowest CV MAE

    generated_at: str
