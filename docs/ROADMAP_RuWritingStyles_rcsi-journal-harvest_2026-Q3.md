# ROADMAP — RCSI journal profiles and article harvest (RuWritingStyles, 2026-Q3)

_Created: 19-08-2026 · Last updated: 24-08-2026_

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
- [ ] **W1.4 Extraction and gate.** `extract.py` with the wave-0 winner pinned, the fallback
      chain, the Cyrillic sanity gate and the OCR escalation of D14.
- [ ] **W1.5 Pinned-article harvest.** `rws journal-harvest --pinned` ingests the five named
      articles end to end: text into `PDFtoTXT/`, sidecar JSON, bibliography row, FTS5 index.
- [ ] **W1.6 The guarantee.** `knowledge/rcsi/pinned_articles.json` plus `rws corpus-verify`
      plus the test that fails when any pinned article stops satisfying D13.
- [ ] **W1.7 Registration.** `SOURCES.md` rows for the six journals with licence facts;
      `.ai_state.md` and `CHANGELOG.md` updated; release cut.

**Unblocked by:** W0.4 for W1.4 onward; W1.1 for everything else.
**Unblocks:** wave 2, and the corpus gate on H944 / H1882.

## Wave 2 — catalogue discovery and the bounded bulk harvest

- [ ] **W2.1 Catalogue crawl.** Walk the paginated platform index, resolve every slug's OAI
      `Identify` and `/about` scope text, and write `knowledge/rcsi/catalogue.json` with a
      per-journal `include` / `exclude` / `uncertain` verdict and the evidence for it.
- [ ] **W2.2 Subject filter.** The ru+en term list and the article-level classifier of D04,
      with its own fixture-backed tests.
- [ ] **W2.3 Review queue.** Uncertain journals and uncertain articles rendered as a
      [/review-sheet](https://github.com/gasyoun/claude-config/blob/main/commands/review-sheet.md)
      voting sheet, registered in
      [Uprava/REVIEW_SHEETS_INDEX.md](https://github.com/gasyoun/Uprava/blob/main/REVIEW_SHEETS_INDEX.md).
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
