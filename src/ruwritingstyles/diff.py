"""Revision diff artifacts."""

from __future__ import annotations

from difflib import unified_diff
import re
from pathlib import Path
from typing import Any


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


def calculate_revision_diff_metrics(run_dir: Path) -> dict[str, Any]:
    """Calculate coarse diff magnitude metrics for normalized.md -> revised.md."""

    run_dir = run_dir.resolve()
    normalized_text = (run_dir / "normalized.md").read_text(encoding="utf-8")
    revised_text = (run_dir / "revised.md").read_text(encoding="utf-8")
    normalized_lines = normalized_text.splitlines()
    revised_lines = revised_text.splitlines()
    diff_lines = list(
        unified_diff(
            normalized_lines,
            revised_lines,
            fromfile="normalized.md",
            tofile="revised.md",
            lineterm="",
        )
    )
    added_lines = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    removed_lines = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
    changed_line_count = added_lines + removed_lines
    line_baseline = max(1, len(normalized_lines) + len(revised_lines))
    original_words = _word_count(normalized_text)
    revised_words = _word_count(revised_text)
    return {
        "original_lines": len(normalized_lines),
        "revised_lines": len(revised_lines),
        "added_lines": added_lines,
        "removed_lines": removed_lines,
        "changed_line_count": changed_line_count,
        "changed_line_ratio": round(changed_line_count / line_baseline, 6),
        "original_chars": len(normalized_text),
        "revised_chars": len(revised_text),
        "char_delta_ratio": round(abs(len(revised_text) - len(normalized_text)) / max(1, len(normalized_text)), 6),
        "original_words": original_words,
        "revised_words": revised_words,
        "word_delta_ratio": round(abs(revised_words - original_words) / max(1, original_words), 6),
    }


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text, flags=re.UNICODE))
