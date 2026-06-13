# План реализации фазы 1: сквозной цикл статьи (ГОСТ + санскритский линтер)

Дата: 2026-06-12. Детализация фазы 1 из [roadmap-sanskrit-dh.md](roadmap-sanskrit-dh.md).
Цель фазы: одна реальная статья по санскритской лингвистике проходит конвейер целиком —
от черновика до `report.tex` со списком литературы по ГОСТ Р 7.0.100-2018 и проверенной
передачей санскрита.

Каждый блок работ (W1–W6) самодостаточен и завершается зелёным CI
(`python tools/validate_project.py`, `python -m unittest discover -s tests`).
Правило репозитория: меняешь форму артефакта — меняешь схему в `schemas/`
и `schema_validation.py` в том же коммите.

---

## W1. Библиография: из заглушки — в ГОСТ (≈2–3 дня)

Сейчас `src/ruwritingstyles/bibtex.py` держит захардкоженный `BIB_DATABASE`
(строки 3–25: Зализняк, Тронский, Гаспаров) — это демо, а не аппарат.

1. **`bibtex.py`**: убрать `BIB_DATABASE`; источником записей сделать
   `knowledge/bibliography.json` (загрузчик `load_bibliography(repo_root)`).
   Расширить схему записи полями ГОСТ: `city`, `pages`, `edition`, `lang`,
   `responsibility` (сведения об ответственности), `kind`
   (`book|article|chapter|web`).
2. **Новый модуль `src/ruwritingstyles/gost.py`**:
   - `format_gost(entry: dict) -> str` — одна запись по ГОСТ Р 7.0.100-2018
     (краткая форма списка литературы): `Зализняк А. А. Древненовгородский
     диалект. — 2-е изд. — М. : Языки славянской культуры, 2004. — 872 с.`;
   - `write_gost_references(run_dir, entries) -> Path` — пишет
     `references-gost.md` рядом с `references.bib`;
   - порядок: алфавитный, кириллица раньше латиницы (как требуют ВЯ/ППВ).
3. **`latex.py`**: в `LATEX_TEMPLATE` добавить секцию `\section*{Литература}`,
   заполняемую из `format_gost`; BibTeX остаётся параллельным выходом для
   журналов с собственным `.bst`.
4. **Связка с проверкой цитирований**: `citations.py::verify_citations_against_knowledge`
   уже возвращает `verified/missing/not_in_bibliography`; в `references-gost.md`
   попадают только `verified`-записи, `not_in_bibliography` идут предупреждением
   в `verification.json.warnings[]`.
5. **Наполнение `knowledge/bibliography.json`**: ~25 записей индологического ядра
   (Елизаренкова, Топоров, Monier-Williams, Böhtlingk/Roth, Whitney, Renou,
   Кочергина, Смирнов + уже имеющиеся 8).

Тесты (`tests/test_gost.py`, unittest + tempfile, по образцу `test_citations.py`):
книга / статья / переиздание / латинская запись / сортировка кириллица-латиница;
интеграционный — `references-gost.md` появляется в `run_dir` при `--provider mock`.

Приёмка: запись Зализняка 2004 в выводе побайтно совпадает с эталоном ГОСТ из теста.

## W2. Детерминированный линтер передачи санскрита (≈3–4 дня)

Не-LLM проверка; встраивается шагом конвейера до `verification`
(в `pipeline.py::run_full_pipeline` через существующий `step()`-реестр,
между `revision` и `verification`).

1. **Новый модуль `src/ruwritingstyles/translit_lint.py`**:
   - `IAST_CHARS = "āīūṛṝḷḹṃḥṅñṭḍṇśṣ"` (+ заглавные), `DEVANAGARI = ऀ–ॿ`;
   - `lint_segment(span_id, text) -> list[dict]` — каждое замечание =
     `{span_id, type, message, severity, fragment}`;
   - `lint_document(segments) -> dict` — агрегат по `segments.json` + сводка схем.
2. **Типы находок** (войдут в словарь типов находок, см. `schemas/`):
   - `mixed_transliteration_scheme` — в одной статье IAST и Harvard-Kyoto
     (эвристика HK: `aa/ii/uu/RR/N̆` + заглавные внутри слова: `bhaaSya`, `kRSNa`);
   - `inconsistent_term_rendering` — один термин то кириллицей, то латиницей
     без системы (индекс пар «бхашья»/«bhāṣya» по нормализованным основам);
   - `missing_iast_on_first_mention` — первая встреча русской передачи термина
     из словарика без IAST в скобках (словарь терминов — новый файл
     `knowledge/sanskrit-terms.json`: pairs русская передача ↔ IAST, ~60 терминов);
   - `devanagari_nfc_issue` — деванагари не в NFC или с битыми огласовками
     (опора на `segment.py::normalize_document`, NFC уже есть);
   - `iast_in_cyrillic_word` — смешение скриптов внутри словоформы
     (расширение `mixed_script_word_count` из `linguistics.py`).
3. **Интеграция**:
   - артефакт `translit-lint.json` в `run_dir` + схема
     `schemas/translit-lint.schema.json` + ветка в `schema_validation.py`
     и `tools/validate_project.py`;
   - находки дублируются в `verification.json.warnings[]`
     (schema это уже допускает: `items: object`), чтобы Web Studio и
     `rws findings --span pNNN` видели их без доработок;
   - CLI: `rws run --lint-translit` (argparse в `cli.py::build_parser`,
     блок `run`-сабпарсера, строки ~111–157) — по умолчанию **включён**, выключение
     `--no-lint-translit`, т. к. проверка детерминированная и бесплатная;
   - отдельная команда `rws lint-translit <file.md>` для проверки любого файла
     вне конвейера (полезно до запуска полного цикла).
4. Линтер **не правит текст** — только находки со span_id (политика
   `rewrite_allowed: false`, как у паспортов-ревьюеров).

Тесты (`tests/test_translit_lint.py`): по 2 позитив/негатив на каждый тип;
краевые — деванагари в код-блоках (`c00N`-сегменты пропускаются), ударения
`сло́во` не считаются IAST, ёлка/ѣ не ломают детектор (фикстуры из
`test_cli_pipeline.py::test_normalization_preserves_russian_philological_marks`).

Приёмка: на чистом тексте 0 находок; на каждом подсаженном дефекте ≥1 находка
нужного типа с верным `span_id`.

## W3. Профиль журнала (≈1–2 дня)

`/.rws-project/project-context.json` сейчас несёт только `stylistic_commitments`
(читается в `verification.py::_render_prompt`, строки 115–130; пишется в
`project.py::update_project_context`).

1. Добавить блок:
   ```json
   "journal_profile": {
     "name": "Вопросы языкознания",
     "max_chars": 40000,
     "citation_format": "GOST-R-7.0.100-2018",
     "transliteration_scheme": "IAST",
     "first_mention_rule": "ru+iast",
     "abstract_required": ["ru", "en"]
   }
   ```
2. Потребители: `verification.py::_render_prompt` (новая секция «Требования
   журнала» в промпте верификатора); `translit_lint.py` (схема и first-mention
   правило из профиля); `report.py` (предупреждение при превышении `max_chars`).
3. Готовые пресеты: `knowledge/journals/{vya,ppv,vestnik-spbu}.json`;
   `rws project set-journal vya` копирует пресет в `project-context.json`.
4. `project.py::update_project_context` сохраняет `journal_profile` при merge
   (сейчас merge только по `stylistic_commitments` — не потерять блок).

Тесты: merge не теряет профиль; верификационный промпт содержит секцию журнала;
линтер берёт схему из профиля.

## W4. Паритет CLI ↔ Web/API (≈0,5 дня; давний пункт `.ai_state.md`)

`pipeline.py::run_full_pipeline` (Web/API) пишет `report.tex` + `references.bib`
(шаг `reports`, строки 171–179), а `rws run` — нет (`cli.py::_write_reports`,
~2418–2420, вызывается не из `cmd_run`).

- Вынести шаг `reports` в общую функцию (`report.py::write_all_reports(run_dir)`),
  вызвать её и из `cmd_run`, и из `run_full_pipeline`;
- добавить туда же `references-gost.md` (W1);
- тест: после `rws run --provider mock` в `run_dir` есть `report.md`,
  `summary.html`, `report.tex`, `references.bib`, `references-gost.md`.

## W5. Eval-кейсы фазы 1 (≈1 день)

В `evals/manifest.json` (схема кейса — `evals.py::EvalCase`, строки 33–49) добавить
первые санскритские кейсы (остальные — фаза 3):

| id | вход (`examples/input/`) | required_finding_types |
|---|---|---|
| `translit-mixed-scheme` | статья с IAST+HK вперемешку | `mixed_transliteration_scheme` |
| `translit-first-mention` | термины без IAST при первом упоминании | `missing_iast_on_first_mention` |
| `gost-hallucinated-ref` | ссылка на несуществующую работу Елизаренковой | `hallucinated_citation` |

Все три должны проходить на `--provider mock` (линтер детерминирован, провайдер
не нужен) — значит, попадают в GitHub-workflow `Eval Smoke` без ключей.

## W6. Прогон реальной статьи (≈2–3 дня, после W1–W5)

1. Кандидат: глава пособия по самасам или лексикографическая статья
   (черновик хранить в приватном `RuWritingStyles-corpus`, в публичный
   `examples/` — только обезличенный фрагмент ~3 абзаца).
2. `rws project set-journal vya` → `rws run --execute --provider anthropic`
   (совет: Зализняк-очерк + Казанский + Лидова + Tronsky-Readings; для
   самасов добавить Зализняк-именное).
3. Снять метрики: число находок по типам, ложные срабатывания линтера
   (каждое ложное — issue с тегом `translit-lint`), время/стоимость прогона.
4. Результат: `docs/case-study-phase1.md` — что поймал конвейер, что пропустил,
   что исправлено руками; это заготовка раздела «инструментарий» для самой статьи
   и доказательная база для фазы 3 (gold-протокол).

---

## Последовательность и оценка

```
W1 ГОСТ ──┐
W2 линтер ─┼─→ W3 профиль журнала ─→ W4 паритет ─→ W5 evals ─→ W6 прогон статьи
           │   (W1+W2 независимы, можно параллельно)
```

Суммарно ≈ 10–14 рабочих дней. Блокеров нет: всё локально, ключи нужны только W6.

## Риски

- **ГОСТ-формат вариативен** (краткая/полная форма, журнальные отступления):
  фиксируем краткую форму списка литературы + эталонные строки в тестах;
  спорные случаи — в `docs/case-study-phase1.md`, не в код.
- **Эвристика Harvard-Kyoto даёт ложные срабатывания** на английских вкраплениях
  (заглавные внутри аббревиатур): детектор HK применять только к словам,
  уже опознанным как кандидаты-термины (по `sanskrit-terms.json` и контексту
  курсива), не ко всему тексту.
- **`schema_validation.py` — собственный мини-валидатор**, не jsonschema:
  новые схемы писать в его подмножестве (см. существующие `eval-*` схемы).
- **Расхождение терминологического словарика с практикой журналов**: словарик
  версионируется, у каждой пары — поле `source` (откуда взята передача:
  Елизаренкова, Кочергина и т. п.).
