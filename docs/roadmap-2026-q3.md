# Дорожная карта Q3 2026 — «Доверенный бенчмарк» (канонический план)

_Created: 03-07-2026 · Last updated: 12-07-2026_

**Статус: принята.** Четыре решения зафиксированы автором 03-07-2026 (сессия Fable 5,
`claude-fable-5`):

1. **Приоритет квартала — доверенный бенчмарк** (измерение прежде улучшений).
2. **Над-переписывание ревизии лечится архитектурно** — span-patch-реконструкция,
   а не калибровкой лимита и не третьим раундом ужесточения промпта.
3. **Бюджет на платные eval-прогоны одобрен** (полный протокол: N=5 усреднение,
   temperature=0-проба, сравнение `deepseek-reasoner`).
4. **Все четыре отложенных релизных действия готовятся сейчас** (Zenodo DOI,
   Obsidian-плагин CI+репозиторий, пакет методологической статьи, консолидация docs).

Этот файл — единственная актуальная дорожная карта. Предыдущие поколения —
[roadmap.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/roadmap.md),
[roadmap-sanskrit-dh.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/roadmap-sanskrit-dh.md)
(фазы 0–4 выполнены),
[GEMINI_ROADMAP.md](https://github.com/gasyoun/RuWritingStyles/blob/main/GEMINI_ROADMAP.md) и
[provider-roadmaps.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/provider-roadmaps.md) —
исторические; фаза R2 помечает их как архивные.

---

## Диагноз (почему именно эти фазы)

Строительная фаза завершена (v2.10.4): DeepSeek — рабочий провайдер, 39 стилей,
именованные советы, журнальные проверки, Obsidian-плагин функционально готов,
security-review закрыт. Узкое место сместилось:

- **Метрика — шум.** Золотой набор дал 1/5 → 2/5 → 3/5 → **0/5** на неизменном коде
  ([benchmark.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/benchmark.md)).
  Детекция стабильна (5/5 почти в каждом прогоне); зачет хоронят два известных рычага —
  недетерминизм DeepSeek (single-run accuracy бессмысленна) и над-переписывание коротких
  заглушек ревизией (Δ > 0.5 при лимите 0.5).
- **Ревизия доверяет LLM копировать нетронутый текст дословно** — это и есть источник
  diff-провалов. Плагинный diff-accept уже доказал обратный паттерн: документ можно
  реконструировать программно из принятых span-правок (accept-all === revised).
- **Очередь авторских релизных действий заилилась**: DOI, методологическая статья,
  плагин (main сейчас не проходит `npm install` — peer-конфликт от dependabot, нет CI-job),
  три поколения roadmap сосуществуют.

## Фаза B1 — Eval-harness: статистически осмысленный бенчмарк

Handoff: [H072](https://github.com/gasyoun/Uprava/blob/main/handoffs/archive/H072-Fable_RuWritingStyles_RWS_eval_harness_nrun_03.07.26.md) · **✅ выполнена — v2.11.0 (03-07-2026)**.

- [x] `rws eval-run --repeat N` (или `eval-suite --repeat`): N независимых прогонов кейса,
      агрегат `eval-aggregate.json` — pass-rate, среднее/σ по Δ-метрикам, разброс детекции.
- [x] Политика меток скорера: alias-список в манифесте кейса (начато в `7dbbcc4`
      для `unsupported_etymology`) — довести до всех 5 золотых кейсов, задокументировать
      в [GOLD_PROTOCOL.md](https://github.com/gasyoun/RuWritingStyles/blob/main/evals/GOLD_PROTOCOL.md).
- [x] Temperature=0-проба: поддерживает ли `deepseek-chat` детерминизм — **нет**
      (детекция воспроизводима, текст ревизии — нет), усреднение по N остается обязательным.
- [x] Полный платный протокол: 5 золотых кейсов × N=5 на `deepseek-chat` выполнен
      (pass-rate 0.48, detection 0.96). Сравнение с `deepseek-reasoner` оказалось
      невозможным — алиас разрешается в тот же `deepseek-v4-flash`; сравнение с
      `deepseek-v4-pro` частичное (3/5, два зависших запроса) — остаток ушел в residue.
- [x] Заполнить [benchmark.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/benchmark.md)
      усредненными числами с доверительными интервалами — это доказательная база статьи.

Критерий готовности: benchmark.md сообщает pass-rate ± разброс по ≥5 прогонам;
повторный запуск протокола воспроизводит выводы (не обязательно числа).

## Фаза B2 — Span-patch-реконструкция ревизии (архитектурный фикс)

Handoff: [H073](https://github.com/gasyoun/Uprava/blob/main/handoffs/archive/H073-Fable_RuWritingStyles_RWS_span_patch_reconstruction_03.07.26.md) · **✅ выполнена — v2.12.0 (03-07-2026)**.

- [x] `revision.py`: LLM выдает только per-span замены (`applied_changes` со span_id +
      replacement); полный `revised.md` собирает движок — нетронутые сегменты копируются
      байт-в-байт из `segments.json`/`normalized.md` (новый модуль `reconstruct.py`).
- [x] Diff-fidelity становится верной **по построению**: измененные символы = только
      принятые спаны. Плюс найденный вживую второй рычаг — **growth-губернатор**
      (`govern_changes`, бюджет роста `RWS_REVISION_MAX_GROWTH_RATIO`): span-patch без
      него давал 0/5 на karaka (модель пере-пишет внутри спана).
- [x] Обратная совместимость: схема `revision.schema.json`, `validate-run`
      (реконструкционный инвариант `_validate_revision_reconstruction`).
- [x] Ре-бенчмарк по протоколу B1 до/после: pass-rate **0.48 → 0.92**, diff-провалы
      **13/25 → 0/25** — критерий готовности (≥ 4/5 при нулевых diff-провалах) выполнен.

Критерий готовности: N=5 усредненный зачет золотых кейсов ≥ 4/5, при нулевых
diff-провалах; регресс-suite mock зеленый.

## Фаза R1 — Obsidian-плагин: CI и релизный репозиторий

Handoff: [H074](https://github.com/gasyoun/Uprava/blob/main/handoffs/archive/H074-Opus_RuWritingStyles_RWS_obsidian_plugin_ci_release_03.07.26.md) · **✅ выполнена — v2.12.0 (03-07-2026)**, кроме кнопок автора.

- [x] Починить `npm install` на main (dependabot peer-конфликт `obsidian@1.13.1` ↔
      `@codemirror/state`); закрепить рабочую матрицу зависимостей (`overrides` +
      сгруппированный dependabot).
- [x] CI-job для плагина (build + 59 тестов) в
      [ci.yml](https://github.com/gasyoun/RuWritingStyles/blob/main/.github/workflows/ci.yml),
      path-filtered через `dorny/paths-filter`.
- [x] Подготовить выделенный релизный репозиторий: каркас
      [obsidian-plugin/release-repo/](https://github.com/gasyoun/RuWritingStyles/tree/main/obsidian-plugin/release-repo)
      + [tools/sync_plugin_release_repo.py](https://github.com/gasyoun/RuWritingStyles/blob/main/tools/sync_plugin_release_repo.py)
      (синк проверен: standalone build + 59/59).
- [ ] **Кнопки автора (открыто)**: создать `gasyoun/ruwritingstyles-obsidian`, пуш тега
      `obsidian-v0.1.0`; PR в obsidianmd/obsidian-releases; BRAT.

Критерий готовности: CI ловит ломающий bump; из релизного репо ставится рабочий плагин.

## Фаза R2 — Публикационный проход (после B1+B2)

Handoff: [H075](https://github.com/gasyoun/Uprava/blob/main/handoffs/archive/H075-Opus_RuWritingStyles_RWS_publish_pass_03.07.26.md) · **✅ выполнена — v2.12.1 (03-07-2026)**, кроме кнопки DOI.

- [ ] **Zenodo DOI**: метаданные release-ready ([CITATION.cff](https://github.com/gasyoun/RuWritingStyles/blob/main/CITATION.cff),
      [.zenodo.json](https://github.com/gasyoun/RuWritingStyles/blob/main/.zenodo.json),
      шаги в [docs/zenodo-doi-steps.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/zenodo-doi-steps.md));
      релиз v2.12.0 опубликован. **Открыта кнопка автора**: включить репозиторий в
      Zenodo, подтвердить релиз, вписать DOI.
- [x] **Пакет методологической статьи**: черновик
      [methodology-paper-draft.ru.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/methodology-paper-draft.ru.md)
      с усредненными числами H072/H073 + [docs/paper-pack/](https://github.com/gasyoun/RuWritingStyles/tree/main/docs/paper-pack);
      зарегистрирована как **A29** (3/5) в
      [ARTICLES.md](https://github.com/gasyoun/Uprava/blob/main/ARTICLES.md);
      венью решено 04-07-2026 — «Вестник СПбГУ. Востоковедение и африканистика».
- [x] **Консолидация docs**: архивные шапки на трех старых поколениях roadmap;
      удалены датированные дубликаты style-gallery; README разделен — каталог стилей
      остался, движок ушел в [docs/ENGINE.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/ENGINE.md).

Критерий готовности: DOI разрешается (**открыто — кнопка автора**); черновик статьи со
всеми числами ✅; одна каноническая дорожная карта ✅.

---

## Итог квартала (11-07-2026)

Все четыре фазы выполнены за один проход 03-07-2026 (v2.11.0 → v2.12.1): pass-rate
золотых кейсов **0.48 → 0.92** при нулевых diff-провалах, плагин собирается и гоняет
59/59, статья A29 на 3/5 с решенным венью. Открытыми остались только **две кнопки
автора** (Zenodo DOI; релизный репозиторий плагина + тег + BRAT/community-PR) и
инженерный остаток, вошедший в следующую фазу ниже.

## Фаза N — пост-Q3: совет как навык, A29 к подаче, верификатор и остаток

Handoff: [H588](https://github.com/gasyoun/Uprava/blob/main/handoffs/archive/H588-Fable_RuWritingStyles_rws_post_q3_council_skill_a29_11.07.26.md)
· принята автором 11-07-2026 (пять направлений одобрены разом; платные прогоны — в
прежнем бюджете N=5-протокола; второй аннотатор золотого набора — **вторая
ИИ-модель с раскрытием** по [docs/AI_DISCLOSURE.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/AI_DISCLOSURE.md)).

- [x] **N1 — «Ученый совет» как навык (skill)** ✅ 11-07-2026 (`/rws-council`):: упаковать конвейер совета в
      вызываемый Claude Code-навык (`/rws-council` или родовое имя) — вход: файл
      статьи + совет (`general`/`sanskrit`/`indology`), выход: находки/рецензия;
      двойник существующих `/sanskrit-council`·`/zaliznyak-council`, но поверх
      реального движка `rws run`. Регистрация в SKILLS_INDEX + синк в Codex-двойник.
- [x] **N2 — A29 к подаче (3/5 → 4/5)** ✅ 11-07-2026 (согласие 24/25; адъюдикация одного расхождения — за человеком):: протокол ≥2-аннотаторной разметки золотых
      кейсов — второй аннотатор = вторая ИИ-модель (иная, чем скорер), сравнение
      каппой/процентом согласия, расхождения решает человек; вписать раздел
      annotation-agreement в черновик; финальная вычитка под требования Вестника СПбГУ.
- [x] **N3 — F4-вторая половина** ✅ 11-07-2026 (до/после измерено; karaka r03 — витринный кейс):: коммитменты стилей (obligations из паспортов) в
      промпт верификатора; эффект измерить N=5-протоколом до/после (платно, бюджет
      одобрен).
- [x] **N4 — eval-остаток инфраструктуры** ✅ 11-07-2026 (wall-clock дедлайн; `--routes`; v4-pro 5/5; driver в tools/):: (а) маршруты `model_policy.yml` реально
      потребляются eval-путем (сейчас stage-модели задаются одним `--model` на кейс);
      (б) жесткий wall-clock-дедлайн на запрос (трюкающее соединение переживает любой
      socket-timeout — причина зависаний v4-pro); (в) добить сравнение `deepseek-v4-pro`
      до 5/5 кейсов; (г) прибрать `scratch/paid_benchmark.py` (в тулзу или удалить).
- [x] **N5 — F2/F5-курирование паспортов**: закрыто prior-art-проверкой 11-07-2026 —
      F2 и F5 уже разрешены автором в раунде 2 ревью
      ([prompt-fidelity-review-2026-06.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/prompt-fidelity-review-2026-06.md)
      «Status round 2»: `overstrong_conclusion` снят, взвешивание де-регионализовано,
      «generic»-паспорта пересмотрены — принуждать нечего). Отдельного курирования
      не требуется; измерительный цикл идет по N3.

Фаза N выполнена за один проход 11-07-2026 (Fable 5 `claude-fable-5`, H588). Остаток —
человеческие действия: адъюдикация расхождения разметки (закрыта 19-07-2026 — см. O1 ниже и
[аудит-запись](https://github.com/gasyoun/RuWritingStyles/blob/main/evals/annotation/decisions_applied_vedic-r02-adjudication_2026-07-19.md)),
ГОСТ-оформление библиографии черновика, Zenodo DOI (freeze до 15-07), релизный
репозиторий плагина.

## Фаза O — пост-N: широкий подъём по всем осям (v4-pro-бенчмарк, корпус, паспорта, A29 к подаче)

**✅ ВЫПОЛНЕНА 12-07-2026 (Fable 5 `claude-fable-5`, v2.14.0).** Оговорки исполнения:
адъюдикация vedic-r02 — оба вердикта подготовлены вставляемо
([vedic-r02-adjudication-verdict-variants.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/paper-pack/vedic-r02-adjudication-verdict-variants.md)),
вписание в §4.6 ждёт решения человека; корпус на диске оказался Зализняк-центричным
(+ Смирнов/Tubb) — обещанных решением №3 текстов Елизаренковой/Топорова/Вертоградовой/
Иванова в `../RuWritingStyles-corpus/PDFtoTXT` НЕТ, доводка паспортов адаптирована к
фактическому корпусу (новый голос `smirnov-mahabharata`, доводка `sanskrit-reader` по
Tubb); v4-pro-прогон — маршрутизированный (судья на v4-pro), 0.72/0.92/25-25, разбор в
[benchmark.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/benchmark.md).

Handoff: [H770](https://github.com/gasyoun/Uprava/blob/main/handoffs/archive/H770-Fable_RuWritingStyles_rws-post-n-axis-uplift_12.07.26.md)
· принята автором 12-07-2026 (сессия сбора решений — Opus 4.8 `claude-opus-4-8`;
исполнитель — Fable 5 `claude-fable-5`). Четыре решения автора:

1. **Фокус — все оси сразу** (improve-every-axis): статья A29, паспорта/стили, база
   знаний, корпус; Fable расставляет приоритеты внутри одобренного бюджета.
2. **Платный бюджет — полный прогон `deepseek-v4-pro`** (N=5 по всем 5 золотым кейсам),
   а не только flash: benchmark публикационного качества для A29.
3. **Приватный корпус засеян** (Елизаренкова/Топоров/Вертоградова/Иванов) —
   корпус-зависимые работы разблокированы.
4. **Автор-кнопки — Fable готовит вставляемый ТЕКСТ** (ГОСТ-библиография, формулировка
   адъюдикации, финальное Zenodo-описание); клики остаются за автором.

### O1 — A29 к подаче (4/5 → 5/5) + текст автор-кнопок
- [x] ГОСТ-оформление библиографии черновика
      ([methodology-paper-draft.ru.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/methodology-paper-draft.ru.md)) —
      движок уже даёт `references-gost.md` (ГОСТ Р 7.0.100-2018); привести список
      литературы статьи к нему, вставляемо.
- [x] Адъюдикация vedic-r02 ✅ **19-07-2026** — автор проголосовал `substantive_detection`
      (вариант Б из [vedic-r02-adjudication-verdict-variants.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/paper-pack/vedic-r02-adjudication-verdict-variants.md));
      применено во всех местах (§4.6 черновика, benchmark «Слой 2», cover-letter,
      venue-checklist, `gold-annotation-vedic-classical-anachronism.json`, GOLD_PROTOCOL
      получил правило двухслойного репортинга). Статья репортит **два числа раздельно**:
      механический слой 24/25 = 0.96, содержательный 25/25 = 1.00. Аудит:
      [decisions_applied_vedic-r02-adjudication_2026-07-19.md](https://github.com/gasyoun/RuWritingStyles/blob/main/evals/annotation/decisions_applied_vedic-r02-adjudication_2026-07-19.md).
      Остаток от заметки автора — два новых вопроса (арша-язык как узаконенное отклонение;
      парсинг комментариев к МБх/Рамаяне), см. аудит-запись § «Остаток».
- [x] Финальная вычитка под Вестник СПбГУ
      ([venue-checklist.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/paper-pack/venue-checklist.md));
      полировка EN abstract/keywords.
- [x] Финальный вставляемый текст Zenodo-описания
      ([zenodo-doi-steps.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/zenodo-doi-steps.md)).
- [x] `/articles-update` A29 → 5/5 (контентно submission-ready; остаются только
      автор-кнопки).

### O2 — корпус-driven доводка паспортов (разблокировано)
- [x] `rws corpus-ingest` засеянного корпуса; `rws corpus-status` подтверждает индекс
      (приватный `../RuWritingStyles-corpus/PDFtoTXT`, тексты сюда не коммитятся).
- [x] corpus-audit → слабейшие indology-паспорта; доводка против реального текста
      (voice recreation); при основании — 1–2 новых научных голоса (все 4 слоя:
      `ClaudeStyles/*.md` + паспорт + `manifest.yml` + README).
- [x] Эффект замерить в том же v4-pro-прогоне (O4), чтобы не платить дважды.

### O3 — база знаний + журналы вглубь
- [x] `knowledge/bibliography.json` + `knowledge/sanskrit-terms.json` (indology-ядро
      всё ещё с пробелами; формат-сохраняюще, cross-ref через `validate_project`).
- [x] Новые русские indology-журнальные профили сверх vya/ppv/vestnik-spbu (кандидаты:
      «Индоевропейское языкознание и классическая филология» (Kazansky), «Восток
      (Oriens)», «Вопросы языкознания») — требования брать с сайтов журналов, не
      выдумывать; провод в `report.journal_compliance`.

### O4 — полный v4-pro N=5 бенчмарк (бюджет одобрен)
- [x] N=5 по всем 5 золотым кейсам на `deepseek-v4-pro` (прежний протокол был на flash;
      v4-pro доведён до 5/5 лишь single-run) — публикационная таблица для A29 в
      [benchmark.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/benchmark.md).
- [x] До/после для O2/O3 сцепить в этот же прогон.

### O5 — детерминированная точность линтера (побочная находка N2, дёшево, без платных)
- [x] `missing_iast_on_first_mention` срабатывает при УЖЕ присутствующем IAST (3 из 4
      ложных срабатываний rater-B в разметке H588 N2) → детерминированный фикс +
      регрессионный тест; повышает precision и укрепляет rater-agreement-нарратив статьи.

Критерий готовности: A29 контентно submission-ready (ГОСТ-библиография + вписанная
адъюдикация + пройденный чек-лист венью, 5/5); v4-pro N=5 таблица в benchmark.md;
корпус засеян и ≥1 паспорт доведён с измеренным эффектом; ≥1 новый журнальный профиль;
линтер-FP закрыт тестом; changelog `[Unreleased]` → релиз по `/cut-release`; Фаза O
оттикана.

**Автор-кнопки (НЕ агент, в GTD):** Zenodo DOI (заморожен до 15-07 — org-wide freeze),
релизный репозиторий плагина + тег `obsidian-v0.1.0` + BRAT + community-PR, gc-запрос в
GitHub Support по dangling до-purge объектам. Fable готовит их вставляемый текст (O1),
клики за автором.

## Вне квартала (паркинг)

gc-запрос в GitHub Support по dangling-объектам до-purge истории (заморожен вместе с
Zenodo до 15-07). Пополнение приватного корпуса выполнено — корпус засеян, работа с ним
перенесена в Фазу O2.

---

_Dr. Mārcis Gasūns_
