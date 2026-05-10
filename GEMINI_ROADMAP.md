# Gemini Agent Roadmap: RuWritingStyles

*Персонализировано на основе https://github.com/codejunkie99/agent-roadmap-2026 и внутренних docs/ 2026-05-08.*


## [2.3.0] - 2026-05-08

## Профиль проекта
- **Уровень**: Сложная многоагентная система (Council + Verifier).
- **Стек**: Python + JSON Schema + Markdown Styles.
- **Цель**: Создание "Gemini-Ready" филологической лаборатории с 17+ кластерами стилей.
- **Текущая Фаза**: v2.3.0 production-ready: CI Golden Gate (33/33 cases), service-layer refactoring, and security hooks stabilized.

## План внедрения (17 кластеров)

### Фаза A: Рефакторинг Манифеста (Шаги G-01, L-01, L-02)
- [x] Обновить `styles/manifest.yml`: добавить поля `cluster`, `level`, `extends`.
- [x] Создать 8 лингвистических паспортов (`mss`, `pfg`, `iesh`, `tsh`, `kmsh`, `nss`, `dss`, `mts`).
- [x] Создать 9 литературоведческих паспортов (`lit_opoyaz`, `lit_structural`, `lit_textology`, `lit_mythopoetics`, `lit_narratology`, `lit_bakhtin`, `lit_historico_cultural`, `lit_reception`, `lit_poststructural`).
- [x] Расширить `text_domain` в метаданных запуска (17 доменов в `run.schema.json`).

### Фаза B: Интеллектуальный Совет (Шаги G-04, L-03)
- [x] Реализовать `get_cluster_weights()` в `council.py`.
- [x] Внедрить матрицу парадигматических конфликтов (напр. ОПОЯЗ vs Бахтин).
- [x] Настроить "Веса доверия" для верификатора (доменно-ориентированная проверка).

### Фаза C: Автоматизация стилей (Шаг G-03, L-04)
- [x] Создать системный промпт `Style Architect`.
- [x] Сгенерировать паспорта для 17 кластеров.
- [x] Верифицировать паспорта на реальных текстах (через `eval-suite`).

### Фаза D: Филологические Эвалы (Шаги G-05, G-06, L-05)
- [x] Создать Golden Dataset и расширенный eval manifest (33 кейса готово).
- [x] Внедрить Adversarial Evals (защита "эпистемической осторожности").
- [x] Настроить CI gate на основе `rws eval-suite`.

### Фаза E: QA и Финальная Интеграция (Завершена)
- [x] Имплементировать `ci-eval-gate.py` и интегрировать в рабочий процесс.
- [x] Обновить Web Studio для визуализации обоснований Совета.
- [x] Внедрить региональные архетипы (Москва vs Ленинград) и Golden Zaliznyak Set.
- [x] Создать руководства по сценариям и деплою (`docs/scenarios.md`, `docs/deployment.md`).

### Фаза F: Интерактивный Схоластический Верстак (v2.0)
- [x] Внедрить когнитивную разметку дебатов по таксономии Блума (Socratic Council).
- [x] Реализовать Методологический Компас (Radar Chart) и Карту Напряжения (Tension Heatmap).
- [x] Добавить визуализацию синтаксических сдвигов (Syntax Shift Map).
- [x] Интегрировать Интерактивный Конкорданс (НКРЯ, Корпус Зализняка).
- [x] Разработать фронтенд-компоненты Web Studio (Radar, Heatmap, Concordance).
- [x] Подготовить демонстрационный сценарий «Socratic Audit».

### Фаза G: Промышленная Инфраструктура (Завершено)
- [x] Переход на SQLite для индексации запусков и метаданных.
- [x] Внедрение фоновой обработки (FastAPI BackgroundTasks) для асинхронных аудитов.
- [x] Поддержка локальных LLM (Ollama/vLLM) для режима Privacy Mode.
- [x] Реализация профилей «Исследователь», «Редактор», «Студент» с профильными инструкциями.

### Фаза H: Филологическое Масштабирование (инфраструктура завершена)
- [x] Промышленная контейнеризация (Docker + Docker Compose).
- [x] Интеграция специализированных корпусов (Тронский, Гаспаров).
- [x] Multi-Document Workbench: API и Визуализация сравнения профилей.
- [x] Style Migration: Поточное преобразование корпуса между регистрами.
- [x] Project Consistency: Аудит набора документов на соблюдение общих обязательств.
- [x] Peer Review A/B: Автоматизированное сравнение рецензий от разных архетипов.
- [x] Style Gallery: Автоматическая генерация Markdown-галерей стилей.
- [x] Scholarly Apparatus: Автоматическая генерация LaTeX-отчетов.
- [x] Начальный BibTeX export (`references.bib`) для scholarly artifacts.

## Дельта после agent-roadmap-2026 audit

Аудит от 2026-05-08 показывает, что RuWritingStyles уже прошел этапы "first agent" и "multi-agent prototype". Следующий слой не в том, чтобы переписать проект на LangGraph, а в том, чтобы превратить текущий pipeline в измеримый, возобновляемый и наблюдаемый production harness.

Детальная архитектура для будущей реализации Gemini Flash: `docs/gemini-flash-implementation-architecture.md`.

### Приоритет 0: привести eval-gate в рабочее состояние
- [x] Исправить `scripts/ci-eval-gate.py`: сейчас он вызывает устаревший интерфейс `eval-suite --mode mock`, тогда как актуальный CLI использует `eval-suite --provider mock`.
- [x] Подключить `rws eval-regression` к CI после появления promoted baseline.
- [x] Зафиксировать baseline promotion workflow: `eval-suite` -> `eval-promote` -> `eval-regression` -> comparison artifact.
- [x] Добавить `web/` lint/build в обязательный CI gate, если Web Studio считается release-critical.

### Приоритет 1: human finalization вместо демонстрационного accept/reject
- [x] Ввести `resolution.json` как переносимый артефакт ручных решений.
- [x] Добавить CLI-команды `rws apply-resolution` и `rws finalize`.
- [x] Сделать Web Studio/HTML accept-reject входом в финализацию, а не только визуальным действием.
- [x] Гарантировать трассировку: source segment -> finding -> council decision -> applied change -> human resolution.

### Приоритет 2: durable execution и resume
- [x] Добавить таблицу `run_steps` в SQLite: step id, status, started/finished, artifact path, error, retry count.
- [x] Чекпойнтить pipeline после каждого этапа: review, council, revision, verification, impact, syntax, reports.
- [x] Реализовать `rws resume <run_id>` для продолжения failed/interrupted run.
- [x] Расширить `/runs/{run_id}` или добавить `/runs/{run_id}/status` с пошаговым состоянием.

### Приоритет 3: observability, cost и context discipline
- [x] Расширить `provider.log.jsonl` до trace events: task, model, artifact, duration, retry, schema repair, token/cost estimate.
- [x] Добавить budget modes в `model_policy.yml`: smoke, standard, expensive, verifier-only.
- [x] Создать единый context builder: style passport, selected knowledge passages, previews for long artifacts, source passage ids.
- [x] Не добавлять vector DB до тех пор, пока evals не покажут реальную проблему recall.

### Приоритет 4: hooks и sandbox boundaries
- [x] Добавить hook-points: `pre_provider_call`, `post_provider_call`, `pre_write_artifact`, `post_schema_validate`, `stop_on_risk`.
- [x] Использовать hooks для JSON repair, secret redaction, file path guardrails, budget stops и human approval.
- [x] Сандбоксировать будущие code execution/PDF tooling/external MCP calls; модель не должна видеть credentials.

### Приоритет 5: scholarly apparatus depth
- [x] Динамическая интеграция библиографии: Zotero/BibTeX ingestion, source mapping и проверка ссылок вместо статического `references.bib`.
- [x] Расширить коллекции "Гаспаров" и "Тронский" с passage ids и reliability metadata.
- [x] Добавить citation verifier: имена, даты, библиографические ссылки, прямые цитаты, transliteration.

## Следующее действие

Все 5 production-harness приоритетов из agent-roadmap-2026 выполнены и прошли CI gate.

### Выполнено в сессии v2.2.3 → v2.3.0 (рефакторинг):
1. Устранена архитектурная ошибка CLI↔API: создан `resolution.py` (сервисный слой для `apply_resolution` и `write_final_manuscript`).
2. CLI-команды `cmd_apply_resolution` и `cmd_finalize` переведены на делегирование к сервисному слою.
3. `api.py`: CORS ограничен до localhost, middleware перенесён выше routes, удалён `argparse.Namespace` из API-эндпоинтов.
4. `hooks.py`: переписан как набор функций модуля (без класса); credential detection заменён на anchored regex по форматам OpenAI/AWS/GitHub/Google; устранён опасный null-prune из `post_schema_validate`.
5. `context_builder.py`: подключён к `verification.py` — knowledge passages и artifact preview теперь реально встраиваются в verification prompt.

### Выполнено в Sprint D (стабилизация CI):
1. [x] **Committed gold baseline**: создан `evals/baselines/gold.json` на основе детерминированного mock-прогона (33 кейса).
2. [x] **CI Golden Gate**: `scripts/ci-eval-gate.py` переведён в GOLD MODE (сравнение с `gold.json`).
3. [x] **Bugfixes**: исправлен `FrozenInstanceError` в `hooks.py` и логика `strict` в `eval-regression`.
4. [x] **Unit-тесты**: Unit-тесты для `hooks.py` и `resolution.py` добавлены в CI gate (44/44 OK).

---
*Math: Total Phases (9) — Phase I implementation complete; v2.3.5 stabilization complete.*

### Phase I: Philological Production (Completed)
- [x] Scholarly Apparatus: Динамическое извлечение цитат и генерация BibTeX.
- [x] Citation Verifier: Проверка цитат на соответствие корпусу знаний.
- [x] LaTeX Export: Генерация академических отчетов (`report.tex`).
- [x] Methodological Bias Audit: Анализ идеологических и методологических смещений.
- [x] Full Corpus Validation: Прогон на 35 файлах `examples/input`.

### Phase II: Scale & Knowledge Integration (Completed)
- [x] Knowledge Hub: Наполнение `knowledge/` реальными данными из НКРЯ и архива Зализняка.
- [x] Multi-Style Batch: Параллельный прогон корпуса через 17+ стилей (17x35 = 595 runs).
- [x] Web Studio V3: Визуализация верифицированных цитат и bias scores в UI.
- [x] Automated Style Evolution: Доработка паспортов на основе результатов "Full Corpus Audit".

### Phase III: External Agent Integration (Completed in v2.4.0)
- [x] Zotero MCP: Живая интеграция с Zotero через Model Context Protocol (stdio/JSON-RPC).
- [x] Web Researcher: Агент на базе OpenAlex API для автоматического поиска академических прецедентов.
- [x] Agentic Loop: Реализация мульти-турного цикла tool-calling в провайдерах OpenAI и Google.

### Phase IV: Advanced Agentic Orchestration (In Progress)
- [x] SQLite Native Orchestration: Протоколирование всех вызовов инструментов в `rws.db` (таблица `run_tool_calls`).
- [x] Dynamic Tool Routing: Инъекция MCP инструментов в `council.py` и `verification.py`.

### Phase V: Real-Time Collaborative Workbench (Completed in v2.4.0)
- [x] WebSocket Web Studio: Переход от статического React-интерфейса к живому взаимодействию ("Thinking Trace").
- [ ] Multi-User Socratic Audit: Совместная работа нескольких исследователей с возможностью инъекции аргументов "на лету" (Socratic Injection).

### Phase VI: Deep Document Retrieval (TXT RAG)
- [ ] TXT Corpus Ingestion: Загрузка первичной литературы (только извлеченные TXT, без хранения PDF) для расширения контекста.
- [ ] Citation Quote Extraction: Агенты не только подтверждают наличие источника, но и извлекают точные цитаты для обоснования стилистических правок.

### Phase VII: Editor Integrations (The Final Mile)
- [ ] Obsidian Plugin: Интеграция API RuWritingStyles в Obsidian (выделение абзаца -> Socratic Council rewrite -> мгновенная подмена).
- [ ] MS Word Add-in: Академический плагин для Word, позволяющий применять паспорта (Bakhtin, Zaliznyak) к черновикам диссертаций.
