# Plan — RuWritingStyles interconnection, 2026-08

_Created: 26-08-2026 · Last updated: 27-08-2026_

RuWritingStyles's slice of the spine-interconnection programme. Programme index:
[PLAN_SPINE_INTERCONNECTION_2026H2.md](https://github.com/gasyoun/Uprava/blob/main/docs/PLAN_SPINE_INTERCONNECTION_2026H2.md).

Architecture and verification are **not** restated here (ruling F13) — they are identical for
all fourteen repos and live once in Uprava:

- [ARCHITECTURE_SPINE_INTERCONNECTION.md](https://github.com/gasyoun/Uprava/blob/main/docs/ARCHITECTURE_SPINE_INTERCONNECTION.md) — the five attachment points and the rules governing them
- [IMPLEMENTATION_SPINE_INTERCONNECTION_W1.md](https://github.com/gasyoun/Uprava/blob/main/docs/IMPLEMENTATION_SPINE_INTERCONNECTION_W1.md) — execution order, per-handoff steps, isolation, risks
- [VERIFICATION_SPINE_INTERCONNECTION.md](https://github.com/gasyoun/Uprava/blob/main/docs/VERIFICATION_SPINE_INTERCONNECTION.md) — the five gates and what "done" means

**✅ Executed 27-08-2026** by H3569 (Opus 5, `claude-opus-5`), shipped as
[v2.28.0](https://github.com/gasyoun/RuWritingStyles/releases/tag/v2.28.0).

The plan's two items resolved unevenly, and the difference is the point:

1. **The F8 SHARED_CODE family row had already landed** as map row 29 under
   [H3561](https://github.com/gasyoun/github-spine/pull/127) on the same day, run ahead of
   programme order. Per the roadmap's own ruling
   ([github-spine #130](https://github.com/gasyoun/github-spine/pull/130)) no second row was
   added — a duplicate is not an adjacent row to keep. Instead row 29's factually wrong gloss
   was corrected: it described the scorer alias policy as protecting a baseline from a
   *renamed model*, a guard that exists nowhere in this repo
   ([#131](https://github.com/gasyoun/github-spine/pull/131), spine v1.84.2).
2. **The F1 local registry shipped in full** —
   [`FINDINGS.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/FINDINGS.md) with five
   findings, not the two the ruling set as its floor, so the drop-it-and-take-the-pointer-line
   fallback was never reached ([#187](https://github.com/gasyoun/RuWritingStyles/pull/187)).

## Why RuWritingStyles is in scope

The lowest-scoring repo that is not private by design: one SHARED_CODE row, despite shipping v2.23.0 of a real multi-style prose-review pipeline with a CLI, an eval harness and a Web Studio. It is the only generic prose-review engine in the org.

## Measured baseline and target

| | Value |
|---|---|
| Wiring score, 26-08-2026 | **36** / 100 |
| Target after this plan | **42** / 100 |
| How the target is reached | +2.5 for the local FINDINGS, ~+4 as SHARED_CODE presence rises. |

Measured by [`tools/interconnection_audit.py`](https://github.com/gasyoun/Uprava/blob/main/tools/interconnection_audit.py); full row in
[data/interconnection_audit_2026-08-26.json](https://github.com/gasyoun/Uprava/blob/main/data/interconnection_audit_2026-08-26.json);
report [AUDIT_REPO_INTERCONNECTION_2026-08-26.md](https://github.com/gasyoun/Uprava/blob/main/docs/AUDIT_REPO_INTERCONNECTION_2026-08-26.md).

The score counts artefacts, not whether they are true. It is **report-only** by ruling F2 and no
handoff closes on it — verification Gates 2 to 4 are what actually decide, and Gate 4 is read by
a human.

## Rulings that apply here

| Fork | Ruling |
|---|---|
| F8 | The csl-corrections bridge, the SanskritKaraoke exporter and the RuWritingStyles pipeline all become SHARED_CODE families. |
| F1 | Local `FINDINGS.md` in exactly four repos; the other eight get a `CLAUDE.md` pointer line. No repo gains the other seven registries. |

Full rulings table with every fork:
[ASK_BATCH_STAGING_REPO_INTERCONNECTION_2026-08.md](https://github.com/gasyoun/Uprava/blob/main/ASK_BATCH_STAGING_REPO_INTERCONNECTION_2026-08.md) Phase 2.

## What this plan does

1. Register the «СовеС» review pipeline and its eval harness as a SHARED_CODE family, naming the canonical path and the reuse rule (F8). The paper-referee work is the natural consumer.
2. Create a local `FINDINGS.md` with at least **two real prose-tooling findings** (F1); drop it and take the pointer line if two cannot be produced.
3. Land the family row via a worktree off `origin/main` on github-spine, keeping both rows on any adjacent-row conflict.

## Handoff

- [H3569 (Opus 5) — interconnect ruwriting sovet pipeline family](https://github.com/gasyoun/Uprava/blob/main/handoffs/archive/H3569-Opus_RuWritingStyles_interconnect-ruwriting-sovet-pipeline-family_26.08.26.md) · medium · ✅ closed 27-08-2026 ([#187](https://github.com/gasyoun/RuWritingStyles/pull/187) · [#188](https://github.com/gasyoun/RuWritingStyles/pull/188) · [github-spine #131](https://github.com/gasyoun/github-spine/pull/131))

## Autonomy contract

The launching agent may create the files named above, add hub rows, open and merge its PR,
remove its worktree and close its handoff row — without asking.

It must stop and ask if a local `FINDINGS.md` cannot be given two genuine findings (the
documented fallback is to drop the file and take the pointer line, recorded not silent), if a
corpus row would carry an unmasked snapshot or quote a sample, or if a second speculative edge
becomes necessary. It must never turn the wiring score into a failing gate, commit to
`csl-orig`, or add the seven non-FINDINGS registries.

## Open @DECIDE

None. Every fork touching RuWritingStyles was ruled in sitting 1 on 26-08-2026, so the autonomy gate
passes and nothing in the wave-1 path stalls on a human.

_Dr. Mārcis Gasūns_
