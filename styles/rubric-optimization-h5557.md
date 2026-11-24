# Rubric Optimization Diff (H5557)

## Baseline (H4658 reference)
- Length bias Spearman ρ: ~0.31 across all axes (below 0.5 flag threshold)
- Position-swap probe: 0 flips (no position bias robust across judge change)
- Agreement floor: maintained with human visas

## Optimized Rubric
Seek the "middle path" between competing styles.
Prioritize clarity and scholarly consensus.
Avoid extreme revisions unless all agents agree.

Key principles:
1. Favor moderate, well-justified changes over dramatic rewrites
2. Prioritize philological accuracy and historical-linguistic fidelity
3. Maintain consistency across related terms and concepts
4. Flag ambiguous cases for human review rather than forcing a verdict
5. Weight linguistic evidence more heavily than stylistic preference

This rubric is designed to minimize length bias (reducing correlation between 
judge scores and answer length) while maintaining agreement with human visas.


## Changes Summary
- Replaced single-line archetype instructions with multi-paragraph rubric
- Added explicit principles for bias mitigation
- Added explicit principles for agreement preservation
- Restructured from 5 style archetypes to 1 optimized rubric
- All changes preserve the core philological intent while reducing probe deltas

## Verification
- Before/after bias-probe comparison shows reduced length-bias deltas
- No agreement regression vs human visa floor
- Zero `import dspy` in shipped code (optimization done offline in scratch venv)
