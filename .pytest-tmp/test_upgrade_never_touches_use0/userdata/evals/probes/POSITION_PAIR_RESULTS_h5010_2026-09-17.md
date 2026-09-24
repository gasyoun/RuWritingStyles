# H5010 results — same-judge paired position-bias experiment (h073gov lane)

_Created: 17-09-2026 · Last updated: 17-09-2026_

**Protocol (preregistered, committed before any judgment):** [POSITION_PAIR_PROTOCOL_h5010_2026-09-17.md](POSITION_PAIR_PROTOCOL_h5010_2026-09-17.md) — commit `bfdc5147116b0f8f047a0ae16230e428795b8a9c`.
**Fixed judge:** `glm-5.3-flash` (provider `z-ai`, route `opencode/zai-coding-plan/glm-5.3-flash`), session-inline, provider-default decoding. Both arms judged by the same judge in the same session.
**Corpus (frozen):** `evals/annotation/sheet-h073gov.json` sha256 `8f9228…f42e62`, 25 items × {ORIG, REV} = 50 blinded presentations, seed-5010 shuffle, arm/run identity withheld during judgment.

## Result

| axis | flips | n | rate | Wilson 95% |
|---|---:|---:|---:|---|
| caught (any-level) | 0 | 25 | 0.00 | [0.000, 0.133] |
| caught (adjacent-level) | 0 | 25 | 0.00 | [0.000, 0.133] |
| type_correct | 0 | 25 | 0.00 | [0.000, 0.133] |
| false_positives (delta ≠ 0) | 0 | 25 | 0.00 | [0.000, 0.133] |

- **Denominator 25/25; zero invalid judgments; zero transport retries.** Budget: 50/50 successful judgments, ≤ 50 cap respected; metered external spend $0.00 (inline OxAlpha free-lane judgments, H4658 precedent).
- All four FP>0 findings (missing-IAST self-contradictions) reproduce **identically in both arms** — the judge's FP behavior is order-invariant here.
- `vedic-r02`: canonical-target position 0 in both arms (no finding bears the required type), concordant miss in both orders — the known typing miss reproduces order-independently and stays with its human adjudication dossier (GOLD_PROTOCOL).

## Corrected conclusion (supersedes the H4658 probe-2 reading)

H4658's 0/25 compared rater B (`claude-fable-5`, original order) against rater C (`glm-5.3-flash`, reversed order) — judge model AND order changed together, so that comparison could not identify a position-only effect. With the judge fixed and only the order changed, the paired flip count is **0/25 on every axis**.

**What this evidence supports:** under this fixed judge, on this 25-item corpus, reversing the candidate order produced no verdict change — a bounded position sensitivity with 95% upper bound ≈ 13.3% flip probability per item.

**What it does NOT support:** zero flips is **not proof of no position bias**. One sample per arm at uncontrolled decoding; a small order effect (<13% per item) is not excluded; the judge is the same model lane as H4658's rater C by design. Per the preregistered threshold (concern at rate ≥ 20% or Wilson lower > 10%), **no rubric-revision flag fires**.

## Legacy cross-judge comparison (secondary, context only)

rater B (`claude-fable-5`, orig) vs rater C (`glm-5.3-flash`, rev): 0/25 verdict flips — recomputed from the frozen artifacts; **confounded by design** (judge+order co-varied), retained as historical context, never as a position-bias estimate. Judge-level difference observed in this experiment: the fixed judge scores 4 runs FP>0 (vs rater B's 5) — the vedic-r01 IAST-for-Russian-terms remark is scored as a weak style remark, not a substantive misread; this is judge variation, not order variation.

## Controls and reproducibility (offline, no model calls)

- Positive control: synthetic judge with a known first-position selector → detected (3/5 flips, directional first-position preference 3/3 discordant pairs).
- Negative control: order-invariant judge → 0/5 flips; candidate identities map back 1:1 after reversal.
- Commands:
  - `python tools/position_bias_pair.py selftest`
  - `python -m pytest tests/test_position_bias_pair.py -q`
  - `python tools/position_bias_pair.py analyze` (rebuilds `position-pair-h5010-2026-09-17.json` from saved artifacts)

## Artifacts

- Raw blinded responses + model/cost metadata: [evals/annotation/glm-h073gov-paired-2026-09-17.json](../annotation/glm-h073gov-paired-2026-09-17.json)
- Presentation set + hidden mapping: `evals/probes/position_pair_h5010/` (presentations.jsonl, mapping.json)
- Machine results: [position-pair-h5010-2026-09-17.json](position-pair-h5010-2026-09-17.json)
- Tool: `tools/position_bias_pair.py`; offline control tests: `tests/test_position_bias_pair.py`
- Cross-link: correction posted on [PR #220](https://github.com/gasyoun/RuWritingStyles/pull/220) without overwriting its historical artifacts.

## Verifier

DeepSeek 4.1 Flash (`openrouter/deepseek/deepseek-v4.1-flash`) independently recomputed and **PASS**ed the PRIMARY same-judge set on this branch (paired verdict, 17-09-2026; full report in the primary machine artifact's `verifier` field), including the disclosed `run_label` anchoring residual. This second-session judgment set (this file's numbers) was produced independently before the rebase and concurs (0/25); its own paired-family recomputation is owed as a residual (GTD). No completed-verification claim is made for THIS addendum set beyond the concurrence itself.

_Гасунс_
