# P3 real-paper run — seeded-problem key (grading rubric)

The draft [`examples/input/lexicography-guna.md`](../examples/input/lexicography-guna.md)
is a genuine ~22k-character Russian article on the lexicographic treatment of *guṇa*,
written for *Вестник СПбГУ. Востоковедение*. Into an otherwise sound draft, **3 problems
were deliberately seeded** to test what the Council catches. This file is the grading key
— it is NOT fed to the pipeline (the pipeline only reads the input above).

After the run, grade detection: did the council flag each seed, and with which finding type?

## Seed 1 — shaky / unsupported etymology (§ 2)

> «Слово *guṇa* восходит к индоевропейскому корню *gʷenǝ- «вить, скручивать» и
> закономерно соответствует латинскому *funis* «верёвка» и греческому *χορδή* «струна»:
> переход начального лабиовелярного в латинский *f* и греческий придыхательный регулярен…»

**Why it's wrong:** fabricated. The actual etymology of *guṇa* is uncertain (Mayrhofer);
*funis* does not derive from a labiovelar, the χορδή correspondence is bogus, and the
"regular" sound change is invented. The confident, un-hedged tone ("закономерно",
"регулярен") is exactly the amateur-etymology pattern.
**Expected finding types:** `unsupported_sanskrit_etymology`, `arbitrary_sound_change`,
`accidental_similarity`, `unsupported_method`.
**Best-placed styles:** toporov-etym, zalizniak-zametki, zaliznyak-method.

## Seed 2 — missing IAST on first mention (§ 4)

> «…противопоставленную … усиленной ступени **вриддхи**.» … «наряду с правилами **сандхи**.»

**Why it's wrong:** *vṛddhi* and *sandhi* are introduced in Cyrillic with **no IAST on
first mention**, whereas *guṇa*, *sattva*, *prakṛti* etc. are correctly given with IAST.
Violates the indology first-mention convention.
**Expected finding types:** `missing_iast_on_first_mention` (deterministic translit-lint
may also catch it if the terms are in `knowledge/sanskrit-terms.json`).
**Best-placed styles:** elizarenkova-veda, panini-traditional, sanskrit-reader; the
deterministic `translit_lint`.

## Seed 3 — anachronism / impossible source-claim (§ 3)

> «Характерно, что Бётлингк и Рот при расположении значений *guṇa* **опирались на
> практический словарь Апте**, заимствовав у него рубрикацию…»

**Why it's wrong:** chronological impossibility. PW (Böhtlingk–Roth) is **1855–1875**;
Apte is **1890** — both dates are given in the Литература, so the contradiction is
checkable from the text itself. PW could not have drawn on a dictionary published 15+
years later.
**Expected finding types:** `anachronistic_sanskrit_period`, an unsupported source-claim /
`unsupported_reading`, `overstrong_conclusion`.
**Best-placed styles:** tronsky-readings, zaliznyak-method, kazanskiy-korpus.

## Scoring

**Result (2026-06-14, `--council sanskrit` on `deepseek-chat`) — see
[case-study-p3-guna.md](case-study-p3-guna.md):**

| Seed | Caught? | Finding type(s) | By which style(s) |
|---|---|---|---|
| 1 — etymology | ✅ | `unsupported_sanskrit_etymology`, `missing_source` | toporov-etym, zaliznyak-method |
| 2 — missing IAST | ✅✅ | `missing_iast_on_first_mention` | deterministic `translit_lint` (named *vṛddhi* + *sandhi*) + toporov-etym |
| 3 — anachronism | ✅ | `unsupported_reading`, `logical_inconsistency` (correct judgement, label ≠ `anachronistic_sanskrit_period`) | tronsky-readings, zaliznyak-method |

**3/3 caught.** Bonus: the linter found 2 *unintended* un-IAST'd terms (*sūtra*,
*vyākaraṇa*) + a *guṇa*/*гуна* inconsistency — real omissions the author missed. No
false-positive storm (elizarenkova-veda = 0; others 3–5 on a 22k-char article). Revision
stayed proportionate (char-delta 0.18 / line 0.22, well inside the 0.50 / 0.75 caps) —
the benchmark's "over-rewrite" was a short-doc ratio artifact.

A genuine pass = all 3 caught with on-target finding types and **no excessive false
positives on the sound remainder of the article** (the rest is intentionally clean). ✅ met.
