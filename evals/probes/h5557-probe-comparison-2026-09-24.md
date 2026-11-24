# Before/After Bias-Probe Comparison (H5557)

## Baseline (H4658, run before rubric optimization)

| Axis | Spearman ρ | Verdict |
|------|-----------|---------|
| rater_a_detected~chars | +0.311 | below flag threshold |
| rater_a_detected~words | +0.283 | below flag threshold |
| rater_a_detected~n_findings | +0.275 | below flag threshold |
| scorer_passed~chars | +0.227 | below flag threshold |
| scorer_passed~words | +0.243 | below flag threshold |
| scorer_passed~n_findings | +0.289 | below flag threshold |
| raterB-h073gov.json_type_correct~chars | +0.311 | below flag threshold |
| raterB-h073gov.json_false_positives~chars | +0.319 | below flag threshold (watch item) |

**Verdict**: No rubric revision flagged. All axes below |ρ| ≥ 0.5 significance bar.

## After Optimization (with optimized rubric H5557)

*Optimization in progress - rerun probe after rubric commit*

## Delta Analysis
- Target: reduce |ρ| by at least 0.05 per axis
- Agreement floor: maintain human visa pass rate ≥ current level
- Position-swap: maintain 0 flips across judge changes

*Full probe rerun required to confirm delta reduction.*
