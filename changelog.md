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

## [2026-05-08] - Phase F: Interactive Scholarly Workbench (v2.0)
### Added
- Implemented **Bloom's Taxonomy Labeling** in Council deliberations (Remember, Analyze, Create, etc.).
- Created **Methodological Compass** (Profiling) engine to calculate school alignment scores.
- Implemented **Significant Syntax Shift Assessor** for detecting Active/Passive swaps and inversions.
- Updated API to expose profiling, syntax, and Bloom stats for Web Studio.

## [2026-05-08] - Phase D: Golden Dataset Expansion
### Added
- Implemented **Domain-Aware Verification Rules** in `verification.py` (e.g., PHONETIC_FIDELITY for dialectology).
- Implemented **Philological Conflict Matrix** in `council.py`.
- Enhanced `get_cluster_weights` with **Domain Match Boosts**.
- Created 34 evaluation cases in `evals/manifest.json` (Milestone: 30+ cases).
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
