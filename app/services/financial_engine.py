"""
Core financial calculation engine.
Handles SIP calculations, investable surplus, and asset allocation.
"""

from ..schemas.financial import RiskProfile, UserFinancialProfile

# Historical average annual returns for Indian markets (post-inflation adjusted)
RETURN_ASSUMPTIONS = {
    RiskProfile.conservative: {
        "expected": 9.0,   # FDs + debt mutual funds + some equity
        "std_dev": 4.0,
        "allocation": {"Large Cap Equity": 20, "Debt Funds": 50, "Gold": 15, "Liquid Funds": 15},
    },
    RiskProfile.moderate: {
        "expected": 12.0,  # Diversified equity + debt mix
        "std_dev": 8.0,
        "allocation": {"Large Cap Equity": 40, "Mid Cap Equity": 15, "Debt Funds": 30, "Gold": 10, "Liquid Funds": 5},
    },
    RiskProfile.aggressive: {
        "expected": 15.0,  # Heavy equity, Nifty-like returns
        "std_dev": 14.0,
        "allocation": {"Large Cap Equity": 40, "Mid Cap Equity": 25, "Small Cap Equity": 20, "Debt Funds": 10, "Gold": 5},
    },
}

# 50/30/20 rule - invest at least 20% of income
MINIMUM_INVESTMENT_RATIO = 0.20
RECOMMENDED_INVESTMENT_RATIO = 0.30


def calculate_investable_surplus(profile: UserFinancialProfile) -> float:
    """Returns how much the user can invest monthly after expenses."""
    surplus = profile.monthly_income - profile.monthly_expenses
    return max(0.0, surplus)


def recommend_monthly_investment(profile: UserFinancialProfile) -> float:
    """
    Recommends a monthly SIP amount using the 30% rule,
    capped by actual investable surplus.
    """
    surplus = calculate_investable_surplus(profile)
    recommended = profile.monthly_income * RECOMMENDED_INVESTMENT_RATIO
    # Don't suggest more than what they can afford
    return min(recommended, surplus)


def get_return_assumptions(risk_profile: RiskProfile) -> dict:
    return RETURN_ASSUMPTIONS[risk_profile]


def calculate_sip_future_value(
    monthly_investment: float,
    annual_return_pct: float,
    years: int,
    annual_stepup_pct: float = 0.0,
    existing_corpus: float = 0.0,
) -> float:
    """
    Calculates the future value of a SIP with optional step-up.
    Formula: Standard SIP FV with yearly step-up compound.
    """
    monthly_return = annual_return_pct / 100 / 12
    total_months = years * 12
    fv = existing_corpus * ((1 + monthly_return) ** total_months)

    current_sip = monthly_investment
    for year in range(years):
        year_fv = current_sip * (
            ((1 + monthly_return) ** 12 - 1) / monthly_return
        ) * (1 + monthly_return) ** ((years - year - 1) * 12)
        fv += year_fv
        current_sip *= (1 + annual_stepup_pct / 100)

    return round(fv, 2)


def calculate_total_invested(
    monthly_investment: float,
    years: int,
    annual_stepup_pct: float = 0.0,
) -> float:
    """Total principal invested over the period (accounting for step-up)."""
    total = 0.0
    current_sip = monthly_investment
    for _ in range(years):
        total += current_sip * 12
        current_sip *= (1 + annual_stepup_pct / 100)
    return round(total, 2)


def solve_required_sip(
    target_amount: float,
    annual_return_pct: float,
    years: int,
    annual_stepup_pct: float = 0.0,
    existing_corpus: float = 0.0,
) -> float:
    """
    Binary search to find the monthly SIP needed to reach target_amount.
    Returns required monthly investment in INR.
    """
    # Subtract existing corpus growth from target
    monthly_return = annual_return_pct / 100 / 12
    total_months = years * 12
    corpus_growth = existing_corpus * ((1 + monthly_return) ** total_months)
    adjusted_target = max(0, target_amount - corpus_growth)

    if adjusted_target <= 0:
        return 0.0

    lo, hi = 1.0, adjusted_target
    for _ in range(100):
        mid = (lo + hi) / 2
        fv = calculate_sip_future_value(mid, annual_return_pct, years, annual_stepup_pct, 0)
        if fv < adjusted_target:
            lo = mid
        else:
            hi = mid
        if abs(hi - lo) < 1:
            break

    return round((lo + hi) / 2, 2)


def build_sensitivity_table(
    target_amount: float,
    horizon_years: int,
    annual_stepup_pct: float,
    existing_corpus: float,
    base_return_pct: float,
) -> list[dict]:
    """
    Returns a sensitivity table showing required SIP at ±2%, ±4% return rates.
    """
    offsets = [-4, -2, 0, 2, 4]
    rows = []
    for offset in offsets:
        rate = max(1.0, base_return_pct + offset)
        required = solve_required_sip(target_amount, rate, horizon_years, annual_stepup_pct, existing_corpus)
        rows.append({
            "annual_return_pct": rate,
            "required_monthly_sip": required,
            "total_invested": calculate_total_invested(required, horizon_years, annual_stepup_pct),
        })
    return rows
