"""Revision diff artifacts."""

from __future__ import annotations

from difflib import unified_diff
from pathlib import Path


def write_revision_diff(run_dir: Path) -> Path:
    """Write a unified diff between normalized.md and revised.md."""

    run_dir = run_dir.resolve()
    normalized_path = run_dir / "normalized.md"
    revised_path = run_dir / "revised.md"
    if not normalized_path.exists():
        raise FileNotFoundError(f"missing {normalized_path}")
    if not revised_path.exists():
        raise FileNotFoundError(f"missing {revised_path}; run `rws revise --execute` first")

    diff_path = run_dir / "revision.diff"
    normalized = normalized_path.read_text(encoding="utf-8").splitlines(keepends=True)
    revised = revised_path.read_text(encoding="utf-8").splitlines(keepends=True)
    diff_lines = unified_diff(
        normalized,
        revised,
        fromfile="normalized.md",
        tofile="revised.md",
        lineterm="",
    )
    diff_path.write_text("\n".join(line.rstrip("\n") for line in diff_lines), encoding="utf-8")
    return diff_path
