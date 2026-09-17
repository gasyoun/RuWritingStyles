# LLM-judge bias probes on the h073gov judge lane — length + position-swap (H4658)

_Created: 14-09-2026 · Last updated: 14-09-2026_

Source: Uprava handoff H4658 · ai-agent-book ch7 (length bias, position bias) · MG ruling 14-09 (assessment doc).
Corpus: the frozen 25-run gold annotation artifact [`evals/annotation/sheet-h073gov.json`](https://github.com/gasyoun/RuWritingStyles/blob/main/evals/annotation/sheet-h073gov.json) (5 gold cases × 5 repeats, deepseek provider, runs 20260703-h073gov). Bounded spend respected: **one** re-judge pass, no pipeline re-execution, no paid provider calls.

## Probe 1 — length bias (mechanical, deterministic)

Question: do high judge scores track long answers? Tool: [`tools/judge_bias_probe.py`](https://github.com/gasyoun/RuWritingStyles/blob/main/tools/judge_bias_probe.py) (Spearman ρ, average ranks, stdlib). Answer = the run's findings output; length in chars / words / finding count. Flag rule: |ρ| ≥ 0.5 on any length~score axis (FP axes excluded).

| length ~ score axis | ρ (n=25) | verdict |
|---|---|---|
| chars ~ rater A detected | +0.311 | below flag threshold |
| chars ~ scorer passed | +0.227 | below flag threshold |
| chars ~ rater B/C caught | undefined | degenerate: 25/25 caught, zero variance |
| chars ~ rater B/C type_correct | +0.311 | below flag threshold |
| chars ~ rater B/C false_positives | +0.319 | below flag threshold (watch item, see below) |

Group means: runs where the required type was matched average 1642 chars of findings vs 590 for the single miss (vedic-classical-anachronism-r02, also the shortest answer, 2 findings). Runs carrying ≥1 false positive average 2349 chars vs 1413 without.

**Verdict: no rubric revision flagged.** No axis reaches |ρ| ≥ 0.5 (the ≈0.31 values are below the n=25 significance bar of ≈0.40). One weak watch item: false-positive rate trends up with answer length (+0.319; 2349 vs 1413 chars) — the rubric already counts FPs separately, so no revision is owed today; re-test if the corpus grows.

## Probe 2 — position swap (bounded re-judge pass)

Design: the SAME 25 runs, findings list **reversed** and positions renumbered (original order and ids never shown), scorer verdicts withheld (blind). Judge C = z-ai glm-5.3-flash, rater-B rubric verbatim (`caught` / `type_correct` / `false_positives`). Judgments: [`evals/annotation/raterC-h073gov-swap-2026-09-14.json`](https://github.com/gasyoun/RuWritingStyles/blob/main/evals/annotation/raterC-h073gov-swap-2026-09-14.json).

**Design disclosure (binds every reading of the numbers):** the comparison is C (glm-5.3-flash, swapped order) vs B (claude-fable-5, original order). A flip would conflate judge identity with position. A **zero** flip rate is therefore the strong reading — no position-bias evidence survives even a judge change — while a HIGH flip rate would need a same-judge control before any position-bias claim.

| metric | result |
|---|---|
| caught flips (B vs C) | **0 / 25** (both raters: 25/25 caught=yes) |
| type_correct flips | **0 / 25** (both raters: 24/25 true — same single miss, vedic-r02) |
| false-positive localization flips | **0 / 25** (both raters flag FP>0 on the same 5 runs: spet-r01, spet-r05, vedic-r01, samasa-r05, comm-r03, with identical per-run counts) |
| **verdict-flip rate** | **0.00** |

Mechanical layer (recomputed from the sheet, label policy per GOLD_PROTOCOL): rater A detected 24/25; verification statuses: 15 passed / 9 needs_human_review / 1 failed.

## Adjudication routing (GOLD_PROTOCOL — human-only)

The swap pass produced **no new disagreements** to adjudicate: zero flips on all three rubric fields. The one pre-existing open item is unchanged and stays where it was — the vedic-r02 labeling-not-detection miss (detection substance present under `unsupported_semantization`/`missing_source` labels, no canonical type or alias) remains with its prepared evidence in [`evals/annotation/decisions_applied_vedic-r02-adjudication_2026-07-19.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/evals/annotation/decisions_applied_vedic-r02-adjudication_2026-07-19.md) / [`docs/paper-pack/vedic-r02-adjudication-verdict-variants.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/paper-pack/vedic-r02-adjudication-verdict-variants.md), awaiting the human verdict. The swapped-order pass adds one datum to that dossier: the miss reproduces under reversed order with a different judge model — it is not position-driven. Per H1325 the aggregate detection number does not distinguish which pole was caught; that caveat already covers this run.

New minor datum for the typing-discipline layer (not a flip): spet-r03 contains a finding typed `unsupported_sansrit_etymology` (label typo) that is substantively on-target; the mechanical layer passes the run via a second, correctly typed finding, so no score is affected.

## Machine results + reproducibility

- Machine-readable: [`evals/probes/judge-bias-h073gov-2026-09-14.json`](https://github.com/gasyoun/RuWritingStyles/blob/main/evals/probes/judge-bias-h073gov-2026-09-14.json)
- Tool selftest (positive + negative controls, incl. a planted monotone length-coupling that must flag): `python tools/judge_bias_probe.py --selftest` → PASS
- Repro:
  ```bash
  python tools/judge_bias_probe.py --sheet evals/annotation/sheet-h073gov.json \
      --raters evals/annotation/raterB-h073gov.json evals/annotation/raterC-h073gov-swap-2026-09-14.json \
      --out evals/probes/judge-bias-h073gov-2026-09-14.json
  ```

## Limitations

1. Cross-judge swap comparison (disclosed above) — zero-flip is robust-across-judge-change evidence, not a pure position estimate.
2. n=25 runs, 5 cases — per-case cells are tiny; ρ estimates are indicative only.
3. The corpus is deepseek-generated reviewer output; bias structure may differ for other providers.
4. `evals/manifest.json` could not carry the probe row: its schema (`schemas/eval-manifest.schema.json`) is `additionalProperties: false` with only `version`/`description`/`cases` — the probe is registered here and in [`docs/benchmark.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/benchmark.md) instead.

_Гасунс_
