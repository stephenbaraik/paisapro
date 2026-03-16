from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum


class RiskProfile(str, Enum):
    conservative = "conservative"
    moderate = "moderate"
    aggressive = "aggressive"


class UserFinancialProfile(BaseModel):
    monthly_income: float = Field(..., gt=0, description="Monthly gross income in INR")
    monthly_expenses: float = Field(..., ge=0, description="Monthly expenses in INR")
    current_savings: float = Field(0, ge=0, description="Existing savings/investments in INR")
    age: int = Field(..., ge=18, le=80)
    risk_profile: RiskProfile = RiskProfile.moderate
    annual_income_growth_pct: float = Field(5.0, ge=0, le=50, description="Expected annual income growth %")


class ForwardPlannerRequest(BaseModel):
    profile: UserFinancialProfile
    monthly_investment: float = Field(..., gt=0, description="Monthly SIP amount in INR")
    annual_stepup_pct: float = Field(10.0, ge=0, le=50, description="Yearly increase in SIP amount %")
    horizon_years: int = Field(..., ge=1, le=40)
    expected_annual_return_pct: Optional[float] = Field(None, description="Override return rate; auto-picked from risk profile if None")
    simulations: int = Field(1000, ge=100, le=10000)


class GoalPlannerRequest(BaseModel):
    profile: UserFinancialProfile
    target_amount: float = Field(..., gt=0, description="Target corpus in INR")
    horizon_years: int = Field(..., ge=1, le=40)
    annual_stepup_pct: float = Field(10.0, ge=0, le=50)
    expected_annual_return_pct: Optional[float] = None


class MonteCarloResult(BaseModel):
    percentile_10: float
    percentile_25: float
    percentile_50: float
    percentile_75: float
    percentile_90: float
    mean: float
    std_dev: float
    probability_of_loss: float
    yearly_expected: list[float]
    yearly_p10: list[float]
    yearly_p90: list[float]


class ForwardPlannerResponse(BaseModel):
    monthly_investment: float
    annual_stepup_pct: float
    horizon_years: int
    expected_annual_return_pct: float
    investable_surplus: float
    recommended_monthly_investment: float
    total_invested: float
    monte_carlo: MonteCarloResult
    asset_allocation: dict[str, float]


class GoalPlannerResponse(BaseModel):
    target_amount: float
    horizon_years: int
    required_monthly_investment: float
    total_invested: float
    expected_annual_return_pct: float
    is_achievable_within_surplus: bool
    investable_surplus: float
    sensitivity: list[dict]
    asset_allocation: dict[str, float]


class AdvisorChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    profile: Optional[UserFinancialProfile] = None
    conversation_history: list[dict] = []


class AdvisorChatResponse(BaseModel):
    reply: str
    suggestions: list[str] = []
