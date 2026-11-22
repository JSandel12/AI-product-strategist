# Claude Code Entrypoint — Стратег Фабрики продуктов

Следуй полному протоколу из [AGENTS.md](./AGENTS.md). Все навыки расположены в `.agents/skills/`, методические стандарты — в `knowledge/`, детерминированный CLI — `uv run python -m tools.strategist_cli`, а MCP-сервер — в `mcp_config.json` / `.cursor/mcp.json`.

При открытии нового сеанса: для продолжения текущей задачи начни с `uv run python -m tools.strategist_cli status` (или MCP `strategist_status`); для новой задачи/продукта создай отдельный проект через `uv run python -m tools.strategist_cli init <new-slug>`.
