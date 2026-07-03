# Changelog

All notable changes to RuWritingStyles are documented here.

## [Unreleased]
### Changed (over-rewrite fixed by construction — span-patch reconstruction, roadmap-2026-q3 Phase B2, H073)
- **The revision stage no longer trusts the model to re-emit the whole document.** The synthesizer now returns only per-span `applied_changes` (each `{span_id, replacement_text, …}`) and the engine reconstructs `revised.md` itself from `segments.json` order — untouched spans are copied **byte-for-byte** from `normalized.md`, only changed spans are substituted. Diff-fidelity is now true **by construction**, killing the dominant gold-eval failure mode (revision over-rewriting, `char_delta_ratio` up to 1.83 on ~300–450-char stubs vs cap 0.5), which was confirmed stochastic across `deepseek-v4-flash` and `deepseek-v4-pro` and survived `temperature=0` (see [`docs/benchmark.md`](docs/benchmark.md)). New module [`src/ruwritingstyles/reconstruct.py`](src/ruwritingstyles/reconstruct.py) (`reconstruct_revised`, `reconstruction_errors`); a zero-change revision reproduces `normalized.md` byte-identically.
- **Revision prompt rewritten** ([`src/ruwritingstyles/revision.py`](src/ruwritingstyles/revision.py)): requests per-span patches (with a compact `{span_id, type, text}` span map injected from `segments.json`) instead of a full revised document; the "re-emit the whole document verbatim" discipline block is replaced by "return only the spans you change."
- **Schemas + validation tightened.** [`schemas/revision-output.schema.json`](schemas/revision-output.schema.json) drops the required `revised_document` (now advisory, ignored by the engine) and requires `span_id` + `replacement_text` on every `applied_changes` item; [`schemas/revision.schema.json`](schemas/revision.schema.json) requires the same on the stored artifact. `validate-run` now checks that `revised.md` is a faithful span-patch reconstruction — every non-referenced segment byte-identical, each changed span holding exactly its `replacement_text` — as a standing safety invariant (`validation._validate_revision_reconstruction`). This invariant should now never trip on engine-produced runs; a trip means the artifact was hand-edited or produced by a stale path.
- **Growth governor (second half of the fix, found necessary by a live N=5 sweep).** Span-patch alone was NOT enough: the live model over-rewrites *inside* the span too (a 291-char paragraph came back as an 864-char essay; karaka N=5 on pure span-patch scored 0/5, worse than baseline). `reconstruct.govern_changes` enforces a document-level growth budget by construction: patches are accepted cheapest-growth-first until net character growth would exceed `RWS_REVISION_MAX_GROWTH_RATIO` (default 0.4) × document length; oversized patches are rejected — their spans stay untouched, the rejection lands in `unresolved` (with reason) and the full rejected patch in the new optional `revision.json` `rejected_changes` field. Offline replay of the governor over all 10 live pre-governor runs: every run within both diff limits (worst char-delta 0.32 vs cap 0.5, worst line-ratio 0.5 vs cap 0.75). The revision prompt states the budget explicitly so the model can comply instead of being governed.
- `resolution.write_final_manuscript` now falls back to the reconstructed `revised.md` (via `revised_document_path`) when `revision.json` has no inline `revised_document` — the engine no longer stores the document inline.
- Tests: `tests/test_reconstruct.py` (byte-identity of zero-change, single/multi-span substitution, unknown-span and missing-`replacement_text` handling, tamper detection, governor acceptance/rejection/budget invariant); full `tests/` suite green (210 passed); `validate_project` green.
- Measured before/after on the H072 N=5 flash protocol (`docs/benchmark.md`): diff-failures → ~0, pass-rate rises toward detection-rate. Baseline was pass 12/25 = 0.48, detection 24/25 = 0.96.

## [2.11.0] - 2026-07-03
### Added (trustworthy benchmark — N-run eval harness, roadmap-2026-q3 Phase B1)
- **`rws eval-run --repeat N` / `rws eval-suite --repeat N`** run N independent executions and write `runs/<agg-id>/eval-aggregate.json` (+ `eval-aggregate.md`): per-case **pass-rate**, **detection-rate** (did the council catch the expected risk, independent of diff limits), **diff-ok rate**, `verification_status` distribution, and **mean/σ/min/max** of `char_delta_ratio` / `changed_line_ratio` / finding count. New [`schemas/eval-aggregate.schema.json`](schemas/eval-aggregate.schema.json), `rws validate-eval-aggregate`, and `validation.validate_eval_aggregate_file` (recomputes the statistics as a cross-check). This replaces meaningless single-run accuracy, which oscillated **1/5 → 2/5 → 3/5 → 0/5 on unchanged code** (DeepSeek non-determinism).
- **Per-case scorer alias policy** — `scoring.accepted_finding_aliases` in [`evals/manifest.json`](evals/manifest.json) maps a canonical required finding type to accepted alternate labels; the scorer matches via the canonical type OR any alias, without loosening into substring matching. `matched_required_finding_types` always records the canonical type. Replaces the hardcoded `unsupported_etymology` alias from `7dbbcc4`; all 5 gold cases backfilled. Documented in [`evals/GOLD_PROTOCOL.md`](evals/GOLD_PROTOCOL.md).
- **Temperature probe** — the DeepSeek provider honors `RWS_DEEPSEEK_TEMPERATURE` (unset by default); used to test reproducibility. Finding: at `temperature=0` **detection is reproducible but the revised text is not** (`docs/benchmark.md`), so N-run averaging is still required and the over-rewrite must be fixed architecturally (H073), not by a temperature pin.
- **DeepSeek model-alias correction** — verified live (2026-07-03) that `deepseek-chat` **and** `deepseek-reasoner` now both resolve to `deepseek-v4-flash`; `deepseek-v4-pro` is the only genuinely heavier model. [`model_policy.yml`](model_policy.yml) repoints council/verification to `deepseek-v4-pro` and documents the alias; `eval-result` provider enum now accepts `deepseek`/`local`/`ollama` so real-provider runs validate.
- **Benchmark filled with measured N=5 numbers** — [`docs/benchmark.md`](docs/benchmark.md) reports the completed 5-case × N=5 `deepseek-chat` protocol: **pass-rate 12/25 = 0.48, detection-rate 24/25 = 0.96**, per-case mean±σ char-delta, and the temperature=0 probe, replacing single-run storytelling. The `deepseek-v4-pro` comparison is **partial (3/5 cases)** — the sweep was stopped after two v4-pro request hangs; verdict on the available runs: detection equal, verification cleaner (all `passed`), over-rewrite NOT solved by the heavier model. The protocol's planned `deepseek-reasoner` comparison was impossible (alias — see above); also discovered that the eval path never consumes `model_policy.yml` task routes (stages get one `--model` per case), so the "reasoner on council/verify" premise had no wiring to test.
- **Transport hardening from the live batch** — read-phase `TimeoutError` is now retried (it escaped the `URLError` handler and killed a whole N=5 batch mid-case) and the per-request HTTP timeout is env-configurable via `RWS_PROVIDER_TIMEOUT_SECONDS` (default 120s; `deepseek-v4-pro` needs 300s on the heavier stages). Known gap (follow-up): a trickling connection keeps `read()` alive past any socket timeout — a hard per-request wall-clock deadline is still needed (observed as intermittent v4-pro hangs, 2 in ~8 case-runs).
- Tests: `tests/test_eval_aggregate.py` (aggregation math, alias matching, mock end-to-end + schema validation); `tests/` suite green; `validate_project` green.

## [2.10.5] - 2026-06-26
### Added (CLI parity test + ARS scaffold)
- **CLI/CI parity guard:** added `tests/test_cli_reports.py`, a hermetic CLI-level regression test that runs `rws run` in a temporary repo fixture and verifies the CLI path emits `report.md`, `summary.html`, `report.tex`, `references.bib`, and `references-gost.md`.
- **First ARS borrow scaffold:** added `docs/claim-faithfulness-audit.md`, `docs/reviewer-calibration-protocol.md`, `schemas/claim-faithfulness-audit.schema.json`, and schema tests. This re-implements ARS-inspired claim-support and reviewer-calibration protocols without copying ARS files or running a provider over unpublished text. Attribution is now recorded in `SOURCES.md` and `CITATION.cff`.

## [2.10.4] - 2026-06-25
### Added (journal compliance — enforceable abstract word limit)
- **`abstract_max_words` is now a checkable journal-profile field** — the first concrete borrow from the [Awesome-Journal-Skills](docs/ajs-comparison-notes.md) comparison. Вестник СПбГУ's requirement, previously only prose in the profile's `notes` ("расширенная, до 200 слов"), is now an enforced rule on [`knowledge/journals/vestnik-spbu.json`](knowledge/journals/vestnik-spbu.json) (`abstract_max_words: 200`).
- **Engine:** [`report.journal_compliance`](src/ruwritingstyles/report.py) extracts the abstract body per required language (locates the marker, takes the paragraph, drops the label, counts word runs via `_abstract_word_count`) and, when a limit is set, emits `words` / `max` / `over` per language; the report's «Соответствие журналу» section renders `114/200 слов — OK` / `⚠ +N сверх лимита`. Word fields appear only when the profile sets a limit, so profiles without it (`vya`, `ppv`) keep their original presence-only shape. Tuned for the inline «**Аннотация.** текст…» style; a heading-style abstract with a blank line before the body is under-counted — safe for a maximum (never a false over-limit).
- **Obsidian parity:** mirrored in [`obsidian-plugin/src/lint/journal.ts`](obsidian-plugin/src/lint/journal.ts) + [`types.ts`](obsidian-plugin/src/lint/types.ts) (over-limit surfaced as a lint warning + in the Notice summary); new schema field in [`schemas/journal-profile.schema.json`](schemas/journal-profile.schema.json). Regenerated golden fixtures (`tools/export_journal_fixtures.py`, +`abstract-over-words` case); **59/59 plugin parity tests + 8/8 `test_journal_run` green**, `validate_project` green, the gúṇa article reports 114/200 — OK.

## [2.10.3] - 2026-06-25
### Added (docs — AI-detector citation + AJS comparison)
- **Cited Bassett et al. 2026, "Heads we win, tails you lose: AI detectors in education"** (*Journal of Higher Education Policy and Management*, CC BY-NC-ND; open preprint [osf.io/preprints/edarxiv/93w6j](https://osf.io/preprints/edarxiv/93w6j_v1)) as the peer-reviewed anchor for the project's **disclose-don't-detect** stance — AI detectors are unverifiable and impose a false human/AI dichotomy that ignores text created *with* AI. Wired into four places: a new `Bassett 2026` entry in [`knowledge/bibliography.json`](knowledge/bibliography.json); a «Почему раскрытие, а не детектор ИИ» rationale in [`docs/AI_DISCLOSURE.md`](docs/AI_DISCLOSURE.md) §1; problem/related-work lines in [`docs/methodology-paper-outline.md`](docs/methodology-paper-outline.md) §1–2; and a **design guardrail** on ARS borrow #4 in [`docs/ars-integration-notes.md`](docs/ars-integration-notes.md) — the Russian "AI-tells" check must stay a style-quality signal, never an authorship verdict.
- **`docs/ajs-comparison-notes.md`** — comparison with [Awesome-Journal-Skills](https://github.com/brycewang-stanford/Awesome-Journal-Skills) (MIT, Stanford REAP): a breadth-index of ~2,895 per-journal submission-mechanic skill packs for econ/Nature/Cell/Chinese venues. Verdict: **not a competitor and not a methods donor** (that role is ARS's), and none of its venues match RuWritingStyles' targets — but **MIT is license-clean** with this Apache-2.0 repo (no NC taint, unlike ARS). The one concrete borrow is a **richer journal-profile schema** for `knowledge/journals/` (`abstract_max_words`, `keywords_min`/`max`, `required_sections` → a deterministic `report.journal_compliance` check); concrete trigger = Вестник СПбГУ's "до 200 слов" abstract, today only prose in `notes`. Linked from the docs index. Comparison/notes only — no code.

## [2.10.2] - 2026-06-22
### Added (docs — ARS borrow plan + license stance)
- **`docs/ars-integration-notes.md`** — a plan for what RuWritingStyles can profitably borrow from [Academic Research Skills (ARS)](https://github.com/Imbad0202/academic-research-skills), the CC BY-NC 4.0 Claude Code research-pipeline plugin. Records the **license interaction up front**: ARS is CC BY-NC 4.0, this repo is Apache-2.0, so the two **do not mix per-file** — the chosen stance is *re-implement ARS's methods/protocols (ideas aren't copyrightable), do not copy ARS files, attribute generously anyway*. Includes ready-to-paste attribution blocks for `SOURCES.md` and `CITATION.cff`, deferred until the first borrow lands. Five ranked borrows, each mapped to an existing module: (1) **claim-faithfulness citation audit** → `citations.py`/`verification.py` (unblocks the Phase-1 presence-only grounding gap); (2) **reviewer calibration (FNR/FPR vs gold)** → `evals.py` + `GOLD_PROTOCOL.md` (unblocks the empty `docs/benchmark.md`, roadmap P2); (3) **multi-reviewer council** (EIC + 3 + Devil's Advocate, editorial-decision letter, re-review mode) → `council.py`/`peer_review.py` (F1 named councils); (4) **Russian "AI-tells" writing-quality check** → `styleguide.py`/`profiling.py`; (5) **Claude Code plugin packaging** → distribution play (roadmap 2.8). Planning-only; no code or borrow yet.

## [2.10.1] - 2026-06-14
### Added (Obsidian plugin M5 — release automation + packaging)
- **`.github/workflows/release-obsidian-plugin.yml`** — on an `obsidian-v*` tag, builds the plugin and publishes a GitHub release with `main.js` / `manifest.json` / `styles.css` + a zip; `workflow_dispatch` runs a build+test smoke. The `obsidian-v` tag prefix keeps plugin releases distinct from the engine's versioning in this monorepo.
- **`obsidian-plugin/RELEASE.md`** — packaging/versioning guide: the automated release flow, manual + BRAT install, and the community-submission path. Documents honestly that a monorepo subdirectory **cannot** be BRAT-installed or submitted to the community catalogue directly (Obsidian wants `manifest.json` at the repo root + bare version tags) → recommends a dedicated repo. The release tag, BRAT add, and community PR are author actions. Plugin is now feature-complete (M0–M5); build green, 36/36 parity tests pass.

## [2.10.0] - 2026-06-14
### Added (Obsidian plugin — deterministic checks inline in the editor, MVP M0–M4)
- **`obsidian-plugin/`** — a TypeScript Obsidian plugin running the engine's deterministic checks inline:
  - **Transliteration linter** (M1/M2): all 5 finding types ported from `translit_lint.py`, shown as CodeMirror 6 native lint diagnostics (400 ms debounce, status-bar count).
  - **Journal compliance** (M3): port of the new pure `report.journal_compliance()` (length / citation format / IAST scheme / abstract + keywords presence per language); a settings tab selects the target journal (vya / ppv / vestnik-spbu).
  - **IAST quick-fix + per-check toggles** (M4): a CodeMirror quick-fix inserts ` (iast)` after a flagged first mention (pure insertion, idempotent, user-triggered); each check is individually toggleable.
- **Parity enforced, not asserted.** `tools/export_lint_fixtures.py` + `tools/export_journal_fixtures.py` regenerate golden fixtures from the *actual Python engine*; the plugin's tests `deepEqual` against them — **36/36 pass**. `tools/validate_project.py` fails if the plugin's bundled `knowledge/` assets drift; a new **`plugin` CI job** (`.github/workflows/ci.yml`, Node 24) runs the parity tests on every PR. `report.journal_compliance()` is a pure function so the Python and TS sides share one source of truth.
- Reviewed pre-merge (M0–M2 and M3–M4 separately): parity sound, security sound (purely local — no network/eval/telemetry; the only write is the user-triggered IAST insertion), build sound, **0 blockers**. Desktop+mobile, zero runtime dependencies (bundled), Apache-2.0.

## [1.0.0] - 2026-06-13

### Changed
- Released the current changelog state as version 1.

## [2.9.2] - 2026-06-14
### Fixed (README top blocks refreshed to reality at v2.9.x)
- **Stale "Границы реализованного" item.** The Obsidian/Word line claimed the plugins were "запланированы на v2.5.0" — long overtaken (v2.5.0 shipped CLI corpus Deep Retrieval, not plugins). Now states honestly that only the FastAPI API layer exists; the plugins remain prototypes, deferred to an author release decision, no longer tied to a version. The Deep Retrieval line now notes it is reachable from the CLI (`rws corpus-status` / `corpus-ingest` / `corpus-search`).
- **Stale roadmap tail.** The single `[ ] v2.5.0 (Next)` bullet predated everything from v2.5–v2.9. Added a "Sanskrit DH — public Russian-Sanskritology resource on DeepSeek" block tracing the actual shipped sequence (v2.5.0 corpus CLI → v2.5.x eval/gold protocol + security review → v2.6.0 named councils → v2.7.0 archival DH metadata → v2.8.0 DeepSeek provider → v2.8.1–2.8.2 benchmark + gúṇa case study → v2.8.3–2.8.4 revision discipline + journal compliance → v2.8.5–2.8.6 Russian quickstart + knowledge base → v2.9.0–2.9.1 docs + style gallery), ending with the open author release actions (Zenodo DOI, methodology paper).
- **Documentation links.** The "Документация разработки" list now leads with the curated map [`docs/README.md`](docs/README.md) and surfaces the new curated docs: [`docs/QUICKSTART.ru.md`](docs/QUICKSTART.ru.md), [`docs/USE_CASES.ru.md`](docs/USE_CASES.ru.md), [`docs/benchmark.md`](docs/benchmark.md), [`docs/case-study-p3-guna.md`](docs/case-study-p3-guna.md).
- **Status line** now leads with the primary provider (**DeepSeek**) and surfaces `--journal`. Version bumped (`pyproject.toml`, `styles/manifest.yml`, README status) to 2.9.2. The large style tables below were not touched.

## [2.9.1] - 2026-06-14
### Added (P6 publish — Claude style gallery)
- **`docs/STYLE_GALLERY.ru.md`** + generator **`tools/generate_style_gallery.py`** — a catalogue of all **39** styles grouped by school, each linking to its `.md` on GitHub (full blob URL) as the shareable **Claude Custom Style**: open → copy → paste into Claude → Settings → Custom styles (the Raw button gives the copyable text). There is no API to mint claude.ai Custom-Style share URLs, so the prompt file *is* the shareable artifact; titles come from the passport `name` for clean, consistent labels. Regenerable; all 39 links verified to resolve to real files. Linked from `README.md` (next to the styles table) and the docs index.

## [2.9.0] - 2026-06-14
### Added (P6 publish — documentation deepened)
- **`docs/USE_CASES.ru.md`** — seven deep, command-level workflows for the Russian Sanskritology researcher (etymology-hypothesis check, journal preparation, Vedic vs Classical period, samāsa analysis, dictionary collation PW/MW/Apte, standalone transliteration, run/provider comparison), each *situation → command → what it returns*, grounded in the verified gúṇa run and using DeepSeek + `--council` + `--journal`.
- **`docs/README.md`** — a curated documentation map (by audience: getting started / evidence / citation+AI / how-it-works / reviews / dev), taming the 35-file `docs/` sprawl — the backbone of the planned Russian docs site.
- **`docs/methodology-paper-outline.md`** — a section-by-section skeleton for the P6 methodology paper, with the evidence (benchmark, case study, gold protocol) mapped to each claim and the open pre-submission tasks (expert annotation, N-run averaging).
### Fixed
- Stale provider lists in `README.md` and `docs/scenarios.md` now lead with **`deepseek`** (the primary backend) and surface `--council`/`--journal`; both point to the new deep use-cases doc. README links the new docs prominently.

## [2.8.6] - 2026-06-14
### Added (knowledge-base depth — quality item 4 / P5)
- **Indological bibliography core** added to `knowledge/bibliography.json` (44 → 49): **Apte 1890** (*The Practical Sanskrit-English Dictionary* — was missing despite being cited in the P3 gúṇa article, so its citation can now ground), **Böhtlingk 1879** (kürzere Fassung / pw), **Mayrhofer 1986** (*Etymologisches Wörterbuch des Altindoarischen* — the standard etymological reference for the etymology styles), **Grassmann 1873** (*Wörterbuch zum Rig-Veda*), **Macdonell 1910** (*Vedic Grammar*). Added Cologne **CDSL** links (sanskrit-lexicon org repos) to Monier-Williams, Böhtlingk-Roth (PW), Apte, Böhtlingk-kürzere and Grassmann. Format-preserving edit; schema + cross-references still resolve.
- `knowledge/sanskrit-terms.json` (60 → 61): added **vigraha** (the analytical decomposition central to the `samasa-manual` style).

## [2.8.5] - 2026-06-14
### Added (onboarding — quality item 3 / P4)
- **`docs/QUICKSTART.ru.md`** — a five-step Russian quickstart (install → DeepSeek key in `.env` → first run on a bundled example → your own article with `--council sanskrit --journal vestnik-spbu` → reading the report), plus an offline/no-key path on `--provider mock` and a cheat-sheet of useful commands. Every command was verified to exist and parse. Linked prominently from the top of `README.md`. This is the entry point for the "install + run the CLI" community deliverable.

## [2.8.4] - 2026-06-14
### Added (journal-profile pass — quality item 2)
- **`rws run --journal <id>`** applies a journal profile inline (no project dir needed): it writes the resolved profile into the run's context, so the verifier, transliteration linter, and report all honour it. Unknown ids fail with the available list.
- **The report's journal-compliance section now *checks* requirements instead of echoing them** — a per-language presence check for the required abstract and keywords (`report._journal_section`). On the P3 gúṇa article vs *Вестник СПбГУ* it correctly reports `Аннотация (ru, en): ru ✓, en ⚠ нет` / `Ключевые слова (ru, en): ru ✓, en ⚠ нет` — a real submission gap (missing English abstract + keywords), caught deterministically. `tests/test_journal_run.py` (3); `docs/cli.md` + the P3 case study updated.

## [2.8.3] - 2026-06-14
### Changed (tighten revision for short notes — quality item 1)
- `revision.py` gained a load-bearing **"Editing discipline"** block: touch only the spans named in accepted council decisions, copy every other span **verbatim**, make the smallest change that resolves each finding, and don't materially lengthen the text. Re-running the over-editing gold cases on `deepseek-chat` shows the effect is real and large where it mattered — `sanskrit-pseudo-etymology` char-delta **0.67 → 0.03**, `samasa` 0.29 → 0.20.
- **Methodological finding (documented in `docs/benchmark.md`):** DeepSeek is **non-deterministic** — `commentary-layer-mix` matched its expected risk in one run and missed it in an identical re-run. So single-run eval pass-counts are noisy; reliable scoring needs N-run averaging (or temperature=0 / majority vote). The eval diff threshold was deliberately **not** loosened (that would game the gold protocol); whether to make it input-length-aware is left to the author. Remaining cap trips are tiny-stub (~300–450 char) artifacts.

## [2.8.2] - 2026-06-14
### Added (P3 — first real full-article run on DeepSeek; case study)
- Authored a genuine ~22k-char Russian article on the lexicography of *guṇa* (PW / Monier-Williams / Apte) for *Вестник СПбГУ*, with **3 deliberately seeded problems** (fabricated IE etymology; missing IAST on *vṛddhi*/*sandhi*; a PW(1855–75)←Apte(1890) anachronism — see `docs/p3-seed-key.md`), and ran it through `--council sanskrit` on `deepseek-chat`. **All 3 caught** at the correct spans with on-target types and genuine explanations — toporov-etym refuted the fake etymology with real comparative knowledge (knew *funis* ← *bʰendʰ-*, not the planted *gʷenǝ-*). Full write-up: `docs/case-study-p3-guna.md`.
- **Revision is proportionate on real-length text** (char-delta 0.18 / changed-line 0.22, well inside the gold caps) — so the short-case "over-rewrite" in the benchmark is now understood as a ratio artifact of ~500-char docs, not a general defect (noted in `docs/benchmark.md`). Bonus: the linter surfaced 2 *unintended* un-IAST'd terms the author missed; no false-positive storm (elizarenkova-veda = 0 on a non-Vedic text). First concrete evidence the pipeline produces philologically credible reviews on real material.

## [2.8.1] - 2026-06-14
### Added (first real-provider benchmark — DeepSeek)
- Ran the 5 gold Sanskrit eval cases on `--provider deepseek` (`deepseek-chat`) and filled `docs/benchmark.md` with real numbers. **Headline: detection 5/5, verification 5/5, but overall pass 1/5** — the four failures are *not* detection misses (the council with the right indology styles caught the expected risk in every case) but the **revision stage over-rewriting** past the gold protocol's diff-fidelity caps (`max_changed_line_ratio 0.75` / `max_char_delta_ratio 0.5`; `karaka-not-padezh` grew +153% chars). The one pass (`commentary-layer-mix`) is exactly the one with minimal edits (0.25 lines / 0.05 chars).
- **Actionable next step for review quality:** tighten the `revision` stage toward minimal, span-scoped surgical edits rather than paragraph rewrites — a prompt/policy change, not a detection problem. Framed in `docs/benchmark.md` as the automated detection layer (layer 1); the ≥2-rater expert gold annotation (layer 2, per `evals/GOLD_PROTOCOL.md`) is still pending.

## [2.8.0] - 2026-06-13
### Added (DeepSeek provider — the project's primary real backend)
- **`--provider deepseek`.** New `DeepSeekProvider` (OpenAI-compatible JSON mode): direct `api.deepseek.com` by default, `DEEPSEEK_API_KEY`, default model `deepseek-chat` (V3). Set `RWS_DEEPSEEK_MODEL=deepseek-reasoner` (R1) or `RWS_DEEPSEEK_URL=<base>` to route the same key through a proxy / OpenRouter. Wired into `PROVIDER_CHOICES`, `provider_from_name`, `provider_status` (`rws provider-status --provider deepseek`), and `model_policy.yml` (a `deepseek` block routing `deepseek-chat` for review/synthesis and `deepseek-reasoner` for council + verification). `tests/test_providers_deepseek.py` (7, mock-safe — no network). `.env.example` documents the keys. Full suite 156 green.
- This unblocks the real-quality work that was previously mock-only: running the gold eval cases on a real provider, filling `docs/benchmark.md`, and end-to-end real-paper runs. **Setup:** add `DEEPSEEK_API_KEY=...` to `.env`, then `rws run paper.md --provider deepseek --execute`.

## [2.7.4] - 2026-06-13
### Changed (prompt-fidelity review F2/F3/F5 — passport curation)
- **F3 — dropped the one over-shared generic check.** Removed `overstrong_conclusion` from all 10 passports that carried it; each already has a sharper, scholar-specific overstatement check (e.g. `weak_reconstruction`, `unsupported_etymology`, `missing_alternative_interpretation`), and no eval references it. The check-overlap audit now shows only 2 checks shared by ≥3 of the 21 passports (`missing_iast_on_first_mention` — the correct Sanskrit-cluster signature — and `weak_classification`). `metadata/dublin-core.xml` regenerated.
- **F5 — de-regioned `get_cluster_weights`.** Clusters encode both a school's method and a city, and the council multiplied a finding's weight by geography (Moscow/Leningrad archetype × cluster `location`) regardless of method fit — so a misfiled passport (the accentology `zalizniak-udarenie` parked in the Moscow *Semantic* cluster) drew the wrong regional authority. Removed the location-string boost; deliberate cluster boosting still works via explicit `styles/archetypes.yml` weights (which key on `cluster_id`, not city). Cluster memberships left as-is (regrouping by method has a real method-vs-region tradeoff and is the author's call). `tests/test_cluster_weights.py` (2).
- **F2 reframed, not forced.** Inspection showed the five "generic" passports are mostly genuine named-scholar voices with adequate signature checks (only `sanskrit-reader` is a pure register preset), so no artificial sharpening was applied. See docs/prompt-fidelity-review-2026-06.md. Full suite 149 green.

## [2.7.3] - 2026-06-13
### Changed (low-priority `/code-review` cleanups)
- **Shared passport loader.** `config.load_passport_dicts(repo_root)` is the single glob+parse over `styles/passports/*.yml`; `tools/audit_passport_checks.py` and `tools/passports_to_dublin_core.py` now call it instead of each re-globbing and parsing. Verified behaviour-preserving: regenerated `metadata/dublin-core.xml` is byte-identical.
- **DRY CLI style selection.** The `--style`/`--styles`/`--council`/`--mvp` mutually-exclusive group (previously copy-pasted into `run`/`review`/`deliberate`) is now one `_add_style_selection_group(parser, *, required, mvp_help)` helper. New parse test asserts `--council` is wired on all three.
- **Clearer council errors.** `rws run --council <name>` now distinguishes an *unknown* council ("unknown council 'x'; available: …") from a *defined-but-empty* one ("council 'x' is defined but empty"), instead of reporting both as unknown.
- Deliberately NOT changed: the `_collect_style_audit` "re-reads 3×/run" finding — `run.json` is written at prepare / completion / failure and the audit must re-read because artifacts accumulate between those calls; memoizing by run_id would serve a stale, empty audit at completion. `tests/test_councils.py` 9 → 11; full suite 147 green.

## [2.7.2] - 2026-06-13
### Fixed (from a `/code-review` pass over the security + councils + Phase-4 diff)
- **Crash on the web-UI run path (pre-existing).** `POST /runs/execute` called `read_document`/`normalize_document`/`segment_markdown` (defined in `segment.py`) but `api.py` never imported them, so the React "New Run" button raised `NameError`. Added the import; new regression test prepares a real in-repo run via `TestClient` without crashing.
- **S4 auth hardened to default-deny.** The middleware previously protected an allowlist of prefixes (`/runs`, `/api`, `/status`), so a future route under a new prefix would have shipped unauthenticated. Inverted to default-deny: every route requires the token except an explicit static-frontend allowlist (`_PUBLIC_PATHS` / `_PUBLIC_PREFIXES`). New test asserts an unknown route 401s under a token while `/` stays public.
- **Single path-containment primitive.** The three resolve+`in .parents` guards (`_run_dir`, the S3 input-path check, the S1 static-route check) were consolidated into one `_within(root, path)` helper, so a later traversal-hardening tweak can't be applied to one guard and forgotten in another. Behaviour preserved (verified: prefix-collision `/repo` vs `/repo-evil` stays False).
- **Second missing-import crash (found by an adversarial verification pass).** `resolve_run`→`background_revision` called `provider_from_name` without importing it in scope, so `/runs/{id}/resolve`'s re-revision raised `NameError` (swallowed by `except Exception`) and silently failed on real providers. Hoisted `provider_from_name` to a module import (fixes both call sites; removes the redundant local import in `audit_selection`).
- **Auth hardening:** the public exemption for static assets is now `/assets/` (trailing slash) so `/assets../x` stays protected. The verification confirmed no unauthenticated bypass of any data route.
- `tests/test_api_security.py` 6 → 12 (adds `_within`/`_is_public_request` unit coverage and the module-global regression). Full suite 145 green. **Documented limitation:** the bundled SPA sends no `Authorization` header, so token-ON mode needs a token-aware client. Other `/code-review` findings (audit re-reads, tool passport-loader duplication, CLI arg copy-paste) were assessed and left as documented low-priority cleanups.

## [2.7.1] - 2026-06-13
### Security (closes security-review S3 + S4 — the public-bind tier)
- **S4 — optional bearer-token auth.** A new HTTP middleware (`api._require_token`) requires `Authorization: Bearer <RWS_API_TOKEN>` on `/runs`, `/api`, and `/status` when `RWS_API_TOKEN` is set; the WebSocket checks the same token (header or `?token=`). **Off by default** so the loopback dev tool needs zero setup; CORS preflight (`OPTIONS`) is never blocked; constant-time comparison (`secrets.compare_digest`).
- **S3 — input_path allowlist.** `POST /runs/execute` now confines `input_path` to an allowed root (`api._input_root`: the repo root by default, widenable via `RWS_INPUT_ROOT`); a path resolving outside returns **403** before any read, closing the arbitrary-file-read. The default web-UI path is under the repo, so the local flow is unaffected.
- `tests/test_api_security.py` (6, via FastAPI `TestClient`). `.env.example` documents `RWS_BIND_HOST` / `RWS_API_TOKEN` / `RWS_INPUT_ROOT`. **To bind publicly: set `RWS_BIND_HOST=0.0.0.0` AND `RWS_API_TOKEN=<secret>`.** All security-review findings are now closed.

## [2.7.0] - 2026-06-13
### Added (Phase 4 — archival DH-grade metadata; closes docs/roadmap-sanskrit-dh.md Фаза 4)
- **`CITATION.cff`** (Citation File Format 1.2.0) — GitHub now shows a "Cite this repository" button; author M. Yu. Gasuns, Apache-2.0, keyworded. A commented `identifiers` block is ready for the Zenodo DOI after the first release.
- **`.zenodo.json`** — Zenodo deposition metadata (software, `language: rus`, creators, keywords, related identifier) so a GitHub release archives with a DOI.
- **`docs/AI_DISCLOSURE.md`** — ready-to-paste AI-use disclosure formulas (RU minimal / RU with provider / EN) for a paper's footnote or Acknowledgements, plus an honest account of the LLM vs deterministic layers and the human-in-the-loop `run.json` trace. Linked from README. Stance: the tool is a reviewer, not a co-author; the researcher carries responsibility.
- **`tools/passports_to_dublin_core.py` + `metadata/dublin-core.xml`** — exports all 21 style passports to the unqualified DCMI element set (field→`dc:*` mapping documented in the tool), one well-formed record each. Re-runnable.
- **Version alignment.** `pyproject.toml` (2.4.0→2.7.0, author fixed to M. Yu. Gasuns), `styles/manifest.yml` (2.4.0→2.7.0 — closes data-review #6, the last stale-version item), `CITATION.cff`, and the README status line now all read v2.7.0.
- Deferred per roadmap (after phases 1–3, not Phase 4): Word/Obsidian plugins; the indological bibliography core beyond the current 44 entries.

## [2.6.0] - 2026-06-13
### Added (prompt/style-fidelity review — docs/prompt-fidelity-review-2026-06.md)
- Whole-content fidelity review of the two layers (39 `ClaudeStyles/*.md` ↔ 39 manifest passports) and the pipeline's preservation of style intent. The `.md`↔passport mapping is faithful and bidirectionally CI-enforced; voice reaches the model verbatim at review + deliberation; the synthesis stages (council/revision/verification) are finding-mediated.
- **F1 — named councils.** New `councils:` block in `styles/manifest.yml`: `general` (= the historical `mvp_style_ids`), `sanskrit` (elizarenkova-veda, toporov-etym, panini-traditional, zaliznyak-method, tronsky-readings, lidova-commentary), `indology`. The default council was pointed away from the project's own subject — Sanskrit linguistics — with zero indology styles. Select a panel with `rws run --council <name>` (also `review`/`deliberate`); `rws councils` lists them. Default unchanged (`mvp_style_ids` = `general`) for back-compat. `config.Manifest.resolve_council`/`council_names`; `_selected_style_ids` honours `--council`; `validate_project` fails if a council names a non-existent passport id. `manifest.schema.json` gains `councils`. `tests/test_councils.py` (9).
- **F4 — style-intent audit trail.** `run.json` now carries a `styles` block (`runs._collect_style_audit`): the styles that actually produced a review, the council's honored/overruled/informational tally (mapped to `council.schema.json`'s status enum — accepted(+modification) = honored, rejected/deferred = overruled, informational = neither), the overruled-dissent trace (reason + primary_school), and the `stylistic_commitments` the rewrite was meant to honour. Purely additive — reads artifacts, changes no prompt or pipeline behaviour. `run.schema.json` gains `styles`. (The other half — feeding commitments into the verification *prompt* — is deferred; it would change verifier output.)
- **F3 — generic-check audit.** `tools/audit_passport_checks.py` (repeatable) measures check-id overlap across the 21 individual passports. Corrected the review's qualitative claim: of 85 distinct checks only 3 are shared by ≥3 passports (`overstrong_conclusion` 10×, `missing_iast_on_first_mention` 5× = correct Sanskrit-cluster signature, `weak_classification` 3×); no passport exceeds 50% shared. The one real item is `overstrong_conclusion` in 10/21. F2 (sharpen thin passports) and F5 (regroup nominal clusters ling_mss/ling_mts) remain documented author-domain calls.

## [2.5.4] - 2026-06-13
### Security (security review — docs/security-review-2026-06.md)
- Whole-surface security review of the public web layer (FastAPI, subprocess, SSRF, secrets, SQL, deserialization, path handling). Threat model: safe as a loopback single-user tool, **not** safe to bind publicly as-is. Two sweep "CRITICAL" alarms were verified false — `.env` is gitignored and **never committed** (`git log --all -- .env` empty; no key leak), and `GET /runs/{run_id}` already bounds-checks via `_run_dir`. SQL is fully parameterized; no unsafe deserialization.
- **Fixed S1 (LFI):** the SPA catch-all route (`api.py`) served `web/dist / full_path` with no bounds check — `GET /..%2f..%2f.env` would read arbitrary files. Now resolves and rejects anything outside `web/dist/` (mirrors the `_run_dir` guard).
- **Fixed S2 (exposure default):** the API bound `0.0.0.0` by default. Now defaults to `127.0.0.1`; set `RWS_BIND_HOST=0.0.0.0` to opt into a public bind. Highest risk-reduction-per-line, since the API ships no auth.
- **Fixed S6 (redaction gap):** the credential scrubber regex `sk-[A-Za-z0-9]{20,}` stopped at the first hyphen, so OpenRouter (`sk-or-…`) / Nous (`sk-nous-…`) keys went un-redacted in exported artifacts. Broadened to `sk-[A-Za-z0-9-]{20,}`.
- **Fixed S7 (subprocess):** dropped `shell=True` on the MCP server launch (`mcp_client.py`); the server path is now `shlex.split` into an argv list and run with `shell=False`.
- **Hardening:** added the `npm` ecosystem (`/web`) to Dependabot.
- **Deferred to a product decision (documented, not changed):** S3 (`/runs/execute` reads any absolute local path — needs an input-path allowlist) and S4 (no API authentication — needs an `RWS_API_TOKEN` gate) are the prerequisites for ever exposing this as a multi-user service.

## [2.5.3] - 2026-06-13
### Added (data review #4: runs are self-describing on disk)
- Every run now writes a `run.json` (`runs.write_run_manifest`) capturing status, timestamps, duration, config, **all metrics** (bloom/compass/tension/bias/citation_stats) and step outcomes — data that previously lived only in the gitignored `rws.db`. A run directory is now portable and the DB is a rebuildable index. Written at prepare, at pipeline completion/failure (`core_pipeline`), and at the end of each eval case.
- This also makes `run.schema.json` a real, validated artifact (it was unused). Fixed its stale vocabulary: `status` enum now matches the actual values (`prepared`/`executing`/`completed`/`failed`, was `initializing`/`segmented`/…), and `text_domain` is a plain string (its old enum excluded `linguistics`, which the eval cases actually use). `validate_run_dir` validates `run.json`. New `test_core_pipeline` assertion.

## [2.5.2] - 2026-06-13
### Added (data/schema review enforcement — docs/data-schema-review-2026-06.md)
- **Strict-keyword guard** (`schema_validation.lint_schema`): `validate_project` now fails if any schema uses a keyword outside the supported subset, so an unsupported constraint fails loudly instead of being silently ignored. It immediately surfaced `minProperties` (model-policy.schema) as unenforced. Implemented the keywords that were used yet ignored — `minItems`, `format: date-time`, `minProperties` (plus `maxItems`/`maxLength`/`maxProperties`). New `tests/test_schema_validation.py` (6).
- **Bibliography cross-reference checks** in `validate_project`: passport `provenance.sources` that look like a bibliography id (Latin + 4-digit year) must exist in `knowledge/bibliography.json`; every `sanskrit-terms.json` `source` must be a bibliography id. A typo'd/renamed id now fails CI. (Eval `required_finding_types` were found to be intentionally looser than passport `checks` — 27/44 cases use types no style enumerates — so that check was dropped.)
- **`segments.schema.json`** added and validated in `validate_run_dir`; the span_id anchor artifact now has a real schema. Span_id referential integrity extended to `revision.json` `applied_changes` (segments-based). `verification.json` warnings and the translit-lint span check are intentionally left unchecked because they mix span_ids from the re-segmented `revised.md` with the original `segments.json` basis.

## [2.5.1] - 2026-06-13
### Added (Phase 3: Sanskrit eval cases + gold-standard protocol)
- **Eight new Sanskrit eval cases** (36 → 44). Three deterministic, mock-safe cases complete linter-type coverage: `translit-inconsistent-rendering` (inconsistent_term_rendering), `translit-cyrillic-latin-hybrid` (iast_in_cyrillic_word), `gost-broken-ref` (hallucinated_citation). Five LLM-judgment **gold** cases flag only on real providers: `sanskrit-pseudo-etymology`, `karaka-not-padezh`, `vedic-classical-anachronism`, `samasa-misclassification`, `commentary-layer-mix` — each scored on a check defined in the indology passports. Mock suite: 44 cases, 6 pass (deterministic), comparison delta 0.0, 0 regressed.
- **`evals/GOLD_PROTOCOL.md`**: the gold-standard annotation protocol (deterministic vs expert classes, ≥2 independent raters per expert case, inter-rater agreement, consent, `gold-annotation.json` schema). **`docs/benchmark.md`**: provider-accuracy table scaffold, intentionally empty until a paid run + expert annotation (numbers without annotation are not a gold standard).
- Note: a `devanagari_nfc_issue` eval case is not viable in-pipeline because `prepare` NFC-normalizes the text before the linter runs; that check is reachable only via standalone `rws lint-translit` on a raw file.

## [2.5.0] - 2026-06-13
### Added (Phase 2: corpus Deep Retrieval is now usable)
- **`rws corpus-status` / `corpus-ingest` / `corpus-search`** expose the SQLite/FTS5 `CorpusManager`, which was implemented but reachable only via the `search_corpus` MCP tool (so unusable without a real-provider tool call). Ingesting indexes the private corpus `.txt` extractions into the local `rws.db`; search returns ranked snippets. Verified on the existing indology source texts (Tubb's *Scholastic Sanskrit*, Smirnov's *Mahābhārata*): `corpus-search "samasa OR vigraha"` returns precise compound-grammar passages — the material backing the `samasa-manual` / `panini-traditional` styles. `CorpusManager.stats()` added; the indology authors' texts (Elizarenkova/Toporov/Vertogradova/Ivanov) remain the author's to add to the private repo, after which `rws corpus-ingest` picks them up.
- `CorpusManager` SQLite connections now close (`contextlib.closing`) — `with sqlite3.connect()` commits but does not close, which leaked handles (and locked the DB on Windows). New `tests/test_corpus.py` (4 tests, offline, tempdir).
- `RWS_CORPUS_DIR` / corpus workflow documented in `docs/cli.md`.

## [2.4.10] - 2026-06-13
### Added / Fixed (architecture review #6: offline tests + the network leak)
- The test suite no longer makes real network calls. `MockProvider` simulates a `search_scholar` tool call during verification, which routed through `WebResearcher` to OpenAlex (10s timeouts / 429s) on every mock run that reached verification — the source of the multi-thousand-second `test_cli_pipeline`/eval runtimes. `WebResearcher.search` now honours an `RWS_OFFLINE` flag (default off, so real-provider runs are unchanged); `run_eval_case` sets it for `--provider mock`, and the pipeline test modules set it at import. `test_eval_sanskrit` dropped from ~9s to ~1.7s.
- New `tests/test_core_pipeline.py` (4 tests): direct fast coverage of the unified `core_pipeline` (execute, prompt-only, and the API `on_update` event stream) and of `execution.execute_review_artifact` — the orchestration code that previously had no unit tests of its own.
- `RWS_OFFLINE` documented in `.env.example`.

## [2.4.9] - 2026-06-13
### Fixed (architecture review #2: unify the two YAML parsers)
- The runtime config loader (`config.py`) and the CI validator (`tools/validate_project.py`) had separate hand-rolled YAML readers that could disagree — and did: `config.py`'s `_scalar`/`_list_items` tolerate a `:` inside a quoted scalar, but the validator's `parse_simple_yaml` split on the first `:` unconditionally, so a passport `name`/source string containing `: ` parsed fine at runtime yet was rejected in CI (the P2a failure). Both now import from a single new module `ruwritingstyles/yaml_lite.py` (generic `parse_simple_yaml` + targeted `scalar`/`block`/`list_items`, sharing `parse_scalar`); the generic parser's key/value split now ignores colons inside quotes (`_kv_colon`). New `tests/test_yaml_lite.py` (10 tests) including the quoted-colon regression and a generic-vs-targeted agreement check.

## [2.4.8] - 2026-06-13
### Removed (architecture review #5: drop the redundant style registry)
- Removed the `available_style_sources` block from `styles/manifest.yml` (and its `manifest.schema.json` definition). It duplicated the `passports` list but no code read it — `rws list-styles` derives the user-facing list from the passports via `load_passport_summaries`. Adding a style now touches 4 places instead of 5; `validate_project` still enforces `ClaudeStyles/*.md` ↔ passport `source_prompt` sync. No behavior change (`rws list-styles` still shows 39 styles / 6 MVP).

## [2.4.7] - 2026-06-13
### Added (architecture review #4: Anthropic tool-calling parity)
- `AnthropicProvider` now runs the same multi-turn tool-use loop as the OpenAI and Google providers (up to 5 turns): it sends MCP tools in Anthropic shape (`input_schema`), executes `tool_use` blocks via `mcp_client.execute_tool`, returns `tool_result` blocks, honours the human-injection queue between turns, and accumulates token usage. Previously single-turn with no tool support, so the agentic grounding (Zotero / OpenAlex / corpus FTS5) silently no-opped on Claude. The no-tools path is unchanged (one request → parse JSON). New `tests/test_providers_anthropic.py` (3 tests) covers the loop without a key.

## [2.4.6] - 2026-06-13
### Fixed (third false positive from the case study)
- `translit_lint`: proper nouns (epic titles like Махабхарата/Рамаяна) are no longer flagged by `inconsistent_term_rendering` or `missing_iast_on_first_mention` — a naturalized Russian form and the transliterated Sanskrit word are both correct. `knowledge/sanskrit-terms.json` entries may now carry `"proper_noun": true` (schema updated); Махабхарата and Рамаяна are marked. On the test article this removes the last 2 false positives, taking linter precision to 7/7 = 1.0.

## [2.4.5] - 2026-06-13
### Added (Phase 2 prep: bibliography population from the case study)
- `knowledge/bibliography.json` expanded 26 → 44 entries with the real sources cited by the commentary-strategies article (Бурба, Эрман, Гринцер, Кальянов, Васильков–Невелева, Сыркин, Казанский, Лидова, Парибок ×2, Malhotra, Goldman ×2, Jhalakikar, and three web corpora), with full GOST fields and ids matching the inline `(Author Year)` citation form. The article's four extracted citations now verify and `references-gost.md` renders a correct GOST list (Cyrillic-sorted) instead of coming out empty — the gap surfaced by `docs/case-study-phase1.md`.
- `citations.py`: unmatched citations are now collected under a `not_in_bibliography` key (renamed from the misleading `hallucinations`), and the `reason` states that absence from an incomplete bibliography is not proof of fabrication. All consumers were updated (`citation-output.schema.json`, `report.py`, `pipeline.py`, `cli.py`, `latex.py`, `dashboard.py`, `web/App.jsx`, `tests/test_citations.py`); the eval scorer still emits the synthetic `hallucinated_citation` type for the deliberately fabricated `gost-hallucinated-ref` case.

## [2.4.4] - 2026-06-13
### Added (Phase 1 W6: real-paper case study — closes the deterministic layer of Phase 1)
- `docs/case-study-phase1.md`: a real Russian Sanskrit-studies article run through the deterministic pipeline layer (transliteration linter, GOST bibliography, citation grounding, `vya` journal profile). Documents what each check caught (7 genuine missing-IAST first mentions, length over the ВЯ limit, 4 citations absent from the seed bibliography) and the false-positive analysis.

### Fixed (both found on live article data)
- `translit_lint`: `iast_in_cyrillic_word` no longer flags acronym-plus-Cyrillic compounds (`IAST-транслитерацией`, `TEI-схемы`) or `Cyrillic-IAST` glosses (`сноски-bhāṣya`); only a single hyphen-free sub-token that itself fuses Cyrillic and Latin (e.g. `бхāшья`) is flagged (`_has_fused_mixed_token`). −5 false positives on the test article.
- `citations.extract_citations`: a negative lookbehind stops `@gmail` (and other email domains) being extracted as a `@`-style citation key.

## [2.4.3] - 2026-06-13
### Added (Phase 1 W5: deterministic Sanskrit eval cases)
- Three eval cases in `evals/manifest.json` — `translit-mixed-scheme`, `translit-first-mention`, `gost-hallucinated-ref` (inputs under `examples/input/`) — that **pass under the `mock` provider** because they are scored on deterministic checks, not provider output. This lets the Eval Smoke CI exercise the transliteration linter and citation grounding without API keys.
- `run_eval_case` now runs the transliteration linter and citation grounding as provider-independent post-verification checks (`_run_deterministic_checks`); `_finding_types` aggregates linter finding types and surfaces a synthetic `hallucinated_citation` type when `citations.json` reports hallucinations.

## [2.4.2] - 2026-06-13
### Added (Phase 1 W3: journal profiles)
- **Journal submission profiles** (`journals.py` + `knowledge/journals/{vya,ppv,vestnik-spbu}.json`): per-journal length limit, citation format, transliteration scheme, first-mention rule, abstract/keyword language requirements. New `journal-profile.schema.json` and `project-context.schema.json` validated in CI.
- **`rws journals`** lists presets; **`rws project-set-journal <id> --project-dir DIR`** writes a `journal_profile` block into `project-context.json` (preserving commitments).
- **Profile-aware consumers**: the verifier prompt gains a «Требования журнала» section; the transliteration linter honours `first_mention_rule` (and `rws lint-translit --journal <id>`); `report.md` gains journal-compliance (char count vs limit) and a transliteration-lint section.

### Fixed
- `verification.py` read the project context from the wrong path (`run_dir.parent`) and the wrong key (`commitments` vs `stylistic_commitments`), so binding-rule sections never rendered; now resolved via `project.load_project_context` (run dir first, then parent) accepting both keys.

## [2.4.1] - 2026-06-13
### Added (Phase 1 W1: GOST bibliography)
- **GOST R 7.0.100-2018 formatter** (`gost.py`): book/article/chapter/web reference rendering, Cyrillic-before-Latin sorting; every run now emits `references-gost.md` alongside `references.bib`, and `report.tex` gains a «Литература» section.
- **Bibliography as single source of truth**: `bibtex.py` rewritten to render BibTeX from `knowledge/bibliography.json` (the hardcoded 3-entry `BIB_DATABASE` stub is gone); bibliography expanded 8 → 26 entries with the indological core (Елизаренкова, Топоров, Вертоградова, Кочергина + Зализняк 1987, Monier-Williams, Böhtlingk/Roth, Whitney, Renou, Tubb/Boose) and GOST fields (`kind`, `city`, `pages`, `edition`); new `bibliography.schema.json` validated in CI.

### Added (Phase 1 W2: Sanskrit transliteration linter)
- **Deterministic linter** (`translit_lint.py`, no LLM): mixed IAST/Harvard-Kyoto schemes, inconsistent кириллица/IAST term rendering, missing IAST on first mention, Devanagari NFC issues, Cyrillic-Latin hybrid words. Term dictionary `knowledge/sanskrit-terms.json` (60 terms, each with a lexicographic source).
- **Pipeline step `translit_lint`** in both CLI and Web pipelines (default on; `--no-lint-translit` to disable); writes `translit-lint.json` (schema + `rws validate-run` support) and merges findings into `verification.json` warnings (`"source": "translit_lint"`).
- **`rws lint-translit <file> [--strict|--json]`**: standalone pre-flight check for any Markdown file.

### Fixed
- `verify_citation` now also matches `## Author Year` headings in `knowledge/collections/*.md`, as documented (fixes the long-failing `test_verify_citations`); collection matches verify citations but are excluded from reference lists.
- `pipeline.py`: missing `json`/`queue` imports that crashed the Web-pipeline citations step.

## [2.4.0] - 2026-05-10
### Added (Phase III: External Agent Integration)
- **Agentic Tool-Calling Loop**: Refactored `GoogleProvider` and `OpenAIProvider` to support a multi-turn (max 5) autonomous execution loop. Providers now automatically pause, execute requested tools, and resume generation with grounding data.
- **MCP Stdio Client**: Implemented a production-grade Model Context Protocol (MCP) client. Supports stdio subprocess communication, JSON-RPC handshakes, and automatic tool discovery (handshake -> tools/list -> tools/call).
- **Web Researcher (OpenAlex)**: Created a live scholarly discovery agent in `researcher.py` using the OpenAlex API. Replaced mock data with real-world academic metadata discovery (Author, Year, DOI).
- **Zotero Integration**: Prepared the pipeline for live Zotero library interrogation via MCP server path configuration.

### Added (Phase IV: Advanced Agentic Orchestration)
- **SQLite Native Orchestration**: Implemented a `run_tool_calls` table in `rws.db`. Every agentic interaction (MCP calls, Web searches) is now permanently logged with full arguments and results for absolute auditability.
- **Dynamic Tool Injection**: Wired MCP tools into both the `Socratic Council` (deliberation) and `Verification` stages, allowing agents to fact-check during the debate process.

## [2.3.5] - 2026-05-10
### Added (Phase I: Philological Production)
- **Scholarly Grounding Engine**: Implemented `citations.py` for automated extraction and verification of academic references against the philological knowledge base.
- **Methodological Bias Audit**: Integrated Stage 2.5 into the production pipeline; automated auditing of Council deliberations for ideological and methodological impartiality.
- **Full Corpus Processing**: Successfully validated the high-throughput pipeline on the entire 35-file `examples/input` corpus (Indo-European linguistics, structuralism, and textology).
- **Consolidated Dashboard**: Updated the Project Dashboard (`DASHBOARD.html`) with Bias Scores, Citation stats, and Methodological Compass metrics.
- **LaTeX Scholarly Reports**: Hardened `latex.py` with robust `NoneType` formatting and academic apparatus (BibTeX, bias critique, grounding stats).
- **BibTeX Synthesis**: Automated generation of `references.bib` for every production run.

### Added (Phase II: Scale & Knowledge Integration)
- **Knowledge Ingestion**: Expanded `bibliography.json` with foundational structuralist and philological works (Ivanov, Toporov, Trubetzkoy, Jakobson).
- **Specialized Collections**: Created `novgorod_gramoty.json` to ground analysis of Birch Bark manuscripts with authentic textual precedents.
- **Enhanced Concordance**: Upgraded `KnowledgeManager` to query JSON collections, significantly improving Interactive Concordance precision.
- **Comparative Corpus Audit**: Implemented `batch_analyzer.py` to automatically execute a manuscript through all 17+ stylistic clusters, mapping out "structural tension" across academic schools.
- **Automated Style Evolution**: Created `style_evolution.py` which dynamically reads SQLite `bias_audit` metrics to inject new constraints directly into stylistic passports, creating a self-correcting feedback loop.

#### Synchronized
- **CLI Pipeline**: Updated `cli.py` to parity with the central `pipeline.py`, ensuring all 7 production stages (Review to Reports) are available via command line.
- **Metric Normalization**: Renamed internal metrics to `compass` to resolve database naming conflicts and improve reporting clarity.

## [2.3.0] - 2026-05-08
### Added
- **CI Golden Gate**: Established `evals/baselines/gold.json` (33/33 cases) and updated `scripts/ci-eval-gate.py` to enforce strict regression testing against the gold baseline (GOLD MODE).
- **Unit Test Expansion**: Added comprehensive tests for `hooks.py`, `resolution.py`, and `context_builder.py`, reaching 44 passing unit tests.

#### Refactored
- **Service Layer**: created `resolution.py` with `apply_resolution()` and `write_final_manuscript()` — business logic extracted from CLI and API into a single canonical location.
- **CLI Shims**: `cmd_apply_resolution` and `cmd_finalize` in `cli.py` are now thin delegation wrappers; duplicate logic eliminated.
- **API Layer Cleanup**: `api.py` no longer imports or calls `cli.py`; all resolution endpoints use `resolution.py` directly.
- **CORS Hardened**: wildcard `allow_origins=["*"]` replaced with env-configurable `CORS_ORIGINS` (defaults to localhost:5173/3000); allowed methods restricted.
- **Middleware Order**: `app.add_middleware()` moved to immediately after `app = FastAPI(...)`, before any route registration.
- **Hooks Rewritten**: `hooks.py` refactored from a stateless class to module-level functions; credential detection now uses anchored regex patterns safe for Slavic morpheme text; `post_schema_validate` null-prune anti-pattern removed.
- **Context Builder Activated**: `context_builder.py` wired into `verification.py`; knowledge passages and artifact previews now injected into the verification prompt.

### Fixed
- **FrozenInstanceError**: Resolved crash in `hooks.py` when modifying frozen `ProviderRequest` objects.
- **CLI Logic**: Fixed `eval-regression` and `eval-suite` strictness logic to properly handle existing failures when comparing against a baseline.
- **CI Gate Stability**: Removed invalid CLI arguments from the CI script and updated the workflow to be self-sufficient with the gold baseline.

## [2.2.3] - 2026-05-08
### Added
- Durable Pipeline Execution: implemented `rws resume <run_id>` to continue failed/interrupted runs.
- Database Step Tracking: main CLI pipeline now checkpoints every stage in SQLite `run_steps`.
- Persistent Run Config: stored full execution parameters in `runs.config_json` for faithful resumption.
- Web Build CI Gate: added `npm run build` check to `scripts/ci-eval-gate.py`.
- Human Finalization: added `POST /runs/{run_id}/resolve` and `/finalize` API endpoints.
- Web Studio UI: integrated interactive human resolution and finalization controls into `App.jsx`.
- Scholarly Depth: augmented verification pipeline with dynamic BibTeX ingestion (`references.bib`) and strict citation checking.
- Knowledge Metadata: enriched Gasparov and Tronsky collections with `passage_id`, `reliability`, and `citation_key`.
- API Step Tracking: added `GET /runs/{run_id}/status` to query execution steps dynamically.
- Model Policy: implemented budget modes (`smoke`, `standard`, `expensive`, `verifier-only`) in `model_policy.yml`.
- Extended Telemetry: configured `execution.py` to extract and log token cost estimates and schema repair flags into `provider.log.jsonl`.
- Context Discipline: introduced `context_builder.py` to unify style passports and knowledge base extraction, formalizing the decision to eschew Vector DBs.
- Execution Hooks: implemented `hooks.py` with `pre_provider_call`, `post_schema_validate`, and `pre_write_artifact` for schema repair, file path guardrails, and secret redaction.
- CI/CD Evaluations: integrated `eval-promote` and `eval-regression` into `cli.py` and the `ci-eval-gate.py` pipeline to establish and test against robust project baselines.

### Fixed
- Unified pipeline implementation between `cmd_run` and `pipeline.py`.
- Modernized `scripts/ci-eval-gate.py` CLI arguments.

## [2.2.2] - 2026-05-08 20:10:00
### Fixed
- **CLI Pipeline Stabilization**: Resolved regressions in `db.py`, `revision.py`, and `provider_log.py` that caused execution failures in the `--execute` path.
- **Telemetry Synchronization**: Propagated the `profile` parameter across all execution stages and database registrations for consistent researcher-centric tracking.
- **Test Suite Calibration**: Synchronized unit test expectations in `test_cli_pipeline.py` with the updated pipeline logic (now correctly including Syntax Assessment and skipping Impact when no segments are found).
- **Path Resolution Integrity**: Fixed issues where global `PYTHONPATH` could cause execution of stale library code from other partitions.

## [2.2.1] - 2026-05-08
### Fixed
- Synchronized JSON schemas with current runtime artifacts: `clusters`, `profile`, `bloom_level`, `primary_school`, `influence`, current council statuses, and underscore-style cluster IDs.
- Fixed Docker build/runtime assumptions: install from `pyproject.toml`, copy runtime project data, build Web Studio in a Node stage, and serve `web/dist` from FastAPI.
- Fixed Windows CLI UTF-8 output for Russian/diacritic text before argparse writes help or errors.
- Fixed SQLite run registration cleanup and connection lifecycle around repeated deterministic run IDs.
- Fixed frontend lint/build issues in Web Studio imports and CSS ordering.

### Changed
- Updated tests and documentation for the current 6-style MVP set and 33 active eval cases.
- Documented current deployment shape: local `rws web`, Docker Compose, FastAPI static frontend, `rws.db`, local/Ollama providers, and release checks.

## [2026-05-08] - Phase E: QA and Final Integration
### Added
- Implemented **CI Gate** in `scripts/ci-eval-gate.py` with 100% infrastructure pass rate.
- Mandated **Epistemic Transparency**: Council must now cite the Conflict Matrix resolution rules in decision reasoning.
- Enhanced **Verification Protocol**: Added `SCHOLARLY_ETIQUETTE` rule for literature domain to preserve academic hedging.
- Formalized **Conflict Resolution** logic in `docs/agent-protocol.md`.
- Added **Regional Archetypes**: Introduced `Moscow School` and `Leningrad School` Council personalities in `styles/archetypes.yml`.
- Implemented **Golden Zaliznyak Set**: Tagged 5 primary Zaliznyak-focused documents in `evals/manifest.json` for standardized benchmarking.
- Expanded Documentation: Added [`docs/scenarios.md`](docs/scenarios.md), [`docs/deployment.md`](docs/deployment.md), and [`docs/project-v2-vision.md`](docs/project-v2-vision.md).
- Enhanced Web Studio: Integrated visual display of Council reasoning and conflict resolution logs.

## [2.2.0] - 2026-05-08 19:40:00
### Added (Phase H: Philological Scale)
- **Docker Orchestration**: Added `Dockerfile` and `docker-compose.yml` for industrial deployment.
- **Academic Corpora**: Integrated **Tronsky** (Classical Philology) and **Gasparov** (Verse Metrics).
- **Comparison Engine**: New `/api/compare` endpoint for multi-run stylistic analysis.
- **LaTeX Reporting**: Automated generation of `report.tex` with scholarly apparatus.
- **Unified Service**: API now serves built Web Studio static files in production.

## [2.1.0] - 2026-05-08 19:37:20
### Added (Phase G: Production Infrastructure)
- **SQLite Indexing**: Migrated run tracking from filesystem scans to a structured `rws.db`.
- **Async Audits**: Implemented `BackgroundTasks` in API for non-blocking audit execution.
- **Privacy Mode**: Added `LocalProvider` and `OllamaProvider` for local LLM execution.
- **User Profiles**: Implemented "Researcher", "Editor", and "Student" profiles with tailored instructions.
- **Database Layer**: New `src/ruwritingstyles/db.py` for persistent metrics and status tracking.

## [2.0.0] - 2026-05-08 16:30:00
### Added (Phase F: Scholarly Workbench)
- **Methodological Compass**: School alignment profiling (Moscow vs Leningrad).
- **Tension Heatmap**: Interactive text overlays for inter-agent conflicts.
- **Interactive Concordance**: Real-time academic citations (Zaliznyak, Tronsky).
- **Bloom Taxonomy**: Cognitive labeling of Socratic Council decisions.
- **Web Studio v2.0**: Premium glassmorphic UI with Recharts integration.

## [2026-05-08 14:20:00] - Phase D: Golden Dataset Expansion
### Added
- Implemented **Domain-Aware Verification Rules** in `verification.py` (e.g., PHONETIC_FIDELITY for dialectology).
- Implemented **Philological Conflict Matrix** in `council.py`.
- Enhanced `get_cluster_weights` with **Domain Match Boosts**.
- Created the 30+ case evaluation layer in `evals/manifest.json`; the active manifest is now normalized to 33 cases.
- Implemented **Adversarial Evals** for "epistemic caution".
- Added `scripts/ci-eval-gate.py` for automated evaluation monitoring.
- Updated `assess.py` to support `epistemic_caution` tags in impact assessment.
- Created 4 adversarial input files in `examples/input/` with RWS tags.
- Implemented core instructions for all 9 literary clusters (`lit_` prefix) in `ClaudeStyles/`.
- Implemented core instructions for all 8 linguistic clusters (`ling_` prefix) in `ClaudeStyles/`.
- Added test cases for paradigmatic conflicts (e.g., OPOYAZ vs Bakhtin).

### Changed
- Standardized cluster infrastructure: all 17 clusters are now registered as top-level passports in `styles/manifest.yml`.
- Updated `styles/manifest.yml` to include mandatory `source_prompt` for all entries, fixing a v0.2 parser regression.
- Refactored all cluster filenames to use `ling_` and `lit_` prefixes consistently.

### Fixed
- Fixed "incomplete manifest passport entry" error in `eval-suite` by populating `source_prompt` fields.
