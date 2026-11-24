# Optimized RuWritingStyles Judge Rubric (H5557)

## Purpose
Guide LLM judges in evaluating Sanskrit scholarly texts with minimal bias and maximal agreement with human visas.

## Core Principles
1. **Moderation**: Favor moderate, well-justified changes over dramatic rewrites
2. **Fidelity**: Prioritize philological accuracy and historical-linguistic fidelity
3. **Consistency**: Maintain consistency across related terms and concepts
4. **Transparency**: Flag ambiguous cases for human review rather than forcing a verdict
5. **Evidence-first**: Weight linguistic evidence more heavily than stylistic preference

## Usage
Wrap the rubric as a signature: `item + rubric → verdict + rationale`

## Metric
Bias-delta reduction with agreement floor (frozen judged sample + human visas).
Target: reduced length-bias Spearman ρ from ~0.31 toward <0.2, no agreement regression.
