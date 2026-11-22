# Стратег Фабрики продуктов — ИИ-папка (Agent Repository)

Репозиторий воспроизводимого ИИ-агента для руководителя цифрового продукта: от размытого бизнес-запроса и разнородных материалов до обоснованной продуктовой и коммуникационной стратегии, плана проверки, реестра решений (ADR) и пересмотра выводов при появлении новых данных.

Разработано для номинации **«ИИ-проект» (MGIMO × AI Challenge — кейс Фабрики Продуктов МегаФона)**. Работает нативно в **Antigravity**, а также в **Cursor**, **Claude Code**, **Windsurf**, **Codex** и через терминальный CLI.

---

## Архитектура и разделение слоёв знаний

```text
├── AGENTS.md / GEMINI.md / CLAUDE.md   # Постоянные инструкции и цикл работы агента
├── .cursor/rules/ & .cursor/mcp.json   # Правила и MCP-конфиг для Cursor
├── mcp_config.json                     # Конфиг MCP-сервера для Antigravity / IDE
├── .agents/
│   ├── hooks.json                      # Lifecycle-хуки (секреты, журнал шагов, восстановление сессии)
│   ├── skills/01..08/SKILL.md          # Пошаговые навыки (Intake -> Research -> Interviews -> UX -> Calc -> Options -> Strategy -> Revision)
│   └── subagents/*.md                  # Специализированные роли (Researcher, Data Analyst, Synthetic Respondent, UX Auditor, Red-Team Critic)
├── knowledge/                          # Методические знания и шаблоны (отделены от данных проекта)
│   ├── frameworks/                     # Стандарты правдивости [ФАКТ | SRC-xx], маршрутизация, экономика A/B
│   └── templates/                      # Шаблоны 5-частной стратегии, гайда интервью, ADR-реестра
├── tools/                              # Детерминированные инструменты (Python CLI + FastMCP + Хуки + БЗ)
│   ├── strategist_cli.py               # Единый CLI
│   ├── mcp_server.py                   # Локальный stdio MCP-сервер
│   ├── routing.py                      # Классификатор задач и маршрутизатор моделей/инструментов
│   ├── kb_index.py                     # Гибридный поиск по БЗ (BM25 + ссылки) + отзыв устаревших записей
│   ├── calculators/economics.py        # Точная юнит-экономика, воронка, А/Б-выборка, чувствительность
│   └── hooks/                          # Проверка цитат, меток фактов, секретов и prompt-injection
├── projects/
│   ├── _template/                      # Чистый шаблон для любой новой задачи
│   └── megafon-family-devices/         # Полный демонстрационный проект по брифу «Связь для близких и собственных устройств»
└── docs/                               # Описание работы, сравнительный бенчмарк и сценарий видеодемонстрации
```

---

## Быстрый старт (без скрытых настроек)

### Предварительные требования
- **Python 3.11+** и менеджер пакетов **`uv`** (опционально можно запускать встроенные калькуляторы на чистом Python, но для `mcp` и `pypdf` рекомендуется `uv`).
- Никакие API-ключи в репозитории не хранятся. Если вы используете внешние API-скрипты, скопируйте `.env.example` в `.env` (файл `.env` исключён в `.gitignore`).

### 1. Установка зависимостей и проверка работоспособности
```powershell
uv sync --all-groups
uv run pytest -v
```

### 2. Запуск в Antigravity / Cursor / Claude Code
1. Откройте папку репозитория как workspace в **Antigravity**, **Cursor** или **Claude Code**.
2. Среда автоматически подхватит `GEMINI.md` / `AGENTS.md` / `.cursor/rules/strategist.mdc`, навыки `.agents/skills/*`, хуки `.agents/hooks.json` и локальный MCP-сервер `product-factory-strategist`.
3. Для запуска нового проекта напишите агенту задачу или выполните:
   ```powershell
   uv run python -m tools.strategist_cli init my-new-product --title "Новый продукт"
   ```
4. Для **продолжения работы после перерыва** откройте **новый чат** и напишите: `продолжи работу по проекту` — агент прочитает `projects/.active_project` и `state/session_state.json` и продолжит с сохранённого этапа без повтора завершённых шагов.

### 3. Основные команды CLI
```powershell
# Проверить состояние активного проекта и накопленные расходы
uv run python -m tools.strategist_cli status

# Подобрать этап, субагента и экономичный уровень модели для задачи
uv run python -m tools.strategist_cli route "Рассчитай прибыль и А/Б выборку для семейного тарифа"

# Детерминированные расчёты (юнит-экономика, А/Б-тест, воронка, чувствительность)
uv run python -m tools.strategist_cli calc economics --paid-months 14000 --direct-cost 25 --extra-opex 400000 --dev-capex 2200000
uv run python -m tools.strategist_cli calc ab --baseline-rate 0.12 --mde 0.03 --weekly-units 400 --obs-days 7

# Поиск по базе знаний и отзыв устаревшей записи
uv run python -m tools.strategist_cli kb search "задержка биллинга"
uv run python -m tools.strategist_cli kb revoke "ADR-001:ASM-001" --reason "Новые данные Q1" --superseded-by "SRC-04"

# Автоматический аудит стратегии (метки фактов, ссылки, альтернативы, утечки секретов)
uv run python -m tools.strategist_cli lint projects/megafon-family-devices/outputs/strategy_v1.md

# Пересмотр стратегии при поступлении новых данных
uv run python -m tools.strategist_cli revise --fact "Задержка биллинга до 4 часов и поток 200 групп/нед." --source-id SRC-04

# Воспроизводимый бенчмарк (SEED=42)
uv run python -m tools.strategist_cli benchmark
```

---

## Демонстрационный проект и документация
- **Исходный бриф:** [primer_brifa.pdf](projects/megafon-family-devices/inputs/primer_brifa.pdf) и постраничная выгрузка [primer_brifa_extracted.md](projects/megafon-family-devices/inputs/primer_brifa_extracted.md)
- **Итоговая стратегия (v1):** [strategy_v1.md](projects/megafon-family-devices/outputs/strategy_v1.md)
- **Демонстрация пересмотра при новых данных (v2):** [strategy_v2_revision_demo.md](projects/megafon-family-devices/outputs/strategy_v2_revision_demo.md)
- **Реестр решений (ADR):** [adr_ledger.yaml](projects/megafon-family-devices/decisions/adr_ledger.yaml)
- **Подробное описание системы (архитектура, промпты, расходы, ограничения):** [docs/description.md](docs/description.md) ([PDF](docs/description.pdf))
