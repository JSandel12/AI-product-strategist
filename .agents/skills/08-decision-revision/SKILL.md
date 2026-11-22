---
name: 08-decision-revision
description: Maintains post-decision ADR ledger and propagates new data to identify stale assumptions, revoke outdated KB entries, and publish strategy v2 diffs.
---
# Этап 8: Поддержка решений и пересмотр при новых данных

1. После утверждения стратегии оформи `projects/<slug>/decisions/adr_ledger.yaml` (по шаблону `knowledge/templates/adr_template.yaml`): решение -> ответственный -> метрики -> пороговые условия пересмотра.
2. Когда приходят новые данные или меняется вводное условие:
   - запусти `uv run python -m tools.strategist_cli revise --fact "<новое сведение>" --source-id "<SRC-xx>"`;
   - если устарел прежний вывод/запись в БЗ — отзови её через `kb revoke <id> --reason "..." --superseded-by "..."`;
   - пересчитай экономику/выборку через `tools/calculators/economics.py`;
   - выпусти обновлённую версию стратегии (`v2`) или лист изменений с явным указанием: что устарело, что изменилось и какое решение нужно принять руководителю **прямо сейчас**.
