# Движок RuWritingStyles (CLI & Multi-Agent)

_Created: 03-07-2026 · Last updated: 19-07-2026_

Инженерная документация движка. Каталог стилей и человеко-ориентированное описание —
в корневом [`README.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/README.md);
карта всей документации — в [`docs/README.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/README.md).

RuWritingStyles — это не просто набор промптов, а полноценная платформа для высокоточного филологического аудита и миграции текстов.

## Основные возможности

*   **Мультиагентный аудит**: Система запускает «Совет» (Council) из MVP-набора стилей и сохраняет цепочку `segment -> review -> council -> revision -> verification`.
*   **Иерархическая таксономия (17 кластеров)**: Внедрена система из 8 лингвистических и 9 литературоведческих школ, позволяющая Совету учитывать методологический контекст (напр. Московская семантическая школа vs ОПОЯЗ).
*   **Динамическое взвешивание**: Агенты автоматически получают приоритет, если их научный профиль совпадает с доменом анализируемого текста (`text_domain`).
*   **Eval-дисциплина**: `evals/manifest.json` содержит 52 кейса; строгий mock-baseline защищает шесть детерминированных проходов и требует явного refresh для новых кейсов, реальные провайдеры сравниваются через `eval-suite` и `eval-compare`. Статистически осмысленный бенчмарк — `eval-run --repeat N` / `eval-suite --repeat N` (усредненный агрегат pass-rate / detection-rate ± σ), см. [`docs/benchmark.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/benchmark.md).
*   **Контракт артефактов**: JSON-схемы покрывают style/review/council/revision/verification/eval artifacts, включая `profile`, `clusters`, `bloom_level`, `primary_school` и `influence`. Стадия ревизии возвращает только пер-спановые `applied_changes`, движок сам реконструирует `revised.md` (diff-fidelity по построению) с бюджетом роста документа.
*   **Web/API слой**: FastAPI обслуживает API и, после `npm run build`, готовый `web/dist`; Web Studio умеет запускать аудит и сравнивать несколько runs, настраивать backend URL и хранить bearer token только в browser session.
*   **Отчеты и экспорт**: CLI executable run генерирует `report.md`, `summary.html`, ZIP bundle, `impact.json` и `syntax.json`; Web/API full pipeline также пишет scholarly artifacts `report.tex` и `references.bib`.
*   **Филологическая база знаний**: Агенты обращаются к локальному репозиторию исследований (`knowledge/`) для проверки терминологии и исключения анахронизмов.

## Филологические школы (Core Clusters)

Система поддерживает 8 базовых лингвистических паспортов, обеспечивающих фундаментальную точность:
- **MSS** (Московская семантическая школа) — системная семантика и декомпозиция.
- **PFG** (Петербургская филологическая группа) — академический классицизм и текстология.
- **IESH** (Историко-этимологическая школа) — диахрония и этимологическая строгость.
- **TSH** (Тартуская семиотическая школа) — структурный анализ и интертекстуальность.
- **KMSH** (Казанская младограмматическая школа) — фонетика и морфологическая системность.
- **NSS** (Нормативно-стилистическая школа) — культура речи и литературная норма.
- **DSS** (Дескриптивная системная школа) — объективное описание языковых фактов.
- **MTS** (Культурно-языковая школа) — антропологическая лингвистика и контекст.

Также реализованы 9 литературоведческих кластеров (Бахтин, ОПОЯЗ, Структурализм, Нарратология и др.).
*   **Сентимент-анализ для ученых**: Отслеживание «академической дистанции», уровня уверенности (модальности) и сложности лексики в процессе редактуры.
*   **Регрессионное тестирование**: Автоматическая проверка того, что новые версии промптов или моделей не ухудшают качество работы с установленными стилями-якорями.
*   **Интерактивный Dashboard**: Единая панель управления проектом (`DASHBOARD.html`) со статистикой по всему корпусу.

## Быстрый старт (CLI)

```bash
# Полный цикл: сегментация, аудит, дискуссия Совета и финальная правка
PYTHONPATH=src python -m ruwritingstyles.cli run input.md --execute --provider google

# Сравнение работы разных архетипов Совета (The Radical vs The Minimalist)
PYTHONPATH=src python -m ruwritingstyles.cli ab-test input.md --archetypes "The Radical" "The Minimalist" --execute

# Миграция всего архива документов в новый стиль
PYTHONPATH=src python -m ruwritingstyles.cli migrate-corpus data/archive --to-style zaliznyak-shkolnikov --execute

# Бенчмарк моделей: кто лучше справляется с филологическими задачами?
PYTHONPATH=src python -m ruwritingstyles.cli eval-benchmark --models "gpt-5.5" "gemini-3.1-pro" --provider google

# Генерация общего интерактивного отчета по проекту
PYTHONPATH=src python -m ruwritingstyles.cli dashboard

# Инфраструктурный smoke и регрессия
PYTHONPATH=src python -m ruwritingstyles.cli eval-regression --provider mock
PYTHONPATH=src python -m ruwritingstyles.cli eval-status runs/last-regression/comparison.json
```

Для работы с реальными провайдерами проверьте готовность ключей: `rws provider-status --strict`.

## Филологический Feedback Loop

Проект поддерживает интеграцию экспертных замечаний (рецензий в формате `.docx` с комментариями Word). Протокол обработки таких замечаний описан в [`docs/philological-feedback-loop.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/philological-feedback-loop.md). Все системные стили (`ClaudeStyles/*.md`) обновлены с учетом последних ревизий ИЛИ РАН (май 2026), что гарантирует соблюдение академического этикета и метатекстовой связности.

_Dr. Mārcis Gasūns_
