# IMPLEMENTATION — RCSI journal profiles and article harvest

_Created: 19-08-2026 · Last updated: 19-08-2026_

Ordered build sequence for waves 0 and 1 of
[PLAN_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/PLAN_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md).
Each step names the files it touches and what it depends on. Wave 2 steps are sketched at the
end; they are not needed for the first unattended run.

## Preconditions

- Work in a session-unique worktree: `git worktree add -b <branch> ../RuWritingStyles-h<id>-<pid> origin/main`.
- `PYTHONPATH=src` in the worktree — the editable install points at the original checkout.
- `RWS_CORPUS_DIR` resolves to the private corpus clone; confirm with `rws corpus-status`
  before writing anything.
- Append every improvised ruling to `docs/rcsi-harvest-decisions.log.md` (create on first use).

---

## Wave 0 — the bake-off

> **Done, 19-08-2026 ([H3153](https://github.com/gasyoun/Uprava/blob/main/handoffs/archive/H3153-Opus_RuWritingStyles_rcsi-pdf-extractor-bakeoff_19.08.26.md), shipped in v2.26.0).** S0.1–S0.5 are all complete; the steps below are kept as the record of how, not as work to do. Verdict, matrix and calibration: [BENCHMARK_pdf-extractors_ru_19-08-2026.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/BENCHMARK_pdf-extractors_ru_19-08-2026.md). Winner `pymupdf-text`; `PDF_EXTRACTOR_CHAIN` and `SANITY_THRESHOLDS` pinned in `config.py`; the gate is `sanity()` in `extract.py`.
>
> **Three results change wave 1 and should be read before starting S1.1:** the UA this document prescribes is 403'd site-wide; RCSI publishes English articles, so the gate needs `expect_cyrillic=False` for them; and `pdftotext` is out of the pipeline entirely, including as the reader for another extractor's output.

### S0.1 Candidate inventory
**Touches:** `docs/BENCHMARK_pdf-extractors_ru_19-08-2026.md` (created)
**Depends on:** nothing

Record what is actually available, with versions. Established on 19-08-2026 on this machine:
`pdftotext` 4.00, `tesseract` 5.5.0 with `rus` and `san` traineddata, `ocrmypdf` 17.8.0,
PyMuPDF (`fitz`), `pdfminer.six`, `pypdf`, `easyocr`, `pytesseract`, `bs4`, `lxml`. Not
installed: `marker`, `docling`, `unstructured`, `pdfplumber`, `trafilatura`. Sweep
`~/.claude/skills` and `~/.claude/commands` for any further extraction path before concluding
the inventory — `deeppapernote` was found this way.

### S0.2 Throwaway venv for the uninstalled candidates
**Touches:** nothing in the repo (scratch venv only)
**Depends on:** S0.1

Per D19, create a scratch virtualenv outside the repo, install the shortlisted uninstalled
candidates there, and benchmark them from it. If an install fails or exceeds a few minutes,
record it as `unavailable` with the reason and move on — a failed install is not a stop
condition.

### S0.3 Sample set
**Touches:** `tools/benchmark_extractors.py` (created), scratch sample directory
**Depends on:** S0.1

Six PDF galleys, one per in-scope journal, fetched through the same throttle the harvester
will use, plus the two known-garbled corpus PDFs. Sample PDFs live outside the repo (D18);
only their SHA-256 and source URL are recorded in the benchmark document.

### S0.4 Scoring harness
**Touches:** `tools/benchmark_extractors.py`, `src/ruwritingstyles/extract.py` (created, gate only)
**Depends on:** S0.3

Write the sanity gate first, in `extract.py`, as a pure function:

```
sanity(text) -> {
    "cyrillic_ratio":     Cyrillic letters / all letters,
    "replacement_ratio":  U+FFFD and control chars / all chars,
    "word_hit_rate":      share of tokens that look like real Russian words,
    "words":              token count,
    "verdict":            "pass" | "fail",
}
```

The harness imports it so the bake-off and production score identically. `word_hit_rate` uses
a small committed Russian stopword-and-affix heuristic, not a downloaded dictionary — it only
has to separate real text from mojibake, not do morphology.

### S0.5 Run and rule
**Touches:** `docs/BENCHMARK_pdf-extractors_ru_19-08-2026.md`, `src/ruwritingstyles/config.py`
**Depends on:** S0.4

Run every candidate over every sample. Commit the score table, the winner, the fallback order,
and the thresholds. Pin them in `config.py` as `PDF_EXTRACTOR_CHAIN` and `SANITY_THRESHOLDS`.

**Marked default if the bake-off is inconclusive** (two candidates within noise): prefer
PyMuPDF, because it handles embedded font encodings — the recorded failure mode — better than
poppler. Log the tie in the decisions file.

---

## Wave 1 — the harvester

### S1.1 Platform client
**Touches:** `src/ruwritingstyles/rcsi.py` (created)
**Depends on:** nothing

```
BASE = "https://journals.rcsi.science"
USER_AGENT = "RuWritingStyles/<version> (research harvester; sanskrit.research.institute@gmail.com)"
```

> **This UA does not work (measured 19-08-2026, H3153).** It is **403'd site-wide** — both the OAI endpoint and article pages — while a common browser UA is served 200 on the same URL in the same second. Wave 1 must send a browser-shaped UA (or obtain an allowance from the platform); as specified here it will fetch nothing at all. The 1 req/s throttle is unaffected and should be kept.

- `fetch(url, *, binary=False)` — 1 request/second minimum interval, on-disk cache keyed by
  URL hash under the scratch cache dir, retry twice on 5xx with backoff, raise a typed
  `RcsiRateLimited` on 429/403.
- `identify(slug)` — `GET {BASE}/{slug}/oai?verb=Identify`, parse `repositoryName`,
  `earliestDatestamp`, `adminEmail`.
- `list_records(slug, since=None)` — `verb=ListRecords&metadataPrefix=oai_dc`, follow
  `resumptionToken` until exhausted, yield dicts of the Dublin Core fields.
- `article_meta(slug, article_id)` — `GET {BASE}/{slug}/article/view/{id}`, parse every
  `citation_*` meta tag, keeping `xml:lang` so ru and en variants stay separate; return the
  sidecar-shaped record plus the raw HTML for the extractor.
- `galley_pdf(meta)` — return `citation_pdf_url` verbatim; do not reconstruct it.

Parse XML with `lxml`, HTML with `bs4`. Never assume the slug is the ISSN.

### S1.2 Schema extension
**Touches:** `schemas/journal-profile.schema.json`, `schemas/article-sidecar.schema.json` (created)
**Depends on:** nothing

Add the optional properties listed in the ARCHITECTURE doc; keep `additionalProperties: false`
and the `id` + `name` required pair. Then run `python tools/validate_project.py` and confirm
all five existing profiles still pass — that is the whole acceptance for this step.

### S1.3 The verified gate
**Touches:** `src/ruwritingstyles/journals.py`, `src/ruwritingstyles/project.py`, `src/ruwritingstyles/cli.py`
**Depends on:** S1.2

`set_journal_profile` raises unless `profile.get("verified") is True`; `cli.py`'s
`project-set-journal` catches it, prints the profile's `guidelines_url` and the
`--allow-unverified` escape, and exits 3. `load_journal_preset` is unchanged — reading stays
ungated, because `rws journals` must be able to list an unverified draft.

### S1.4 Subject classifier
**Touches:** `src/ruwritingstyles/journal_scope.py` (created), `knowledge/rcsi/subject_terms.json` (created)
**Depends on:** nothing

The term list is data, not code: three groups (`linguistics`, `philology`, `oriental`), each
with ru and en terms, plus a `negative` group for the general-science noise that Вестник РАН
will otherwise contribute (physics, biology, medicine, geology). `classify_article(record)`
scores title, keywords and Dublin Core subject; a positive hit with no negative hit is
`include`, a negative-only hit is `exclude`, everything else is `uncertain`.

### S1.5 Extraction chain
**Touches:** `src/ruwritingstyles/extract.py`
**Depends on:** S0.5, S1.1

Add to the gate already written in S0.4: `extract_html(html)` using `bs4` against the article
page's body container, the PDF extractors as a registry of callables, `escalate_ocr(pdf_path)`
via `ocrmypdf --language rus --force-ocr` into a temp file then re-extract, and
`extract_best(meta, html, pdf_bytes)` implementing the D07/D14 order. The return value is
always `(text_or_None, provenance_dict)` — never an exception for a bad document, because a
bad document is normal.

### S1.6 Harvest orchestration
**Touches:** `src/ruwritingstyles/harvest.py` (created)
**Depends on:** S1.1, S1.4, S1.5

`harvest_journal(slug, limit, since, dry_run)` and `harvest_pinned()`. Per article: fetch
meta, classify, extract, gate, build the stem, write `<stem>.txt` and `<stem>.json` into
`RWS_CORPUS_DIR`, append the bibliography row, append to the run manifest. Idempotent — an
article whose sidecar already exists with a `pass` verdict is skipped unless `--force`.
Quarantine failures to `RWS_CORPUS_DIR/quarantine/` with their score and reason.

**Windows note:** write text files with `encoding="utf-8"` and `newline="\n"` explicitly, and
never a BOM — the org lint blocks it.

### S1.7 CLI wiring
**Touches:** `src/ruwritingstyles/cli.py`, `docs/cli.md`
**Depends on:** S1.3, S1.6

Four subparsers per the ARCHITECTURE interfaces block, following the existing
`add_parser(...)` + `set_defaults(func=...)` pattern used by all sixty-odd commands. Document
each in [docs/cli.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/cli.md).

### S1.8 Pinned manifest and corpus-verify
**Touches:** `knowledge/rcsi/pinned_articles.json` (created), `src/ruwritingstyles/harvest.py`, `src/ruwritingstyles/cli.py`
**Depends on:** S1.6

Seed the manifest with the five article URLs from the PLAN. `corpus_verify()` checks, per
entry: the text file exists and is non-empty; the sidecar exists, validates, and carries a
DOI; the sanity verdict is `pass`; a bibliography row with that DOI exists; and
`CorpusManager.search` on a distinctive phrase from the title returns that file.

### S1.9 Fixtures and tests
**Touches:** `tests/fixtures/rcsi/*`, `tests/test_rcsi_client.py`, `tests/test_journal_scope.py`, `tests/test_extract_sanity.py`, `tests/test_journal_profile_gate.py`, `tests/test_pinned_articles.py` (all created)
**Depends on:** S1.8

Freeze as fixtures: one OAI `Identify` response, one `ListRecords` page including a
`resumptionToken`, one article HTML page (the Плунгян one), one small PDF, and one
deliberately mojibake text sample. Every test runs offline against these. The live smoke is a
single test skipped unless `RWS_LIVE_SMOKE=1`.

Mirror the fixture-export convention already in
[tools/export_journal_fixtures.py](https://github.com/gasyoun/RuWritingStyles/blob/main/tools/export_journal_fixtures.py).

### S1.10 Registration and release
**Touches:** `SOURCES.md`, `knowledge/bibliography.json`, `.ai_state.md`, `changelog.md`, `CITATION.cff`
**Depends on:** S1.9

One `SOURCES.md` row per journal with its licence verbatim, under a new subsection making
clear these are article corpora rather than style-model sources. Update `.ai_state.md` — in
particular the H944 / H1882 corpus-gate entries, which now have material. Then
[/cut-release](https://github.com/gasyoun/claude-config/blob/main/commands/cut-release.md).

### S1.11 Corpus repo push
**Touches:** the private [RuWritingStyles-corpus](https://github.com/gasyoun/RuWritingStyles-corpus) clone
**Depends on:** S1.6

Commit the new `PDFtoTXT/*.txt` and `*.json` sidecars there and push. Confirm with
`git -C <corpus> status --porcelain` that nothing is left uncommitted. Then re-check that the
public repo's `git status` shows no `.txt`, `.pdf`, or `rws.db` change — the D18 fence check,
run explicitly rather than assumed.

---

## Wave 2 sketch

- **S2.1** `rcsi.catalogue()` — walk the paginated index, collect slugs, `identify` each.
- **S2.2** `journal_scope.classify_journal` over each `/about` scope text; write
  `knowledge/rcsi/catalogue.json` with verdicts and evidence.
- **S2.3** Render the `uncertain` tail as a review sheet; register it in
  [Uprava/REVIEW_SHEETS_INDEX.md](https://github.com/gasyoun/Uprava/blob/main/REVIEW_SHEETS_INDEX.md).
- **S2.4** Loop `harvest_journal` over every `include` slug with the D20 cap; push.
- **S2.5** `rws corpus-ingest && rws corpus-status`; write the corpus-gate statement.

## Known implementation hazards

| Hazard | Handling |
|---|---|
| Slug is not the ISSN | Always key on the URL slug; store `citation_issn` separately |
| Same surname, same year, two articles | Bibliography `id` gets a letter suffix; the file stem gets a short DOI-tail suffix |
| Windows path length | Truncate the transliterated title to 80 characters; the full title is in the sidecar |
| Article HTML has no body container | Falls through to the PDF branch — this is expected for PDF-only journals, not an error |
| `resumptionToken` expiring mid-walk | Retry the walk from the last completed page; caching makes the retry cheap |
| Вестник РАН is general-science | The `negative` term group exists for exactly this; expect a large `exclude` count there and report it rather than treating it as a bug |

_Dr. Mārcis Gasūns_
