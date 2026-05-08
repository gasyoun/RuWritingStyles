# Gemini Agent Roadmap: RuWritingStyles

*Персонализировано на основе https://github.com/codejunkie99/agent-roadmap-2026 и внутренних docs/ 2026-05-08.*

## Профиль проекта
- **Уровень**: Сложная многоагентная система (Council + Verifier).
- **Стек**: Python + JSON Schema + Markdown Styles.
- **Цель**: Создание "Gemini-Ready" филологической лаборатории с 17+ кластерами стилей.
- **Текущая Фаза**: v2.2.1 stabilization после Фазы H: схемы, Docker/runtime, Web build, Windows CLI и eval/test discipline синхронизированы.

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
- [x] Scholarly Apparatus: Автоматическая генерация LaTeX-отчетов.
- [x] Начальный BibTeX export (`references.bib`) для scholarly artifacts.

## Дельта после agent-roadmap-2026 audit

Аудит от 2026-05-08 показывает, что RuWritingStyles уже прошел этапы "first agent" и "multi-agent prototype". Следующий слой не в том, чтобы переписать проект на LangGraph, а в том, чтобы превратить текущий pipeline в измеримый, возобновляемый и наблюдаемый production harness.

### Приоритет 0: привести eval-gate в рабочее состояние
- [ ] Исправить `scripts/ci-eval-gate.py`: сейчас он вызывает устаревший интерфейс `eval-suite --mode mock`, тогда как актуальный CLI использует `eval-suite --provider mock`.
- [ ] Подключить `rws eval-regression` к CI после появления promoted baseline.
- [ ] Добавить `web/` lint/build в обязательный CI gate, если Web Studio считается release-critical.
- [ ] Зафиксировать baseline promotion workflow: `eval-suite` -> `eval-promote` -> `eval-regression` -> comparison artifact.

### Приоритет 1: human finalization вместо демонстрационного accept/reject
- [ ] Ввести `resolution.json` как переносимый артефакт ручных решений.
- [ ] Добавить CLI-команды `rws apply-resolution` и `rws finalize`.
- [ ] Сделать Web Studio/HTML accept-reject входом в финализацию, а не только визуальным действием.
- [ ] Гарантировать трассировку: source segment -> finding -> council decision -> applied change -> human resolution.

### Приоритет 2: durable execution и resume
- [ ] Добавить таблицу `run_steps` в SQLite: step id, status, started/finished, artifact path, error, retry count.
- [ ] Чекпойнтить pipeline после каждого этапа: review, council, revision, verification, impact, syntax, reports.
- [ ] Реализовать `rws resume <run_id>` для продолжения failed/interrupted run.
- [ ] Расширить `/runs/{run_id}` или добавить `/runs/{run_id}/status` с пошаговым состоянием.

### Приоритет 3: observability, cost и context discipline
- [ ] Расширить `provider.log.jsonl` до trace events: task, model, artifact, duration, retry, schema repair, token/cost estimate.
- [ ] Добавить budget modes в `model_policy.yml`: smoke, standard, expensive, verifier-only.
- [ ] Создать единый context builder: style passport, selected knowledge passages, previews for long artifacts, source passage ids.
- [ ] Не добавлять vector DB до тех пор, пока evals не покажут реальную проблему recall.

### Приоритет 4: hooks и sandbox boundaries
- [ ] Добавить hook-points: `pre_provider_call`, `post_provider_call`, `pre_write_artifact`, `post_schema_validate`, `stop_on_risk`.
- [ ] Использовать hooks для JSON repair, secret redaction, file path guardrails, budget stops и human approval.
- [ ] Сандбоксировать будущие code execution/PDF tooling/external MCP calls; модель не должна видеть credentials.

### Приоритет 5: scholarly apparatus depth
- [ ] Динамическая интеграция библиографии: Zotero/BibTeX ingestion, source mapping и проверка ссылок вместо статического `references.bib`.
- [ ] Расширить коллекции "Гаспаров" и "Тронский" с passage ids и reliability metadata.
- [ ] Добавить citation verifier: имена, даты, библиографические ссылки, прямые цитаты, transliteration.

## Следующее действие
1. Исправить `scripts/ci-eval-gate.py`, чтобы он вызывал `rws eval-suite --provider mock` через актуальный CLI.
2. Добавить `web/` lint/build в GitHub CI, если Web Studio становится обязательным release gate.
3. Затем вернуться к динамической библиографии: Zotero/BibTeX ingestion, source mapping и проверка ссылок вместо статического `references.bib`.

---
*Math: Total Phases (8) - Phase H infrastructure complete; agent-roadmap-2026 delta adds 5 production-harness priorities: eval gate, human finalization, durable resume, observability/context discipline, and sandboxed hardening.*
