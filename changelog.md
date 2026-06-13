### [2.4.4] - 2026-06-13
#### Added (Phase 1 W6: real-paper case study — closes the deterministic layer of Phase 1)
- `docs/case-study-phase1.md`: a real Russian Sanskrit-studies article run through the deterministic pipeline layer (transliteration linter, GOST bibliography, citation grounding, `vya` journal profile). Documents what each check caught (7 genuine missing-IAST first mentions, length over the ВЯ limit, 4 citations absent from the seed bibliography) and the false-positive analysis.

#### Fixed (both found on live article data)
- `translit_lint`: `iast_in_cyrillic_word` no longer flags acronym-plus-Cyrillic compounds (`IAST-транслитерацией`, `TEI-схемы`) or `Cyrillic-IAST` glosses (`сноски-bhāṣya`); only a single hyphen-free sub-token that itself fuses Cyrillic and Latin (e.g. `бхāшья`) is flagged (`_has_fused_mixed_token`). −5 false positives on the test article.
- `citations.extract_citations`: a negative lookbehind stops `@gmail` (and other email domains) being extracted as a `@`-style citation key.

### [2.4.3] - 2026-06-13
#### Added (Phase 1 W5: deterministic Sanskrit eval cases)
- Three eval cases in `evals/manifest.json` — `translit-mixed-scheme`, `translit-first-mention`, `gost-hallucinated-ref` (inputs under `examples/input/`) — that **pass under the `mock` provider** because they are scored on deterministic checks, not provider output. This lets the Eval Smoke CI exercise the transliteration linter and citation grounding without API keys.
- `run_eval_case` now runs the transliteration linter and citation grounding as provider-independent post-verification checks (`_run_deterministic_checks`); `_finding_types` aggregates linter finding types and surfaces a synthetic `hallucinated_citation` type when `citations.json` reports hallucinations.

### [2.4.2] - 2026-06-13
#### Added (Phase 1 W3: journal profiles)
- **Journal submission profiles** (`journals.py` + `knowledge/journals/{vya,ppv,vestnik-spbu}.json`): per-journal length limit, citation format, transliteration scheme, first-mention rule, abstract/keyword language requirements. New `journal-profile.schema.json` and `project-context.schema.json` validated in CI.
- **`rws journals`** lists presets; **`rws project-set-journal <id> --project-dir DIR`** writes a `journal_profile` block into `project-context.json` (preserving commitments).
- **Profile-aware consumers**: the verifier prompt gains a «Требования журнала» section; the transliteration linter honours `first_mention_rule` (and `rws lint-translit --journal <id>`); `report.md` gains journal-compliance (char count vs limit) and a transliteration-lint section.

#### Fixed
- `verification.py` read the project context from the wrong path (`run_dir.parent`) and the wrong key (`commitments` vs `stylistic_commitments`), so binding-rule sections never rendered; now resolved via `project.load_project_context` (run dir first, then parent) accepting both keys.

### [2.4.1] - 2026-06-13
#### Added (Phase 1 W1: GOST bibliography)
- **GOST R 7.0.100-2018 formatter** (`gost.py`): book/article/chapter/web reference rendering, Cyrillic-before-Latin sorting; every run now emits `references-gost.md` alongside `references.bib`, and `report.tex` gains a «Литература» section.
- **Bibliography as single source of truth**: `bibtex.py` rewritten to render BibTeX from `knowledge/bibliography.json` (the hardcoded 3-entry `BIB_DATABASE` stub is gone); bibliography expanded 8 → 26 entries with the indological core (Елизаренкова, Топоров, Вертоградова, Кочергина + Зализняк 1987, Monier-Williams, Böhtlingk/Roth, Whitney, Renou, Tubb/Boose) and GOST fields (`kind`, `city`, `pages`, `edition`); new `bibliography.schema.json` validated in CI.

#### Added (Phase 1 W2: Sanskrit transliteration linter)
- **Deterministic linter** (`translit_lint.py`, no LLM): mixed IAST/Harvard-Kyoto schemes, inconsistent кириллица/IAST term rendering, missing IAST on first mention, Devanagari NFC issues, Cyrillic-Latin hybrid words. Term dictionary `knowledge/sanskrit-terms.json` (60 terms, each with a lexicographic source).
- **Pipeline step `translit_lint`** in both CLI and Web pipelines (default on; `--no-lint-translit` to disable); writes `translit-lint.json` (schema + `rws validate-run` support) and merges findings into `verification.json` warnings (`"source": "translit_lint"`).
- **`rws lint-translit <file> [--strict|--json]`**: standalone pre-flight check for any Markdown file.

#### Fixed
- `verify_citation` now also matches `## Author Year` headings in `knowledge/collections/*.md`, as documented (fixes the long-failing `test_verify_citations`); collection matches verify citations but are excluded from reference lists.
- `pipeline.py`: missing `json`/`queue` imports that crashed the Web-pipeline citations step.

### [2.4.0] - 2026-05-10
#### Added (Phase III: External Agent Integration)
- **Agentic Tool-Calling Loop**: Refactored `GoogleProvider` and `OpenAIProvider` to support a multi-turn (max 5) autonomous execution loop. Providers now automatically pause, execute requested tools, and resume generation with grounding data.
- **MCP Stdio Client**: Implemented a production-grade Model Context Protocol (MCP) client. Supports stdio subprocess communication, JSON-RPC handshakes, and automatic tool discovery (handshake -> tools/list -> tools/call).
- **Web Researcher (OpenAlex)**: Created a live scholarly discovery agent in `researcher.py` using the OpenAlex API. Replaced mock data with real-world academic metadata discovery (Author, Year, DOI).
- **Zotero Integration**: Prepared the pipeline for live Zotero library interrogation via MCP server path configuration.

#### Added (Phase IV: Advanced Agentic Orchestration)
- **SQLite Native Orchestration**: Implemented a `run_tool_calls` table in `rws.db`. Every agentic interaction (MCP calls, Web searches) is now permanently logged with full arguments and results for absolute auditability.
- **Dynamic Tool Injection**: Wired MCP tools into both the `Socratic Council` (deliberation) and `Verification` stages, allowing agents to fact-check during the debate process.

### [2.3.5] - 2026-05-10
#### Added (Phase I: Philological Production)
- **Scholarly Grounding Engine**: Implemented `citations.py` for automated extraction and verification of academic references against the philological knowledge base.
- **Methodological Bias Audit**: Integrated Stage 2.5 into the production pipeline; automated auditing of Council deliberations for ideological and methodological impartiality.
- **Full Corpus Processing**: Successfully validated the high-throughput pipeline on the entire 35-file `examples/input` corpus (Indo-European linguistics, structuralism, and textology).
- **Consolidated Dashboard**: Updated the Project Dashboard (`DASHBOARD.html`) with Bias Scores, Citation stats, and Methodological Compass metrics.
- **LaTeX Scholarly Reports**: Hardened `latex.py` with robust `NoneType` formatting and academic apparatus (BibTeX, bias critique, grounding stats).
- **BibTeX Synthesis**: Automated generation of `references.bib` for every production run.

#### Added (Phase II: Scale & Knowledge Integration)
- **Knowledge Ingestion**: Expanded `bibliography.json` with foundational structuralist and philological works (Ivanov, Toporov, Trubetzkoy, Jakobson).
- **Specialized Collections**: Created `novgorod_gramoty.json` to ground analysis of Birch Bark manuscripts with authentic textual precedents.
- **Enhanced Concordance**: Upgraded `KnowledgeManager` to query JSON collections, significantly improving Interactive Concordance precision.
- **Comparative Corpus Audit**: Implemented `batch_analyzer.py` to automatically execute a manuscript through all 17+ stylistic clusters, mapping out "structural tension" across academic schools.
- **Automated Style Evolution**: Created `style_evolution.py` which dynamically reads SQLite `bias_audit` metrics to inject new constraints directly into stylistic passports, creating a self-correcting feedback loop.

#### Synchronized
- **CLI Pipeline**: Updated `cli.py` to parity with the central `pipeline.py`, ensuring all 7 production stages (Review to Reports) are available via command line.
- **Metric Normalization**: Renamed internal metrics to `compass` to resolve database naming conflicts and improve reporting clarity.

### [2.3.0] - 2026-05-08
#### Added
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

#### Fixed
- **FrozenInstanceError**: Resolved crash in `hooks.py` when modifying frozen `ProviderRequest` objects.
- **CLI Logic**: Fixed `eval-regression` and `eval-suite` strictness logic to properly handle existing failures when comparing against a baseline.
- **CI Gate Stability**: Removed invalid CLI arguments from the CI script and updated the workflow to be self-sufficient with the gold baseline.

### [2.2.3] - 2026-05-08
#### Added
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

#### Fixed
- Unified pipeline implementation between `cmd_run` and `pipeline.py`.
- Modernized `scripts/ci-eval-gate.py` CLI arguments.

### [2.2.2] - 2026-05-08 20:10:00
#### Fixed
- **CLI Pipeline Stabilization**: Resolved regressions in `db.py`, `revision.py`, and `provider_log.py` that caused execution failures in the `--execute` path.
- **Telemetry Synchronization**: Propagated the `profile` parameter across all execution stages and database registrations for consistent researcher-centric tracking.
- **Test Suite Calibration**: Synchronized unit test expectations in `test_cli_pipeline.py` with the updated pipeline logic (now correctly including Syntax Assessment and skipping Impact when no segments are found).
- **Path Resolution Integrity**: Fixed issues where global `PYTHONPATH` could cause execution of stale library code from other partitions.

### [2.2.1] - 2026-05-08
#### Fixed
- Synchronized JSON schemas with current runtime artifacts: `clusters`, `profile`, `bloom_level`, `primary_school`, `influence`, current council statuses, and underscore-style cluster IDs.
- Fixed Docker build/runtime assumptions: install from `pyproject.toml`, copy runtime project data, build Web Studio in a Node stage, and serve `web/dist` from FastAPI.
- Fixed Windows CLI UTF-8 output for Russian/diacritic text before argparse writes help or errors.
- Fixed SQLite run registration cleanup and connection lifecycle around repeated deterministic run IDs.
- Fixed frontend lint/build issues in Web Studio imports and CSS ordering.

#### Changed
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

### [2.2.0] - 2026-05-08 19:40:00
#### Added (Phase H: Philological Scale)
- **Docker Orchestration**: Added `Dockerfile` and `docker-compose.yml` for industrial deployment.
- **Academic Corpora**: Integrated **Tronsky** (Classical Philology) and **Gasparov** (Verse Metrics).
- **Comparison Engine**: New `/api/compare` endpoint for multi-run stylistic analysis.
- **LaTeX Reporting**: Automated generation of `report.tex` with scholarly apparatus.
- **Unified Service**: API now serves built Web Studio static files in production.

### [2.1.0] - 2026-05-08 19:37:20
#### Added (Phase G: Production Infrastructure)
- **SQLite Indexing**: Migrated run tracking from filesystem scans to a structured `rws.db`.
- **Async Audits**: Implemented `BackgroundTasks` in API for non-blocking audit execution.
- **Privacy Mode**: Added `LocalProvider` and `OllamaProvider` for local LLM execution.
- **User Profiles**: Implemented "Researcher", "Editor", and "Student" profiles with tailored instructions.
- **Database Layer**: New `src/ruwritingstyles/db.py` for persistent metrics and status tracking.

### [2.0.0] - 2026-05-08 16:30:00
#### Added (Phase F: Scholarly Workbench)
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
