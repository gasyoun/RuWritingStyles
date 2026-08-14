"""Refuse a release unless merged commits and git tags are the source of truth.

Two incidents made this check:

  * RuWritingStyles#128 had to delay the tag until after merge. Tagging an
    unmerged PR (or a stale local main) files later-landing changelog bullets
    under a released heading the tag does not contain (Uprava FINDINGS §300).
  * IndologyScholars#177 showed changelog headings drifting from the real tag
    sequence: a stray ``## [1.12.0]`` sat above a real ``v1.6.0`` tag, so a
    naive ``max(headings, tags)`` pick would have cut 1.12.1.

This script never creates, moves, or deletes a tag. It classifies the repo
and refuses the *decision* to release.

    python scripts/release_source_truth.py                 # print state + diff
    python scripts/release_source_truth.py --require-releaseable
    python scripts/release_source_truth.py --json
    python scripts/release_source_truth.py --repo PATH

Exit codes: 0 already-tagged / merged-untagged (and pre-merge/stale without
``--require-releaseable``) · 2 unmerged / not on origin default · 3 stale
local default · 4 sequence mismatch · 5 remote probe exhausted the 5-try cap.

Historical headings *below* the latest real tag that were never tagged (this
repo has many, from 1.0.0 through 2.10.5 plus 2.21.0) are reported, not
treated as sequence drift. They stay in the changelog; this check does not
rewrite history.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

CHANGELOG_NAMES = ("CHANGELOG.md", "changelog.md", "Changelog.md")
VERSION_H = re.compile(r"^##[ \t]+\[?v?(\d+\.\d+\.\d+)\]?", re.M | re.I)
TAG_VER = re.compile(r"^v?(\d+\.\d+\.\d+)$")
RESERVE_VER = re.compile(r"^reserve-v(\d+\.\d+\.\d+)$")
MAX_REMOTE_TRIES = 5

STATE_ALREADY_TAGGED = "already_tagged"
STATE_MERGED_UNTAGGED = "merged_untagged"
STATE_PRE_MERGE = "pre_merge"
STATE_STALE_BRANCH = "stale_branch"
STATE_SEQUENCE_MISMATCH = "sequence_mismatch"
STATE_REMOTE_EXHAUSTED = "remote_exhausted"

EXIT_OK = 0
EXIT_PRE_MERGE = 2
EXIT_STALE = 3
EXIT_MISMATCH = 4
EXIT_REMOTE = 5


class RemoteProbeError(RuntimeError):
    """``git ls-remote`` failed after the 5-try cap."""


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def ls_remote_with_retry(
    repo: Path,
    remote: str,
    ref: str,
    max_tries: int = MAX_REMOTE_TRIES,
    runner=None,
) -> str:
    """Return stdout of ``git ls-remote <remote> <ref>``.

    Transient failures retry up to ``max_tries`` (default 5) and then raise
    ``RemoteProbeError``. The runner is injectable so tests can prove the cap
    without touching a network or a real remote.
    """
    if max_tries < 1:
        raise ValueError("max_tries must be >= 1")
    run = runner or (lambda argv: run_git(argv, repo))
    last: subprocess.CompletedProcess | None = None
    argv = ["git", "ls-remote", "--exit-code", remote, ref]
    for _attempt in range(max_tries):
        last = run(argv)
        if last.returncode == 0 and last.stdout.strip():
            return last.stdout
    detail = ""
    if last is not None:
        detail = (last.stderr or last.stdout or "").strip()
    raise RemoteProbeError(
        f"git ls-remote {remote} {ref} failed after {max_tries} tries"
        + (f": {detail}" if detail else "")
    )


def parse_version(token: str) -> tuple[int, int, int]:
    a, b, c = token.split(".")
    return int(a), int(b), int(c)


def bump_candidates(version: str) -> set[str]:
    a, b, c = parse_version(version)
    return {
        f"{a}.{b}.{c + 1}",
        f"{a}.{b + 1}.0",
        f"{a + 1}.0.0",
    }


def is_one_step(previous: str, candidate: str) -> bool:
    return candidate in bump_candidates(previous)


def find_changelog(repo: Path) -> Path | None:
    for name in CHANGELOG_NAMES:
        path = repo / name
        if path.is_file():
            return path
    return None


def changelog_versions(text: str) -> list[str]:
    """Released ``## [x.y.z]`` tokens, first-seen order. ``[Unreleased]`` skipped."""
    seen: set[str] = set()
    out: list[str] = []
    for match in VERSION_H.finditer(text):
        ver = match.group(1)
        if ver in seen:
            continue
        seen.add(ver)
        out.append(ver)
    return out


def local_release_tags(repo: Path) -> list[str]:
    result = run_git(["git", "tag", "-l"], repo)
    tags: list[str] = []
    for line in result.stdout.splitlines():
        raw = line.strip()
        if RESERVE_VER.match(raw):
            continue
        match = TAG_VER.match(raw)
        if match:
            tags.append(match.group(1))
    return tags


def default_branch_ref(repo: Path, remote: str) -> str:
    result = run_git(
        ["git", "symbolic-ref", "--quiet", f"refs/remotes/{remote}/HEAD"],
        repo,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    for name in ("main", "master"):
        probe = run_git(["git", "rev-parse", "--verify", f"{remote}/{name}"], repo)
        if probe.returncode == 0:
            return f"refs/remotes/{remote}/{name}"
    return f"refs/remotes/{remote}/main"


def sha_of(repo: Path, rev: str) -> str | None:
    result = run_git(["git", "rev-parse", "--verify", rev], repo)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def current_branch(repo: Path) -> str:
    result = run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo)
    return (result.stdout or "").strip() or "HEAD"


def heading_tag_diff(headings: list[str], tags: list[str]) -> dict[str, list[str]]:
    hset, tset = set(headings), set(tags)
    return {
        "headings_without_tag": sorted(hset - tset, key=parse_version),
        "tags_without_heading": sorted(tset - hset, key=parse_version),
    }


@dataclass
class ReleaseState:
    state: str
    repo: str
    branch: str
    head_sha: str | None
    origin_sha: str | None
    latest_tag: str | None
    latest_heading: str | None
    untagged_candidate: str | None
    headings_without_tag: list[str] = field(default_factory=list)
    tags_without_heading: list[str] = field(default_factory=list)
    historical_orphans: list[str] = field(default_factory=list)
    refusal: str | None = None
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        return asdict(self)


def classify_sequence(
    headings: list[str],
    tags: list[str],
) -> tuple[str, str | None, str | None, list[str], str | None]:
    """Return (state, latest_heading, untagged_candidate, historical_orphans, refusal)."""
    latest_tag = max(tags, key=parse_version) if tags else None
    latest_heading = headings[0] if headings else None
    if headings:
        latest_heading = max(headings, key=parse_version)

    if not tags and not headings:
        return STATE_ALREADY_TAGGED, None, None, [], None

    if tags and not headings:
        return (
            STATE_SEQUENCE_MISMATCH,
            None,
            None,
            [],
            "tags exist but changelog has no ## [x.y.z] headings",
        )

    if not tags and headings:
        if len(headings) == 1:
            return STATE_MERGED_UNTAGGED, latest_heading, latest_heading, [], None
        extra = sorted(set(headings) - {latest_heading}, key=parse_version)
        return (
            STATE_SEQUENCE_MISMATCH,
            latest_heading,
            None,
            extra,
            "several changelog headings and no tags — cannot pick a sequence",
        )

    assert latest_tag is not None
    above = [h for h in headings if parse_version(h) > parse_version(latest_tag)]
    orphans = [
        h for h in headings
        if h not in tags and parse_version(h) <= parse_version(latest_tag)
    ]
    if latest_heading is not None and parse_version(latest_heading) < parse_version(latest_tag):
        return (
            STATE_SEQUENCE_MISMATCH,
            latest_heading,
            None,
            orphans,
            f"latest heading [{latest_heading}] is behind latest tag v{latest_tag}",
        )
    if len(above) > 1:
        return (
            STATE_SEQUENCE_MISMATCH,
            latest_heading,
            None,
            orphans,
            "more than one changelog heading is newer than latest tag "
            f"v{latest_tag}: {', '.join(sorted(above, key=parse_version))}",
        )
    if len(above) == 1:
        candidate = above[0]
        if not is_one_step(latest_tag, candidate):
            return (
                STATE_SEQUENCE_MISMATCH,
                latest_heading,
                None,
                orphans,
                f"heading [{candidate}] is not a one-step bump from tag v{latest_tag} "
                f"(allowed: {', '.join(sorted(bump_candidates(latest_tag)))})",
            )
        return STATE_MERGED_UNTAGGED, latest_heading, candidate, orphans, None
    return STATE_ALREADY_TAGGED, latest_heading, None, orphans, None


def inspect_release_state(
    repo: Path,
    remote: str = "origin",
    max_tries: int = MAX_REMOTE_TRIES,
    ls_remote=None,
) -> ReleaseState:
    repo = repo.resolve()
    changelog = find_changelog(repo)
    headings = changelog_versions(changelog.read_text(encoding="utf-8")) if changelog else []
    tags = local_release_tags(repo)
    diff = heading_tag_diff(headings, tags)
    branch = current_branch(repo)
    head_sha = sha_of(repo, "HEAD")

    origin_sha = None
    remote_error: str | None = None
    default_ref = default_branch_ref(repo, remote)
    default_name = default_ref.rsplit("/", 1)[-1]
    try:
        raw = ls_remote_with_retry(
            repo, remote, default_name, max_tries=max_tries, runner=ls_remote,
        )
        origin_sha = raw.split()[0]
    except RemoteProbeError as exc:
        # Fall back to the fetched remote-tracking ref so offline tests still
        # classify merge state. The 5-try exhaustion is recorded either way.
        remote_error = str(exc)
        origin_sha = sha_of(repo, f"{remote}/{default_name}")
        if origin_sha is None:
            seq_state, latest_heading, candidate, orphans, refusal = classify_sequence(
                headings, tags,
            )
            return ReleaseState(
                state=STATE_REMOTE_EXHAUSTED,
                repo=str(repo),
                branch=branch,
                head_sha=head_sha,
                origin_sha=None,
                latest_tag=max(tags, key=parse_version) if tags else None,
                latest_heading=latest_heading,
                untagged_candidate=candidate,
                headings_without_tag=diff["headings_without_tag"],
                tags_without_heading=diff["tags_without_heading"],
                historical_orphans=orphans,
                refusal=remote_error,
                notes=[f"sequence_without_remote={seq_state}", f"sequence_note={refusal}"],
            )

    on_default = branch == default_name
    merged = bool(head_sha and origin_sha and head_sha == origin_sha)
    stale = bool(
        on_default
        and head_sha
        and origin_sha
        and head_sha != origin_sha
        and run_git(["git", "merge-base", "--is-ancestor", "HEAD", f"{remote}/{default_name}"], repo).returncode == 0
    )

    seq_state, latest_heading, candidate, orphans, seq_refusal = classify_sequence(
        headings, tags,
    )

    notes: list[str] = []
    if remote_error:
        notes.append(f"ls-remote failed, used {remote}/{default_name}: {remote_error}")
    if orphans:
        notes.append(
            f"{len(orphans)} historical heading(s) have no tag and sit at or below "
            f"latest tag — reported, not treated as sequence drift"
        )

    if seq_state == STATE_SEQUENCE_MISMATCH:
        state = STATE_SEQUENCE_MISMATCH
        refusal = seq_refusal
    elif stale:
        state = STATE_STALE_BRANCH
        refusal = (
            f"local {default_name} {head_sha[:12] if head_sha else '?'} is behind "
            f"{remote}/{default_name} {origin_sha[:12] if origin_sha else '?'}; "
            "fetch and fast-forward before any tag or gh release"
        )
    elif not merged:
        state = STATE_PRE_MERGE
        refusal = (
            f"HEAD {head_sha[:12] if head_sha else '?'} on {branch} is not "
            f"{remote}/{default_name} {origin_sha[:12] if origin_sha else '?'}; "
            "refuse tag/release on an unmerged PR or a local-only commit "
            "(RuWritingStyles#128 / FINDINGS §300)"
        )
    else:
        state = seq_state
        if state == STATE_ALREADY_TAGGED:
            refusal = (
                f"v{latest_heading} is already tagged; refuse re-tag / tag mutation"
                if latest_heading
                else "nothing to tag"
            )
        elif state == STATE_MERGED_UNTAGGED:
            refusal = None
            notes.append(
                f"merged at {origin_sha[:12]}; ready to tag v{candidate} in a "
                "separate explicit action — this check will not create it"
            )
        else:
            refusal = seq_refusal

    return ReleaseState(
        state=state,
        repo=str(repo),
        branch=branch,
        head_sha=head_sha,
        origin_sha=origin_sha,
        latest_tag=max(tags, key=parse_version) if tags else None,
        latest_heading=latest_heading,
        untagged_candidate=candidate,
        headings_without_tag=diff["headings_without_tag"],
        tags_without_heading=diff["tags_without_heading"],
        historical_orphans=orphans,
        refusal=refusal,
        notes=notes,
    )


def format_report(info: ReleaseState) -> str:
    lines = [
        f"state: {info.state}",
        f"repo: {info.repo}",
        f"branch: {info.branch}",
        f"HEAD: {info.head_sha or '(none)'}",
        f"origin default: {info.origin_sha or '(none)'}",
        f"latest tag: {info.latest_tag or '(none)'}",
        f"latest heading: {info.latest_heading or '(none)'}",
        f"untagged candidate: {info.untagged_candidate or '(none)'}",
    ]
    if info.headings_without_tag:
        lines.append("changelog headings not on a tag:")
        for ver in info.headings_without_tag:
            kind = "historical orphan" if ver in info.historical_orphans else "sequence"
            lines.append(f"  - {ver}  ({kind})")
    if info.tags_without_heading:
        lines.append("tags with no changelog heading:")
        for ver in info.tags_without_heading:
            lines.append(f"  - v{ver}")
    if not info.headings_without_tag and not info.tags_without_heading:
        lines.append("heading/tag diff: (empty)")
    for note in info.notes:
        lines.append(f"note: {note}")
    if info.refusal:
        lines.append(f"refusal: {info.refusal}")
    return "\n".join(lines)


def exit_code(info: ReleaseState, require_releaseable: bool) -> int:
    if info.state == STATE_REMOTE_EXHAUSTED:
        return EXIT_REMOTE
    if info.state == STATE_SEQUENCE_MISMATCH:
        return EXIT_MISMATCH
    if require_releaseable:
        if info.state == STATE_STALE_BRANCH:
            return EXIT_STALE
        if info.state == STATE_PRE_MERGE:
            return EXIT_PRE_MERGE
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="repository root (default: cwd)")
    parser.add_argument("--remote", default="origin")
    parser.add_argument(
        "--max-tries",
        type=int,
        default=MAX_REMOTE_TRIES,
        help=f"ls-remote retry cap (default {MAX_REMOTE_TRIES})",
    )
    parser.add_argument(
        "--require-releaseable",
        action="store_true",
        help="exit non-zero on unmerged PR or stale local default (release gate)",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    if not (repo / ".git").exists() and not (repo / ".git").is_file():
        print(f"[FATAL] not a git repo: {repo}", file=sys.stderr)
        return 2

    try:
        info = inspect_release_state(
            repo, remote=args.remote, max_tries=args.max_tries,
        )
    except RemoteProbeError as exc:
        print(f"[FATAL] {exc}", file=sys.stderr)
        return EXIT_REMOTE

    if args.json:
        print(json.dumps(info.to_json(), ensure_ascii=False, indent=2))
    else:
        print(format_report(info))
    return exit_code(info, args.require_releaseable)


if __name__ == "__main__":
    raise SystemExit(main())
