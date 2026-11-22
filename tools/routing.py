"""Task classifier & cost/quality-aware model/tool router with fallback recovery."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class RouteDecision:
    """Routing recommendation for a strategist workflow task."""

    stage: str
    skill: str
    subagent: str
    compute_tier: str
    recommended_model_class: str
    deterministic_tools: list[str]
    fallback_on_failure: str
    rationale: str
    estimated_cost_rub: float


STAGE_SIGNALS: list[tuple[str, str, str, list[str], str, float]] = [
    (
        "data_economics",
        "05-data-economics",
        "data-analyst",
        [r"расч[её]т", r"прибыл", r"окупаем", r"воронк", r"выборк", r"a/b", r"unit", r"экономик", r"прогноз", r"таблиц"],
        "deterministic_python + fast_tier",
        1.5,
    ),
    (
        "synthetic_interview",
        "03-synthetic-interview",
        "synthetic-respondent",
        [r"интервью", r"респондент", r"персон", r"опрос", r"гай[д|д]", r"interview"],
        "fast_tier",
        4.0,
    ),
    (
        "ux_audit",
        "04-ux-audit",
        "ux-auditor",
        [r"ux", r"ui", r"интерфейс", r"экран", r"скрин", r"путь\s+клиента", r"композиц", r"кнопк"],
        "multimodal_reasoning",
        6.0,
    ),
    (
        "options_redteam",
        "06-options-redteam",
        "red-team-critic",
        [r"вариант", r"альтернатив", r"возражен", r"риск", r"критик", r"red.?team", r"оставить\s+как\s+есть"],
        "reasoning_tier",
        12.0,
    ),
    (
        "decision_revision",
        "08-decision-revision",
        "researcher",
        [r"пересмотр", r"нов(ые|ых)\s+данн", r"adr", r"обнов", r"устарел", r"отклон", r"revise"],
        "reasoning_tier + deterministic_python",
        7.0,
    ),
    (
        "strategy_packager",
        "07-strategy-packager",
        "red-team-critic",
        [r"стратег", r"квартал", r"коммуникац", r"план\s+проверк", r"итог", r"документ", r"финал"],
        "reasoning_tier + deterministic_python",
        14.0,
    ),
    (
        "research_sources",
        "02-research-sources",
        "researcher",
        [r"исслед", r"источник", r"пробел", r"анализ\s+рынка", r"бриф", r"pdf", r"данн"],
        "fast_tier + deterministic_python",
        5.0,
    ),
    (
        "task_intake",
        "01-task-intake",
        "researcher",
        [r"постав", r"уточн", r"запрос", r"бриф", r"начн", r"старт", r"цел"],
        "fast_tier",
        2.0,
    ),
]


def classify_and_route(task_text: str, has_images_or_video: bool = False) -> dict[str, Any]:
    """Score task features and select optimal process, model tier, tools, and fallback."""
    lowered = task_text.lower()
    scores: dict[str, int] = {}
    for stage, _, _, patterns, _, _ in STAGE_SIGNALS:
        scores[stage] = sum(1 for p in patterns if re.search(p, lowered))

    if has_images_or_video:
        scores["ux_audit"] = scores.get("ux_audit", 0) + 3

    best_stage = max(scores, key=lambda k: scores[k])
    if scores[best_stage] == 0:
        best_stage = "task_intake"

    selected = next(row for row in STAGE_SIGNALS if row[0] == best_stage)
    stage, skill, subagent, _, tier, cost_rub = selected

    tools_map = {
        "data_economics": ["tools/calculators/economics.py", "tools/strategist_cli.py calc"],
        "research_sources": ["tools/kb_index.py", "tools/hooks/validators.py"],
        "decision_revision": ["tools/kb_index.py", "tools/strategist_cli.py revise"],
        "strategy_packager": ["tools/hooks/validators.py", "tools/strategist_cli.py lint"],
    }
    fallback_map = {
        "deterministic_python + fast_tier": "Run pure-Python CLI directly; if fast LLM unavailable, downgrade to template + manual review.",
        "fast_tier": "If fast tier rate-limited, switch to secondary fast model or interactive structured template.",
        "multimodal_reasoning": "If vision API unavailable, require textual UI event log + explicit [НЕДОСТАТОК ДАННЫХ] gap.",
        "reasoning_tier": "If reasoning tier unavailable, decompose into 2 fast-tier passes (generate -> red-team checklist).",
        "reasoning_tier + deterministic_python": "Always run deterministic validators first; split synthesis if context tight.",
        "fast_tier + deterministic_python": "Use local KB BM25 index without external web search when offline.",
    }
    model_class_map = {
        "deterministic_python + fast_tier": "Python stdlib + Fast/Economical LLM (e.g., Flash / Haiku / GPT-4o-mini)",
        "fast_tier": "Fast/Economical LLM (e.g., Flash / Haiku / GPT-4o-mini)",
        "multimodal_reasoning": "Multimodal Vision-Capable LLM (only when images/audio/video attached)",
        "reasoning_tier": "Deep Reasoning LLM (e.g., Gemini Pro / Opus / Sonnet / o3-mini)",
        "reasoning_tier + deterministic_python": "Deep Reasoning LLM + Python Validators",
        "fast_tier + deterministic_python": "Fast/Economical LLM + Local Python KB Index",
    }

    decision = RouteDecision(
        stage=stage,
        skill=skill,
        subagent=subagent,
        compute_tier=tier,
        recommended_model_class=model_class_map[tier],
        deterministic_tools=tools_map.get(stage, ["tools/strategist_cli.py status"]),
        fallback_on_failure=fallback_map[tier],
        rationale=f"Matched stage '{stage}' (signal score={scores[best_stage]}). Economizes reasoning tokens by delegating arithmetic/linting to Python.",
        estimated_cost_rub=cost_rub,
    )
    return {"decision": asdict(decision), "all_stage_scores": scores}
