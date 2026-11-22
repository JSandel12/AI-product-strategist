---
name: 05-data-economics
description: Runs reproducible Python calculators for unit economics, funnel reconciliation, break-even boundaries, sensitivity, and A/B sample size.
---
# Этап 5: Анализ данных, юнит-экономика и дизайн проверки

**Запрещено считать в уме или приближённо.** Все числа обязаны пройти через `tools/calculators/economics.py` (CLI `calc` или MCP `strategist_calc_*`).

1. Проверь единицы измерения, периоды, знаменатели и пропуски (согласно `knowledge/frameworks/experiment_economics.md`).
2. Сбалансируй воронку: `Начало + Новые - Выбывшие = Конец`, исключи двойной счёт каналов, проверь знаменатель активации (Intent-to-Treat).
3. Рассчитай:
   - вклад удержания (500 руб./доп. оплаченный месяц минус прямые расходы);
   - границу безубыточности и предельную сумму вложений в разработку;
   - сетку чувствительности (базовый и неблагоприятный сценарии);
   - размер выборки A/B и проверку темпа набора за отведённые недели пилота.
4. Сохрани JSON/итоги расчётов в `projects/<slug>/research/calculations.json`.
