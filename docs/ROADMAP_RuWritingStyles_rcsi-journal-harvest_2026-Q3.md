# ROADMAP — RCSI journal profiles and article harvest (RuWritingStyles, 2026-Q3)

_Created: 19-08-2026 · Last updated: 02-09-2026_

Wave layer of [PLAN_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/PLAN_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md).
Ruling references (D01–D20) point at that document's decisions table.

## Wave 0 — the extractor bake-off (blocks everything that touches a PDF) ✅ DONE 19-08-2026 (H3153, v2.26.0)

Wave 0 exists because D08 makes the extractor a measured choice, and because the rest of the
pipeline needs a pinned winner before it can extract anything. It is small, self-contained,
and produces a document rather than a feature.

- [x] **W0.1 Candidate discovery.** Inventory every text extractor and OCR path reachable
      from this machine — the four named in D09, plus a sweep of installed skills
      (`~/.claude/skills`), installed Python distributions, and the `PATH` — and shortlist
      any modern layout-aware extractor worth a throwaway-venv install (`marker`, `docling`,
      `unstructured` are the named candidates; none is installed today).
- [x] **W0.2 Sample set.** Assemble a fixed benchmark sample: one PDF galley from each of the
      six in-scope journals, plus the two known-garbled corpus PDFs that
      [.ai_state.md](https://github.com/gasyoun/RuWritingStyles/blob/main/.ai_state.md)
      names as `pdftotext` failures (`Digital_Humanities-2023.pdf`,
      `Digital-Humanities_IgorPilshchikov.pdf`). The failures are the point: an extractor
      that only handles the easy PDFs has not been tested.
- [x] **W0.3 Scored run.** Run every candidate over every sample, scoring Cyrillic character
      ratio, replacement-character rate, real-word hit rate, word count against the article's
      declared page range, and wall-clock seconds per page.
- [x] **W0.4 Verdict.** Commit [docs/BENCHMARK_pdf-extractors_ru_19-08-2026.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/BENCHMARK_pdf-extractors_ru_19-08-2026.md) with the score
      table, the pinned winner (`pymupdf-text`), the fallback order
      (`pymupdf-text → pdfminer.six → pypdf → ocrmypdf+tesseract rus`, pinned as
      `PDF_EXTRACTOR_CHAIN`), and the calibrated sanity-gate thresholds (`SANITY_THRESHOLDS`).

**Unblocked by:** nothing. **Unblocks:** W1.4, W1.5 and all of wave 2.

## Wave 1 — the harvester, proven on the pinned articles

- [x] **W1.1 Platform client.** `rcsi.py`: throttled cached HTTP, OAI `Identify` /
      `ListRecords` with `resumptionToken` paging, `citation_*` meta parsing, galley URL
      resolution. ✅ DONE 23-08-2026 — shipped in
      [PR #175](https://github.com/gasyoun/RuWritingStyles/pull/175) (commit
      [`970619e`](https://github.com/gasyoun/RuWritingStyles/commit/970619e5053dd0aba00bf8480f5e1e00c7d080c0),
      H3154): `_throttled_get` (disk cache + 1 req/s throttle),
      `identify()`, `list_records()` (resumptionToken loop), `article_meta()`
      (`citation_*` tag parsing incl. ru/en variants), `galley_pdf_url()`.
      5/5 tests green in
      [tests/test_rcsi_client.py](https://github.com/gasyoun/RuWritingStyles/blob/main/tests/test_rcsi_client.py).
      (A09, tick-only pass — the code predates this roadmap-drain unit.)
- [x] **W1.2 Schema extension.** Extend
      [schemas/journal-profile.schema.json](https://github.com/gasyoun/RuWritingStyles/blob/main/schemas/journal-profile.schema.json)
      per D10 and confirm all five existing profiles still validate. ✅ DONE 24-08-2026 —
      shipped in [PR #175](https://github.com/gasyoun/RuWritingStyles/pull/175) (commit
      [`970619e`](https://github.com/gasyoun/RuWritingStyles/commit/970619e5053dd0aba00bf8480f5e1e00c7d080c0),
      H3154): all eleven D10 optional properties (`verified`, `checked_on`, `platform`,
      `slug`, `issn`, `url`, `guidelines_url`, `oai_endpoint`, `license`, `subjects`,
      `derived_by`) present with `additionalProperties: false` and `id`+`name` still the only
      required pair; [schemas/article-sidecar.schema.json](https://github.com/gasyoun/RuWritingStyles/blob/main/schemas/article-sidecar.schema.json)
      (D11, S1.2's second touched file) also shipped. `python tools/validate_project.py`
      confirms all five existing profiles in
      [knowledge/journals/](https://github.com/gasyoun/RuWritingStyles/tree/main/knowledge/journals)
      still validate; `pytest -k "journal or schema"` is 46/46 green. (A10, tick-only pass —
      the code predates this roadmap-drain unit, same pattern as W1.1/A09.)
- [x] **W1.3 Profile derivation.** `rws journal-add <slug>` — fetch `/about/submissions`,
      derive what is mechanically derivable, draft the judgment fields, write the profile with
      `verified: false`, and refuse to overwrite an existing profile in place (emit a proposed
      diff instead). ✅ DONE 28-08-2026 — shipped in [PR #175](https://github.com/gasyoun/RuWritingStyles/pull/175)
      (commit [`970619e`](https://github.com/gasyoun/RuWritingStyles/commit/970619e5053dd0aba00bf8480f5e1e00c7d080c0),
      H3154): `cmd_journal_add` + `journals.derive_profile` / `proposed_profile_diff` —
      the live OAI `Identify` fetch resolves the platform name; mechanically derivable
      fields only (`url`, `guidelines_url` = `/about/submissions`, `oai_endpoint`,
      `platform`, `slug`, `checked_on`, `derived_by`) are written with `verified: false`,
      while judgment fields (`max_chars`, `citation_format`, `first_mention_rule`, …)
      deliberately stay absent — an auto-derived draft never pretends to know them (D10
      note in the docstring). An existing profile is never overwritten: refusal exit 3
      with the key-level proposed diff, `--force` as the explicit escape. Verified live
      28-08-2026: `journal-add 0869-5873` against a planted stub resolved "Herald of the
      Russian Academy of Sciences", refused with the full proposed diff, stub
      byte-identical after the run; `pytest -k "journal or schema"` 46/46 green.
      (A11, tick-only pass — same pattern as W1.1/A09 and W1.2/A10.)
- [x] **W1.4 Extraction and gate.** `extract.py` with the wave-0 winner pinned, the fallback
      chain, the Cyrillic sanity gate and the OCR escalation of D14. ✅ DONE 28-08-2026 —
      shipped in [PR #175](https://github.com/gasyoun/RuWritingStyles/pull/175)
      (commit [`970619e`](https://github.com/gasyoun/RuWritingStyles/commit/970619e5053dd0aba00bf8480f5e1e00c7d080c0),
      H3154; wave-0 chain pinned earlier by H3153, commit
      [`924b1b6`](https://github.com/gasyoun/RuWritingStyles/commit/924b1b6)):
      [`extract.py`](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/extract.py)
      walks `PDF_EXTRACTOR_CHAIN` (`pymupdf-text → pdfminer.six → pypdf → ocrmypdf+tesseract rus`,
      `pdftotext` deliberately absent after its 1/8 Cyrillic blanking), `sanity()` /
      `verdict_for()` gate every attempt, and `extract_best()` implements the D07/D14 order
      HTML → PDF chain → `escalate_ocr()` with full attempts provenance plus the
      language-flip retry; quarantine on total failure stays the caller's (`harvest.py`).
      Verified 28-08-2026: `pytest -k "extract or sanity or journal or schema"` 58/58 green.
      (A12, tick-only pass — same pattern as W1.1/A09, W1.2/A10 and W1.3/A11.)
- [x] **W1.5 Pinned-article harvest.** `rws journal-harvest --pinned` ingests the five named
      articles end to end: text into `PDFtoTXT/`, sidecar JSON, bibliography row, FTS5 index.
      — shipped in two halves. Harvest half 23-08-2026
      ([RuWritingStyles PR #175](https://github.com/gasyoun/RuWritingStyles/pull/175), H3154/v2.27.0):
      live harvest 5/5 pinned articles written to the private corpus, zero quarantined,
      `rws corpus-verify` 5/5 — text + sidecars + bibliography rows recorded in
      [.ai_state.md](https://github.com/gasyoun/RuWritingStyles/blob/main/.ai_state.md) (v2.27.0 entry).
      FTS5 half 28-08-2026 (OxAlpha `opencode`, via `/drain`): the index had been left empty
      (0 rows in `corpus_segments`) — `rws corpus-ingest` run against the private corpus:
      **18 file(s), 5091 segment(s)** indexed; `rws corpus-search "национальный корпус русского языка"`
      retrieves the pinned articles (Moldovan 2024, Plungian 2024, Savchuk 2024 confirmed in top hits).
      `rws.db` stays gitignored — no corpus content in the public repo.
- [x] **W1.6 The guarantee.** `knowledge/rcsi/pinned_articles.json` plus `rws corpus-verify`
      plus the test that fails when any pinned article stops satisfying D13. ✅ DONE 28-08-2026 —
      shipped in [PR #175](https://github.com/gasyoun/RuWritingStyles/pull/175)
      (commit [`970619e`](https://github.com/gasyoun/RuWritingStyles/commit/970619e5053dd0aba00bf8480f5e1e00c7d080c0),
      H3154): the committed five-entry manifest with `expected_stem` backfilled from the live
      harvest, `rws corpus-verify` re-checking text presence, sidecar schema validity,
      DOI-or-URL bibliography keying, sanity verdict and FTS retrievability per entry
      (self-healing re-index of an absent file, sidecar-URL match when a stem is renamed),
      and [tests/test_pinned_articles.py](https://github.com/gasyoun/RuWritingStyles/blob/main/tests/test_pinned_articles.py)
      (manifest shape + verifier green path and bibliography/text-missing failure paths).
      Verified live 28-08-2026: `rws corpus-verify` **5/5 pinned articles verified**, exit 0;
      `pytest tests/test_pinned_articles.py` 7/7 green. (A06, tick-only pass — the code
      predates this roadmap-drain unit, same pattern as W1.1/A09 through W1.4/A12.)
- [x] **W1.7 Registration.** `SOURCES.md` rows for the six journals with licence facts;
      `.ai_state.md` and `CHANGELOG.md` updated; release cut. ✅ DONE 30-08-2026 —
      shipped in [PR #197](https://github.com/gasyoun/RuWritingStyles/pull/197):
      [`SOURCES.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/SOURCES.md)
      one row per journal (D16) with licence facts live-re-verified 30-08-2026
      (Вестник РАН: copy retained + exclusive first-publication licence, no CC statement;
      RUDN: no CC badge; Филологические науки: **CC BY 3.0 declared on /about/submissions**
      — correction of the 23-08 "no badge" note; Вопросы языкознания: copyright agreement
      text, no CC; Acta: exclusive-right transfer to ИЛИ РАН on about + CC BY-NC-ND 4.0
      stays the declared publication licence; sixth row — ИЯКФ/Тронские чтения behind
      profile `iyakf`, off-platform). `.ai_state.md` + `CHANGELOG.md` updated;
      registration-only change — no eval-gate impact, release carries the docs bump.

**Unblocked by:** W0.4 for W1.4 onward; W1.1 for everything else.
**Unblocks:** wave 2, and the corpus gate on H944 / H1882.

## Wave 2 — catalogue discovery and the bounded bulk harvest

- [x] **W2.1 Catalogue crawl.** Walk the paginated platform index, resolve every slug's OAI
      `Identify` and `/about` scope text, and write `knowledge/rcsi/catalogue.json` with a
      per-journal `include` / `exclude` / `uncertain` verdict and the evidence for it.
      ✅ DONE 31-08-2026 — shipped in
      [PR #198](https://github.com/gasyoun/RuWritingStyles/pull/198):
      [`rcsi.index_pages()` / `rcsi.walk_index()`](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/rcsi.py)
      walk the measured layout (`/index?searchInitial=&journalsPage=N`, 50 entries/page;
      walk stops on the first empty page, the first page byte-identical to the previous one —
      the platform re-serves its final 5-entry page forever past the end — or a 40-page hard
      stop), `rcsi.fetch_scope_text()` reads
      `/about/editorialPolicies#focusAndScope`,
      [`harvest.build_catalogue()`](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/harvest.py)
      crawls the index, `Identify`s every slug, classifies via
      `journal_scope.classify_journal` and writes
      [`knowledge/rcsi/catalogue.json`](https://github.com/gasyoun/RuWritingStyles/blob/main/knowledge/rcsi/catalogue.json)
      (schema: [`schemas/rcsi-catalogue.schema.json`](https://github.com/gasyoun/RuWritingStyles/blob/main/schemas/rcsi-catalogue.schema.json)).
      **Live run 31-08-2026: 992 journals — include 61, exclude 302, uncertain 629.**
      CLI: `rws journal-catalogue` (crawls when absent) / `--refresh` / `--json`; the
      wave-2 placeholder is gone. Measured exceptions recorded as `evidence_other`:
      five journals (incl. 2542-1816, 2782-4926) redirect their OAI endpoint to a Login
      page — `_parse_oai` now degrades non-XML payloads to `RcsiError` and the record
      carries the anomaly instead of crashing the crawl. Вестник РАН (`0869-5873`) is
      honestly `uncertain` — its Editorial Policies page has no `#focusAndScope` section
      at all; the five named journals stay pinned by name regardless of verdict.
      Offline tests 16 strong against frozen live-layout fixtures
      ([tests/test_journal_catalogue.py](https://github.com/gasyoun/RuWritingStyles/blob/main/tests/test_journal_catalogue.py),
      fixtures re-frozen through `tools/export_rcsi_fixtures.py`); full suite 364 green,
      validate_project SUCCESS, ci-eval-gate 0 regressions.
      (W2.2/W2.3 own the uncertain tail — the subject filter re-scores it at the article
      level and the review sheet surfaces the residue.)
- [x] **W2.2 Subject filter.** The ru+en term list and the article-level classifier of D04,
      with its own fixture-backed tests.
      ✅ DONE 02-09-2026 — shipped in
      [PR #200](https://github.com/gasyoun/RuWritingStyles/pull/200):
      the classifier core (`journal_scope.classify_article` +
      [`knowledge/rcsi/subject_terms.json`](https://github.com/gasyoun/RuWritingStyles/blob/main/knowledge/rcsi/subject_terms.json))
      existed since wave 1 (H3154, S1.4); this unit closed its two real gaps.
      **The dead rescue path:** D04 filters over "OAI Dublin Core subject plus
      title and keywords", but both `harvest.py` call sites dropped the OAI
      record — `selection_record` is now threaded through `harvest_journal`
      and `_harvest_one`, so an article the page metadata alone classifies
      `uncertain` can be rescued by its `dc:subject` (live: «К лингвистическим
      воззрениям Франца Боаса» — the title's «лингвистическим» is not a
      substring of the term «лингвистика»; the OAI subject decides include).
      Sidecar `selection` now also records `negative_terms` (schema extended,
      optional — existing sidecars stay valid). **Fixture-backed tests:**
      [`article_meta_samples.json`](https://github.com/gasyoun/RuWritingStyles/blob/main/tests/fixtures/rcsi/article_meta_samples.json)
      freezes six real article metas + OAI subjects (exported live 02-09-2026
      via `tools/export_rcsi_fixtures.py`, which now refuses to write a drifted
      verdict over a frozen expectation), one per verdict class — linguistics
      include, English-language include (`expect_cyrillic: false`), two
      Вестник РАН general-science excludes, an honest uncertain, and the
      dc:subject rescue;
      [`tests/test_journal_scope.py`](https://github.com/gasyoun/RuWritingStyles/blob/main/tests/test_journal_scope.py)
      gains 6 fixture-backed + wiring tests (13 total in the file), including
      an offline `harvest_journal(dry_run=True)` test that fails if the OAI
      subject ever stops reaching the classifier. Gates: pytest 371 + 74
      subtests green (up from 364), validate_project SUCCESS, ci-eval-gate
      0 regressions. The 629-journal `uncertain` tail is W2.3's review-queue
      input and stays untouched here.
- [x] **W2.3 Review queue.** Uncertain journals and uncertain articles rendered as a
      [/review-sheet](https://github.com/gasyoun/claude-config/blob/main/commands/review-sheet.md)
      voting sheet, registered in
      [Uprava/REVIEW_SHEETS_INDEX.md](https://github.com/gasyoun/Uprava/blob/main/REVIEW_SHEETS_INDEX.md).
      ✅ DONE 03-09-2026 — sheet
      `ruwritingstyles-rcsi-catalogue_uncertain-628` cut by
      [tools/build_rcsi_review_sheet.py](https://github.com/gasyoun/RuWritingStyles/blob/main/tools/build_rcsi_review_sheet.py)
      from the committed catalogue: **628 cards → 63 packs + parent** (csl-pyutil
      0.23.0 V16 packset), published to the
      [vote hub](https://gasyoun.github.io/vote/sheets/rws_rcsi_uncertain_628.html),
      registered in
      [Uprava/REVIEW_SHEETS_INDEX.md](https://github.com/gasyoun/Uprava/blob/main/REVIEW_SHEETS_INDEX.md).
      Screening (Phase 0-bis, [evidence](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/SCREENING_EVIDENCE_rcsi-uncertain-review_03-09-2026.md)):
      (a) 1 — Вестник РАН stays pinned by name (roadmap W2.1), (b) 0 — the five
      hand-verified profiles are all include, (c) 0 — deliberate, D04 keeps the
      tail human-visible, (d) 628 in three classes: 15 term conflicts, 325 no
      Focus & Scope section, 288 scope text without terms (U7 chips carry
      count + share over the 629 tail on every card). Uncertain ARTICLES:
      empty with reason — the W2.4 harvest produces article-level verdicts; a
      separate article-level sheet follows it. V9 manifest joins
      catalogue.json on slug; V13 identity gate = escaped catalogue slugs
      (year ranges in verbatim English prose correctly trip nothing); SLP1
      allow-list computed per render over verbatim English excerpts.
      github_inbox NOT wired (no device-flow client_id on this machine) —
      per-pack `_pack-NN_decisions.json` exports with the V8 banner naming
      `RuWritingStyles/review/` as the drop path. Shaper
      ([rcsi_review.py](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/rcsi_review.py))
      is derive-don't-store: tests recompute 992/629/628 and the 15/325/288
      split from the committed catalogue on every run. Gates: pytest 379 +
      74 subtests green, validate_project SUCCESS, ci-eval-gate 0 regressions.
- [ ] **W2.4 Bounded harvest.** Run the capped harvest of D20 across every `include` journal;
      commit and push texts to the private corpus repo; report counts, quarantine size and
      the per-journal extraction-source split.
- [ ] **W2.5 Corpus re-index and report.** `rws corpus-ingest`, then `rws corpus-status`, then
      a written statement of what the corpus gate on H944 / H1882 now permits.

**Unblocked by:** wave 1 complete. **Unblocks:** the corpus-gated passport work.

## Non-goals

Named explicitly so an execution agent does not drift into them.

- **No new style passports.** This plan supplies corpus material; deciding which scholar's
  voice deserves a passport stays with H944 / H1882 and their own gates.
- **No changes to eval scoring.** `evals/baselines/gold.json`, `evals/manifest.json` and
  `styles/passports/` are untouched. Harvesting cannot change a score, so a baseline refresh
  would be masking something.
- **No rewrite of `vya.json` or the other four hand-verified profiles.** Re-derivations are
  written as proposed diffs, never applied in place.
- **No publisher beyond RCSI.** eLIBRARY, Cyberleninka and direct journal sites are out of
  scope; the platform-specific facts in the PLAN do not transfer to them.
- **No public-repo corpus.** Restated because it is the one hard fence (D18).
- **No `corpus.py` rewrite.** Sidecars are written in wave 1 but not yet read; teaching the
  indexer to prefer them is deliberately deferred so wave 1 cannot regress indexing.

_Dr. Mārcis Gasūns_
