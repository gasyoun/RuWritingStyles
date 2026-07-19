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
- **Eval-Centricity**: Любое изменение в логике должно проверяться через `eval-suite`; текущий manifest содержит 52 кейса, из которых 6 детерминированно проходят на mock, а MVP-набор содержит 6 стилей.
- **Agentic Autonomy (v2.4)**: Агенты обязаны использовать инструменты (Zotero, OpenAlex, FTS5) для подтверждения гипотез; галлюцинации библиографии считаются критическим отказом.

**Канонический роадмап:** https://github.com/codejunkie99/agent-roadmap-2026
**Филологические кластеры:** 8 лингвистических + 9 литературоведческих (см. `styles/manifest.yml` и `docs/`).

**Минимальный локальный gate:**

```bash
python -m compileall -q src tools tests
python tools/validate_project.py
python -m pytest -q
python scripts/ci-eval-gate.py
cd web && npm ci && npm test && npm run lint && npm run build
cd ../obsidian-plugin && npm ci && npm run build && npm test
cd .. && python -m build --wheel --sdist
python scripts/verify-runtime-assets.py dist/*.whl dist/*.tar.gz
```

CI also runs clean-wheel consumers on Ubuntu/Windows (Python 3.10/3.14) and a Docker API/SPA/mock-run smoke; all jobs feed strict `CI / Required gate`.
