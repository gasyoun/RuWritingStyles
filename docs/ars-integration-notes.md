# Borrowing from Academic Research Skills (ARS) — integration notes

**Status:** plan / not yet started · **Author of note:** Claude Code session 2026-06-22 · **Decision owner:** M. Gasūns

## What ARS is

[`Imbad0202/academic-research-skills`](https://github.com/Imbad0202/academic-research-skills)
(ARS, v3.13.0) is a **Claude Code plugin** — a prompt-driven suite of four skills
(`deep-research`, `academic-paper`, `academic-paper-reviewer`, `academic-pipeline`) plus
`/ars-*` slash commands, packaged through
[`.claude-plugin/marketplace.json`](https://github.com/Imbad0202/academic-research-skills/blob/main/.claude-plugin/marketplace.json).
It is English / 中文 / 日本語, discipline-agnostic, has a Zenodo DOI
([10.5281/zenodo.20696614](https://doi.org/10.5281/zenodo.20696614)), and runs a 10-stage
orchestrated pipeline with integrity gates.

ARS is the **same genre** as RuWritingStyles (agentic research→write→review→revise pipeline),
but it has **no Russian, no GOST, no IAST/русская передача, no indology**. So it does not make
RuWritingStyles redundant — RuWritingStyles is the Russian-Sanskritology localization of
machinery ARS has already hardened. ARS is a *parts donor*, not a competitor.

---

## ⚠️ License interaction — read first

| Repo | License | Nature |
|---|---|---|
| RuWritingStyles | **Apache 2.0** ([LICENSE](../LICENSE)) | permissive — allows commercial use |
| ARS | **CC BY-NC 4.0** | source-available, **non-commercial**, attribution required, *not* OSI open source |

These do **not** mix cleanly:

- **CC BY-NC 4.0 content cannot be relicensed under Apache 2.0.** If we copy ARS markdown
  verbatim, those files stay CC BY-NC 4.0 per-file; the repo's blanket Apache grant in
  [LICENSE](../LICENSE) / [SOURCES.md](../SOURCES.md) no longer covers them, and the **NC clause
  taints that subtree** — downstream commercial reuse of those specific files is forbidden. That
  is a meaningful regression for an Apache repo whose whole point is permissive reuse.

- **Ideas, protocols, and architecture are not copyrightable.** Re-implementing ARS's *method*
  (e.g. a claim-support audit, an FNR/FPR calibration loop) in our own Russian-language code and
  prose carries **no license obligation** and creates **no conflict**. Attribution is then a
  matter of scholarly courtesy, not law.

### Chosen stance (2026-06-22)

> **Default = re-implement from ARS's design, do not copy ARS files. Attribute generously
> anyway.** We give full credit (SOURCES.md row + CITATION reference + inline doc credit) even
> though re-implementation does not legally require it, because (a) it is honest, (b) it matches
> RuWritingStyles' "assistive, not deceptive" ethos, and (c) it keeps the whole repo cleanly
> Apache 2.0.

If a specific ARS file is ever worth vendoring **verbatim**, isolate it: put it under
`third_party/ars/` with its own `LICENSE` (CC BY-NC 4.0) + `NOTICE`, and record the carve-out in
[SOURCES.md](../SOURCES.md). Accept that that subtree loses Apache's commercial-use freedom. Prefer
not to.

### Ready-to-paste attribution (use when the first borrow lands)

`SOURCES.md` table row:

```markdown
| — | Academic Research Skills (ARS), Imbad0202, v3.13.0, CC BY-NC 4.0, https://doi.org/10.5281/zenodo.20696614 | методологический донор: протоколы аудита цитат, калибровки рецензента, проверки качества письма (переосмыслены, текст не копировался) |
```

`CITATION.cff` — add to `references:`:

```yaml
references:
  - type: software
    title: "Academic Research Skills for Claude Code"
    authors:
      - alias: Imbad0202
    version: "3.13.0"
    license: CC-BY-NC-4.0
    doi: 10.5281/zenodo.20696614
    repository-code: "https://github.com/Imbad0202/academic-research-skills"
    notes: "Design/protocol donor for citation-faithfulness audit, reviewer calibration, and writing-quality checks. Methods re-implemented, not copied."
```

---

## Borrows, ranked by payoff

Each maps an ARS component to the RuWritingStyles module/roadmap item it upgrades.

### 1. Claim-faithfulness citation audit — highest value

**ARS:** goes past "does this citation exist" to "does the cited source actually *support* this
claim." Three-layer locator anchors + an opt-in audit (`ARS_CLAIM_AUDIT=1`) with five HIGH-WARN
refuse classes (claim-not-supported, fabricated-reference, anchorless, …).
- [`academic-pipeline/references/claim_verification_protocol.md`](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-pipeline/references/claim_verification_protocol.md)
- [`academic-pipeline/agents/claim_ref_alignment_audit_agent.md`](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-pipeline/agents/claim_ref_alignment_audit_agent.md)
- [`academic-paper/references/anti_leakage_protocol.md`](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-paper/references/anti_leakage_protocol.md)

**RuWritingStyles today:** [citations.py](../src/ruwritingstyles/citations.py) +
[verification.py](../src/ruwritingstyles/verification.py) emit a `hallucinated_citation` finding,
grounded against [knowledge/bibliography.json](../knowledge/bibliography.json). But grounding is
**presence-only** — the Phase-1 open item is that an unpopulated bib flags every real citation as
hallucinated ([docs/case-study-phase1.md](case-study-phase1.md)).

**Upgrade:** re-implement ARS's claim→source *support* check as a new deterministic-ish stage
(claim is anchored to a `span_id`; verifier checks the cited source backs the claim, not just that
the ref resolves). Adds HIGH-WARN classes to `verification.schema.json`. **Unblocks** the Phase-1
citation-grounding gap. No ARS files copied.

### 2. Reviewer calibration → fill `benchmark.md`

**ARS:** measures its own false-negative / false-positive rate against a user-supplied gold set —
[`academic-paper-reviewer/references/calibration_mode_protocol.md`](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-paper-reviewer/references/calibration_mode_protocol.md).

**RuWritingStyles today:** [evals.py](../src/ruwritingstyles/evals.py) +
[assess.py](../src/ruwritingstyles/assess.py) + [scrutiny.py](../src/ruwritingstyles/scrutiny.py),
44 eval cases, [evals/GOLD_PROTOCOL.md] — but roadmap **P2** ("measure real DeepSeek quality →
fill [docs/benchmark.md](benchmark.md)") is blocked on *how to measure*. [benchmark.md](benchmark.md)
is empty.

**Upgrade:** adopt ARS's FNR/FPR-against-gold methodology as the protocol for the DeepSeek council
benchmark. Plugs straight into the existing gold cases. **Unblocks P2.**

### 3. Multi-reviewer council design for the `indology` cluster

**ARS:** [`academic-paper-reviewer`](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-paper-reviewer/SKILL.md)
runs EIC + 3 peer reviewers + **Devil's Advocate** over four *non-overlapping* perspectives
(methodology / domain / cross-disciplinary / core-argument), emits an Editorial Decision Letter +
Revision Roadmap, and has a `re-review` verification mode. See
[`agents/`](https://github.com/Imbad0202/academic-research-skills/tree/main/academic-paper-reviewer/agents)
and [`templates/editorial_decision_template.md`](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-paper-reviewer/templates/editorial_decision_template.md).

**RuWritingStyles today:** named councils (`general`/`sanskrit`/`indology`) in
`styles/manifest.yml`, driven by [council.py](../src/ruwritingstyles/council.py) +
[peer_review.py](../src/ruwritingstyles/peer_review.py) + [review.py](../src/ruwritingstyles/review.py)
— the F1 "named councils" feature, but thinner.

**Upgrade:** model the `indology` council on ARS's persona structure — add a devil's-advocate
seat, non-overlapping perspective assignment, an editorial-decision-letter output, and a re-review
mode in [revision.py](../src/ruwritingstyles/revision.py)/[verification.py](../src/ruwritingstyles/verification.py).

### 4. Russian "AI-tells" writing-quality check

**ARS:** [`academic-paper/references/writing_quality_check.md`](https://github.com/Imbad0202/academic-research-skills/blob/main/academic-paper/references/writing_quality_check.md)
catches machine-prose patterns (overused terms, em-dash overuse, throat-clearing openers, uniform
paragraph length, monotonous rhythm) + Style Calibration that learns voice from 3+ past papers.

**RuWritingStyles today:** the whole point of the repo is style — passports +
[styleguide.py](../src/ruwritingstyles/styleguide.py) + [profiling.py](../src/ruwritingstyles/profiling.py)
+ [style_evolution.py](../src/ruwritingstyles/style_evolution.py) +
[docs/style-contract.md](style-contract.md).

**Upgrade:** build a **Russian** AI-tells checklist (Russian machine-prose patterns differ from
English) as a deterministic check, complementing the style passports. Squarely in our wheelhouse;
re-implement, don't copy (ARS's list is English).

> **⚠️ Design guardrail (Bassett et al. 2026, [doi:10.1080/1360080X.2026.2622146](https://doi.org/10.1080/1360080X.2026.2622146)).**
> This check is the one place RuWritingStyles edges toward detector-like heuristics, and AI
> detectors are exactly what that paper shows to be unverifiable and unfair. So the AI-tells
> check must stay a **style-quality signal** — flag clichés / monotonous rhythm to *improve the
> prose* — and must **never** be framed as an origin classifier, an "is this AI?" score, or an
> accusation tool. It produces editing suggestions for the author, not a verdict on authorship.
> This keeps the feature consistent with [AI_DISCLOSURE.md](AI_DISCLOSURE.md)'s
> disclose-don't-detect stance.

### 5. Plugin packaging for distribution

**ARS:** ships via `/plugin marketplace add … && /plugin install …`
([marketplace.json](https://github.com/Imbad0202/academic-research-skills/blob/main/.claude-plugin/marketplace.json),
`/ars-plan`, `/ars-full`, …).

**RuWritingStyles today:** a pip CLI ([cli.py](../src/ruwritingstyles/cli.py), ~80 subcommands) +
[gallery.py](../src/ruwritingstyles/gallery.py). Roadmap 2.8 wants "installable CLI + Claude style
gallery."

**Upgrade:** wrap the core flows (`run`, `lint-translit`, `journals`, `councils`) as a thin Claude
Code skill/plugin **alongside** the CLI, so Russian Sanskritologists on Claude Code install in one
line. ARS explicitly invites community platform ports under its license — a Russian sibling is a
sanctioned pattern.

### Lower-value, cheap

- **CI hygiene patterns** — ARS's
  [`eval-harness.yml`](https://github.com/Imbad0202/academic-research-skills/blob/main/.github/workflows/eval-harness.yml),
  `test-count-monotonic.yml`, `spec-consistency.yml`, `freshness-check.yml` are reusable guards for
  our eval suite ([.github/workflows/ci.yml]).
- **Citation-API protocols** — ARS's
  [`crossref_api_protocol.md`](https://github.com/Imbad0202/academic-research-skills/blob/main/deep-research/references/crossref_api_protocol.md)
  / `openalex_api_protocol.md` / `source_quality_hierarchy.md` can harden
  [researcher.py](../src/ruwritingstyles/researcher.py) and auto-enrich GOST refs
  ([gost.py](../src/ruwritingstyles/gost.py), [bibtex.py](../src/ruwritingstyles/bibtex.py)) from
  canonical metadata.
- **AI-disclosure / process record** — ARS auto-generates a "Paper Creation Process Record"; we
  already have [docs/AI_DISCLOSURE.md](AI_DISCLOSURE.md), so this is a small enhancement matching
  our ethos.

---

## Recommended order

1. **#1 claim-faithfulness audit** and **#2 calibration** first — they unblock two standing
   roadmap items (citation grounding + `benchmark.md`) and require **zero ARS files copied**, only
   re-implemented protocols against the DeepSeek provider.
2. Land the attribution blocks above the moment the first borrow merges.
3. **#5 plugin packaging** once the engine is solid — that is the distribution play.

## Do-not-do

- Do not vendor ARS markdown into the Apache tree without the `third_party/ars/` carve-out above.
- Do not adopt ARS's English writing-quality / anti-tell wordlists as-is — Russian patterns differ.
- Do not let the AI-tells check (#4) become an AI-detector / authorship verdict — it is a
  style-quality signal only (Bassett et al. 2026; see the guardrail under borrow #4).
- Do not assume ARS's `ANTHROPIC_API_KEY`-first defaults; our primary provider is DeepSeek.
