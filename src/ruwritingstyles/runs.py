"""Run artifact creation."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from pathlib import Path

from .config import Manifest, ModelPolicy
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
    (run_dir / "report.md").write_text(
        _report(
            run_id=actual_run_id,
            input_path=input_path,
            repo_root=repo_root,
            segments=segments,
            manifest=manifest,
            model_policy=model_policy,
        ),
        encoding="utf-8",
    )
    return run_dir


def _repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _report(
    *,
    run_id: str,
    input_path: Path,
    repo_root: Path,
    segments: list[Segment],
    manifest: Manifest,
    model_policy: ModelPolicy,
) -> str:
    counts: dict[str, int] = {}
    for segment in segments:
        counts[segment.segment_type] = counts.get(segment.segment_type, 0) + 1

    count_lines = "\n".join(f"- {key}: {value}" for key, value in sorted(counts.items()))
    style_lines = "\n".join(f"- `{style_id}`" for style_id in manifest.mvp_style_ids)

    return f"""# Run {run_id}

## Input

- Source: `{_repo_relative(repo_root, input_path)}`
- Segment count: {len(segments)}

## Segment Types

{count_lines or "- none: 0"}

## MVP Styles

{style_lines or "- none"}

## Default Model Policy

- Provider: `{model_policy.default_provider}`
- Model: `{model_policy.default_model}`
- Reasoning: `{model_policy.default_reasoning}`
- Speed: `{model_policy.default_speed}`

## Next Step

Use `segments.json` as the stable input for style reviewers. The first implementation layer only prepares run artifacts; review, council, synthesis, and verification will be added in later steps.
"""
