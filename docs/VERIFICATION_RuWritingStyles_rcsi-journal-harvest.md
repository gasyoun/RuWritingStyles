# VERIFICATION — RCSI journal profiles and article harvest

_Created: 19-08-2026 · Last updated: 19-08-2026_

Acceptance layer of [PLAN_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/PLAN_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md).
Every deliverable below states the command that proves it. "Report PASS/FAIL", not "please
verify".

## Acceptance criteria

### Wave 0

| Deliverable | Passes when | Command |
|---|---|---|
| W0.1 candidate inventory | Every candidate is listed with a version or an explicit `unavailable` reason; the skills-tree sweep is recorded | read `docs/BENCHMARK_pdf-extractors_ru_19-08-2026.md` |
| W0.3 scored run | Every candidate has a score on every sample, including the two known-garbled PDFs; no cell is blank | `python tools/benchmark_extractors.py --report` |
| W0.4 verdict | A winner and a fallback order are named; thresholds appear in `config.py`; at least one candidate scores `pass` on at least one of the two known-garbled PDFs, or the document states plainly that none does | `python -c` free — grep `PDF_EXTRACTOR_CHAIN` in `src/ruwritingstyles/config.py` |

The last clause matters: if no extractor rescues the garbled PDFs, that is a legitimate result
and must be written down rather than hidden — it tells H1882 that those two files stay
unusable.

### Wave 1

| Deliverable | Passes when | Command |
|---|---|---|
| W1.2 schema | All five existing profiles validate unchanged against the extended schema | `python tools/validate_project.py` |
| W1.3 verified gate | Attaching an unverified profile exits 3 with a message naming `guidelines_url`; `--allow-unverified` succeeds | `rws project-set-journal <dir> 2306-5737` then the same with `--allow-unverified` |
| W1.3 profile derivation | `knowledge/journals/2306-5737.json` exists, validates, carries `verified: false`, `license`, `oai_endpoint`, `guidelines_url` | `rws journal-add 2306-5737 && python tools/validate_project.py` |
| W1.3 no in-place overwrite | Running `rws journal-add 0373-658X` against the hand-verified `vya` profile prints a diff and exits 3 | `rws journal-add 0373-658X; echo $?` |
| W1.5 pinned harvest | All five articles have text, sidecar, bibliography row | `rws journal-harvest --pinned` |
| W1.6 the guarantee | `rws corpus-verify` exits 0 and reports 5/5 | `rws corpus-verify --json` |
| W1.6 the guarantee bites | Deleting one pinned text makes `corpus-verify` exit 1 naming that article | delete, run, restore |
| W1.9 offline tests | The full suite passes with no network; the live smoke is skipped by default | `pytest -q` |
| W1.9 live smoke | Passes when explicitly enabled | `RWS_LIVE_SMOKE=1 pytest -q -k live_smoke` |
| W1.11 fence | The public repo's working tree contains no `.txt`, `.pdf`, or `rws.db` change | `git status --porcelain \| grep -E '\.(txt\|pdf)$\|rws\.db'` returns nothing |
| Regression bar | Existing suite green, `validate_project` SUCCESS, eval gate zero regressions against the **unchanged** baseline | `pytest -q && python tools/validate_project.py && python scripts/ci-eval-gate.py` |

No `gold.json` refresh is owed. Harvesting cannot change an eval score; if the gate moves,
something is wrong and that is the finding, not a reason to re-baseline.

### The specific request, restated as a check

The user asked that five named articles be "included for sure". That is satisfied exactly
when `rws corpus-verify` exits 0 **and** a test in CI runs the same check, so the guarantee
survives the next re-harvest, cleanup, or corpus migration. Anything short of that is a
one-time verification, not a guarantee.

## Risks and spikes

| # | Risk | Likelihood | Impact | Handling |
|---|---|---|---|---|
| R1 | The article HTML body is theme-dependent and the container selector breaks | Medium | Harvest silently returns abstracts instead of full text | The sanity gate's `words` count catches it — a 300-word "article" fails against the declared page range. Spike in W1.5: verify the selector on one article from each of the six journals before building the loop |
| R2 | No extractor rescues the two known-garbled PDFs | Medium | The H1882 gate stays shut for those two files | Explicitly an acceptable outcome; W0.4 requires it be written down either way |
| R3 | RCSI rate-limits or blocks the harvester | Low | Wave 2 stalls | 1 request/second, on-disk cache, a real contact address in the user agent, and a typed `RcsiRateLimited` that stops the run cleanly after three consecutive journals. Log the outage in [Uprava/SERVER_OUTAGES.md](https://github.com/gasyoun/Uprava/blob/main/SERVER_OUTAGES.md) before abandoning |
| R4 | Вестник РАН floods the corpus with non-linguistic articles | High | Corpus quality drops | The `negative` term group and the `uncertain` review queue; the run reports the include/exclude split per journal so a bad filter is visible immediately |
| R5 | Licences differ per journal and some forbid redistribution | Medium | Nothing, for the private corpus | Rights uncertainty is not a stop under [the standing policy](https://github.com/gasyoun/Uprava/blob/main/docs/STANDING_POLICY_RIGHTS_UNCERTAINTY_IS_NOT_A_STOP_2026.md). Record the declared licence verbatim in the sidecar and the `SOURCES.md` row; keep everything in the private repo; do not publish extracts |
| R6 | The transliterated stem collides between two articles | Low | One text overwrites another | Stem uniqueness is asserted before writing; collision appends a short DOI tail |
| R7 | A future `corpus.py` change starts reading sidecars and finds them inconsistent | Low | Wrong metadata in `rws.db` | The sidecar schema is versioned from day one and validated in `corpus-verify` |
| R8 | An uninstalled bake-off candidate pulls a multi-gigabyte model | Medium | Wasted time in an unattended run | D19's throwaway venv, plus a hard rule: an install that fails or runs long is recorded `unavailable` and skipped, never retried |

### Spikes to run before committing to the architecture

1. **HTML body selector across all six journals** (30 minutes) — confirms R1 is handled and
   tells you whether the HTML-first order of D07 actually pays off, or whether some journals
   are PDF-only in practice.
2. **One OCR pass on one known-garbled PDF** (15 minutes) — answers R2 early, before the full
   bake-off harness exists, and decides whether OCR escalation is worth wiring at all.

Both are cheap, both change wave-1 shape if they fail, and both should run first.

_Dr. Mārcis Gasūns_
