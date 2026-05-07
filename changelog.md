# Changelog

All notable changes to the RuWritingStyles project will be documented in this file.

## [Unreleased] - 2026-05-07

### Added
- `schemas/manifest.schema.json`: New schema for the style manifest.
- `schemas/eval-manifest.schema.json`: New schema for the evaluation suite manifest.

### Changed
- `tools/validate_project.py`: Upgraded to a robust, zero-dependency validation script with a custom YAML parser and full JSON Schema support.
- Expanded repository validation to include every style passport and model policy file.

## [Unreleased] - 2026-05-07

### Added
- HTML Report: Side-by-side document comparison view (Original vs Revised).
- HTML Report: Council decisions now displayed as stylized status cards instead of a plain table.
- HTML Report: Modernized UI with CSS Grid, improved typography, and interactive hover states.
- Eval Scoring: Added `strict_fidelity` check to fail cases if verification produces warnings.
- Eval Scoring: Added `max_finding_count` limit to catch hallucination/over-reporting.
- Eval Manifest: Updated `pseudo-etymology` case to enforce strict factual fidelity.
- Council Logic: Upgraded deliberation system with archetypes and conflict resolution strategies.
- Council Logic: Findings are now grouped by `span_id` in the prompt for easier cross-style comparison.
- Council Logic: Introduced `_style_weight` to help the council weigh different style authoritativeness.
- Manifest Schema: Added `weight` to style passports and a `council` configuration block.
- Fact-Checking Loop: Implemented iterative refinement loop in `rws run` and `eval-run`.
- Fact-Checking Loop: Council prompt now accepts verification feedback to address factual regressions.
- Fact-Checking Loop: Added `--max-iterations` argument to control the depth of recursive improvement.
- Multi-turn Deliberation: Introduced a cross-style "debate" phase where agents critique each other's findings.
- Multi-turn Deliberation: Council Coordinator now synthesizes both initial reviews and cross-agent deliberation replies.
- Multi-turn Deliberation: Added `--deliberate` flag to all run commands and a standalone `rws deliberate` utility.

### Task 3: Real-world provider validation
- Blocked by: Missing API keys for OpenAI, Anthropic, and Google.
- Readiness: All adapters (urllib-based) are implemented and passed code review.
