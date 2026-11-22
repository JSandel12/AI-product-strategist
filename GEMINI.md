# Antigravity Entrypoint — Стратег Фабрики продуктов

Следуй полному протоколу из [AGENTS.md](./AGENTS.md), используя нативные навыки `.agents/skills/*/SKILL.md`, субагентов `.agents/subagents/*.md`, хуки `.agents/hooks.json` и детерминированные инструменты через MCP (`mcp_config.json`) или CLI (`uv run python -m tools.strategist_cli ...`).

При открытии нового чата:
- Если пользователь просит **продолжить** текущий проект — проверь состояние (`strategist_status` или `uv run python -m tools.strategist_cli status`) и продолжай с сохранённого этапа без повторного прогона завершённых шагов.
- Если пользователь ставит **новую задачу / новый продукт** — инициализируй новый изолированный проект (`uv run python -m tools.strategist_cli init <new-slug>`) и начни с `01-task-intake`, не смешивая его с `megafon-family-devices`.
