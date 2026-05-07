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


def export_eval_suite_bundle(suite_dir: Path, output_path: Path | None = None) -> Path:
    """Create a ZIP bundle with an eval suite and its referenced case runs."""

    suite_dir = suite_dir.resolve()
    if not suite_dir.exists():
        raise FileNotFoundError(f"missing eval suite directory {suite_dir}")

    result_path = suite_dir / "eval-suite-result.json"
    if not result_path.exists():
        raise FileNotFoundError(f"missing {result_path}")
    suite = _load_json(result_path)
    suite_id = str(suite.get("suite_id") or suite_dir.name)
    bundle_path = (output_path or (suite_dir / f"{suite_id}-bundle.zip")).resolve()
    bundle_path.parent.mkdir(parents=True, exist_ok=True)

    repo_root = _repo_root_from_suite_dir(suite_dir)
    archive_entries = _eval_suite_archive_entries(repo_root, suite_dir, suite_id, suite)
    manifest = {
        "suite_id": suite_id,
        "case_run_count": _case_run_count(suite),
        "artifact_count": len(archive_entries),
        "artifacts": [archive_name for _, archive_name in archive_entries],
    }

    with ZipFile(bundle_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(f"{suite_id}/bundle-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        for path, archive_name in archive_entries:
            archive.write(path, archive_name)

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


def _eval_suite_archive_entries(
    repo_root: Path,
    suite_dir: Path,
    suite_id: str,
    suite: dict[str, Any],
) -> list[tuple[Path, str]]:
    entries: list[tuple[Path, str]] = []
    seen: set[Path] = set()

    for path in _suite_files(suite_dir):
        _add_entry(entries, seen, path, f"{suite_id}/{path.resolve().relative_to(suite_dir).as_posix()}")

    for run_dir in _suite_case_run_dirs(repo_root, suite):
        report_path = write_run_report(run_dir)
        html_path = write_html_report(run_dir)
        run_id = _run_id(run_dir)
        for path in _bundle_files(run_dir, report_path, html_path):
            archive_name = f"{suite_id}/cases/{run_id}/{path.resolve().relative_to(run_dir).as_posix()}"
            _add_entry(entries, seen, path, archive_name)

    return entries


def _suite_files(suite_dir: Path) -> list[Path]:
    candidates = [
        suite_dir / "eval-suite-result.json",
        suite_dir / "eval-suite-report.md",
    ]
    candidates.extend(sorted(suite_dir.glob("*.json")))
    candidates.extend(sorted(suite_dir.glob("*.md")))
    return [path for path in candidates if path.exists()]


def _suite_case_run_dirs(repo_root: Path, suite: dict[str, Any]) -> list[Path]:
    rows = suite.get("results") if isinstance(suite.get("results"), list) else []
    run_dirs: list[Path] = []
    seen: set[Path] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        run_dir = _repo_path(repo_root, row.get("run_dir"))
        if run_dir is None or not run_dir.exists():
            continue
        resolved = run_dir.resolve()
        if resolved not in seen:
            seen.add(resolved)
            run_dirs.append(resolved)
    return run_dirs


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


def _add_entry(entries: list[tuple[Path, str]], seen: set[Path], path: Path, archive_name: str) -> None:
    resolved = path.resolve()
    if resolved in seen:
        return
    seen.add(resolved)
    entries.append((resolved, archive_name))


def _case_run_count(suite: dict[str, Any]) -> int:
    rows = suite.get("results")
    return len(rows) if isinstance(rows, list) else 0


def _repo_root_from_suite_dir(suite_dir: Path) -> Path:
    if suite_dir.parent.name == "runs":
        return suite_dir.parent.parent
    return Path(__file__).resolve().parents[2]


def _repo_path(repo_root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return repo_root / path
