"""Run artifact creation."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from pathlib import Path
from typing import Any

from .config import Manifest, ModelPolicy
from .html_summary import write_html_report
from .report import write_run_report
from .segment import Segment


def make_run_id(input_path: Path, now: datetime | None = None) -> str:
    timestamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%d-%H%M%S")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", input_path.stem).strip("-").lower() or "document"
    return f"{timestamp}-{slug}"


def create_prepare_run(
    *,
    repo_root: Path,
    input_path: Path,
    original_text: str,
    normalized_text: str,
    segments: list[Segment],
    manifest: Manifest,
    model_policy: ModelPolicy,
    run_id: str | None = None,
) -> Path:
    actual_run_id = run_id or make_run_id(input_path)
    run_dir = repo_root / "runs" / actual_run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    (run_dir / "original.md").write_text(original_text, encoding="utf-8")
    (run_dir / "normalized.md").write_text(normalized_text, encoding="utf-8")
    (run_dir / "segments.json").write_text(
        json.dumps(
            {
                "run_id": actual_run_id,
                "input_path": _repo_relative(repo_root, input_path),
                "segment_count": len(segments),
                "segments": [segment.to_json() for segment in segments],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    write_run_report(run_dir)
    write_html_report(run_dir)
    return run_dir


def list_runs(repo_root: Path) -> list[str]:
    runs_dir = repo_root / "runs"
    if not runs_dir.exists():
        return []
    # Return directory names, sorted by creation time (newest first)
    dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
    dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return [d.name for d in dirs]


def load_run_artifact(run_dir: Path, filename: str) -> dict[str, Any]:
    path = run_dir / filename
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)
