# Reviewer Calibration Protocol

This protocol turns claim-faithfulness review into a measurable process before
it is used for publication decisions.

## Inputs

- A frozen run directory with `segments.json`, `revised.md` or `normalized.md`,
  `citations.json`, and any human notes.
- A `claim-faithfulness-audit.json` packet following
  [`schemas/claim-faithfulness-audit.schema.json`](../schemas/claim-faithfulness-audit.schema.json).
- Two independent reviewers for expert cases, named anonymously as `A` and `B`.

## Measures

| Measure | Definition |
|---|---|
| True positive | Reviewer flags a claim that the gold note says is unsupported, wrong-source, or anchor-missing. |
| False positive | Reviewer flags a claim that the gold note says is supported with an adequate locator. |
| False negative | Reviewer accepts a claim that the gold note says should be flagged. |
| Agreement | Share of claims where reviewers choose the same `support_status`. |

For a calibrated packet, report:

- precision: `true_positive / (true_positive + false_positive)`;
- recall: `true_positive / (true_positive + false_negative)`;
- false-positive rate over supported claims;
- false-negative rate over unsupported claims;
- reviewer agreement, with a short note on disagreements.

## Reviewer Instructions

1. Judge only whether the cited source supports the claim, not whether the prose
   is elegant.
2. Prefer `needs_human_review` over guessing when a source is unavailable.
3. Do not penalize a claim merely because `knowledge/bibliography.json` lacks an
   entry; that is bibliography coverage, not claim support.
4. Treat Sanskrit, IAST, Russian transmission, and GOST issues as separate
   findings unless they change the meaning of the claim.

## Readiness Gate

Claim-faithfulness warnings may feed the main verification report only after a
calibration note records at least one double-reviewed packet and the false
positive / false negative definitions above are applied consistently.
