### [2.3.0] - 2026-05-09
#### Refactored
- **Service Layer**: created `resolution.py` with `apply_resolution()` and `write_final_manuscript()` — business logic extracted from CLI and API into a single canonical location.
- **CLI Shims**: `cmd_apply_resolution` and `cmd_finalize` in `cli.py` are now thin delegation wrappers; duplicate logic eliminated.
- **API Layer Cleanup**: `api.py` no longer imports or calls `cli.py`; all resolution endpoints use `resolution.py` directly.
- **CORS Hardened**: wildcard `allow_origins=["*"]` replaced with env-configurable `CORS_ORIGINS` (defaults to localhost:5173/3000); allowed methods restricted.
- **Middleware Order**: `app.add_middleware()` moved to immediately after `app = FastAPI(...)`, before any route registration.
- **Hooks Rewritten**: `hooks.py` refactored from a stateless class to module-level functions; credential detection now uses anchored regex patterns (`sk-[A-Za-z0-9]{20,}`, `AKIA[A-Z0-9]{16}`, etc.) safe for Slavic morpheme text; `post_schema_validate` null-prune anti-pattern removed.
- **Context Builder Activated**: `context_builder.py` wired into `verification.py`; knowledge passages and artifact previews now injected into the verification prompt.

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
