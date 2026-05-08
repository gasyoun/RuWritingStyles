# Project: RuWritingStyles Agent Engineering

Этот проект следует строгому агентскому протоколу и персонализированному роадмапу.

**При каждом начале сессии:**
1. Прочитать [GEMINI_ROADMAP.md](./GEMINI_ROADMAP.md) — актуальный план действий.
2. Прочитать [changelog.md](./changelog.md) — последние изменения.
3. Определить текущий шаг из раздела "Следующее действие" в роадмапе.
4. Если меняется форма JSON-артефакта, синхронно обновить `schemas/`, `tools/validate_project.py`, тесты и документацию.

**Основные принципы (2026 Standard):**
- **Harness Over Model**: Логика обвязки (Council, Verifier) приоритетнее промптов.
- **Philological Fidelity**: Никогда не упрощать эпистемические маркеры ("по-видимому", "вероятно") без явного разрешения кластера.
- **Eval-Centricity**: Любое изменение в логике должно проверяться через `eval-suite`; текущий manifest содержит 33 кейса, а MVP-набор содержит 6 стилей.

**Канонический роадмап:** https://github.com/codejunkie99/agent-roadmap-2026
**Филологические кластеры:** 8 лингвистических + 9 литературоведческих (см. `styles/manifest.yml` и `docs/`).

**Минимальный локальный gate:**

```bash
python -m compileall -q src tools tests
python tools/validate_project.py
python -m unittest discover -s tests
rws eval-regression --provider mock
cd web && npm run lint && npm run build
```
