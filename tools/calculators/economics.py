"""Reproducible unit economics, funnel accounting, A/B power, and sensitivity models.

All calculations verify units, denominators, and missing values explicitly so the LLM
never approximates arithmetic in strategy documents.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class EconomicsInput:
    """Inputs for annual incremental gross profit and break-even modeling."""

    baseline_profit_mln_rub: float = 279.0
    target_profit_mln_rub: float = 285.0
    profit_per_paid_month_rub: float = 500.0
    incremental_paid_months: int = 12_000
    direct_cost_per_month_rub: float = 0.0
    extra_support_or_sms_rub: float = 0.0
    other_savings_or_revenue_rub: float = 0.0
    dev_capex_rub: float = 0.0


def _normal_quantile(p: float) -> float:
    """Acklam-style inverse standard normal CDF approximation (pure Python)."""
    if not 0.0 < p < 1.0:
        raise ValueError(f"Probability p must be in (0, 1), got {p}")
    a = [-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
         1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00]
    b = [-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
         6.680131188771972e01, -1.328068155288572e01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
         -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
         3.754408661907416e00]
    plow, phigh = 0.02425, 1.0 - 0.02425
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
               ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1.0)
    if p <= phigh:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r + a[1])*r + a[2])*r + a[3])*r + a[4])*r + a[5]) * q / \
               (((((b[0]*r + b[1])*r + b[2])*r + b[3])*r + b[4])*r + 1.0)
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -(((((c[0]*q + c[1])*q + c[2])*q + c[3])*q + c[4])*q + c[5]) / \
            ((((d[0]*q + d[1])*q + d[2])*q + d[3])*q + 1.0)


def calculate_unit_economics(inp: EconomicsInput) -> dict[str, Any]:
    """Compute incremental gross profit, gap closure, break-even months, and payback cap."""
    gap_rub = (inp.target_profit_mln_rub - inp.baseline_profit_mln_rub) * 1_000_000.0
    net_unit_margin = inp.profit_per_paid_month_rub - inp.direct_cost_per_month_rub
    retention_profit_rub = inp.incremental_paid_months * net_unit_margin
    total_incremental_profit_rub = (
        retention_profit_rub + inp.other_savings_or_revenue_rub - inp.extra_support_or_sms_rub
    )
    projected_profit_mln = inp.baseline_profit_mln_rub + (total_incremental_profit_rub / 1_000_000.0)
    remaining_gap_rub = max(0.0, gap_rub - total_incremental_profit_rub)

    required_paid_months_for_target = (
        math.ceil((gap_rub + inp.extra_support_or_sms_rub - inp.other_savings_or_revenue_rub) / net_unit_margin)
        if net_unit_margin > 0
        else None
    )

    payback_months = None
    if inp.dev_capex_rub > 0 and total_incremental_profit_rub > 0:
        monthly_net_runrate = total_incremental_profit_rub / 12.0
        payback_months = round(inp.dev_capex_rub / monthly_net_runrate, 2)

    return {
        "inputs": asdict(inp),
        "units": {"currency": "RUB", "profit_scale": "RUB (and mln RUB for annual totals)"},
        "annual_gap_to_target_rub": round(gap_rub, 2),
        "net_margin_per_paid_month_rub": round(net_unit_margin, 2),
        "retention_incremental_profit_rub": round(retention_profit_rub, 2),
        "total_incremental_profit_rub": round(total_incremental_profit_rub, 2),
        "projected_annual_profit_mln_rub": round(projected_profit_mln, 3),
        "meets_annual_target": projected_profit_mln >= inp.target_profit_mln_rub,
        "remaining_gap_rub": round(remaining_gap_rub, 2),
        "required_paid_months_to_close_gap": required_paid_months_for_target,
        "max_dev_budget_for_1yr_payback_rub": round(max(0.0, total_incremental_profit_rub), 2),
        "estimated_payback_months_at_dev_capex": payback_months,
    }


def calculate_ab_sample_size(
    baseline_rate: float,
    min_detectable_effect_abs: float,
    alpha: float = 0.05,
    power: float = 0.80,
    weekly_eligible_units: float | None = None,
    observation_window_days: int = 7,
) -> dict[str, Any]:
    """Two-sided two-proportion sample size per arm + recruitment feasibility check."""
    if not (0.0 < baseline_rate < 1.0):
        raise ValueError("baseline_rate must be between 0 and 1")
    treatment_rate = baseline_rate - min_detectable_effect_abs
    if not (0.0 < treatment_rate < 1.0):
        treatment_rate = baseline_rate + min_detectable_effect_abs
    if not (0.0 < treatment_rate < 1.0):
        raise ValueError("Resulting treatment_rate must be between 0 and 1")

    z_alpha = _normal_quantile(1.0 - alpha / 2.0)
    z_beta = _normal_quantile(power)
    p_bar = 0.5 * (baseline_rate + treatment_rate)
    num = (
        z_alpha * math.sqrt(2.0 * p_bar * (1.0 - p_bar))
        + z_beta * math.sqrt(baseline_rate * (1.0 - baseline_rate) + treatment_rate * (1.0 - treatment_rate))
    ) ** 2
    den = (baseline_rate - treatment_rate) ** 2
    n_per_arm = math.ceil(num / den)
    total_n = n_per_arm * 2

    feasibility: dict[str, Any] = {}
    if weekly_eligible_units and weekly_eligible_units > 0:
        recruitment_weeks = total_n / weekly_eligible_units
        total_calendar_weeks = recruitment_weeks + (observation_window_days / 7.0)
        feasibility = {
            "weekly_eligible_units": weekly_eligible_units,
            "recruitment_weeks": round(recruitment_weeks, 2),
            "observation_window_days": observation_window_days,
            "total_calendar_weeks": round(total_calendar_weeks, 2),
            "fits_in_single_quarter_12w": total_calendar_weeks <= 12.0,
        }

    relative_change_pct = ((treatment_rate - baseline_rate) / baseline_rate) * 100.0
    return {
        "baseline_rate": baseline_rate,
        "target_rate": round(treatment_rate, 4),
        "absolute_diff_pp": round((treatment_rate - baseline_rate) * 100.0, 2),
        "relative_change_pct": round(relative_change_pct, 2),
        "alpha": alpha,
        "power": power,
        "n_per_arm": n_per_arm,
        "total_sample_size": total_n,
        "feasibility": feasibility,
    }


def calculate_funnel_balance(
    start_connected: int,
    new_connected: int,
    churned: int,
    active_rate: float,
    addressable_market: int,
    acquisition_cost_rub: float = 0.0,
    baseline_new_connected: int = 0,
) -> dict[str, Any]:
    """Reconcile connected stock (start + new - churned = end), active count, and incremental CAC."""
    end_connected = start_connected + new_connected - churned
    active_end = round(end_connected * active_rate)
    penetration_pct = (end_connected / addressable_market) * 100.0 if addressable_market > 0 else 0.0
    incremental_connections = max(0, new_connected - baseline_new_connected)
    incremental_cac = (
        round(acquisition_cost_rub / incremental_connections, 2)
        if incremental_connections > 0 and acquisition_cost_rub > 0
        else None
    )
    return {
        "start_connected": start_connected,
        "new_connected": new_connected,
        "churned": churned,
        "end_connected": end_connected,
        "active_rate": active_rate,
        "active_end": active_end,
        "addressable_market": addressable_market,
        "addressable_penetration_pct": round(penetration_pct, 2),
        "incremental_vs_baseline_connections": incremental_connections,
        "incremental_cac_rub": incremental_cac,
    }


def run_sensitivity_matrix(
    active_groups_affected: list[int],
    months_retained_gain: list[float],
    net_margin_per_month: float = 500.0,
    fixed_annual_opex_rub: float = 0.0,
) -> list[dict[str, Any]]:
    """Build deterministic sensitivity grid for decision boundary checks."""
    rows: list[dict[str, Any]] = []
    for groups in active_groups_affected:
        for months in months_retained_gain:
            paid_months = round(groups * months)
            net_profit_rub = paid_months * net_margin_per_month - fixed_annual_opex_rub
            rows.append(
                {
                    "affected_units": groups,
                    "avg_extra_paid_months": months,
                    "incremental_paid_months": paid_months,
                    "net_incremental_profit_mln_rub": round(net_profit_rub / 1_000_000.0, 3),
                    "closes_6m_gap": net_profit_rub >= 6_000_000.0,
                }
            )
    return rows
