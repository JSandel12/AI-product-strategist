"""Local Stdio MCP Server exposing Product Strategist deterministic tools.

Compatible with Antigravity (mcp_config.json), Cursor (.cursor/mcp.json), and Claude Code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from mcp.server.mcpserver import MCPServer
except ImportError:  # pragma: no cover - compatibility with mcp<2
    from mcp.server.fastmcp import FastMCP as MCPServer

from tools.calculators.economics import (
    EconomicsInput,
    calculate_ab_sample_size,
    calculate_unit_economics,
)
from tools.common import PROJECTS_DIR, get_active_project_slug, read_json, utc_now_iso, write_json
from tools.hooks.validators import lint_strategy_document
from tools.kb_index import revoke_record, search_kb
from tools.routing import classify_and_route

mcp = MCPServer("product-factory-strategist")


@mcp.tool()
def strategist_status(project_slug: str = "") -> dict[str, Any]:
    """Return active project workflow stage, next action, and open gaps for seamless resume."""
    slug = get_active_project_slug(project_slug or None)
    state = read_json(PROJECTS_DIR / slug / "state" / "session_state.json", default={}) or {}
    return {"active_project": slug, "state": state}


@mcp.tool()
def strategist_checkpoint(stage: str, summary: str, next_action: str = "", project_slug: str = "") -> dict[str, Any]:
    """Persist current stage checkpoint so work can resume cleanly in a brand-new chat."""
    slug = get_active_project_slug(project_slug or None)
    state_path = PROJECTS_DIR / slug / "state" / "session_state.json"
    state = read_json(state_path, default={"project_slug": slug, "completed_stages": []}) or {}
    prev = state.get("current_stage")
    completed = list(state.get("completed_stages", []))
    if prev and prev != stage and prev not in completed:
        completed.append(prev)
    state.update(
        {
            "current_stage": stage,
            "completed_stages": completed,
            "last_summary": summary,
            "next_action": next_action or state.get("next_action", ""),
            "updated_at": utc_now_iso(),
        }
    )
    write_json(state_path, state)
    return {"status": "checkpointed", "project": slug, "state": state}


@mcp.tool()
def strategist_route(task_text: str, has_images_or_video: bool = False) -> dict[str, Any]:
    """Classify a PM request and recommend workflow skill, model tier, tools, and fallback."""
    return classify_and_route(task_text, has_images_or_video=has_images_or_video)


@mcp.tool()
def strategist_calc_economics(
    incremental_paid_months: int,
    direct_cost_per_month_rub: float = 0.0,
    extra_support_or_sms_rub: float = 0.0,
    other_savings_or_revenue_rub: float = 0.0,
    dev_capex_rub: float = 0.0,
    baseline_profit_mln_rub: float = 279.0,
    target_profit_mln_rub: float = 285.0,
    profit_per_paid_month_rub: float = 500.0,
) -> dict[str, Any]:
    """Deterministically calculate incremental gross profit, 6M gap closure, and payback."""
    return calculate_unit_economics(
        EconomicsInput(
            baseline_profit_mln_rub=baseline_profit_mln_rub,
            target_profit_mln_rub=target_profit_mln_rub,
            profit_per_paid_month_rub=profit_per_paid_month_rub,
            incremental_paid_months=incremental_paid_months,
            direct_cost_per_month_rub=direct_cost_per_month_rub,
            extra_support_or_sms_rub=extra_support_or_sms_rub,
            other_savings_or_revenue_rub=other_savings_or_revenue_rub,
            dev_capex_rub=dev_capex_rub,
        )
    )


@mcp.tool()
def strategist_calc_ab(
    baseline_rate: float,
    min_detectable_effect_abs: float,
    weekly_eligible_units: float = 0.0,
    observation_window_days: int = 7,
    alpha: float = 0.05,
    power: float = 0.80,
) -> dict[str, Any]:
    """Compute required A/B sample size per arm and test whether pilot weeks suffice."""
    return calculate_ab_sample_size(
        baseline_rate=baseline_rate,
        min_detectable_effect_abs=min_detectable_effect_abs,
        alpha=alpha,
        power=power,
        weekly_eligible_units=weekly_eligible_units or None,
        observation_window_days=observation_window_days,
    )


@mcp.tool()
def strategist_kb_search(
    query: str,
    project_slug: str = "",
    top_k: int = 5,
    include_agent_outputs: bool = False,
) -> list[dict[str, Any]]:
    """Search separated KB tiers (methodology, inputs, sources); past outputs flagged as unverified."""
    slug = get_active_project_slug(project_slug or None)
    return search_kb(query=query, project_slug=slug, top_k=top_k, include_agent_outputs=include_agent_outputs)


@mcp.tool()
def strategist_kb_revoke(record_id: str, reason: str, superseded_by: str = "", project_slug: str = "") -> dict[str, Any]:
    """Revoke or supersede an outdated knowledge record so stale facts do not pollute decisions."""
    slug = get_active_project_slug(project_slug or None)
    return revoke_record(slug, record_id, reason, superseded_by)


@mcp.tool()
def strategist_lint_document(file_path: str, project_slug: str = "") -> dict[str, Any]:
    """Lint a strategy report for truth tags, citation validity, option diversity, and secret leaks."""
    slug = get_active_project_slug(project_slug or None)
    sources_path = PROJECTS_DIR / slug / "research" / "sources.yaml"
    return lint_strategy_document(Path(file_path), sources_yaml_path=sources_path)


if __name__ == "__main__":
    mcp.run()
