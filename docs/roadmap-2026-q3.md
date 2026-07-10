# Дорожная карта Q3 2026 — «Доверенный бенчмарк» (канонический план)

_Created: 03-07-2026 · Last updated: 03-07-2026_

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

Handoff: [H072](https://github.com/gasyoun/Uprava/blob/main/handoffs/H072-Fable_RuWritingStyles_RWS_eval_harness_nrun_03.07.26.md) · выполняется первой.

- [ ] `rws eval-run --repeat N` (или `eval-suite --repeat`): N независимых прогонов кейса,
      агрегат `eval-aggregate.json` — pass-rate, среднее/σ по Δ-метрикам, разброс детекции.
- [ ] Политика меток скорера: alias-список в манифесте кейса (начато в `7dbbcc4`
      для `unsupported_etymology`) — довести до всех 5 золотых кейсов, задокументировать
      в [GOLD_PROTOCOL.md](https://github.com/gasyoun/RuWritingStyles/blob/main/evals/GOLD_PROTOCOL.md).
- [ ] Temperature=0-проба: поддерживает ли `deepseek-chat` детерминизм; если да —
      закрепить в `model_policy.yml` для eval-контекста.
- [ ] Полный платный протокол: 5 золотых кейсов × N=5 на `deepseek-chat` + один
      сравнительный прогон с `deepseek-reasoner` на council/verify (маршрут уже описан
      в `model_policy.yml`, но никогда не тестировался).
- [ ] Заполнить [benchmark.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/benchmark.md)
      усредненными числами с доверительными интервалами — это доказательная база статьи.

Критерий готовности: benchmark.md сообщает pass-rate ± разброс по ≥5 прогонам;
повторный запуск протокола воспроизводит выводы (не обязательно числа).

## Фаза B2 — Span-patch-реконструкция ревизии (архитектурный фикс)

Handoff: [H073](https://github.com/gasyoun/Uprava/blob/main/handoffs/H073-Fable_RuWritingStyles_RWS_span_patch_reconstruction_03.07.26.md) · после B1 (harness измеряет эффект).

- [ ] `revision.py`: LLM выдает только per-span замены (`applied_changes` со span_id +
      replacement); полный `revised.md` собирает движок — нетронутые сегменты копируются
      байт-в-байт из `segments.json`/`normalized.md`.
- [ ] Diff-fidelity становится верной **по построению**: измененные символы = только
      принятые спаны. Лимиты в eval остаются как страховка, но перестают быть лотереей.
- [ ] Обратная совместимость: схема `revision.schema.json`, `validate-run`,
      плагинный diff-accept (он уже работает от line-diff — переключить на
      engine-предоставленные changes, пункт «optional» из плана Tier-2).
- [ ] Ре-бенчмарк по протоколу B1 до/после — ожидание: diff-провалы → ~0, зачет
      определяется детекцией и верификацией.

Критерий готовности: N=5 усредненный зачет золотых кейсов ≥ 4/5, при нулевых
diff-провалах; регресс-suite mock зеленый.

## Фаза R1 — Obsidian-плагин: CI и релизный репозиторий

Handoff: [H074](https://github.com/gasyoun/Uprava/blob/main/handoffs/H074-Opus_RuWritingStyles_RWS_obsidian_plugin_ci_release_03.07.26.md) · независима, можно параллельно с B1/B2.

- [ ] Починить `npm install` на main (dependabot peer-конфликт `obsidian@1.13.1` ↔
      `@codemirror/state`); закрепить рабочую матрицу зависимостей.
- [ ] CI-job для плагина (build + 59 тестов) в
      [ci.yml](https://github.com/gasyoun/RuWritingStyles/blob/main/.github/workflows/ci.yml) —
      сейчас CI Python-only, и сломанные bump-ы не ловятся.
- [ ] Подготовить выделенный релизный репозиторий `gasyoun/ruwritingstyles-obsidian`
      (root-manifest, bare-теги) по
      [RELEASE.md](https://github.com/gasyoun/RuWritingStyles/blob/main/obsidian-plugin/RELEASE.md);
      монорепозиторная папка остается dev-источником.
- [ ] Кнопки автора: пуш тега `obsidian-v0.1.0`; PR в obsidianmd/obsidian-releases; BRAT.

Критерий готовности: CI ловит ломающий bump; из релизного репо ставится рабочий плагин.

## Фаза R2 — Публикационный проход (после B1+B2)

Handoff: [H075](https://github.com/gasyoun/Uprava/blob/main/handoffs/H075-Opus_RuWritingStyles_RWS_publish_pass_03.07.26.md) · последняя — статья зависит от чисел B1/B2.

- [ ] **Zenodo DOI**: первый GitHub-релиз (v2.11.x с B1+B2 в changelog) → DOI →
      вписать в [CITATION.cff](https://github.com/gasyoun/RuWritingStyles/blob/main/CITATION.cff)
      и README. Кнопка автора: включить репозиторий в Zenodo и подтвердить релиз.
- [ ] **Пакет методологической статьи**: развернуть
      [methodology-paper-outline.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/methodology-paper-outline.md)
      в черновик с реальными усредненными числами; байлайн/CITATION/cover letter —
      по `/paper-submission-pack`; зарегистрировать статью в
      [ARTICLES.md](https://github.com/gasyoun/Uprava/blob/main/ARTICLES.md) (новый Axx).
- [ ] **Консолидация docs**: пометить три старых поколения roadmap архивными шапками;
      удалить датированные дубликаты style-gallery; README разделить — каталог стилей
      (человеческий) vs движок (инженерный) — каталог остается в README, движок уходит
      в `docs/ENGINE.md` со ссылкой.

Критерий готовности: DOI разрешается; черновик статьи со всеми числами; одна
каноническая дорожная карта.

## Вне квартала (паркинг)

Пополнение приватного корпуса (Елизаренкова/Топоров/Вертоградова/Иванов — сканы дает
автор), F2/F5-курирование паспортов (доменные решения), F4-вторая половина (коммитменты
стилей в промпт верификатора — требует eval-прохода, естественно ложится ПОСЛЕ B1),
gc-запрос в GitHub Support по dangling-объектам до-purge истории.

---

_Dr. Mārcis Gasūns_
