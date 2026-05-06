"""Export run artifacts into a portable bundle."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from .html_summary import write_html_report
from .report import write_run_report


def export_run_bundle(run_dir: Path, output_path: Path | None = None) -> Path:
    """Create a ZIP bundle with the stable artifacts for a run."""

    run_dir = run_dir.resolve()
    if not run_dir.exists():
        raise FileNotFoundError(f"missing run directory {run_dir}")

    report_path = write_run_report(run_dir)
    html_path = write_html_report(run_dir)
    run_id = _run_id(run_dir)
    bundle_path = (output_path or (run_dir / f"{run_id}-bundle.zip")).resolve()
    bundle_path.parent.mkdir(parents=True, exist_ok=True)

    files = _bundle_files(run_dir, report_path, html_path)
    manifest = {
        "run_id": run_id,
        "artifact_count": len(files),
        "artifacts": [_archive_name(run_id, run_dir, path) for path in files],
    }

    with ZipFile(bundle_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(f"{run_id}/bundle-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        for path in files:
            archive.write(path, _archive_name(run_id, run_dir, path))

    return bundle_path


def _bundle_files(run_dir: Path, report_path: Path, html_path: Path) -> list[Path]:
    candidates = [
        run_dir / "original.md",
        run_dir / "normalized.md",
        run_dir / "segments.json",
        report_path,
        html_path,
        run_dir / "provider.log.jsonl",
        run_dir / "eval-result.json",
        run_dir / "revised.md",
        run_dir / "revision.diff",
        run_dir / "council.json",
        run_dir / "revision.json",
        run_dir / "verification.json",
        run_dir / "council.prompt.md",
        run_dir / "revision.prompt.md",
        run_dir / "verification.prompt.md",
    ]
    review_dir = run_dir / "reviews"
    candidates.extend(sorted(review_dir.glob("*.review.json")))
    candidates.extend(sorted(review_dir.glob("*.prompt.md")))
    return [path for path in candidates if path.exists()]


def _run_id(run_dir: Path) -> str:
    segments_path = run_dir / "segments.json"
    if segments_path.exists():
        data = _load_json(segments_path)
        if isinstance(data.get("run_id"), str) and data["run_id"]:
            return data["run_id"]
    return run_dir.name


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _archive_name(run_id: str, run_dir: Path, path: Path) -> str:
    return f"{run_id}/{path.resolve().relative_to(run_dir).as_posix()}"
