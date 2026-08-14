"""Release-state matrix for scripts/release_source_truth.py (H2580).

Three fixture states plus the IndologyScholars#177 mismatch. Every case
snapshots ``git tag -l`` before and after so a regression that starts
mutating tags fails here rather than on a real repo.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from release_source_truth import (  # noqa: E402
    EXIT_MISMATCH,
    EXIT_PRE_MERGE,
    EXIT_REMOTE,
    EXIT_STALE,
    MAX_REMOTE_TRIES,
    RemoteProbeError,
    STATE_ALREADY_TAGGED,
    STATE_MERGED_UNTAGGED,
    STATE_PRE_MERGE,
    STATE_SEQUENCE_MISMATCH,
    STATE_STALE_BRANCH,
    inspect_release_state,
    ls_remote_with_retry,
    main,
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _tags(repo: Path) -> list[str]:
    result = subprocess.run(
        ["git", "tag", "-l"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return sorted(line.strip() for line in result.stdout.splitlines() if line.strip())


def _seed_pair(tmp_path: Path, name: str, changelog: str, tag: str | None) -> tuple[Path, Path]:
    """Bare origin + working clone on main, optional annotated-style lightweight tag."""
    origin = tmp_path / f"{name}.git"
    work = tmp_path / name
    subprocess.run(
        ["git", "init", "--bare", "-q", "-b", "main", str(origin)],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    _git(tmp_path, "clone", "-q", str(origin), str(work))
    _git(work, "config", "user.email", "h2580@test")
    _git(work, "config", "user.name", "H2580")
    _write(work / "changelog.md", changelog)
    _git(work, "add", "changelog.md")
    _git(work, "commit", "-q", "-m", "seed")
    if tag:
        _git(work, "tag", tag)
    _git(work, "push", "-q", "origin", "HEAD:main")
    if tag:
        _git(work, "push", "-q", "origin", tag)
    return origin, work


CHANGELOG_TAGGED = (
    "# Changelog\n\n"
    "## [Unreleased]\n\n"
    "## [1.0.0] - 2026-01-01\n\n"
    "- birth\n"
)

CHANGELOG_NEXT = (
    "# Changelog\n\n"
    "## [Unreleased]\n\n"
    "## [1.0.1] - 2026-01-02\n\n"
    "- next\n\n"
    "## [1.0.0] - 2026-01-01\n\n"
    "- birth\n"
)

CHANGELOG_STRAY = (
    "# Changelog\n\n"
    "## [Unreleased]\n\n"
    "## [1.12.0] - 2026-06-10\n\n"
    "- stray heading\n\n"
    "## [1.6.0] - 2026-08-06\n\n"
    "- real\n"
)


def test_pre_merge_refuses_release_and_does_not_mutate_tags(tmp_path: Path) -> None:
    _origin, work = _seed_pair(tmp_path, "pre", CHANGELOG_TAGGED, "v1.0.0")
    _git(work, "checkout", "-q", "-b", "feature/unmerged")
    _write(work / "changelog.md", CHANGELOG_NEXT)
    _git(work, "add", "changelog.md")
    _git(work, "commit", "-q", "-m", "unmerged heading")
    before = _tags(work)

    info = inspect_release_state(work)
    assert info.state == STATE_PRE_MERGE
    assert info.refusal is not None
    assert "unmerged" in info.refusal.lower() or "not origin/main" in info.refusal

    rc = main(["--repo", str(work), "--require-releaseable"])
    assert rc == EXIT_PRE_MERGE
    assert _tags(work) == before


def test_merged_untagged_is_ready_and_does_not_create_a_tag(tmp_path: Path) -> None:
    _origin, work = _seed_pair(tmp_path, "untagged", CHANGELOG_TAGGED, "v1.0.0")
    _write(work / "changelog.md", CHANGELOG_NEXT)
    _git(work, "add", "changelog.md")
    _git(work, "commit", "-q", "-m", "promote 1.0.1")
    _git(work, "push", "-q", "origin", "HEAD:main")
    before = _tags(work)
    assert "v1.0.1" not in before

    info = inspect_release_state(work)
    assert info.state == STATE_MERGED_UNTAGGED
    assert info.untagged_candidate == "1.0.1"
    assert info.latest_tag == "1.0.0"

    rc = main(["--repo", str(work), "--require-releaseable"])
    assert rc == 0
    assert _tags(work) == before
    assert "v1.0.1" not in _tags(work)


def test_already_tagged_refuses_retag_and_does_not_mutate_tags(tmp_path: Path) -> None:
    _origin, work = _seed_pair(tmp_path, "tagged", CHANGELOG_TAGGED, "v1.0.0")
    before = _tags(work)

    info = inspect_release_state(work)
    assert info.state == STATE_ALREADY_TAGGED
    assert info.latest_tag == "1.0.0"
    assert info.refusal is not None
    assert "already tagged" in info.refusal
    assert "refuse re-tag" in info.refusal

    rc = main(["--repo", str(work), "--require-releaseable"])
    assert rc == 0
    assert _tags(work) == before


def test_stale_local_default_refuses_and_does_not_mutate_tags(tmp_path: Path) -> None:
    origin, work = _seed_pair(tmp_path, "stale", CHANGELOG_TAGGED, "v1.0.0")
    other = tmp_path / "stale-other"
    _git(tmp_path, "clone", "-q", str(origin), str(other))
    _git(other, "config", "user.email", "h2580@test")
    _git(other, "config", "user.name", "H2580")
    _write(other / "extra.txt", "ahead\n")
    _git(other, "add", "extra.txt")
    _git(other, "commit", "-q", "-m", "origin moved")
    _git(other, "push", "-q", "origin", "HEAD:main")
    before = _tags(work)

    info = inspect_release_state(work)
    assert info.state == STATE_STALE_BRANCH
    assert info.refusal is not None
    assert "behind" in info.refusal

    rc = main(["--repo", str(work), "--require-releaseable"])
    assert rc == EXIT_STALE
    assert _tags(work) == before


def test_stale_changelog_heading_vs_tag_is_a_clear_diff(tmp_path: Path) -> None:
    """IndologyScholars#177 shape: stray [1.12.0] above a real v1.6.0 tag."""
    _origin, work = _seed_pair(tmp_path, "drift", CHANGELOG_STRAY, "v1.6.0")
    before = _tags(work)

    info = inspect_release_state(work)
    assert info.state == STATE_SEQUENCE_MISMATCH
    assert info.latest_tag == "1.6.0"
    assert "1.12.0" in info.headings_without_tag
    assert info.refusal is not None
    assert "1.12.0" in info.refusal
    assert "1.6.0" in info.refusal
    assert "1.6.1" in info.refusal

    report = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "release_source_truth.py"),
         "--repo", str(work)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert report.returncode == EXIT_MISMATCH
    assert "1.12.0" in report.stdout
    assert "v1.6.0" in report.stdout or "1.6.0" in report.stdout
    assert "not a one-step bump" in report.stdout
    assert _tags(work) == before


def test_historical_orphan_below_latest_tag_is_not_sequence_drift(tmp_path: Path) -> None:
    changelog = (
        "# Changelog\n\n"
        "## [Unreleased]\n\n"
        "## [1.1.0] - 2026-02-01\n\n"
        "- tagged\n\n"
        "## [1.0.0] - 2026-01-01\n\n"
        "- never tagged, older than latest tag\n"
    )
    _origin, work = _seed_pair(tmp_path, "orphan", changelog, "v1.1.0")
    info = inspect_release_state(work)
    assert info.state == STATE_ALREADY_TAGGED
    assert info.historical_orphans == ["1.0.0"]
    assert main(["--repo", str(work)]) == 0


def test_five_try_cap_on_ls_remote(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def failing(_argv: list[str]):
        calls.append(list(_argv))
        return subprocess.CompletedProcess(
            args=_argv, returncode=128, stdout="", stderr="fatal: could not read",
        )

    with pytest.raises(RemoteProbeError, match="after 5 tries"):
        ls_remote_with_retry(tmp_path, "origin", "main", max_tries=5, runner=failing)
    assert len(calls) == MAX_REMOTE_TRIES == 5

    calls.clear()

    def always_fail(_argv: list[str]):
        calls.append(list(_argv))
        return subprocess.CompletedProcess(
            args=_argv, returncode=128, stdout="", stderr="fatal: still down",
        )

    with pytest.raises(RemoteProbeError):
        ls_remote_with_retry(tmp_path, "origin", "main", max_tries=5, runner=always_fail)
    assert len(calls) == 5


def test_pre_merge_without_require_flag_does_not_fail_ci(tmp_path: Path) -> None:
    _origin, work = _seed_pair(tmp_path, "pr", CHANGELOG_TAGGED, "v1.0.0")
    _git(work, "checkout", "-q", "-b", "feature/docs")
    _write(work / "note.txt", "n\n")
    _git(work, "add", "note.txt")
    _git(work, "commit", "-q", "-m", "docs")
    assert main(["--repo", str(work)]) == 0
    assert main(["--repo", str(work), "--require-releaseable"]) == EXIT_PRE_MERGE
    assert inspect_release_state(work).state == STATE_PRE_MERGE


def test_script_never_invokes_git_tag_mutate() -> None:
    """Static: list tags only. No create / force / delete / push-tags path."""
    source = (REPO_ROOT / "scripts" / "release_source_truth.py").read_text(encoding="utf-8")
    assert '["git", "tag", "-l"]' in source
    assert source.count('["git", "tag"') == 1
    assert "tag -f" not in source
    assert "tag -d" not in source
    assert "--delete" not in source
    assert "git push" not in source
    assert '["git", "push"' not in source
