_Created: 20-09-2026 · Last updated: 20-09-2026_

# W2.4 bounded harvest — run report and recovery provenance

**Status: RUN IN PROGRESS** — this file is finalised when the run lands. If you are a
successor session reading this before the "Final numbers" section exists, read
"Recovery provenance" first: the run may still be executing detached.

## Scope (D20)

The capped harvest across every `include` journal of
[knowledge/rcsi/catalogue.json](https://github.com/gasyoun/RuWritingStyles/blob/main/knowledge/rcsi/catalogue.json)
— **61 journals**, cap **50 accepted articles** each (D20 "about 50 articles each"),
one request per second, HTML cached on disk, texts + sidecars written to the private
corpus repo, committed and pushed in the same pass. Enumeration is itself bounded:
`max_records=300` OAI records per journal (D17 default, 20-09-2026 — 3 OAI pages;
without it a large mostly-uncertain archive enumerates for hours while writing
nothing). Driver: [tools/run_w24_bounded_harvest.py](https://github.com/gasyoun/RuWritingStyles/blob/main/tools/run_w24_bounded_harvest.py),
resumable — `already-pass` sidecars are skipped, `remaining = cap - existing`.

## Recovery provenance (why this unit has two sessions in it)

1. 14:31 local — drain window 1 (driver PID 21508) claimed A06, worked in worktree
   `RuWritingStyles-rd-a06-21508` (branch `w24-bounded-harvest`), committed the
   selection gate + driver (`e8578f7`), fixed the OAI article-id bug, launched the
   bounded harvest detached (`nohup python tools/run_w24_bounded_harvest.py`,
   PID 12088) at 15:19.
2. 16:32 local — window 1 hit its 7200 s driver timeout; the pick was released
   `fail_soft`. The agent session died with uncommitted edits (the article-id fix,
   `--max-records`, docs); **the detached harvester kept running** and kept writing
   into the shared private corpus repo `~/Documents/GitHub/RuWritingStyles-corpus`.
3. 16:52 local — window 2 (this session, Claude/c1, worktree `RuWritingStyles-rd-a06-14592`)
   re-claimed A06 per the ledger, adopted the orphaned run, and landed the dead
   session's committed + uncommitted code (branch `a06-w24-bounded-harvest`:
   `e8578f7` fast-forwarded + the run-tail commit).

Rules honoured: never a second concurrent harvester (D20 pins one request per second
— a second runner would double the platform-side rate); the corpus repo is committed
and pushed only after the harvester exits, so no file is mid-write at commit time.

## Final numbers

(to be filled from the driver JSON + corpus sidecars when the run completes —
counts, quarantine size, per-journal extraction-source split, failures and gaps.)

## Landing checklist (for this session or a successor)

Branch `a06-w24-bounded-harvest` (pushed) already carries: the sibling's
committed selection gate + driver (`e8578f7`), the run-tail commit
(`--max-records` D17 bound + OAI article-id fix), the report skeleton +
generator + tests, and a root `conftest.py` fix for a full-suite-only
module-cache failure (stale editable install pointing at the main tree —
432 passed / 106 subtests with the fix). Gates already green on the branch:
compileall, validate_project, ci-eval-gate, full pytest.

When the driver JSON gains a `"finished"` key (`runs/rcsi-harvest/
w24-driver-20260920T151922.json` in `RuWritingStyles-rd-a06-21508`) and the
console log prints `driver finished`:

1. Re-run the one failed journal (`1993-1778`) from this worktree:
   `python -m src.ruwritingstyles.cli journal-harvest 1993-1778 --limit 50`
   (warm cache makes it cheap; if it fails again, keep it as an honest gap).
2. Copy the sibling worktree's final `knowledge/bibliography.json` and
   `knowledge/rcsi/article_review_queue.json` into this branch (they are the
   harvester's repo_root and still growing until the run ends).
3. Corpus repo `RuWritingStyles-corpus`: fast-forward main to origin, stage
   `PDFtoTXT/` new files + `quarantine/`, commit (provenance message), push.
4. `python tools/build_w24_harvest_report.py --driver <sibling json> --out
   fragment.md`; paste into "Final numbers" above; delete the skeleton
   "Status: RUN IN PROGRESS" line.
5. Tick W2.4 in the roadmap (✅ DONE pattern with PR link), add the
   `changelog_queue/` entry, update `.ai_state.md`, re-run the four python
   gates, open the PR, merge when green.
6. Clean up: remove this worktree's `.pytest-tmp`, then after merge
   `git worktree remove` both `RuWritingStyles-rd-a06-14592` and (after
   salvaging nothing else) `RuWritingStyles-rd-a06-21508`.

_Dr. Mārcis Gasūns_
