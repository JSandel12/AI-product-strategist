---
name: 07-strategy-packager
description: Assembles aligned 5-part Product + Communication Strategy, Verification Plan, Q1-Q4 + Year 3 roadmap, resources, risks, and passes linter hook.
---
# Этап 7: Итоговая продуктовая и коммуникационная стратегия

1. Используй структуру `knowledge/templates/strategy_report_template.md` и требования `knowledge/frameworks/strategy_rubric.md`.
2. Проверь согласованность продуктовой и коммуникационной стратегий:
   - ни одно рекламное/продуктовое обещание не выходит за рамки реальных тарифов, задержек обновления остатков и правил согласия;
   - указаны конкретные роли каналов, барьеры понимания и доказательства.
3. Оформи план проверки (метрика пользы, метрика работы сервиса, нежелательные последствия, пороги Stop/Go), план по кварталам Q1–Q4, таблицу прогноза по всем 5 KPI (основной + неблагоприятный сценарий), ориентир 3-го года, человеко-месяцы ресурсов, риски и финальную просьбу на Gate Q1/Q2.
4. Прогони итоговый документ через `uv run python -m tools.strategist_cli lint <file>` (или MCP `strategist_lint_document`) и устрани все ошибки и предупреждения.
5. Сохрани чекпоинт `07-strategy-packager`.
