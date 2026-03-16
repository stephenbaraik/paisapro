"""
Monte Carlo simulation engine for investment projections.
Runs N simulations with randomized annual returns drawn from a normal distribution.
"""

import numpy as np
from ..schemas.financial import MonteCarloResult


def run_simulation(
    monthly_investment: float,
    annual_return_pct: float,
    annual_std_dev_pct: float,
    years: int,
    annual_stepup_pct: float = 0.0,
    existing_corpus: float = 0.0,
    simulations: int = 1000,
    seed: int = 42,
) -> MonteCarloResult:
    """
    Runs Monte Carlo simulation for SIP investments.

    Each simulation draws a random annual return (normal distribution) per year.
    Returns percentile outcomes and year-by-year trajectory arrays.
    """
    rng = np.random.default_rng(seed)
    final_values = np.zeros(simulations)

    # Store yearly medians for trajectory chart
    yearly_matrix = np.zeros((simulations, years))

    for sim in range(simulations):
        corpus = existing_corpus
        current_sip = monthly_investment

        # Draw annual returns for all years at once
        annual_returns = rng.normal(
            loc=annual_return_pct / 100,
            scale=annual_std_dev_pct / 100,
            size=years,
        )

        for year_idx, annual_r in enumerate(annual_returns):
            monthly_r = annual_r / 12
            for _ in range(12):
                corpus = corpus * (1 + monthly_r) + current_sip
            # Apply step-up at year end
            current_sip *= (1 + annual_stepup_pct / 100)
            yearly_matrix[sim, year_idx] = corpus

        final_values[sim] = corpus

    # Compute percentiles for final year
    p10, p25, p50, p75, p90 = np.percentile(final_values, [10, 25, 50, 75, 90])

    # Year-by-year percentile trajectories
    yearly_expected = np.mean(yearly_matrix, axis=0).tolist()
    yearly_p10 = np.percentile(yearly_matrix, 10, axis=0).tolist()
    yearly_p90 = np.percentile(yearly_matrix, 90, axis=0).tolist()

    probability_of_loss = float(np.mean(final_values < existing_corpus)) * 100

    return MonteCarloResult(
        percentile_10=round(float(p10), 2),
        percentile_25=round(float(p25), 2),
        percentile_50=round(float(p50), 2),
        percentile_75=round(float(p75), 2),
        percentile_90=round(float(p90), 2),
        mean=round(float(np.mean(final_values)), 2),
        std_dev=round(float(np.std(final_values)), 2),
        probability_of_loss=round(probability_of_loss, 2),
        yearly_expected=[round(v, 2) for v in yearly_expected],
        yearly_p10=[round(v, 2) for v in yearly_p10],
        yearly_p90=[round(v, 2) for v in yearly_p90],
    )
