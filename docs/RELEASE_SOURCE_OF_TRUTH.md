# Release source of truth

_Created: 14-08-2026 · Last updated: 14-08-2026_

Merged commits on the default branch, and the real `vX.Y.Z` git tags, are the
release sequence. Changelog headings are a report of that sequence, not a
source that can outvote it.

This is the operator check for [H2580 (Grok 4.6) — RuWritingStyles release source of truth](https://github.com/gasyoun/Uprava/blob/main/handoffs/H2580-Grok_RuWritingStyles_release-source-truth_11.08.26.md).
It exists because two release cuts already had to work around the opposite
assumption:

- [RuWritingStyles#128](https://github.com/gasyoun/RuWritingStyles/pull/128) delayed the tag until after merge. Tagging an unmerged PR (or a stale local `main`) files later-landing bullets under a released heading the tag does not contain ([Uprava FINDINGS §300](https://github.com/gasyoun/Uprava/blob/main/FINDINGS.md)).
- [IndologyScholars#177](https://github.com/gasyoun/IndologyScholars/pull/177) had changelog headings that had drifted from the real tags — a stray `## [1.12.0]` sat above a real `v1.6.0`. `/cut-release` continues the **tag** sequence, not the heading sequence.

The check never creates, moves, or deletes a tag. A real version cut is a
separate explicit action after this gate is green.

## Commands

From a checkout of [gasyoun/RuWritingStyles](https://github.com/gasyoun/RuWritingStyles):

```text
python scripts/release_source_truth.py
python scripts/release_source_truth.py --require-releaseable
python scripts/release_source_truth.py --json
python -m pytest -q tests/test_release_source_truth.py
```

`--require-releaseable` is the release gate. The default run is safe on a
pull-request branch: it still fails on a sequence-breaking heading, but it
does not treat "this branch is not `origin/main`" as a CI failure.

Then, and only then, the org cutter (never this script) may promote and tag,
off freshly-fetched `origin/main`:

```text
python C:/Users/user/Documents/GitHub/Uprava/tools/cut_release.py .
python C:/Users/user/Documents/GitHub/Uprava/tools/cut_release.py . --reserve
python C:/Users/user/Documents/GitHub/Uprava/tools/cut_release.py . --version X.Y.Z --apply
```

Do **not** pass `--tag` or `--gh-release` from a feature branch, from a local
`main` that is behind `origin/main`, or while this check prints
`sequence_mismatch`.

## State matrix

| State | Meaning | `--require-releaseable` | Default |
|---|---|---|---|
| `pre_merge` | `HEAD` is not `origin/<default>` (unmerged PR, unpushed local commit) | exit 2 | exit 0 |
| `stale_branch` | local default is behind `origin/<default>` (`git ls-remote`) | exit 3 | exit 0 |
| `merged_untagged` | `HEAD` equals origin default; exactly one heading is a one-step bump past the latest real tag | exit 0 (ready; this script still does not tag) | exit 0 |
| `already_tagged` | latest heading equals latest tag | exit 0 (prints "refuse re-tag") | exit 0 |
| `sequence_mismatch` | a heading newer than the latest tag is not a one-step bump, or the changelog is behind the tags | exit 4 | exit 4 |
| `remote_exhausted` | `git ls-remote` failed five times | exit 5 | exit 5 |

A **one-step bump** from `vA.B.C` is only `A.B.C+1`, `A.B+1.0`, or `A+1.0.0`.
That is what turns the IndologyScholars `1.6.0` → stray `1.12.0` heading into
a refusal instead of a `1.12.1` cut.

`git ls-remote` is retried at most **five** times and then fails loudly. The
cap is `--max-tries` (default 5). There is no sixth probe and no fallback
that invents a SHA.

## Heading / tag diff

The report lists every `## [x.y.z]` with no matching `vX.Y.Z` tag, and every
release tag with no heading. Headings **at or below** the latest real tag
that were never tagged (this repo has a long pre-`v2.11.0` tail, plus
`2.21.0`) are labelled `historical orphan`. They stay in
[changelog.md](https://github.com/gasyoun/RuWritingStyles/blob/main/changelog.md).
This check will not delete them and will not back-fill tags for them.

`reserve-vX.Y.Z` refs from [cut_release.py](https://github.com/gasyoun/Uprava/blob/main/tools/cut_release.py)
are ignored. They are locks, not releases.

## Sample refusal (unmerged PR)

```text
state: pre_merge
repo: C:\Users\user\Documents\GitHub\RuWritingStyles
branch: h2580-release-source-truth-33884
HEAD: <feature-sha>
origin default: <origin/main-sha>
latest tag: 2.25.1
latest heading: 2.25.1
untagged candidate: (none)
changelog headings not on a tag:
  - 2.21.0  (historical orphan)
  - 2.10.5  (historical orphan)
  ...
refusal: HEAD <feature-sha> on h2580-release-source-truth-33884 is not origin/main <origin-sha>; refuse tag/release on an unmerged PR or a local-only commit (RuWritingStyles#128 / FINDINGS §300)
```

## Tests

[`tests/test_release_source_truth.py`](https://github.com/gasyoun/RuWritingStyles/blob/main/tests/test_release_source_truth.py)
builds throwaway git remotes. It never tags this repository. The matrix is:

1. pre-merge → exit 2 under `--require-releaseable`, tags unchanged
2. merged-but-untagged → exit 0, candidate printed, no `vX.Y.Z` created
3. already-tagged → exit 0, "refuse re-tag", tags unchanged
4. stale local default → exit 3, tags unchanged
5. stray heading `1.12.0` above tag `v1.6.0` → exit 4, diff names both versions
6. `ls-remote` failing five times → `RemoteProbeError`, sixth call not made

_Dr. Mārcis Gasūns_
