_Created: 24-08-2026 · Last updated: 05-09-2026_

# Документация RuWritingStyles — карта

Указатель по документации. Начните сверху (для пользователя), ниже — материалы для
рецензентов кода и разработчиков.

## Начать (пользователю)

- [`QUICKSTART.ru.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/QUICKSTART.ru.md) — установка → ключ DeepSeek → первый прогон за
  пять шагов.
- [`USE_CASES.ru.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/USE_CASES.ru.md) — рабочие сценарии: этимология, подготовка к
  журналу, ведийский период, самаса, сверка словарей, транслитерация. Команда → что вернет.
- [`cli.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/cli.md) — полный справочник команд `rws`.
- [`STYLE_GALLERY.ru.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/STYLE_GALLERY.ru.md) — галерея всех 40 стилей со ссылками на
  `.md` для использования как Claude Custom Style (открыть → скопировать → вставить).

## Доверие к результату (доказательная база)

- [`benchmark.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/benchmark.md) — реальная точность на золотых санскритских кейсах
  (DeepSeek): детекция 5/5, где расходится с протоколом, оговорка о недетерминизме.
- [`case-study-p3-guna.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/case-study-p3-guna.md) — разбор реальной статьи (≈22k знаков):
  Совет поймал все три заложенные ошибки; проверка под Вестник СПбГУ.
- [`p3-seed-key.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/p3-seed-key.md) — ключ к заложенным проблемам этого кейса.
- [`case-study-phase1.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/case-study-phase1.md) — детерминированный слой на реальной статье.
- [`../evals/GOLD_PROTOCOL.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/evals/GOLD_PROTOCOL.md) — протокол золотого стандарта
  (≥2 разметчика, согласие, метрики).

## Цитирование и использование ИИ

- [`../CITATION.cff`](https://github.com/gasyoun/RuWritingStyles/blob/main/CITATION.cff) — как цитировать («Cite this repository»).
- [`zenodo-doi-steps.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/zenodo-doi-steps.md) — кнопки автора для минтинга Zenodo-DOI и
  готовый патч в `CITATION.cff`/README после его получения.
- [`AI_DISCLOSURE.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/AI_DISCLOSURE.md) — готовые формулы декларации ИИ для статьи (рус./англ.).
- [`../metadata/dublin-core.xml`](https://github.com/gasyoun/RuWritingStyles/blob/main/metadata/dublin-core.xml) — метаданные паспортов (DCMI).

## Как это устроено

- [`ENGINE.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/ENGINE.md) — инженерная документация движка: возможности, 17 филологических
  школ-кластеров, контракт артефактов, быстрый старт CLI, feedback loop (вынесено из README).
- [`philological-feedback-loop.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/philological-feedback-loop.md) — идея «Совета» и петли
  обратной связи.
- [`agent-protocol.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/agent-protocol.md) — протокол: как стили проверяют документ,
  отвечают друг другу, синтезируют правку.
- [`style-contract.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/style-contract.md) — контракт паспорта стиля.
- [`roadmap-2026-q3.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/roadmap-2026-q3.md) — **актуальная единственная дорожная карта**
  (Доверенный бенчмарк, фазы B1/B2/R1/R2). Прежние поколения (`roadmap.md`,
  `roadmap-sanskrit-dh.md`, `../GEMINI_ROADMAP.md`, `provider-roadmaps.md`) помечены
  архивными шапками.

## Рецензии (для рецензентов кода)

- [`security-review-2026-06.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/security-review-2026-06.md) — обзор веб-поверхности
  (S1–S7 закрыты; default-deny авторизация; путь к публичному развертыванию).
- [`prompt-fidelity-review-2026-06.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/prompt-fidelity-review-2026-06.md) — верность
  паспортов и сохранение голоса стиля по конвейеру.
- [`data-schema-review-2026-06.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/data-schema-review-2026-06.md) — слой данных и схем.
- [`architecture-review-2026-06.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/architecture-review-2026-06.md) — архитектура конвейера.
- [`methodology-paper-draft.ru.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/methodology-paper-draft.ru.md) — **полный русский
  черновик** методологической статьи «Совет филологов» (A29, 3/5) с усредненными числами
  бенчмарка (0.48→0.92) и кейсом *guṇa*; [`methodology-paper-outline.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/methodology-paper-outline.md)
  — исходный скелет; [`paper-pack/`](paper-pack/) — cover letter + чек-лист площадок.
- [`ars-integration-notes.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/ars-integration-notes.md) — что заимствовать у Academic
  Research Skills (CC BY-NC 4.0) без конфликта с нашей Apache-2.0: правовая позиция
  (переосмыслять методы, не копировать файлы, указывать авторство) + пять приоритетных заимствований.
- [`ajs-comparison-notes.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/ajs-comparison-notes.md) — сравнение с Awesome-Journal-Skills
  (MIT, Stanford REAP): не конкурент и не донор методов, но образец для расширения схемы
  профилей журналов (`knowledge/journals/`).

## Разработка и развертывание

- [`RELEASE_SOURCE_OF_TRUTH.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/RELEASE_SOURCE_OF_TRUTH.md) — merged `origin/main` + real `vX.Y.Z` tags are the release sequence; run `python scripts/release_source_truth.py --require-releaseable` before `/cut-release`.
- [`obsidian-plugin-plan.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/obsidian-plugin-plan.md) — план плагина для Obsidian:
  MVP с легкими детерминированными проверками (порт линтера на TypeScript), полный
  аудит «Совета» через локальный FastAPI как Tier 2.
- [`deployment.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/deployment.md), [`onboarding.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/onboarding.md),
  [`adr-001-reject-langgraph.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/adr-001-reject-langgraph.md),
  [`provider-roadmaps.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/provider-roadmaps.md) и прочие — внутренние материалы.

> Историческое: ранние `quickstart.md`, `scenarios.md`, `roadmap*.md`,
> `*-phase*.md`, `project-v2-vision.md` отражают прежние этапы; актуальны
> русскоязычные `QUICKSTART.ru.md` и `USE_CASES.ru.md` выше.

_Dr. Mārcis Gasūns_
