# Prompt / Style-Fidelity Review — 2026-06

Scope: the *content* layer, not the code. Three questions — (1) do the
machine-readable passports faithfully encode their `ClaudeStyles/*.md` prompts;
(2) do the styles actually carry a *distinctive philologist's method* or generic
"be rigorous" boilerplate; (3) does that distinctiveness survive the pipeline
(review → council → revision → verification). Companion to
[architecture-review-2026-06.md](architecture-review-2026-06.md),
[data-schema-review-2026-06.md](data-schema-review-2026-06.md),
[security-review-2026-06.md](security-review-2026-06.md).

Method: three parallel read-only sweeps (layer-mapping / pipeline-flow /
voice-authenticity), claims spot-verified against the manifest and code.

## Overall assessment

The fidelity *machinery* is sound: the two layers are in lockstep, bidirectionally
enforced, and the per-passport compression of each `.md` is honest. The problems are
**curatorial and architectural**, not bugs: the default council is pointed away from
the project's actual subject, several passports are generic enough to be
interchangeable, and the pipeline preserves each style's voice perfectly through the
*judging* stages but cannot confirm it survived the *rewriting* stages. None of this
is broken; all of it is drift between what the catalog *is* and what this author
*needs it for*.

## What is solid (keep)

- **`.md` ↔ passport is faithful and enforced both ways.** 39 `ClaudeStyles/*.md` map
  1:1 to 39 manifest passport entries (21 individual + 18 cluster-prompt); 0 orphans.
  [validate_project.py](../tools/validate_project.py) compares the two sets for *equality*,
  so an unpaired `.md` or a dangling `source_prompt` fails CI. Spot-checked
  zalizniak-method, tronsky-readings, melchuk, elizarenkova-veda, lidova-commentary —
  each passport's `checks`/`limits` compress the `.md`'s actual demands without
  inventing methods or dropping load-bearing ones.
- **Voice reaches the model verbatim at the stages that judge.** The review prompt
  injects **both** the full passport YAML and the full `.md` instruction
  ([review.py:244-301](../src/ruwritingstyles/review.py)); deliberation re-injects
  the passport and every *other* style's findings with `style_id` attribution
  ([review.py:179-224](../src/ruwritingstyles/review.py)). Distinctiveness is fully
  preserved where a style forms and defends its opinion.
- **The best passports are unmistakable.** ~16 of 21 encode a real signature:
  `anti_amateur_linguistics` (zalizniak-method), `formal_notation`/`semantic_decomposition`
  (melchuk), `missing_apparatus`/`missing_alternative_interpretation` (tronsky),
  `anachronistic_sanskrit_period`/`missing_context_of_hymn` (elizarenkova-veda),
  `missing_sutra_reference`/`missing_commentary_layer` (panini-traditional). Swap the
  name and these would not survive — which is the point.

## Findings (prioritized)

### F1 · The default council is pointed away from the project's subject. `HIGH`
`mvp_style_ids` = [zalizniak-method, zalizniak-novgorod, tronsky-readings, melchuk,
averintsev, gasparov] ([manifest.yml:5](../styles/manifest.yml)). The project's whole
purpose is **Russian scientific papers on Sanskrit linguistics**, and the MVP set
contains **zero of the eight Sanskrit/indology styles** (elizarenkova-veda,
toporov-etym, panini-traditional, sanskrit-reader, samasa-manual, lidova-commentary,
albedil-sbornik, kazanskiy-korpus). The default `rws run` council — what gets exercised
in every smoke test and every quick pass — reviews Sanskrit prose with an Old-Novgorod
dialectologist and a verse-theory metrician, while the people who actually know Vedic
period boundaries and Pāṇinian commentary layers sit on the bench. This is the single
highest-leverage change and it is one edited list. zalizniak-method (general rigor,
anti-pseudo-etymology) and tronsky-readings (apparatus/source criticism) transfer and
should stay; the Sanskrit core (elizarenkova-veda, toporov-etym, panini-traditional)
belongs in the default six. **This is your scholarly call — see the question at the end.**

### F2 · Five passports are generic enough to be interchangeable. `MEDIUM`
sanskrit-reader, samasa-manual, zalizniak-shkolnikov-1, kazanskiy-korpus, and
albedil-sbornik read as universal pedagogy/commentary method wearing a name — their
`checks` (`undefined_term`, `missing_example`, `translation_replaces_analysis`,
`weak_translation_equivalence`, `tone_too_dry`) would apply to any competent teacher or
translator. Two of these (sanskrit-reader, samasa-manual) are *teaching* manuals by
design, so genericness is defensible; but it means the council cannot tell them apart
from each other or from the cluster baseline. Either sharpen each with one or two
signature checks (samasa-manual already has the good `wrong_samasa_type`/`missing_vigraha`
— lean into that register), or accept them as "register presets" rather than "scholar
voices" and label them so in the README.

### F3 · Generic `checks` dilute discriminability — but less than it looks. `LOW-MEDIUM`
*(Corrected against measured data — see [audit_passport_checks.py](../tools/audit_passport_checks.py).)*
The qualitative sweep read several check *concepts* as generic (`undefined_term`,
`missing_example`, `weak_classification`) and inferred wide collusion. The objective
overlap across the 21 individual passports is much smaller: of **85 distinct checks**,
only **3** are shared by ≥3 passports — `overstrong_conclusion` (**10×**),
`missing_iast_on_first_mention` (5×, the *correct* Sanskrit-cluster signature, not a
defect), and `weak_classification` (3×). **No passport exceeds 50% shared checks**; the
most-shared are samasa-manual and zalizniak-ocherk at 40%. So the catalog is well
differentiated by check id.
The one genuine item: **`overstrong_conclusion` is in 10 of 21 passports** — a generic
rigor check that carries no "which style raised it" signal, and the council weights by
style. Either lift it to a baseline check every style inherits (so it stops masquerading
as a per-style signature), or replace it in the passports where a sharper finding would
do. The broader "is the *concept* generic" question (F2) is a positioning call, not an
overlap defect. `tools/audit_passport_checks.py` makes this re-checkable as passports change.

### F4 · Voice is preserved where styles *judge*, but unverifiable where text is *rewritten*. `MEDIUM`
The honest finding from the pipeline trace: voice is fully present through review +
deliberation, then progressively *finding-mediated*:
- **Council** ([council.py:198-316](../src/ruwritingstyles/council.py)) works from the
  *findings* + cluster weights + a hardcoded conflict matrix — it does **not** re-inject
  any passport/`.md` text. Defensible: the findings *are* each style's distilled verdict.
- **Revision** ([revision.py:133-143](../src/ruwritingstyles/revision.py)) sees only
  `council.json`. A minority style voted down by the weighting **leaves no trace** in the
  rewrite — there is no "deferred dissent" record.
- **Verification** ([verification.py:205-227](../src/ruwritingstyles/verification.py))
  checks facts-preservation + domain rules + journal limits, but has **no record of which
  styles were selected or what they committed to**, so it cannot confirm the revised text
  honored the council's own style verdict.

This is mostly *by design* — synthesis on distilled findings is reasonable — but for a
DH-grade auditable pipeline the gap is real: a run cannot show *that* style intent
survived its own revision, and dissent vanishes silently. The cheap, safe fix is an
audit trail, not a redesign: record the selected `style_id`s + their `stylistic_commitments`
into `run.json`/verification input so the verifier (and a human) can check preservation
and see what was overruled. (Ties into data-review #4's self-describing `run.json`.)

### F5 · Two clusters are nominal, which skews archetype/region weighting. `LOW-MEDIUM`
`get_cluster_weights` weights findings by cluster, so cluster membership has to mean
something methodologically. **ling_mss** ("Московская семантическая школа") pairs melchuk
(formal Meaning-Text semantics) with zalizniak-udarenie (historical accentology) — almost
no shared method beyond institutional geography. **ling_mts** ("Московско-Тартуская",
semiotic) contains zalizniak-enklitiki and zalizniak-imennoe (formal morphology) and
kazanskiy-korpus (translation commentary), none of which are semiotic; only albedil-sbornik
fits. The **indology** cluster, by contrast, is tight. Where a cluster is grouped by
biography rather than method, a regional archetype boost lands on the wrong findings.
Either regroup by method or down-weight region for these.

### F6 · Minor
- **melchuk passport understates the voice.** The `.md`'s combative register
  ("это чистейшее шаманство, а не лингвистика") is real method for him, but the passport's
  neutral field names strip it. Harmless — the full `.md` reaches the reviewer — but the
  passport alone misrepresents the tone. Consider a `register`/`tone` field for styles
  whose polemic *is* the method (melchuk, zalizniak-zametki).
- **Naming inconsistency:** `zalizniak-shkolnikov_1-style.md` (underscore) vs passport id
  `zalizniak-shkolnikov-1` (dash). Cosmetic, and renaming risks the `source_prompt` match —
  leave it, but note it so the next person doesn't "fix" half of it.
- **The 9 `lit_*` literary-theory styles** (Bakhtin, narratology, OPOYAZ, poststructural,
  reception, structural, textology, mythopoetics, historico-cultural) are cluster-level
  catalog entries with no individual passport. Fine for a general catalog; just orthogonal
  to a Sanskrit-linguistics author and worth flagging as "catalog breadth, not council depth."

## Verdict

The fidelity *plumbing* is the healthiest layer reviewed so far — faithful, enforced,
and voice-preserving where it counts. The work is curatorial: **aim the default council
at Sanskrit (F1)**, sharpen the handful of name-only passports (F2/F3), and give the
rewrite/verify half of the pipeline an audit trail so style intent is *demonstrably*
preserved, not just probably (F4). F1 is the one that changes the product today.

## Recommended sequence

1. **F1** — re-pick `mvp_style_ids` for the Sanskrit purpose *(author's call; proposal below)*.
2. **F4** — record selected styles + commitments into `run.json`/verification *(mechanical, safe)*.
3. **F3/F2** — audit generic-check ratios; add a signature check to the thin passports *(author's domain)*.
4. **F5** — regroup or de-region ling_mss / ling_mts *(taxonomy; low urgency)*.

## Status (2026-06-13): F1, F4, F3 addressed

- **F1 — named councils.** Rather than swap the default (the author's choice was a *menu*),
  `styles/manifest.yml` now has a `councils:` block: `general` (= the historical MVP),
  `sanskrit` (elizarenkova-veda, toporov-etym, panini-traditional, zalizniak-method,
  tronsky-readings, lidova-commentary), and `indology`. Selectable via `rws run --council
  <name>` (also `review`/`deliberate`); `rws councils` lists them. The default stays
  `mvp_style_ids` (= `general`) for back-compat. `validate_project` now fails if a council
  names a non-existent passport. `tests/test_councils.py` (9).
- **F4 — audit trail (implemented, the safe half).** `run.json` now carries a `styles`
  block via `runs._collect_style_audit`: the styles that actually produced a review, the
  council's honored/overruled/informational tally (mapped to the real
  `council.schema.json` status enum), the **overruled dissent** trace (rejected/deferred
  findings with reason + primary_school), and the `stylistic_commitments` the rewrite was
  meant to honor. Purely additive metadata — reads artifacts, changes no prompt or
  pipeline behaviour. The *other* half — feeding the selected styles' commitments into the
  verification **prompt** so the verifier actively checks preservation — is intentionally
  deferred (it changes verifier output and warrants its own eval pass).
- **F3 — generic-check audit.** Built `tools/audit_passport_checks.py` (repeatable) and
  corrected this section against its data: the catalog is well-differentiated; the single
  real item is `overstrong_conclusion` (10/21).

## Status (2026-06-13, round 2): F2, F3, F5 resolved

The author chose **drop `overstrong_conclusion`** (F2/F3) and **de-region the weighting** (F5).

- **F2 reframed.** Re-reading the five "generic" passports against their `.md` showed three
  are genuine named-scholar voices with adequate signature checks (`zalizniak-shkolnikov-1`,
  `kazanskiy-korpus`, `albedil-sbornik`) and `samasa-manual` is already sharp
  (`wrong_samasa_type`/`missing_vigraha`); only `sanskrit-reader` is a pure register preset.
  So no forced "sharpening" — the premise was softer than the first pass implied.
- **F3 done.** Dropped `overstrong_conclusion` from all **10** passports that carried it —
  each already has a *sharper*, scholar-specific overstatement check (`weak_reconstruction`,
  `unsupported_etymology`, `missing_alternative_interpretation`, …), and no eval references
  it. The audit now shows only 2 checks shared by ≥3 passports (`missing_iast_on_first_mention`,
  the correct Sanskrit-cluster signature, and `weak_classification`). `metadata/dublin-core.xml`
  regenerated.
- **F5 done by de-regioning, not regrouping.** The clusters mix *method* and *city* and
  `get_cluster_weights` boosted on both, so a misfiled passport (e.g. the accentology
  `zalizniak-udarenie` parked in the Moscow *Semantic* cluster) drew a wrong regional
  authority. Rather than contested per-passport reassignments (one sub-agent target,
  `kazanskiy-korpus`→indology, was itself wrong — Kazansky is a classicist), the
  geography-based location boost was **removed**; deliberate cluster boosting survives via
  explicit `styles/archetypes.yml` weights, which key on `cluster_id`, not city.
  `tests/test_cluster_weights.py` (2). The cluster *memberships* are left as the author's
  documentation, no longer a silent weighting hazard.
