# H6845 — LLM-judge bias calibration report (W8): addendum recompute + length re-derivation + self-preference screen

_Created: 2026-10-22 · Executor: OxAlpha (opencode/z-ai/glm-5.3-flash) · Handoff: Uprava H6845_

**API spend cap, named before any call: $0.00** (zero new paid judge calls; session-subscription lane, no provider keys — H5010 budget precedent). **Spend used: $0.00.** Every probe below runs offline from committed artifacts.

**Honesty note (handoff prior-art order):** the probes were NOT first built here. Length correlation = H4658 ([tools/judge_bias_probe.py](../../tools/judge_bias_probe.py), [JUDGE_BIAS_PROBES_h073gov_2026-09-14.md](JUDGE_BIAS_PROBES_h073gov_2026-09-14.md)); paired position-swap = H5010 ([tools/position_order_paired.py](../../tools/position_order_paired.py), [ORDER_PAIRED_h5010_2026-09-17.md](ORDER_PAIRED_h5010_2026-09-17.md), [POSITION_PAIR_RESULTS_h5010_2026-09-17.md](POSITION_PAIR_RESULTS_h5010_2026-09-17.md)). This handoff closes the owed residuals: (1) the H5010 §53/§Verifier paired-family recomputation of the addendum set, (2) an independent re-derivation of the length axes, (3) the self-preference screen (new), (4) the honest CS329Z index flip in Uprava.

## Tool and raw outputs

- Tool: [tools/judge_bias_calibration.py](../../tools/judge_bias_calibration.py) — stdlib-only, offline, independent reimplementation (does not import the H5010/H4658 analysis code; the point is a second implementation agreeing with the committed numbers). Selftest: 7/7 offline controls (planted-discordance detection ×2, planted-monotone-length detection, degenerate-constant rejection, self-preference positive/negative/fail-closed).
- Tests: [tests/test_judge_bias_calibration.py](../../tests/test_judge_bias_calibration.py) — `python -m pytest tests/test_judge_bias_calibration.py -q` → **5 passed**.
- Raw machine outputs: [h6845_judge_bias_calibration/](h6845_judge_bias_calibration/) — `addendum_recompute_2026-10-22.json`, `length_correlation_2026-10-22.json`, `self_preference_screen_2026-10-22.json`.

## Probe 1 — position-swap, addendum-set paired recompute (the H5010 residual)

| metric | value |
|---|---|
| N (paired items / judgments) | **25 / 50** (all from `evals/probes/h5010_order_paired/`, zero new calls) |
| discordant pairs (any axis) | **0/25** — caught 0, type_correct 0, false_positives 0 |
| flip rate Wilson-95 | **[0.000, 0.133]** |
| invalid judgments | 0/50 |
| directional first-position | 35 early / 13 late positive; median target-pos 1 when positive; **not detected** |
| **parity vs committed `order_paired_analysis.json`** | **PASS — 15/15 checks** (heads, axes, Wilson, all 7 directional fields, per-run discordance) |

**Effect size: 0.00 (0/25), 95% CI [0.000, 0.133].** The second-session (addendum) judgment set's own paired-family recomputation, owed since POSITION_PAIR_RESULTS §53, reproduces the committed analysis exactly under an independent implementation. Known disclosed caveat carries over unchanged: `run_label` anchoring lets the judge re-identify items across arms within the session, so 0/25 is a bounded in-sample order-invariance result, not proof of no position bias (H5010 §Limitations stands).

## Probe 2 — verbosity/length correlation (re-derivation from H4658 artifacts)

| axis (max \|ρ\`) | ρ | n |
|---|---:|---:|
| raterB false_positives ~ n_findings | **+0.3821** | 25 |
| raterB false_positives ~ words | +0.3468 | 25 |
| raterB false_positives ~ chars | +0.3190 | 25 |
| raterB type_correct ~ chars | +0.3114 | 25 |
| raterC (swap) axes | identical to raterB (same 25 runs, order-invariant verdicts) | 25 |

- **Parity vs the committed H4658 machine artifact: PASS — 18/18 axes within 1e-3** (both degenerate caught axes reproduce as None with the same reason).
- **Effect size: max ρ +0.382 (FP vs answer length), n=25** — below the n=25 significance bar ≈0.40; **no rubric-revision flag fires**, the H4658 verdict stands. The FP-vs-length correlation stays a **watch item**: 5 FP-positive runs only; a FP/verbosity coupling at ρ≈0.38 is one borderline sample away from the bar.
- Judge-identity note: raterB (claude-fable-5) and raterC (glm-5.3-flash) produce identical length axes on the shared FP set — the length correlation is a rubric/corpus property here, not a judge quirk.

## Probe 3 — self-preference screen (new, bounded)

| metric | value |
|---|---|
| status on real artifacts | **UNMEASURED** (fail-closed, recorded in `self_preference_screen_2026-10-22.json`) |
| reason | committed graded artifacts carry no `(judged_by, produced_by, score)` provenance — the h073gov/h5010 corpora never recorded which model family produced each judged run; measuring the screen needs new judged calls |
| within cap? | **No — outside the $0.00 cap; not called** |
| detector | built + proven: permutation test (seeded, two-sided) over own-family vs other-family mean-score delta; positive control detects a planted 3-vs-2 own-family bonus (p<0.05), negative control stays p≥0.05, no-provenance input fails closed UNMEASURED |

**What remained unmeasured (explicit, per the cap rule):** the real-data self-preference estimate. It requires (a) backfilling run→producer-family provenance for the existing corpus (owner/human metadata question, not solvable offline), and (b) one bounded judge pass over family-labelled answers — estimated ≤50 calls, ≈$0 on the session lane but nonzero provider-side; queue it as a follow-up with an explicit cap if wanted.

## Verdict for the CS329Z W8 row

Position-swap: measured, 0/25, bounded [0.000, 0.133], two independent implementations + DeepSeek primary-set verifier agree. Length/verbosity: measured, max ρ +0.382 < 0.40 bar at n=25, watch item. Self-preference: screen built, **unmeasured on real data with the reason and the cap named**. On that basis the Uprava `docs/AGENT_EVAL_SUITES_INDEX.md` row flips to **covered with residual** citing H4658 + H5010 + this report — with the self-preference residual disclosed in the row text rather than silently dropped.

## Verifier path (independent)

```
python tools/judge_bias_calibration.py selftest                          # 7/7 PASS, no calls
python -m pytest tests/test_judge_bias_calibration.py -q                 # 5 passed
python tools/judge_bias_calibration.py recompute-addendum                # parity=PASS 15/15
python tools/judge_bias_calibration.py length-correlation                # parity=PASS 18/18
python tools/judge_bias_calibration.py self-preference --records \
  evals/annotation/raterB-h073gov.json --judge glm-5.3-flash             # UNMEASURED (fail-closed)
```

Each command re-derives the report numbers from committed artifacts only; no network, no model calls.

_Гасунс (OxAlpha lane)_
