# SIGNOFF A29 — author-voice pass

_Created: 06-09-2026 · Last updated: 06-09-2026_

**Scope.** Manuscript [docs/methodology-paper-draft.ru.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/methodology-paper-draft.ru.md) («Совет филологов»: агентное рецензирование научной прозы по санскритологии с детерминированным контролем качества; Russian, target venue «Вестник СПбГУ. Востоковедение и африканистика»). Pass under [H3857](https://github.com/gasyoun/Uprava/blob/main/handoffs/H3857-Fable_Uprava_all-articles-author-voice-pass-workflow_01.09.26.md), executed by Fable 5.1 (`claude-fable-5-1`) on 06-09-2026. Voice, register and framing only; no number, claim or citation altered; mechanical drift gate (`voice_drift_check.py --git origin/main`) CLEAN: numbers 411/411, URLs 16/16, DOIs 3/3, citations 1/1, IAST 8/8, headings 19/19, table rows 36/36.

The paper was already at readiness 5/5, so the pass was deliberately light: eight edits, of which two are the standing no-yo rule (the Cyrillic letter yo is never used) and one is the required header note. Byline `М. Ю. Гасунс · независимый исследователь · ORCID … · gasyoun@ya.ru` kept as is — it is the journal's initials form and equivalent to the standing RU byline.

## 1. Voice calls made — each may be vetoed

| # | Location | Call | Rationale |
|---|---|---|---|
| 1 | Header note (blockquote under byline) | `Last updated` 14-08-2026 → 06-09-2026; appended `Author-voice pass 06-09-2026 ([SIGNOFF_A29_author_pass.md](…))` to the status blockquote | Required by the pass; the blockquote already lists the manuscript's status history |
| 2 | §1, new closing paragraph | Added one sentence: «Вклад статьи методологический: показано, что одиночный прогон не дает метрики, и введен N-усредненный бенчмарк.» — cut after adversarial verify: the first draft's tail «которым получены все цифры ниже» over-claimed (§4.2/§4.5/§4.6 report single-run and annotation figures), so the sentence now restates the abstract's claim and nothing more | §1 posed the problem and jumped into §2 without stating the contribution; the sentence restates the abstract's own contribution claim in the body so the question asked up front is the one §4–§5 answer. No new claim, no number. A first draft carried a section roadmap («§2 и §3 задают…»); dropped because the drift gate counts section numbers |
| 3 | §2 «Связанные работы» | ~~Four bold-lead bullets rewritten as one prose paragraph~~ — reverted after adversarial verify: the prose version mis-sourced ГОСТ Р 7.0.100-2018 and IAST to Sanskrit lexicography («Из цифровой лексикографии санскрита взяты … а ГОСТ … и IAST»); the original bullet list is restored verbatim | Meaning drift outweighs the de-bulleting gain; bullets stand |
| 4 | §3 «Совет» | «Все привязано» — the yo removed from the first word | No-yo rule; the neuter verb keeps the reading unambiguous |
| 5 | §4.3, after table | ~~«Гигантский разброс Δ символов…» → «Разброс Δ символов…»~~ — reverted after adversarial verify: the magnitude word is part of the claim, not decoration | Original wording restored |
| 6 | §4.5 | ~~«не заIAST'енных автором по недосмотру» → «оставленных автором без IAST по недосмотру»~~ — reverted after adversarial verify: the coinage is the author's own voice | Original wording restored |
| 7 | §4.7, after table | «Три вывода. (1)…» → «Отсюда три вывода. (1)…» | Telegram fragment with a dropped verb; the transition now carries the thread from the counts to the conclusions |
| 8 | §5, bullet on `vedic-classical-anachronism` | «зачет» — the yo removed | No-yo rule (the only other yo in the file) |

Not touched, on purpose: §5 «Обсуждение и ограничения» stays a bulleted list (a limitations list is conventional and each item is a full paragraph); the in-sentence bold emphases (**только**, **знал**, **не**) are sparse and load-bearing; impersonal/authorial voice («Предлагается», «Наш метод») kept because first-person singular is not the register of «Вестник СПбГУ»; the draft-status blockquote's own jargon («контентно submission-ready») is a working note, not paper text.

## 2. Substance flags carried (not fixed)

1. **Stale open task.** The last item under «Открытые задачи перед сабмишном» («Вписать в §4.6 вердикт человеческой адъюдикации `vedic-r02`…») is already done: §4.6 carries the adjudication block dated 19-07-2026, and the first strikethrough item even says so. Striking it is a status change, so it is left for the author; while it stands, the header note's «остаются кнопки автора — адъюдикация `vedic-r02`» is also stale.
2. **Abstract omits §4.7.** Both abstracts end the story at 23/25 = 0.92 (§4.4); the later routed run with the heavy judge (§4.7, 18/25 = 0.72, detection 23/25 = 0.92) and its argument that the two figures are not comparable are absent from the abstract. A reviewer reading only the abstract sees a rosier bottom line than §4.7. A human should decide whether the abstract gains one sentence on §4.7 or whether §4.7 is framed explicitly as a post-hoc calibration run.
3. **RU and EN abstracts differ in content.** The EN abstract states the two-rater gold-set agreement (0.96) and lists four philologists; the RU abstract has no sentence on §4.6 and lists six names (adds Мельчук, Лидова). Either could be the intended venue form, but they should say the same thing.
4. **§4.3 heading vs table caption.** The heading says `deepseek-chat` → `deepseek-v4-flash` and §4.3's last paragraph explains the alias; §4.5 still cites the run as `deepseek-chat` without the alias note. Consistent, but a reader may stumble; not a defect, a readability note.
5. **Byline form.** The manuscript carries `М. Ю. Гасунс`; the standing RU academic byline is `Марцис Гасунс (Mārcis Gasūns), независимый исследователь, ORCID …`. Kept as is because the journal uses initials; the author may want the Latin form in parentheses for ORCID matching.
6. **Two over-long source lines** (§4.6 last paragraph, §7 penultimate sentence) exceed the file's wrap width; cosmetic in Markdown source only, left alone to keep the diff to voice.

## 3. Read-and-sign

About 30 minutes: read §1's new closing sentence and the §2 paragraph against the bullets on `origin/main` (that is the whole non-trivial diff), then rule on flags 1–3. Proposed readiness: stays 5/5 (propose only). Venue: no change recommended; «Вестник СПбГУ. Востоковедение и африканистика» was decided 04-07-2026 and the manuscript already meets its formal requirements (EN abstract, ГОСТ Р 7.0.100-2018 list). No submission action before 2026-11-01.

_Dr. Mārcis Gasūns_
