# FINDINGS — RuWritingStyles prose-tooling and style-eval registry

_Created: 27-08-2026 · Last updated: 23-09-2026_

Non-obvious, **evidence-backed** facts about *this* repo's subject matter: multi-style LLM
prose review, the scored eval harness, and the gold-standard annotation protocol. Every entry
below is expensive to re-discover and easy to get wrong by assumption.

**Routing — what does NOT belong here.** RuWritingStyles is the middle tier of the two-hub
routing design ([ruling F1](https://github.com/gasyoun/Uprava/blob/main/ASK_BATCH_STAGING_REPO_INTERCONNECTION_2026-08.md),
26-08-2026): only prose-tooling and style-eval gotchas land here.

| Kind of gotcha | Goes to |
|---|---|
| Sanskrit data, encodings, dictionary content | [SanskritLexicography/FINDINGS.md](https://github.com/gasyoun/SanskritLexicography/blob/master/FINDINGS.md) |
| Infra, CI, platform, process, cross-repo tooling | [Uprava/FINDINGS.md](https://github.com/gasyoun/Uprava/blob/main/FINDINGS.md) |
| Who owns which code family | [github-spine/SHARED_CODE.md](https://github.com/gasyoun/github-spine/blob/main/SHARED_CODE.md) row 29 |

Two live examples of the boundary: the `pdftotext`/poppler zero-Cyrillic trap is an infra
finding and already lives at [Uprava/FINDINGS.md §506](https://github.com/gasyoun/Uprava/blob/main/FINDINGS.md)
(the operational rule for this corpus is restated in
[CLAUDE.md](https://github.com/gasyoun/RuWritingStyles/blob/main/CLAUDE.md)); the entries
below are held by neither hub.

This repo gains **no** other epistemic registry — no ASSUMPTIONS, CONTRADICTIONS, GAPS,
DEAD_ENDS, RECIPES, STALENESS or GLOSSARY (ruling F1).

## §1 — An exact-string finding-type scorer turns a correct detection into a formal miss; the fix is a per-case alias map, never substring matching

The eval scorer requires an **exact** match on the finding-type string. A non-deterministic
model regularly produces the conceptually correct error under a slightly different label, and
the run then scores zero on a case it actually solved.

Measured, run 2026-06-30: the `sanskrit-pseudo-etymology` case found the planted problem and
tagged it `unsupported_etymology` rather than the required `unsupported_sanskrit_etymology` —
a formal fail on a correct detection.

The tempting repair is the wrong one. Relaxing the comparison to a substring or regex
(`unsupported.*etymology`) also admits genuine noise, and quietly weakens the protocol for
every case at once. The shipped fix is a **per-case** alias map:

```json
"scoring": {
  "required_finding_types": ["unsupported_sanskrit_etymology"],
  "accepted_finding_aliases": {
    "unsupported_sanskrit_etymology": ["unsupported_etymology", "pseudo_etymology"]
  }
}
```

Three properties make it safe, and all three are load-bearing:

1. A canonical type counts as caught if it **or** one of its own declared aliases appears —
   `_accepted_finding_aliases` and the satisfaction test in
   [`src/ruwritingstyles/evals.py`](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/evals.py).
2. `matched_required_finding_types` always records the **canonical** type, never the alias
   that satisfied it — this is what keeps tables comparable across runs and across providers.
   Record the alias instead and every historical table silently becomes a different measurement.
3. Aliases are added **pointwise and with justification** (an observed or self-evidently
   equivalent label), never as vocabulary expansion to rescue one run. Widening the map
   because a specific run missed is how a gold standard stops measuring anything.

This replaced a hardcoded alias carried in commit `7dbbcc4`; all five expert cases moved onto
the scheme. Protocol: [`evals/GOLD_PROTOCOL.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/evals/GOLD_PROTOCOL.md) «Политика меток».

## §2 — Editing a gold case's `input` after its numbers are published silently redirects those numbers onto a different document

A gold case is supposed to plant **one** deliberate error, and its `purpose` is the rubric a
run is scored against. Two independent failure modes follow from breaking that, and the second
is unrecoverable.

**Rubric/text parity.** `vedic-classical-anachronism` planted the same periodisation error at
two poles — classical (Pāṇini, the "classical aorist") and epic (accentuation "by the norms of
the epic language", scansion as a Mahābhārata verse) — while `purpose` named only the classical
pole. Runs were credited with a detection on the **epic** pole under a rubric that never
described it, and the resulting figure was ambiguous between the two. H1325, 14-08-2026.

The repair depends on whether the poles are one finding class or two:

- **Same class** → widen `purpose` only. `required_finding_types` and
  `accepted_finding_aliases` are not touched (that would be §1's banned vocabulary expansion).
- **Different classes** → either narrow the text back to a single claim, or split it into a
  separate case.

**The unrecoverable half.** Never retro-edit `input` on a case whose numbers have already been
published. The case id, the run directories and every published table keep pointing at that id
while the document underneath them has changed — the published figure now describes a text that
no longer exists, and nothing in the pipeline can detect it. Open a new case instead.

**And the aggregate does not distinguish pole.** Where a rubric legitimately lists several
poles, any paper quoting the detection number must say outright that the number does not
identify which pole the run caught. Ruling:
[`docs/arsa-prayoga-vedic-gold-case-ruling.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/arsa-prayoga-vedic-gold-case-ruling.md).

## §3 — Cohen's kappa is uninformative at extreme marginals, and the implementation returns a flattering 1.0 rather than refusing

Two-rater gold annotation pairs rater A (the mechanical scorer's verdicts, already in each run's
`eval-result.json`) against rater B (an independent expert, or by the author's 11-07-2026
ruling a second frontier model blind to A). Agreement is then reported as percent plus Cohen's
kappa.

Kappa degenerates exactly where this protocol most often lands. When one rater answers "yes"
to every run — routine for a scorer on a healthy suite — expected agreement `pe` reaches 1.0
and the coefficient carries no information at all. The implementation in
[`tools/gold_annotation.py`](https://github.com/gasyoun/RuWritingStyles/blob/main/tools/gold_annotation.py)
returns **`1.0`** in that branch, i.e. it reports *perfect* agreement precisely when the statistic
is meaningless. Read naively, a degenerate suite looks like the best-agreeing row in the table.

So: when the marginals are extreme, report **percent agreement and the disagreement table**,
not the coefficient — and say which one is being reported. `kappa()` also returns `None` on an
empty pair set, which the summary prints as `n/a`; `n/a` and `1.000` are both signals to look at
the marginals rather than at the number.

A human (a third rater) resolves disagreements. Resolving one by widening that case's
`accepted_finding_aliases` is forbidden — it converts a measured disagreement into a definition
change and destroys comparability with every earlier run (§1).

## §4 — Expert eval cases are *designed* to fail on `--provider mock`; only deterministic cases belong in the CI gate

The suite holds two classes of case, and conflating them breaks the gold standard in a way that
looks like a green build.

| Class | Tag | Checked by | Provider-dependent |
|---|---|---|---|
| Deterministic | `deterministic` | automatic (transliteration linter, citation checks) | no — identical on any provider, `mock` included |
| Expert (LLM-judgment) | *(untagged)* | ≥2 independent raters | yes — the substantive finding appears only on a real provider |

Deterministic cases are infrastructure regression tests: they belong in the required `CI`
workflow and pass on `--provider mock`. Expert cases are the gold standard itself, and on `mock`
they **do not pass by construction** — a stub returns no substantive findings, so there is
nothing for the scorer to match.

The CI gate [`scripts/ci-eval-gate.py`](https://github.com/gasyoun/RuWritingStyles/blob/main/scripts/ci-eval-gate.py)
therefore runs the committed baseline `evals/baselines/gold.json` against `--provider mock`
deliberately — it proves the harness still works without keys, not that the models are good.
Anyone who "repairs" a red gate by making expert cases pass on `mock` has deleted the gold
standard and left a green check in its place.

## §5 — Scorer detection and expert detection are two layers; report both, and the gap is the measurement

When adjudication finds that a detection genuinely happened but under a non-matching finding
type, the two numbers are reported **separately and neither replaces the other**:

- **Layer 1** — the mechanical scorer: detection counted only on a canonical-type or declared-alias match.
- **Layer 2** — the gold annotation: detection counted on the substance.

Measured on the H073 protocol (5 cases × N=5 = 25 runs, `20260703-h073gov-*`), adjudicated
19-07-2026: layer 1 = **24/25 = 0.96**, layer 2 = **25/25**. Rater B was Claude Fable 5
(`claude-fable-5`), blind to A's verdicts, with the AI role disclosed in the paper.

The gap between the layers is not noise to be collapsed — it *is* the measured quantity, and it
measures **typing discipline**, not the model's ability to find the error. Publishing only
layer 2 hides a real weakness in the label vocabulary; publishing only layer 1 understates
detection. The adjudication outcome is written into the run's `gold-annotation-*.json` as an
`adjudication` block (rater, date, verdict, effect, link to the audit entry), so a later reader
can tell an adjudicated 0.96 from an unexamined one.

Related, and the reason single numbers are untrustworthy here at all: a **single-run** eval
figure is noise. The harness aggregates over N runs (`rws eval-suite --repeat N` →
`eval-aggregate.json`) precisely because these cases are non-deterministic.

## §6 — A frequency list over the private corpus is only as good as its tokeniser: stress bytes, sigla and abbreviations become fake "key words"

Found while building the NKRYa keyness tables ([H5283](https://github.com/gasyoun/Uprava/blob/main/handoffs/archive/H5283-Opus_RuWritingStyles_nkrya-keyness-zaliznyak-first_23.09.26.md), 23-09-2026). The first top list for Zaliznyak's «Древнерусское ударение» (2019) was космы, регулы, увар, биб — none of them the author's vocabulary. The noise had three independent sources, and each fix alone left the list broken:

1. **Stress marks are stored as `\x01`/`\x02` bytes inside words** in that extraction (`ко\x01смы`). A `\w+` tokeniser splits the word at the byte, so the pieces lemmatise to unrelated words. The fix is to strip the bytes before tokenising.
2. **Capitalised sigla followed by a period** (`Чуд.`, `Феод.` — manuscript sigla) count thousands of times. The fix is to skip any capitalised token that is followed by `.`.
3. **Lowercase abbreviations** (`нов.` 2192×, `регул.` 708×, `соврем.` 283×, `табл.` 190×) lemmatise into real words. The fix is to skip a token followed by `.` and then a lowercase letter, a digit or punctuation — a real sentence end is followed by a capital.

After all three fixes the top list is акцентный +12.8, акцентуация +11.0, ударение +7.4, говор +6.3. That is the book's actual metalanguage.

Two related traps:

1. **pymorphy3 never sets the `Arch` grammeme**, so "archaic word" cannot be read off its tags. The scrutiny candidates use a seed list of Church-Slavonic function words, out-of-dictionary forms and pre-reform spellings instead, and a seed word is matched on its lemma too (`оным` → `оный`).
2. **A raw 1800–1899 hit count is not comparable to an all-periods ipm.** Divide the hits by the slice size (`subcorpStats.wordUsageCount`, 82 049 244 words) before comparing the two.

The NKRYa API rate limit (HTTP 429 after about 10 requests a minute) is an infra fact. It belongs to the shared client ([H5282](https://github.com/gasyoun/Uprava/blob/main/handoffs/H5282-Opus_csl-pyutil_nkrya-client-shared-module_23.09.26.md)), not to this registry.

Code: [`src/ruwritingstyles/nkrya_evidence.py`](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/nkrya_evidence.py) (`STRESS_MARKS`, `ABBREV_TAIL`, `ARCHAIC_SEED`). Method note: [docs/NKRYA_KEYNESS_STYLE_PASSPORTS_H5283_23-09-2026.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/NKRYA_KEYNESS_STYLE_PASSPORTS_H5283_23-09-2026.md).

_Dr. Mārcis Gasūns_
