_Created: 24-08-2026 · Last updated: 05-09-2026_

# Data / Schema Review — 2026-06

Scope: the data layer — 32 JSON schemas, the human-editable data files
(bibliography, sanskrit-terms, journals, manifest, passports, model_policy,
eval manifest), the run-artifact contract, and the SQLite DB. Companion to
[architecture-review-2026-06.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/architecture-review-2026-06.md).

Method: three parallel read-only sweeps over `schemas/`, `knowledge/`,
`styles/`, `evals/`, `src/ruwritingstyles/{schema_validation,validation,db}.py`,
and `tools/validate_project.py`.

## Overall assessment

The data layer is well-structured and **currently consistent**, but its
integrity rests on **manual discipline rather than enforcement**, and the custom
validator gives **false confidence** by silently ignoring schema features it
does not implement. The risks are concentrated in three places: the validator's
silent-ignore behaviour, partial referential-integrity checking, and run state
that lives only in a gitignored local DB.

## What is solid (keep)

- **Cross-reference content is clean.** All 60 `sanskrit-terms.json` `source`
  ids resolve to `bibliography.json` (44 entries, no duplicates); every passport
  `provenance.sources` bibliography-id resolves; all five expert GOLD cases map
  to a real `checks` entry in their named passport; all `source_prompt` /
  passport / cluster paths exist; all 3 journals validate.
- **The dual-schema split is intentional and consistent** — `*-output.schema.json`
  validates the provider's raw JSON; the artifact schema validates the stored
  file (with orchestration metadata: `run_id`, `status`, `prompt_path`).
- **`span_id`** has a real pattern (`^[a-z]+[0-9]{3,}$`) and *is* validated for
  reviews against `segments.json` in `validate_run_dir`, which runs in CI
  transitively (eval-smoke → `validate-eval-suite` → `validate_run_dir`).

## Weaknesses and risks (prioritized)

### 1. The validator silently ignores unsupported schema keywords — the meta-risk
`schema_validation.py` implements a subset (type/required/properties/
additionalProperties/items/enum/const/minLength/pattern/min-max/`$ref`).
Anything else is silently skipped. Two keywords are **used yet unenforced**:
`format: "date-time"` (run.schema.json) and `minItems: 1` (style.schema.json
`best_for`/`checks`). The forward-looking danger is worse: a future schema can
use `oneOf`/`uniqueItems`/`allOf` believing it is enforced, and it is not.
→ Make the validator **reject unknown keywords** (strict-subset guard) and
implement the two that are actually used (`minItems`, `format`).

### 2. `segments.json` — the span_id anchor — has no JSON schema
Stored artifacts without a schema: `segments.json`, the stored `citations.json`
(the existing `citation-output.schema.json` governs a different `{citation,
source_file}` shape), `bias-audit.json`, `impact.json`, `syntax.json`.
`segments.json` is the worst gap — every other artifact references it, yet it is
only checked by hand-rolled field asserts.
→ Add `segments.schema.json` and validate it in `validate_run_dir`.

### 3. `span_id` referential integrity is only half-enforced
`validate_run_dir` checks `reviews/*.review.json` findings against known
span_ids, but **not** `revision.json` `applied_changes[].span_id` or
`verification.json` `warnings[].span_id`. The translit-lint span check is gated
on `source_file == "normalized.md"`, but the pipeline lints `revised.md`, so it
is effectively never exercised.
→ Extend span_id validation to revision + verification; fix the translit-lint
condition.

### 4. Run state lives only in the gitignored local `rws.db`
Status, timestamps, `duration_seconds`, `config_json`, and all metrics
(bloom/compass/tension/bias/citation_stats) exist only in `rws.db`;
`metadata.json` is written conditionally. A run directory on disk cannot say
whether it completed or what it scored. (Architecture review #7, from the data
angle.)
→ Write a `run.json` into each run dir; the DB becomes a rebuildable index.

### 5. The integrity that is clean today is not enforced — it will drift
`validate_project.py` does not check: (a) passport `provenance.sources`
bibliography-ids exist in `bibliography.json`; (b) `sanskrit-terms.json` `source`
ids exist in `bibliography.json`; (c) eval `required_finding_types` exist as a
deterministic linter type or in a referenced passport's `checks`. These are
consistent now only because they were verified by hand each time; the first typo
passes CI silently.
→ Add these three cross-reference checks to `validate_project.py`.

### 6. Minor
- `manifest.yml` `version: "2.4.0"` vs changelog `2.5.x` — a stale, meaningless
  field (wire to the package version or drop it).
- `citation-output.schema.json` omits `additionalProperties` and does not
  document its `entry` field.

## Status (2026-06-13): cheap wins #1, #5, #2, #3 implemented

#1 strict-keyword guard + `minItems`/`format`/`minProperties` enforced (the guard
caught `minProperties` as unenforced). #5 (a)+(b) bibliography cross-references
enforced in CI; (c) eval→checks dropped — the finding-type vocabulary is
intentionally looser (27/44 cases use types no style enumerates). #2
`segments.schema.json` added + validated. #3 revision `applied_changes` span_ids
validated; `verification.warnings` and translit-lint left unchecked on
investigation — they legitimately mix the original `segments.json` basis with
`revised.md`'s re-segmented span_ids, so a blanket check would false-positive
(the translit-lint condition is a correct guard, not a bug). #4 done: every run
writes a self-describing `run.json` (status/timestamps/config/metrics/steps) via
`runs.write_run_manifest`, validated against `run.schema.json` (whose stale
status/text_domain vocabulary was corrected). Only #6 (manifest `version`)
remains.

## Recommended sequence (all cheap, all lock in existing good state)

1. Strict-unknown-keyword guard + implement `minItems`/`format` (#1).
2. Three cross-reference checks in `validate_project.py` (#5).
3. `segments.schema.json` + extend span_id validation to revision/verification (#2, #3).
4. `run.json` per run dir (#4) — slightly larger.
5. Drop/wire the manifest `version` (#6).

## Verdict

Healthy content, under-enforced contracts. The system trusts authors not to use
unsupported keywords and trusts maintainers to keep cross-references in sync by
hand. Items #1, #5 and #3 convert that manual discipline into CI enforcement for
very little code — the highest-leverage work here.

_Dr. Mārcis Gasūns_
