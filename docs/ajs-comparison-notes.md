# Comparison with Awesome-Journal-Skills (AJS) — notes

**Status:** comparison / no borrow yet · **Author of note:** Claude Code session 2026-06-25 · **Decision owner:** M. Gasūns

## What AJS is

[`brycewang-stanford/Awesome-Journal-Skills`](https://github.com/brycewang-stanford/Awesome-Journal-Skills)
(AJS) is a large **index of Claude Code / Codex "skill packs"** — ~2,895 skills in ~194 packs
covering ~519 academic journals and ~155 CS/AI conferences, across ~11 disciplines. Bilingual
(English + 简体中文). Maintained by Stanford's REAP program with CoPaper.AI; **MIT licensed**.

Each pack encodes one venue's *submission mechanics*: topic/strategy selection, section and
table-formatting standards, abstract/keyword constraints, reviewer-response preparation. Major
targets are economics and life-science flagships (AER, QJE, Nature, Cell) plus Chinese-language
journals (管理世界, 经济研究).

## Verdict: a reference point, not a competitor or a parts donor

AJS is **breadth**: one pack per journal, telling you *which rules venue X wants*. RuWritingStyles
is **depth**: an agentic multi-style Council + a deterministic Sanskrit/GOST/IAST quality layer
over a single manuscript. The functional overlap is near-nil:

- AJS has **no Russian, no GOST Р 7.0.100-2018, no IAST / русская передача, no indology, no
  multi-agent review council.** It does not make RuWritingStyles redundant and is not the same
  genre as it (cf. [ars-integration-notes.md](ars-integration-notes.md) — ARS *is* the same genre
  and *is* a methods donor; AJS is neither).
- AJS's target venues (econ / Nature / Cell / Chinese-language) **do not include any
  RuWritingStyles target** (Вестник СПбГУ, ИЯКФ / чтения памяти Тронского, DH journals). So there
  is no ready-made pack to reuse — only a *structure* to learn from.

## License: clean (unlike ARS)

| Repo | License | Mixing with this Apache-2.0 repo |
|---|---|---|
| RuWritingStyles | Apache 2.0 | — |
| ARS | CC BY-NC 4.0 | **NC taints** any verbatim-copied subtree (see ARS notes) |
| **AJS** | **MIT** | **Compatible** — MIT content may be included in an Apache-2.0 project with attribution; no NC clause |

So AJS is the *easier* donor legally: you could adapt pack text directly. The reason to still
re-implement is practical (its packs are for the wrong venues/languages), not legal. If any AJS
text is ever copied verbatim, keep the MIT `LICENSE`/attribution with it and record it in
[SOURCES.md](../SOURCES.md) — but a one-line MIT credit, not the `third_party/` carve-out ARS needs.

## The one concrete borrow: a richer journal-profile schema

RuWritingStyles' journal layer is thin — 3 presets
([knowledge/journals/](../knowledge/journals/): `vya`, `ppv`, `vestnik-spbu`) over a small
[journal-profile.schema.json](../schemas/journal-profile.schema.json) (`max_chars`,
`citation_format`, `transliteration_scheme`, `first_mention_rule`, `abstract_required`,
`keywords_required`, `notes`). AJS's value is the **wider model of what a journal profile should
capture**, observed across hundreds of venues. Candidate fields to lift from AJS's structure
(re-implemented for our deterministic checks, not copied):

- **abstract word limit** — ✅ **SHIPPED (v2.10.4).** `abstract_max_words` is now a checkable
  field: [report.py](../src/ruwritingstyles/report.py)'s `journal_compliance` extracts the abstract
  body per language and counts words; over-limit is flagged in the report and the Obsidian panel.
  Backfilled on [vestnik-spbu.json](../knowledge/journals/vestnik-spbu.json) (`200`), converting
  the old prose note "расширенная, до 200 слов" into an enforced rule. The gúṇa article reports
  114/200 — OK. This was the concrete trigger that motivated the whole AJS comparison.
- **structure / section order** — required sections and their order (e.g. IMRaD vs. humanities
  free-form), so the report can flag a missing/mis-ordered section. *(not yet built)*
- **keywords constraints** — min/max count. *(not yet built)*
- **figures/tables** — formatting/caption rules (low priority for philology, but cheap to model).
- **reviewer-response template** — AJS ships these per venue; maps to a future RuWritingStyles
  "rebuttal helper" rather than the review pipeline.

**Pattern for the remaining fields (prose note → enforced rule):** add the optional field to
`journal-profile.schema.json`; teach [report.py](../src/ruwritingstyles/report.py)'s
`journal_compliance` to check it deterministically (no provider call); **mirror it in the Obsidian
port** [obsidian-plugin/src/lint/journal.ts](../obsidian-plugin/src/lint/journal.ts) +
[types.ts](../obsidian-plugin/src/lint/types.ts) and regenerate fixtures
(`python tools/export_journal_fixtures.py`); backfill the presets. The `abstract_max_words` commit
is the worked example to copy — note the engine↔TS parity obligation enforced by
`obsidian-plugin/test/journal.test.ts`.

## Do-not-do

- Do not treat AJS as a methods donor for the Council — it has none; that role is ARS's.
- Do not import AJS packs for foreign venues hoping they transfer — the rules are venue- and
  discipline-specific and none match our target journals.
- Do not over-build the journal schema speculatively — add a field only when a real target
  journal needs it (Вестник СПбГУ's 200-word abstract is the one concrete trigger today).
