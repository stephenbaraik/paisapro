from fastapi import APIRouter
from ...schemas.financial import (
    ForwardPlannerRequest, ForwardPlannerResponse,
    GoalPlannerRequest, GoalPlannerResponse,
)
from ...services.financial_engine import (
    calculate_investable_surplus,
    recommend_monthly_investment,
    get_return_assumptions,
    calculate_sip_future_value,
    calculate_total_invested,
    solve_required_sip,
    build_sensitivity_table,
)
from ...services.monte_carlo import run_simulation

router = APIRouter(prefix="/planner", tags=["Planner"])


@router.post("/forward", response_model=ForwardPlannerResponse)
def forward_planner(req: ForwardPlannerRequest):
    """
    Given monthly SIP + horizon → project wealth with Monte Carlo simulation.
    """
    assumptions = get_return_assumptions(req.profile.risk_profile)
    return_pct = req.expected_annual_return_pct or assumptions["expected"]
    std_dev = assumptions["std_dev"]

    investable_surplus = calculate_investable_surplus(req.profile)
    recommended_sip = recommend_monthly_investment(req.profile)
    total_invested = calculate_total_invested(req.monthly_investment, req.horizon_years, req.annual_stepup_pct)

    mc = run_simulation(
        monthly_investment=req.monthly_investment,
        annual_return_pct=return_pct,
        annual_std_dev_pct=std_dev,
        years=req.horizon_years,
        annual_stepup_pct=req.annual_stepup_pct,
        existing_corpus=req.profile.current_savings,
        simulations=req.simulations,
    )

    return ForwardPlannerResponse(
        monthly_investment=req.monthly_investment,
        annual_stepup_pct=req.annual_stepup_pct,
        horizon_years=req.horizon_years,
        expected_annual_return_pct=return_pct,
        investable_surplus=investable_surplus,
        recommended_monthly_investment=recommended_sip,
        total_invested=total_invested,
        monte_carlo=mc,
        asset_allocation=assumptions["allocation"],
    )


@router.post("/goal", response_model=GoalPlannerResponse)
def goal_planner(req: GoalPlannerRequest):
    """
    Given a target corpus + horizon → calculate required monthly SIP.
    """
    assumptions = get_return_assumptions(req.profile.risk_profile)
    return_pct = req.expected_annual_return_pct or assumptions["expected"]

    investable_surplus = calculate_investable_surplus(req.profile)
    required_sip = solve_required_sip(
        target_amount=req.target_amount,
        annual_return_pct=return_pct,
        years=req.horizon_years,
        annual_stepup_pct=req.annual_stepup_pct,
        existing_corpus=req.profile.current_savings,
    )
    total_invested = calculate_total_invested(required_sip, req.horizon_years, req.annual_stepup_pct)
    sensitivity = build_sensitivity_table(
        target_amount=req.target_amount,
        horizon_years=req.horizon_years,
        annual_stepup_pct=req.annual_stepup_pct,
        existing_corpus=req.profile.current_savings,
        base_return_pct=return_pct,
    )

    return GoalPlannerResponse(
        target_amount=req.target_amount,
        horizon_years=req.horizon_years,
        required_monthly_investment=required_sip,
        total_invested=total_invested,
        expected_annual_return_pct=return_pct,
        is_achievable_within_surplus=required_sip <= investable_surplus,
        investable_surplus=investable_surplus,
        sensitivity=sensitivity,
        asset_allocation=assumptions["allocation"],
    )
