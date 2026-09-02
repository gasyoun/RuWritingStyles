# Дорожная карта: санскритологический контур и DH-соответствие

> **АРХИВ (помечено 2026-07-03, фаза R2).** Фазы 0–4 выполнены; документ сохранен как
> история. Актуальная единственная дорожная карта —
> [`docs/roadmap-2026-q3.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/roadmap-2026-q3.md).

Дата: 2026-06-12 · Last updated: 02-09-2026.

> **Human-gate 27-08-2026** (Grok 4.6 `grok-4.6`). The next residual (purge PDF/txt from git history) is a human act, not `/roadmap-item-exec` for an agent. Do not tick a box. Do not run filter-repo. Prior: 07-08 Phase 0 doc honesty.

> **Triage 02-09-2026 (H3780, Sonnet 5).** This archived carte was gated as a whole because its
> first open unit is human-only. It should not have been — of the 17 open units, 9 are
> agent-doable today, 3 are agent-doable but blocked on another open unit's prerequisite, and
> 5 genuinely need a human (a real decision, a real name, a paid run, or copyrighted-corpus
> acquisition). Every unit below now carries an inline tag — **[AGENT]** ·
> **[BLOCKED: <what it waits on>]** · **[HUMAN-ONLY]** — and the 5 human-only units each have a
> GTD `@DO`/`@DECIDE` row in
> [Uprava/GTD_NEXT_ACTIONS.md](https://github.com/gasyoun/Uprava/blob/main/GTD_NEXT_ACTIONS.md)
> naming the physical act. The agent-doable units are listed first, in start order, so a future
> `/roadmap-item-exec` run does not have to re-triage the phase list to find one.

## Триаж — что можно начать прямо сейчас (агентское, приоритет сверху вниз)

1. ~~**[Ф1] ГОСТ-аппарат**~~ — **done, DUPLICATE-SHIPPED 02-09-2026** (checkbox was stale; see the Ф1 item below for evidence).
2. ~~**[Ф1] Прогнать пример статьи**~~ — **done 02-09-2026**, see [`examples/output/phase1-council-example/`](https://github.com/gasyoun/RuWritingStyles/tree/main/examples/output/phase1-council-example).
3. **[Ф1] Унифицировать CLI и Web/API** — `rws run` тоже пишет `report.tex` и `references.bib` (Ф1, unit "Унифицировать CLI и Web/API").
4. **[Ф2] Провенанс в паспортах** — расширить `schemas/style.schema.json` (`provenance_sources`, `derived_by`, `derivation_date`, `validated_by`, `last_validated`) и дозаполнить все 16 существующих паспортов (Ф2, unit "Провенанс в паспортах").
5. **[Ф3] 10–15 eval-кейсов** в `evals/manifest.json` + документы в `examples/input/` (Ф3, unit "eval-кейсы").
6. **[Ф4] `CITATION.cff` + релиз на Zenodo с DOI** — agents may mint DOIs and cut public releases (standing ruling, MG 16-08-2026); publish-safety-check still gates (Ф4, unit "CITATION.cff").
7. **[Ф4] Раздел «Как сообщать об использовании ИИ»** в README — готовая формула для сноски (Ф4, unit "AI-usage README").
8. **[Ф4] Экспорт метаданных паспортов в Dublin Core** (поле→dc-мэппинг в `tools/`) (Ф4, unit "Dublin Core export").
9. **[Ф4] Расширить `knowledge/bibliography.json` индологическим ядром** (Елизаренкова, Топоров, Monier-Williams, Böhtlingk, Whitney, Renou — все public-domain, со ссылками на Кельнские словари); FTS5-поиск сам уже рабочий (Ф2 статус выше) — эта строка теперь только про библиографию (Ф4, unit "FTS5/библиография").

**Заблокировано (агентское, ждёт предпосылку):**

- **[Ф2] Новые стили + паспорта + кластер `indology`** — ждёт корпус (человеческий пункт «Корпуса» ниже); нельзя моделировать голос автора без исходных текстов.
- **[Ф2] Блок «Источники и метод»** в каждом новом `*-style.md` — тот же блокер (новые стили ещё не написаны).
- **[Ф4] Плагины Word/Obsidian** — явно секвенировано «только после фаз 1–3» в самом документе.

**Human-only (GTD-строка в [Uprava/GTD_NEXT_ACTIONS.md](https://github.com/gasyoun/Uprava/blob/main/GTD_NEXT_ACTIONS.md), H3780):**

- **[Ф0] Human-only:** вычистить PDF/txt из истории (уже было помечено; строка ниже не менялась).
- **[Ф1] Профиль журнала** в `.rws-project/project-context.json` — нужно решение автора, какой журнал целевой для флагманской статьи.
- **[Ф2] Корпуса** (Елизаренкова, Топоров, Вертоградова, Иванов) — приобретение охраняемых текстов, делает автор (см. фаза 2 статус выше).
- **[Ф3] Золотой стандарт** — нужны реальные имена эксперт-разметчиков (≥2 на кейс), не может быть анонимным.
- **[Ф3] Прогон полного eval-suite на реальных провайдерах** — платный прогон, «решение автора» (текст фазы 3 выше).

---

Статус: архив фаз 0–4 (filter-repo history — human-only residual).
Цель: превратить RuWritingStyles из каталога стилей в рабочий инструмент написания
русскоязычных научных статей по санскритской лингвистике — при этом довести репозиторий
до публикуемого (public) и архивного (DH-grade) состояния.

Решения, на которых построена карта (зафиксированы 2026-06-12):

- репозиторий **становится публичным** — права на исходные PDF — задача № 1;
- типы статей: грамматика санскрита, хрестоматии/ридеры для студентов, пособие по самасам,
  лексикография, этимология и сравнительно-историческое языкознание, панинеевская традиция,
  комментаторская традиция;
- опорные образцы прозы: Зализняк (есть), **Елизаренкова, Топоров, Вертоградова, Иванов** (добавить),
  плюс существующие Тронский/Казанский/Лидова;
- первый квартал: **сквозной цикл написания реальной статьи** — DH-исправления делаются по ходу.

---

## Фаза 0 — Права и история git (до публикации; ~1 неделя) 🔴

Публиковать репозиторий с `PDFtoTXT/` нельзя: ~95 МБ охраняемых монографий
(Зализняк 2002/2004/2008/2026, Smirnoff 2025, Tubb 2007) без правовых оговорок.

- [x] Создать приватный репозиторий-спутник `RuWritingStyles-corpus`; перенести туда
      `PDFtoTXT/` целиком (PDF + txt + извлекающие скрипты). Готово: репозиторий
      [gasyoun/RuWritingStyles-corpus](https://github.com/gasyoun/RuWritingStyles-corpus)
      создан и приватен, `PDFtoTXT/` (PDF, txt, `index-update.py`) перенесен туда целиком;
      в основном репозитории каталог `PDFtoTXT/` отсутствует и в git не отслеживается.
- [ ] **[HUMAN-ONLY]** **Human-only:** вычистить PDF/txt из истории основного репозитория
      (`git filter-repo` + force-push с полным бэкапом). **Не агентами.** На 07-08-2026
      рабочее дерево чистое, но `git log --all -- PDFtoTXT` ещё не пуст (H2369).
- [x] Написать `SOURCES.md` в основном репозитории: библиографическая запись каждого
      источника (ГОСТ), правовой статус, и явная формула «стилевые модели — аналитические
      описания манеры письма, тексты источников не воспроизводятся». Готово; H2369
      убрал ложный claim «history purged via filter-repo» и добавил таблицу
      соответствие строка↔файл private corpus.
- [x] Честная маркировка возможностей в `README.md`: разделить «реализовано» и «запланировано»
      (OpenAlex / Zotero-MCP / FTS5 — живой код с явными внешними зависимостями, не
      заглушки-no-op; Obsidian code+CI vs BRAT/publish; Word = HTML-прототип). H2369.
- [x] Проверить `.env`, `rws.db`, `DASHBOARD.html`, `runs/` на утечки ключей и личных данных.
      `.env` / `rws.db` / `runs/` / `PDFtoTXT/` в `.gitignore`; tracked `.env` отсутствует (H2369 spot-check).

Критерий готовности (обновлён H2369): README не обещает нереализованного — **выполнено**;
`git log --all -- PDFtoTXT` пуст — **ещё нет** (human-only filter-repo).

## Фаза 1 — Сквозной цикл статьи (недели 2–6) — главный приоритет

Детальный план реализации (по файлам, с тестами и приемкой):
[implementation-plan-phase1.md](implementation-plan-phase1.md).

**Статус (2026-06-13): детерминированный слой завершен.** W1 (ГОСТ-библиография),
W2 (линтер транслитерации), W3 (профили журналов), W5 (mock-safe eval-кейсы) и W6
(прогон реальной статьи) — на `main`. Кейс-стади: [case-study-phase1.md](case-study-phase1.md)
(прогон выявил и исправил 2 ложных правила). Открыто: содержательный совет стилей
требует платного провайдера (решение автора) и пополнения библиографического ядра под
конкретные статьи (переходит в фазу 2).

Выбрать одну реальную статью (рекомендация: лексикографическая — продолжение линии P1–P6,
или глава пособия по самасам) и провести ее через конвейер от черновика до файла,
готового к подаче в журнал.

- [x] **ГОСТ-аппарат**: формирование списка литературы по ГОСТ Р 7.0.100-2018 из
      `references.bib`; цели — ВЯ, «Письменные памятники Востока», Вестник СПбГУ.
      **DUPLICATE-SHIPPED (02-09-2026, H3780 residual, `/roadmap-item-exec`):** checkbox
      was stale — the apparatus shipped 13-06-2026 alongside the transliteration linter
      (commit [cfdd464](https://github.com/gasyoun/RuWritingStyles/commit/cfdd4643b6cfee470ab56eb0623ae434bbd2f7f3)):
      [`gost.py`](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/gost.py)
      (`format_gost`, `write_gost_references` — hand-rolled Python formatter per
      ГОСТ Р 7.0.100-2018 п. 4.9, not a Pandoc/CSL style file — same output contract, no
      external CSL dependency) plus
      [`bibtex.py`](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/bibtex.py)
      writing both `references.bib` and `references-gost.md` per run, wired into the
      `report` pipeline stage (`pipeline.py:508`, `cli.py:2909`) and the LaTeX report
      (`latex.py`). `python -m pytest -q -k gost` — 13 passed 02-09-2026.
- [x] **Линтер передачи санскрита** (детерминированный, без LLM, как этап `verify`):
      shipped 13-06-2026 as Phase 1 W2 (`translit_lint.py`, pipeline step after
      `verify`, CLI sibling `rws lint-translit`; commit
      [cfdd464](https://github.com/gasyoun/RuWritingStyles/commit/cfdd4643b6cfee470ab56eb0623ae434bbd2f7f3);
      later FP fixes in [PR #76](https://github.com/gasyoun/RuWritingStyles/pull/76) / v2.14.0).
      Re-verified 28-08-2026 (H3264): `pytest tests/test_translit_lint.py` 22 passed;
      `--strict` flags the golden bad fixtures (`translit-mixed-scheme`,
      `translit-first-mention`, `translit-cyrillic-latin-hybrid`) with no LLM call.
      Markdown italic vs roman is not a separate finding type (tests accept
      unitalicized IAST in parentheses).
      - первая встреча термина: русская передача + IAST в скобках — «бхашья (*bhāṣya*)»;
      - единообразие IAST по всему тексту (ṛ/ри, ś/ш и т. п. — один вариант на статью);
      - деванагари пропускается без порчи (UTF-8, NFC-нормализация);
      - курсив для латинской транслитерации, прямой шрифт для русской передачи.
- [ ] **[HUMAN-ONLY]** Профиль журнала в `.rws-project/project-context.json`: целевой журнал, лимит знаков,
      требования к аннотации/ключевым словам (рус.+англ.).
- [x] Прогнать статью: prepare → review (совет: Зализняк-очерк + Казанский + Лидова +
      Tronsky-Readings) → council → revise → verify → report; зафиксировать рабочий
      пример в `examples/` (на нечувствительном фрагменте).
      **Готово 02-09-2026 (H3780 residual, `/roadmap-item-exec`):**
      [`examples/output/phase1-council-example/`](https://github.com/gasyoun/RuWritingStyles/tree/main/examples/output/phase1-council-example)
      — full pipeline run over
      [`examples/input/article-snippet.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/examples/input/article-snippet.md)
      (public non-sensitive excerpt of the same manuscript
      [case-study-phase1.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/case-study-phase1.md)
      measured) with exactly the named council (`zalizniak-ocherk`,
      `kazanskiy-korpus`, `lidova-commentary`, `tronsky-readings`), journal
      profile `vya`, `--execute --provider mock`. `validate-run` OK; transliteration
      linter 0 findings; citations 4/4 verified; `report.tex` +
      `references.bib` + `references-gost.md` all produced. Content-level council
      advice under `mock` is still a stub (real judgment needs the paid-provider
      run — separate GTD `@DECIDE` row) — this unit is about exercising the
      deterministic pipeline end to end, which it does for real.
- [ ] **[AGENT]** Унифицировать CLI и Web/API: `rws run` тоже пишет `report.tex` и `references.bib`
      (давний пункт из `.ai_state.md`).

Критерий готовности: один реальный текст прошел цикл; список литературы в ГОСТ;
линтер транслитерации ловит подсаженные ошибки.

## Фаза 2 — Индологические стили и корпус (недели 4–10)

**Статус (2026-06-13): структурная часть и инфраструктура корпуса выполнены.**
Кластер `indology` и пять стилей (elizarenkova-veda, toporov-etym,
sanskrit-reader, samasa-manual, panini-traditional) добавлены с паспортами,
провенансом и записями в README; схема паспортов расширена блоком `provenance`,
все 16 прежних паспортов дозаполнены. **Deep Retrieval (FTS5) теперь рабочий и
доступен** через `rws corpus-status|ingest|search` — индексирует `.txt` из
приватного корпуса в локальный `rws.db`, проверено на Tubb/Smirnoff
(грамматика санскрита, самасы). Остается пополнить приватный корпус опорными
текстами (Елизаренкова, Топоров, Вертоградова, Иванов) — это делает автор;
после этого `rws corpus-ingest` их подхватит.

Новые корпуса кладутся **только** в приватный `RuWritingStyles-corpus`.

- [ ] **[HUMAN-ONLY]** Корпуса: Елизаренкова (статьи о языке Ригведы, предисловия к переводам),
      Топоров (этимологические работы, палийский словарь), Вертоградова, Иванов —
      по 1–3 опорных текста на автора.
- [ ] **[BLOCKED: ждёт корпус]** Новые стили (`ClaudeStyles/`) + паспорта + новый кластер `indology` в
      `styles/manifest.yml`:
      - `elizarenkova-veda-style` — ведийская филология: текст → грамматический факт →
        осторожная интерпретация, поэтика формулы;
      - `toporov-etym-style` — этимология и семантическая реконструкция;
      - `sanskrit-reader-style` — учебный ридер/хрестоматия (родственен
        Зализняк-школьников_1: ясность без упрощения, разбор формы шаг за шагом);
      - `samasa-manual-style` — учебное пособие по грамматике: определение → классификация
        (таблица типов самас) → правило → пример с разбором → исключение → упражнение;
      - `panini-traditional-style` — изложение с опорой на туземную традицию
        (сутра → вритти → пример), терминология вьякараны по-русски.
- [ ] **[AGENT]** **Провенанс в паспортах** (расширить `schemas/style.schema.json`):
      `provenance_sources` (источник + страницы), `derived_by`, `derivation_date`,
      `validated_by`, `last_validated` — и заполнить для всех 16 существующих паспортов
      задним числом.
- [ ] **[BLOCKED: ждёт новые стили]** Блок «Источники и метод» в каждом новом `*-style.md`: из каких текстов выведена модель,
      кем и когда проверена.

Критерий готовности: ≥4 новых стиля с полным провенансом; все старые паспорта
дозаполнены; `rws list-styles --cluster indology` работает.

## Фаза 3 — Санскритские eval-кейсы и золотой стандарт (недели 8–14)

**Статус (2026-06-13): кейсы и протокол готовы; ждет платного прогона.** В
`evals/manifest.json` 44 кейса (8 новых санскритских: 3 детерминированных,
mock-safe + 5 экспертных gold). Протокол экспертной разметки —
`evals/GOLD_PROTOCOL.md`; пустой каркас таблицы точности — `docs/benchmark.md`.
Открыто: платный прогон на реальных провайдерах + экспертная разметка (решение
автора).

Сейчас все 33 кейса — русистика; санскритский контур не проверяется ничем.

- [ ] **[AGENT]** 10–15 кейсов в `evals/manifest.json` + документы в `examples/input/`:
      - псевдоэтимология на санскритском материале (мокша, тапас, «рус. бог ← бхага»);
      - непоследовательная транслитерация (смешение IAST/Harvard-Kyoto/русской передачи);
      - неверное употребление панинеевского термина (карака ≠ падеж);
      - анахронизм «ведийский/эпический/классический санскрит»;
      - самаса-кейс: ошибочная классификация сложного слова (бахуврихи vs татпуруша);
      - регистр ридера: сползание учебного текста в наукообразие;
      - комментаторский кейс: смешение слоев мула-текста и комментария;
      - ГОСТ-кейс: битые ссылки на Елизаренкову/Monier-Williams.
- [ ] **[HUMAN-ONLY]** Задокументировать золотой стандарт: кто эксперт-разметчик, протокол проверки,
      согласие разметчиков (хотя бы 2 оценщика на кейс) — файл `evals/GOLD_PROTOCOL.md`.
- [ ] **[HUMAN-ONLY]** Прогнать полный suite на реальных провайдерах (Anthropic/OpenAI/Google),
      опубликовать таблицу точности по типам находок в `docs/benchmark-результаты`.

Критерий готовности: `rws eval-suite` включает санскритский блок; протокол
валидации опубликован; есть числа по ≥2 реальным провайдерам.

## Фаза 4 — Архивный DH-уровень (квартал 4, параллельно)

- [ ] **[AGENT]** `CITATION.cff` + релиз на Zenodo с DOI (обновляемый при каждом релизе) —
      чтобы систему можно было цитировать в статьях, написанных с ее помощью.
- [ ] **[AGENT]** Раздел «Как сообщать об использовании ИИ» в README: готовая формула для
      сноски в статье (журналы всё чаще требуют декларацию).
- [ ] **[AGENT]** Экспорт метаданных паспортов в Dublin Core (поле→dc-мэппинг в `tools/`).
- [ ] **[AGENT]** (FTS5-часть уже сделана — см. статус фазы 2 выше; открыт только пункт про bibliography.json) Реализовать (или честно отложить) FTS5-поиск по приватному корпусу;
      расширить `knowledge/bibliography.json` индологическим ядром
      (Елизаренкова, Топоров, Monier-Williams, Böhtlingk, Whitney, Renou) со ссылками
      на Кельнские словари.
- [ ] **[BLOCKED: секвенировано после фаз 1–3]** Плагины Word/Obsidian — только после фаз 1–3; для санскрита проверить
      деванагари-ввод и связку с Zotero.

---

## Сквозные правила

1. Ни одна возможность не упоминается в README до ее реализации.
2. Каждый новый стиль = `.md` + паспорт + manifest + README-таблицы + провенанс (5 мест).
3. Корпусные тексты — только в приватном репозитории; в публичном — только модели и ссылки.
4. `.ai_state.md` ведется по протоколу; коммиты `ai-wip:` по вехам.
