# Preregistered protocol — H5010 same-judge paired position-bias experiment (h073gov lane)

_Created: 17-09-2026 · Last updated: 17-09-2026_

**Status:** locked before any judgment call of this experiment. Any deviation must be
declared in the dated results file, never silently.

## Motivation (correction target)

H4658 (PR #220) probe 2 compared rater B (`claude-fable-5`, original order) against
rater C (`glm-5.3-flash`, reversed order). Judge model AND candidate order changed
together, so the observed 0/25 flip rate **cannot** identify a position-only effect.
This experiment isolates order: one fixed judge scores both orders of the same 25 items.

## Fixed experimental conditions

- **Corpus (frozen, unchanged):** `evals/annotation/sheet-h073gov.json`
  sha256 `8f92288f6595c3b49813c3e6f377a6c8c91c8b704e8791caaa3f22a184f42e62`;
  `evals/annotation/raterB-h073gov.json`
  sha256 `0a922826b12a65a3b4d8285054de7e7ca430b2fee8383bbd1d2c355f9e99ae29`.
- **Items (all 25, no exclusions):** the 25 runs `20260703-h073gov-{case}-r0{1..5}` for
  cases `sanskrit-pseudo-etymology`, `karaka-not-padezh`,
  `vedic-classical-anachronism`, `samasa-misclassification`,
  `commentary-layer-mix` (5 findings-list sizes 2–10; 148 findings total).
  `vedic-r02` is judged like every run; its standing typing-miss adjudication dossier
  (GOLD_PROTOCOL) is unaffected — this experiment measures judge order sensitivity,
  not the miss.
- **Judge (both arms, identical):** `glm-5.3-flash`, provider `z-ai`, route
  `opencode/zai-coding-plan/glm-5.3-flash`, executed inline in the H5010 OxAlpha
  session on 17-09-2026. Single judge identity for all 50 presentations.
- **Decoding:** session-inline generation, provider-default decoding; no explicit
  temperature/top-p control is available in this lane. Declared limitation: run-to-run
  stochasticity is not controllable here; results are one paired sample, not a
  distributional estimate of the judge.
- **Prompt/rubric (rater-B rubric verbatim, scorer verdicts withheld):**
  - `caught`: does any finding substantively identify the planted error from the case
    purpose (yes/partial/no)
  - `type_correct`: is a finding bearing the canonical required type (or a listed
    alias) aimed at the planted error
  - `false_positives`: count of substantively spurious findings (misread the input);
    extra legitimate style-driven remarks are NOT counted
  - Presentation per item: `case purpose` + `required_finding_types` +
    `accepted_finding_aliases` + `input_text` + findings as `{pos, type, finding}`
    renumbered 1..N. Finding `id`/`style_id`/`span_id`/`severity`/`council_status` are
    stripped uniformly in both arms (uniform stripping cannot create an order
    confound); `type` and finding text are content and stay.
- **Arms:** ORIG = sheet order, positions 1..N; REV = exact reversal of the sheet
  order, positions renumbered 1..N (mirrors rater C's swap construction).
- **Canonical candidate identity:** sha256 of whitespace-normalized finding text;
  stable across arms, used to map blinded positions back to sheet findings after
  judgment. Canonical target per run = first sheet finding whose `type` is the
  required type or an accepted alias.
- **Blinding and call order:** 50 presentations (25 ORIG + 25 REV) shuffled by
  `random.Random(5010).shuffle` (seed recorded here, before judgments); the judge sees
  only `pres_id` (P01..P50), never the arm label or run id; the mapping file is
  written by the builder and not consulted until analysis. Judgment call order =
  shuffled order.
- **Baseline reuse:** NONE. The rater-B baseline fails fixed-condition equality
  (different judge model), so both arms are judged fresh by the fixed judge. Rater B/C
  files are used only as legacy cross-judge context in the correction, never as an arm.
- **Budget/authorization:** ≤ 50 successful judgments (2×25), ≤ 5 transport retries.
  Zero metered external API spend: judgments are produced inline by the executing
  OxAlpha lane (free mechanical lane, MG 25-08-2026), the same no-paid-provider
  pattern as H4658's rater-C pass. No pipeline re-execution, no new provider keys.
  Cost ledger records judgment counts, retries, and $0.00 metered spend.

## Analysis plan (offline, rerunnable without model calls)

Tool: `tools/position_bias_pair.py` (`build` → `analyze` → `selftest`).

1. Per run, per axis (`caught` any-level change, `caught` adjacent-level change,
   `type_correct`, `false_positives` delta): discordance between the fixed judge's
   ORIG and REV verdicts.
2. Primary statistic: paired flip count k / n=25 with Wilson 95% interval, reported
   separately for `type_correct` and `caught`.
3. Directional first-position preference: within each run, target position (1-based)
   of the canonical finding per arm; among discordant pairs, the share where the more
   favorable verdict coincides with the earlier target position.
4. Ties/invalids: `caught=partial` treated as its own level (adjacent to both yes and
   no); unparsable or missing judgments count invalid and shrink the denominator,
   reported explicitly.
5. **Threshold (preregistered):** position-bias concern if flip-rate point estimate
   ≥ 20% on either primary axis, or Wilson lower bound > 10%. Zero flips is NOT proof
   of no bias: report the Wilson upper bound (bounded estimate) and the single-sample
   stochasticity limitation.
6. Controls (synthetic, no model calls, must pass before analysis is trusted):
   - positive: a judge with a known first-position selector (caught=yes iff position-1
     finding is on-target) must be flagged (high discordance + first-position
     preference detected);
   - negative: an order-invariant judge (verdict = f(sorted finding set)) must show
     zero discordance after mapping candidate identities back.
7. Secondary (correction context only): recompute the legacy cross-judge comparison
   rater B (orig) vs rater C (rev) and restate that it is confounded by design.

## Outputs

`evals/probes/position-pair-h5010-2026-09-17.json` (machine), `POSITION_PAIR_RESULTS_h5010_2026-09-17.md`
(human), raw blinded responses `evals/annotation/glm-h073gov-paired-2026-09-17.json`
(+ per-presentation mapping), protocol SHA recorded in the results header. Corrected
conclusion cross-linked to PR #220 without overwriting its historical artifacts.

_Гасунс_
