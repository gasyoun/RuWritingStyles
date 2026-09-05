_Created: 24-08-2026 · Last updated: 05-09-2026_

# Architecture Review — 2026-06

Scope: whole-system review of RuWritingStyles after Phases 0–2 (corpus split,
deterministic Sanskrit layer, indology styles). Companion to the earlier
[architecture-review-phase3.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/architecture-review-phase3.md) and
[architecture-review-phase4.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/architecture-review-phase4.md).

Method: three parallel read-only sweeps over `src/ruwritingstyles/`, `tools/`,
`schemas/`, `tests/`, `web/`, and the agentic modules. Line counts are
approximate (the tree moves).

## v2.15.3 reconciliation (2026-07-19)

The duplicated-orchestrator and duplicated-YAML-parser findings below are historical: CLI and API now share `core_pipeline`, and runtime/validation share `yaml_lite`. v2.15.3 adds a typed prepare/prompt/execute contract, artifact-validating resume with durable `run.json`, and enforced provider budgets. Distribution now has four explicit shapes: a source checkout for development; an installed wheel plus `rws init` workspace for normal use; bundled production Web Studio on port 8000; and Vite development via `rws web --dev`. The wheel, sdist and Docker image consume the same allowlisted, hashed top-level runtime assets.

## Overall assessment

A well-conceived pipeline with a sound core contract, wrapped in an
orchestration layer that has accumulated real duplication and a few load-bearing
fragilities. The domain design — staged philological review with a stable
cross-artifact anchor — has held up as the project scaled to ~60 Python modules,
39 styles, 36 eval cases, a FastAPI + React surface, and agentic integrations.
The weaknesses are not in the idea; they are concentrated at the orchestration
seam: two parallel pipeline implementations, two homegrown YAML parsers, manual
multi-place coupling, and inverted test coverage. All are fixable.

## What is well-designed (keep)

- **Bundle/execute split.** `create_*_bundle` builds the prompt deterministically
  and writes a `status: prompt_ready` shell; `execute_*_artifact` makes the
  opt-in provider call. This is the keystone — it is what makes the pipeline
  testable offline with `--provider mock`, applied consistently across
  review / council / revision / verification / impact / scrutiny.
- **`span_id` as the universal anchor** (`p002`/`h004`/`c003`,
  `^[a-z]+[0-9]{3,}$`). Every finding, council reply, revision change, and
  verification warning references it. Clean, traceable contract.
- **Schema-per-artifact + CI enforcement.** ~32 schemas, validated by
  `tools/validate_project.py`. The "change the artifact shape → change the schema
  in the same commit" rule is real and working.
- **Provider abstraction + `model_policy.yml` routing** decouples vendor params
  (reasoning vs. thinking) from the protocol. Centralized retry/backoff with
  rate-limit-header parsing.
- **Deterministic eval cases** that pass identically on mock — the right way to
  gate the linter/citation layer in CI without keys.

## Weaknesses and risks (prioritized)

### 1. Two orchestrators, ~85 % duplicated — top maintenance hazard
`cli.py::_execute_run_pipeline` (~250 lines) and
`pipeline.py::run_full_pipeline` (~165 lines) reimplement the same stage
sequence (review → council → bias → revision → verify → translit_lint →
citations → impact → syntax → reports). They diverge only in: iteration loop +
interactive override (CLI only) and `on_update` / `injection_queue` callbacks
(API only). Proven cost: the `translit_lint` step and the `not_in_bibliography`
rename each had to be applied in both. They will drift.
→ Extract one `core_pipeline(run_dir, *, iterations, interactive, on_update,
injection_queue, ...)`; both CLI and API call it. Highest ROI.

### 2. `cli.py` (~2,600 lines, 54 subcommands) holds pipeline logic inline
Acceptable as a dispatcher, but the orchestration living inside the CLI file is
the smell that produced #1. Moving the pipeline into the unified core turns
`cli.py` back into thin dispatch.

### 3. Two homegrown YAML parsers that can disagree
`config.py` (runtime) and `tools/validate_project.py::parse_simple_yaml` (CI) are
separate hand-rolled parsers for the same files. A real bug was hit in P2a: a
`:` inside a quoted passport string broke the parser (it splits on `: ` even
inside quotes). Two parsers means a file can validate in CI yet parse
differently at runtime.
→ Unify into one shared parser module (CI and runtime agree) and document the
subset (no `: ` in scalars). Better: vendor a minimal YAML lib — the
"zero runtime deps" purity buys little here.

### 4. The Anthropic provider has no tool-calling — agentic features no-op on Claude
`AnthropicProvider` is single-turn with no tool support; only OpenAI and Google
implement the multi-turn loop that invokes the MCP / OpenAlex / corpus tools. So
the "Agentic" grounding (Zotero / OpenAlex / FTS5) does not fire on Anthropic —
likely the primary provider — behind a uniform-looking interface.
→ Bring `AnthropicProvider` to tool-use parity, or document that grounding
requires OpenAI/Google.

### 5. The 5-place coupling for adding a style is manual and only partly validated
A new style touches `.md` + passport + manifest `passports` + manifest
`available_style_sources` + README. The validator enforces only
`.md ↔ passport` sync — not `available_style_sources` or the README tables. And
`available_style_sources` is largely redundant with `passports`.
→ Derive `available_style_sources` from passports (drop the duplicate),
generate README tables from the manifest, and/or add an `rws add-style`
scaffolder.

### 6. Inverted test coverage — simple code tested, risky code not
97 test methods, but the deterministic leaves (gost, translit_lint, journals,
citations) are well-covered while the orchestrators, `execution.py`, `api.py`,
and the council/review/verification bundle builders are exercised only through
the one slow `test_cli_pipeline` — which also appears to touch the network
(its multi-thousand-second runtime and 429s suggest provider-readiness or
OpenAlex calls leak in despite mock).
→ Add fast mock+tempfile unit tests for the unified `core_pipeline` and
`execution.py`; make `test_cli_pipeline` fully offline.

### 7. Smaller items
- `syntax.py`'s bundle returns a `dict` instead of a frozen dataclass — breaks
  the otherwise-uniform bundle pattern.
- ~47 in-function imports indicate import cycles / missing layering.
- Run metadata/status/timings live only in the local gitignored `rws.db`; a run
  is not self-describing or portable. Writing a `run.json` into each run dir
  would make the DB a pure rebuildable index.

## Recommended sequence

1. Unify the two pipelines into one `core_pipeline` (fixes #1, #2; unblocks #6).
2. Unify the YAML parsers (or vendor one) + document the subset (#3).
3. Anthropic tool-calling parity (#4).
4. De-duplicate the style registry (derive `available_style_sources`; generate
   README) (#5).
5. Fast offline tests for the core + execution (#6).

## Verdict

Architecturally healthy at the core, with concentrated, well-understood debt at
the orchestration seam. The single most valuable change is collapsing the two
pipelines — it removes the duplication, shrinks `cli.py`, and makes the risky
code testable at once. Everything else is incremental.

_Dr. Mārcis Gasūns_
