---
name: 01-task-intake
description: Clarifies PM request, goal, decision-maker, constraints, and allowed sources without asking redundant questions.
---
# Этап 1: Постановка задачи (Task Intake)

1. Проверь активный проект: вызови `strategist_status` (или `uv run python -m tools.strategist_cli status`). Если начинается новый проект — создай его через `init <slug>`.
2. Сформулируй, что уже понятно из запроса и приложенных материалов.
3. Спроси **только те вопросы, без которых нельзя выбрать следующий шаг**:
   - какой конкретный вопрос решается и кто принимает решение;
   - к какому сроку/гейту нужен вывод;
   - какие ограничения (бюджет, разработчики, тарифы, права доступа/согласия) жёсткие;
   - какие источники и материалы разрешены (и запрет на закрытые данные без допуска).
4. Сохрани результат в `projects/<slug>/state/session_state.json` через `strategist_checkpoint`.
