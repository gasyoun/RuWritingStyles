# ARCHITECTURE — RCSI journal profiles and article harvest

_Created: 19-08-2026 · Last updated: 19-08-2026_

Structural layer of [PLAN_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/PLAN_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md).

## Component boundaries

Six new modules under
[src/ruwritingstyles/](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles),
each with one job, none reaching past its neighbour.

| Module | Owns | Never does |
|---|---|---|
| `rcsi.py` | All HTTP against journals.rcsi.science: throttle, on-disk cache, user agent, OAI paging, `citation_*` parsing, galley URL resolution | Decide what is in scope; write files outside the cache |
| `journal_scope.py` | The ru+en subject term list; `classify_journal(scope_text)` and `classify_article(record)` returning `include` / `exclude` / `uncertain` with the matched terms as evidence | Fetch anything |
| `extract.py` | The extractor registry, the Cyrillic sanity gate, the OCR escalation, and the extraction-provenance record | Know what a journal or an article is |
| `harvest.py` | Orchestration: enumerate, filter, fetch, extract, gate, write text and sidecar, write bibliography row, write run manifest | Contain HTTP or extraction logic of its own |
| `journals.py` (extended) | Preset load and list as today, **plus** `derive_profile(slug)` and the `verified` gate | Harvest articles |
| `cli.py` (extended) | Four new subparsers, argument validation, human-readable output | Business logic |

`corpus.py` is deliberately untouched in wave 1. It keeps globbing `*.txt` and keeps
deriving metadata from filenames; the sidecars written next to those texts are inert until a
later wave teaches it to prefer them. That is what makes wave 1 incapable of regressing the
existing index.

## A trap the design has to route around

`knowledge/journals/*.json` is globbed by **two** consumers that both assume every file there
is a submission profile:
[list_journal_presets](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/journals.py)
and the validator in
[tools/validate_project.py](https://github.com/gasyoun/RuWritingStyles/blob/main/tools/validate_project.py),
which validates every match against `journal-profile.schema.json`.

Dropping a catalogue or a pinned-article manifest into that directory would therefore both
fail `validate_project` and surface as a phantom journal in `rws journals`. **All new machine
data lives in a new `knowledge/rcsi/` directory instead.** No exceptions, no leading-underscore
tricks.

## Data contracts

### Submission profile — extended (D10)

[schemas/journal-profile.schema.json](https://github.com/gasyoun/RuWritingStyles/blob/main/schemas/journal-profile.schema.json)
keeps `additionalProperties: false` and keeps `id` and `name` as the only required fields.
New optional properties, all absent from the five existing profiles so they keep validating:

| Property | Type | Meaning |
|---|---|---|
| `verified` | boolean | A human or a verifying agent confirmed the judgment fields against the journal's own rules. Absent is treated as `false` |
| `checked_on` | string, `DD-MM-YYYY` | When `verified` was last established |
| `platform` | string | `rcsi` for this family; free for hand-written profiles |
| `slug` | string | The URL path component on the platform. **Not** the ISSN — slug `0869-5873` carries `citation_issn` `3034-5200` |
| `issn` | array of strings | Whatever ISSNs the journal actually declares, print and online |
| `url` | string | Journal home |
| `guidelines_url` | string | The page the judgment fields were derived from |
| `oai_endpoint` | string | Per-journal OAI base |
| `license` | string | Declared licence, verbatim (`CC BY-NC-ND 4.0` for Acta Linguistica Petropolitana) |
| `subjects` | array of strings | Declared scope terms, used by the classifier as evidence |
| `derived_by` | string | Tool and version that produced an auto-derived profile |

**The verified gate.** `load_journal_preset` returns the profile unchanged — reading is never
gated. The gate lives in `set_journal_profile` and in the `rws project-set-journal` command:
attaching a profile whose `verified` is not `true` fails with a message naming
`guidelines_url`, unless `--allow-unverified` is passed. A scraped `max_chars` can then never
drive `report.journal_compliance` without someone having said so.

### Article sidecar — new (D11)

Written as `<stem>.json` beside `<stem>.txt` in the corpus directory; schema
`schemas/article-sidecar.schema.json`.

```
{
  "stem": "2024_Plungian_Korpusnaya-lingvistika-na-sovremennom-etape",
  "journal_slug": "0869-5873",
  "journal_name_ru": "Вестник Российской академии наук",
  "article_id": "268311",
  "url": "https://journals.rcsi.science/0869-5873/article/view/268311",
  "doi": "10.31857/S0869587324090018",
  "edn": "FCHMFE",
  "title_ru": "Корпусная лингвистика на современном этапе",
  "title_en": "Corpus linguistics nowadays",
  "authors_ru": ["Плунгян Владимир Александрович"],
  "authors_en": ["V. A. Plungian"],
  "affiliations_ru": ["Институт русского языка им. В.В. Виноградова РАН"],
  "year": 2024,
  "volume": "94",
  "issue": "9",
  "firstpage": 787,
  "lastpage": 794,
  "language": "ru",
  "keywords_ru": ["корпусная лингвистика", "теория языка"],
  "keywords_en": ["corpus linguistics", "linguistic theory"],
  "license": "CC BY-NC-ND 4.0",
  "pdf_url": "https://journals.rcsi.science/0869-5873/article/download/268311/247270",
  "extraction": {
    "source": "html",
    "extractor": "bs4-article-body",
    "fallback_chain": ["html", "pymupdf", "pdftotext-layout", "ocrmypdf-tesseract-rus"],
    "sanity": {"cyrillic_ratio": 0.71, "replacement_ratio": 0.0, "word_hit_rate": 0.93, "words": 5612},
    "verdict": "pass",
    "harvested_on": "19-08-2026"
  },
  "selection": {"verdict": "include", "matched_terms": ["корпусная лингвистика", "лингвистика"]}
}
```

**Filename rule.** The stem is `<year>_<LatinSurnameOfFirstAuthor>_<slugified-ru-title>`, so
today's `corpus.py` heuristic — four-digit first part is the year, second part is the author —
keeps producing correct metadata with no code change. Titles are transliterated to Latin and
truncated to keep Windows path lengths safe; the true Cyrillic title lives in the sidecar.

### Journal catalogue — new (D05)

`knowledge/rcsi/catalogue.json`: one record per platform journal with `slug`,
`repository_name`, `url`, `scope_text_excerpt`, `verdict`, `matched_terms`, `checked_on`.
Exclusions are records with `verdict: "exclude"`, not omissions — a journal absent from the
file has never been looked at, which is a different fact.

### Pinned articles — new (D13)

`knowledge/rcsi/pinned_articles.json`: an array of `{url, slug, article_id, expected_stem,
reason}`. `rws corpus-verify` and one test read it. Adding an article to this file is how a
future session says "this one must never disappear".

### Bibliography row (D16)

Appended to
[knowledge/bibliography.json](https://github.com/gasyoun/RuWritingStyles/blob/main/knowledge/bibliography.json),
matching the existing shape — `id`, `author`, `year`, `title`, `kind`, `tags` — with `kind`
set to `article` and `journal`, `volume`, `issue`, `pages`, `doi` added. The `id` follows the
existing `Surname YYYY` convention with a letter suffix on collision.

## Extraction pipeline (D07, D08, D14)

```
article page ──> HTML body present?
                   │ yes ──> strip ──> sanity gate ──┬─ pass ──> write text + sidecar
                   │                                 └─ fail ─┐
                   └ no ─────────────────────────────────────┤
                                                             ▼
                                          PDF galley ──> pinned wave-0 winner
                                                             │
                                              fail ──> next extractor in chain
                                                             │
                                              all fail ──> OCR (ocrmypdf + tesseract rus)
                                                             │
                                              still fail ──> quarantine/ + reason, never indexed
```

The sanity gate is a pure function of the text — no network, no model — so it is trivially
testable and identical in the bake-off harness and in production. Thresholds are set by wave 0
and stored in config, not hardcoded in the gate.

## Build vs reuse

| Piece | Verdict | Evidence |
|---|---|---|
| PDF text extraction | **Reuse** `deeppapernote/scripts/extract_source_text.py` (PyMuPDF, 390 lines, already does page text and section structuring), wrapped behind `extract.py`'s registry | Found by prior-art sweep of the installed skills tree; it is the only maintained PDF extractor in the org |
| Metadata discipline for an inbound PDF | **Reuse the discipline** of [/reference-pdf-ingest](https://github.com/gasyoun/claude-config/blob/main/commands/reference-pdf-ingest.md) — never trust the filename, mark every inferred field | Its "mark inferred fields" rule is why the sidecar carries `extraction.verdict` and `selection.matched_terms` rather than bare values |
| Journal-requirements scraping | **Do not reuse** [IndologyScholars/tools/scrape_journal_requirements.py](https://github.com/gasyoun/IndologyScholars/blob/main/tools/scrape_journal_requirements.py) as code — its output file has three data rows and records Acta Linguistica Petropolitana as `no_site`. **Do reuse** its `AUTHOR_GUIDE_PATTERNS` list as a URL-probe seed | Measured: `journal_requirements.csv` is 4 lines including the header |
| VAK journal lists | **Consult, do not depend.** [analytics_output/vak_journals.csv](https://github.com/gasyoun/IndologyScholars/blob/main/analytics_output/vak_journals.csv) (3088 rows) is a useful cross-check on whether an RCSI journal is VAK-listed; it is not the discovery mechanism (D05 rules that a crawl is) | The RCSI slug is absent from every column of those CSVs |
| HTTP, OAI, XML | **Build**, on the standard library plus `lxml`/`bs4` which are already installed | No org-wide HTTP client exists; adding `requests` for one module is not worth a dependency |
| FTS5 indexing | **Reuse unchanged** [corpus.py](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/corpus.py) | Already ingests `*.txt` from `RWS_CORPUS_DIR`; the filename convention was chosen to fit it |
| Review sheets | **Reuse** [/review-sheet](https://github.com/gasyoun/claude-config/blob/main/commands/review-sheet.md) for the uncertain tail | Markdown checkbox sheets are banned org-wide; the skill already produces the decisions.json this pipeline can consume |

## Interfaces

```
rws journal-catalogue [--refresh] [--json]
      Crawl or re-read knowledge/rcsi/catalogue.json; print slug, name, verdict.

rws journal-add <slug> [--force] [--verify]
      Derive and write knowledge/journals/<slug>.json with verified:false.
      Existing profile → print a proposed diff and exit 3 unless --force.

rws journal-harvest <slug> [--limit N] [--since YYYY-MM-DD] [--dry-run]
rws journal-harvest --pinned
      Enumerate, filter, extract, gate, write text + sidecar + bibliography row.

rws corpus-verify [--json]
      Re-check every entry of knowledge/rcsi/pinned_articles.json. Exit 1 on any failure.
```

Exit codes follow the repo's existing convention: `0` success, `1` failure, `3` refused for a
policy reason (unverified profile, existing profile without `--force`).

_Dr. Mārcis Gasūns_
