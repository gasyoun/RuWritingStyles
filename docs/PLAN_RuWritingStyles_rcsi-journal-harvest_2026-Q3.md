# PLAN — RCSI journal profiles and article harvest (RuWritingStyles, 2026-Q3)

_Created: 19-08-2026 · Last updated: 19-08-2026_

Execution-ready plan authored by `/ask` on 19-08-2026 (Opus 5, `claude-opus-5`) from a
five-round interview. Every fork a builder would hit is ruled below; an execution agent
runs this unattended without asking anything.

## Goal

Make adding any [journals.rcsi.science](https://journals.rcsi.science/) journal to
RuWritingStyles a single command that produces **both** halves of what a journal means to
this project: a submission profile in
[knowledge/journals/](https://github.com/gasyoun/RuWritingStyles/blob/main/knowledge/journals)
that `report.journal_compliance` can enforce, **and** article full texts in the private
corpus that the FTS5 index and the style passports can feed on. Five named articles are
pinned so they can never silently drop out of the corpus.

This directly reopens the corpus gate that
[.ai_state.md](https://github.com/gasyoun/RuWritingStyles/blob/main/.ai_state.md) records
as shut: H944 and H1882 both report "batch size = 0 — no attributable texts", and a working
RCSI harvester is precisely the missing input.

## The five pinned articles

| # | Article | Journal |
|---|---|---|
| 1 | [Плунгян В. А. Корпусная лингвистика на современном этапе](https://journals.rcsi.science/0869-5873/article/view/268311) (DOI 10.31857/S0869587324090018) | Вестник Российской академии наук |
| 2 | [0869-5873/article/view/268371](https://journals.rcsi.science/0869-5873/article/view/268371) | Вестник Российской академии наук |
| 3 | [2313-2299/article/view/323403](https://journals.rcsi.science/2313-2299/article/view/323403) | RUDN Journal of Language Studies, Semiotics and Semantics |
| 4 | [2782-5329/article/view/400674](https://journals.rcsi.science/2782-5329/article/view/400674) | Philological Sciences Bulletin |
| 5 | [0373-658X/article/view/261465](https://journals.rcsi.science/0373-658X/article/view/261465) | Вопросы языкознания |

Plus the journal named first in the request,
[Acta Linguistica Petropolitana, 2306-5737](https://journals.rcsi.science/2306-5737), which
supplies a profile but no pinned article.

## Platform facts established by live probe (19-08-2026)

These are measured, not assumed. Re-verify only if a fetch starts failing.

| Fact | Evidence |
|---|---|
| The platform is PKP/OJS under an RCSI skin | article pages load `lib/pkp/xml/oai2.xsl`; paths are the OJS set (`/about/submissions`, `/issue/archive`, `/article/view/<id>`) |
| Per-journal OAI-PMH works | `https://journals.rcsi.science/2306-5737/oai?verb=Identify` returns 200 `text/xml` |
| Site-wide OAI is broken | `/index/oai?verb=Identify` returns `DB Error: relation "published_articles__" does not exist`; harvesting must be per journal |
| Article pages carry full Google-Scholar metadata | `citation_title` and `citation_author` in **both** ru and en, `citation_doi`, `citation_edn`, `citation_firstpage`/`citation_lastpage`, `citation_keywords` ru+en, `citation_pdf_url` |
| PDF galleys are openly fetchable | `article/download/268311/247270` returns 200 `application/pdf`, 150 KB, `%PDF-1.7` |
| Article HTML also carries the body text | the Плунгян page yields about 5 600 words of stripped text |
| The URL slug is not always the ISSN in the metadata | slug `0869-5873`, `citation_issn` `3034-5200` — the **slug** is the profile `id`, never the metadata ISSN |
| The journal catalogue is crawlable | the platform home page lists 49 slug links on page one, paginated |
| **Every fact above depends on the User-Agent** (added 19-08-2026, H3153) | the harvester UA this plan prescribes in S1.1 is **403'd site-wide**; a browser UA is served 200 on the same URLs in the same second, on both `/{slug}/oai?verb=Identify` and `/{slug}/article/view/{id}`. Not an endpoint problem, not a rate limit. The rows above were established with a different client — re-read them as "reachable *with a served UA*". See [BENCHMARK](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/BENCHMARK_pdf-extractors_ru_19-08-2026.md) § *Findings that bind wave 1* |
| **Not every article is in Russian** (added 19-08-2026, H3153) | Acta Linguistica Petropolitana 21.1 is entirely English. A clean extraction scores `cyrillic_ratio` 0.06, so a Cyrillic-expecting gate applied blind discards it as garbled; language is a classification input (S1.4), not an extraction verdict |

## Decisions taken

Every row is a ruling from the 19-08-2026 interview. An execution agent treats these as
settled and does not re-derive them.

| # | Decision | Ruling | Why |
|---|---|---|---|
| D01 | What one command produces | **Both** a submission profile and a harvested article corpus | The two halves are what "a journal" means here; either alone leaves half the request unmet |
| D02 | Wave-1 journal scope | The five named slugs **plus** the rest of RCSI's linguistics / philology / oriental set | Requested explicitly; requires a catalogue-discovery step (D05) |
| D03 | Where full texts land | Private [RuWritingStyles-corpus](https://github.com/gasyoun/RuWritingStyles-corpus), existing flat `PDFtoTXT/` directory | Reuses the directory `corpus.py` already resolves; no indexing change needed on day one |
| D04 | Article selection | Subject/keyword filter over OAI Dublin Core subject plus title and keywords, with a review queue for the uncertain tail | Deterministic, auditable, no model cost; the uncertain tail stays visible instead of silently dropped |
| D05 | Journal discovery | Crawl the paginated catalogue, fetch each slug's OAI `Identify` and `/about` scope, classify, and commit a catalogue file with a per-journal verdict | Site-wide OAI is broken, so a crawl is the only enumeration path; a committed verdict makes exclusions reviewable |
| D06 | Article metadata source | OAI-PMH `ListRecords` to enumerate, `citation_*` meta tags on the article page for the authoritative record | `oai_dc` alone loses DOI, EDN, page range and the ru/en title pairing that a bibliography row needs |
| D07 | Text extraction order | HTML body first, PDF galley fallback, every result gated on a Cyrillic sanity check | `.ai_state.md` records `pdftotext` garbling Cyrillic on these PDFs; HTML sidesteps the font-encoding layer entirely |
| D08 | Extractor choice | Settled by a **scored bake-off** with a committed dated verdict; winner pinned in config, losers kept as the fallback chain | "Compare the OCR tooling we have and use the best" — the comparison is an artifact, not an opinion |
| D09 | Bake-off candidates | PyMuPDF / `fitz` (including the `deeppapernote` extractor), `pdftotext` plain and `-layout`, `pdfminer.six`, `ocrmypdf` with `tesseract rus` — **plus** any further extractor found installed or worth installing | Breadth was explicitly requested; the discovery sub-step is part of the bake-off, not a separate wave |
| D10 | Schema | Extend [schemas/journal-profile.schema.json](https://github.com/gasyoun/RuWritingStyles/blob/main/schemas/journal-profile.schema.json) with optional provenance fields **and** a `verified` boolean gate | An auto-derived guess must never quietly govern a real submission; all five existing profiles keep validating |
| D11 | Corpus metadata | Keep the `YYYY_Author_Title.txt` filename convention **and** write a `<stem>.json` sidecar beside each text | Nothing in `corpus.py` breaks today; DOI, pages, licence and extraction provenance stop being lost |
| D12 | Code home | New `rws` CLI subcommands inside the package | Matches the roughly sixty existing subcommands, gets test and `validate_project` coverage, importable from `api.py` |
| D13 | Pinned-article guarantee | A committed pinned manifest re-verified by a test: text present, sanity gate passed, sidecar with DOI, bibliography row, retrievable by `rws corpus-search` | "Included for sure" has to be mechanical, or it decays on the first re-harvest |
| D14 | Sanity-gate failure | Escalate to OCR automatically; quarantine with score and reason only if OCR also fails; never index a failing text | Salvages the majority unattended while keeping mojibake out of `rws.db` |
| D15 | Test strategy | Committed fixtures for every network path; a live smoke behind an opt-in environment flag | Follows the `tools/export_journal_fixtures.py` precedent; CI stays deterministic and polite to a third-party server |
| D16 | Registration | Automatic `knowledge/bibliography.json` row per article; one `SOURCES.md` row per **journal**, with licence facts | Per-article `SOURCES.md` rows would turn a rights document into a database dump |
| D17 | Ambiguity policy | Apply the plan's marked default, append a line to the decisions log, continue; park only when no default applies | The run must finish; every improvised call stays visible in one file |
| D18 | The fence | **No corpus text, PDF, or FTS index may enter the public RuWritingStyles repo** | `SOURCES.md` principle 1 and the reason for the phase-0 history purge |
| D19 | New dependencies | Bake-off candidates may be installed into a **throwaway virtualenv**; nothing enters `pyproject.toml` unless it wins, and then only as an optional extra | Broad comparison without the project inheriting a heavy machine-learning dependency |
| D20 | Run scope | The five pinned articles plus a bounded sample per in-scope journal (about 50 articles each), one request per second, HTML cached on disk; commit and push to the private corpus repo in the same pass | Enough material to unblock the corpus-gated passports, small enough to inspect and re-run |

### Explicitly not fenced

The fence (D18) was narrowed by the author to the public-repo rule alone. Three candidate
fences were offered and **not** selected — rewriting the five existing journal profiles,
touching evals / gold baselines / passports, and history rewrites. They are therefore *not*
prohibitions. The plan nevertheless does not schedule any of them, and D10's `verified`
gate means a scraped profile cannot overwrite a hand-verified one in place: a re-derivation
of an existing profile is written as a proposed diff for review, which is the marked default
under D17. An execution agent that believes it needs to change an eval baseline or a
passport has left this plan's scope and should park the item.

## Autonomy contract

Recorded verbatim for the execution agent.

1. **On ambiguity** — apply the marked default for that class of decision, append one line
   to `docs/rcsi-harvest-decisions.log.md` naming the choice and the reason, and continue.
   Park the item only when no default applies.
2. **Stop conditions** — halt the run only on: the fence in D18 being about to be crossed;
   the private corpus repo refusing a push after one retry; or the platform returning HTTP
   429 or 403 across three consecutive journals (treat as a rate-limit block, stop and
   report). A single bad article, a single failed extraction, and a single unreachable
   journal are **not** stop conditions — they quarantine or skip and the run continues.
3. **Commit authority** — this work is handoff-scoped, so commit, PR and merge on
   RuWritingStyles proceed without asking, and texts are committed and pushed to the
   private RuWritingStyles-corpus in the same pass (D20). No force-push, no history rewrite.
4. **The fence** — no corpus text, PDF, or FTS index in the public repo, in any wave, for
   any reason (D18).
5. **Dependencies** — install bake-off candidates into a throwaway virtualenv only (D19).

## The layer documents

| Layer | Document |
|---|---|
| Waves, deliverables, non-goals | [ROADMAP](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/ROADMAP_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md) |
| Components, data contracts, build-vs-reuse | [ARCHITECTURE](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/ARCHITECTURE_RuWritingStyles_rcsi-journal-harvest.md) |
| File-level ordered build sequence | [IMPLEMENTATION](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/IMPLEMENTATION_RuWritingStyles_rcsi-journal-harvest.md) |
| Acceptance criteria, commands, risk register | [VERIFICATION](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/VERIFICATION_RuWritingStyles_rcsi-journal-harvest.md) |

_Dr. Mārcis Gasūns_
