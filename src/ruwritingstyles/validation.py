"""Validation for run artifacts and style findings."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ValidationResult:
    """Validation result for a run directory."""

    ok: bool
    messages: tuple[str, ...]


def validate_run_dir(run_dir: Path) -> ValidationResult:
    run_dir = run_dir.resolve()
    messages: list[str] = []

    segments = _load_json(run_dir / "segments.json", messages)
    if isinstance(segments, dict):
        _validate_segments(segments, messages)
    span_ids = _span_ids(segments)

    for required in ["original.md", "normalized.md", "report.md"]:
        if not (run_dir / required).exists():
            messages.append(f"missing {required}")

    review_paths = sorted((run_dir / "reviews").glob("*.review.json"))
    if not review_paths:
        messages.append("missing review JSON files")
    for path in review_paths:
        review = _load_json(path, messages)
        if isinstance(review, dict):
            _validate_review(review, span_ids, messages, path)

    for artifact in ["council.json", "revision.json", "verification.json"]:
        data = _load_json(run_dir / artifact, messages)
        if isinstance(data, dict):
            _validate_common_status(data, messages, artifact)
    _validate_provider_log(run_dir / "provider.log.jsonl", messages)

    return ValidationResult(ok=not messages, messages=tuple(messages))


def _load_json(path: Path, messages: list[str]) -> Any:
    if not path.exists():
        messages.append(f"missing {path.name}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        messages.append(f"invalid JSON in {path}: {exc}")
        return None


def _validate_segments(data: dict[str, Any], messages: list[str]) -> None:
    segments = data.get("segments")
    if not isinstance(segments, list):
        messages.append("segments.json must contain a list in `segments`")
        return
    if data.get("segment_count") != len(segments):
        messages.append("segments.json segment_count does not match segments length")
    for segment in segments:
        if not isinstance(segment, dict):
            messages.append("segments.json contains a non-object segment")
            continue
        for key in ["span_id", "type", "text", "start_line", "end_line"]:
            if key not in segment:
                messages.append(f"segment missing {key}")


def _span_ids(data: Any) -> set[str]:
    if not isinstance(data, dict) or not isinstance(data.get("segments"), list):
        return set()
    return {
        str(segment.get("span_id"))
        for segment in data["segments"]
        if isinstance(segment, dict) and segment.get("span_id")
    }


def _validate_review(data: dict[str, Any], span_ids: set[str], messages: list[str], path: Path) -> None:
    for key in ["run_id", "style_id", "status", "prompt_path", "segment_count", "findings"]:
        if key not in data:
            messages.append(f"{path.name} missing {key}")
    if data.get("status") not in {"prompt_ready", "completed"}:
        messages.append(f"{path.name} has invalid status {data.get('status')!r}")
    findings = data.get("findings")
    if not isinstance(findings, list):
        messages.append(f"{path.name} findings must be a list")
        return
    for finding in findings:
        _validate_finding(finding, span_ids, messages, path)


def _validate_finding(finding: Any, span_ids: set[str], messages: list[str], path: Path) -> None:
    if not isinstance(finding, dict):
        messages.append(f"{path.name} contains a non-object finding")
        return
    for key in ["id", "style_id", "span_id", "severity", "type", "finding", "suggestion", "confidence"]:
        if key not in finding:
            messages.append(f"{path.name} finding missing {key}")
    if finding.get("severity") not in {"blocker", "major", "minor", "note"}:
        messages.append(f"{path.name} finding {finding.get('id')} has invalid severity")
    if finding.get("span_id") not in span_ids:
        messages.append(f"{path.name} finding {finding.get('id')} references unknown span_id {finding.get('span_id')!r}")
    confidence = finding.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        messages.append(f"{path.name} finding {finding.get('id')} has invalid confidence")


def _validate_common_status(data: dict[str, Any], messages: list[str], artifact: str) -> None:
    if "status" not in data:
        messages.append(f"{artifact} missing status")
    if "run_id" not in data:
        messages.append(f"{artifact} missing run_id")


def _validate_provider_log(path: Path, messages: list[str]) -> None:
    if not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        messages.append(f"could not read provider.log.jsonl: {exc}")
        return
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            messages.append(f"provider.log.jsonl line {index} invalid JSON: {exc}")
            continue
        if not isinstance(entry, dict):
            messages.append(f"provider.log.jsonl line {index} must be an object")
            continue
        for key in ["timestamp", "task", "provider", "model", "artifact", "status", "duration_ms"]:
            if key not in entry:
                messages.append(f"provider.log.jsonl line {index} missing {key}")
        if entry.get("status") not in {"completed", "error"}:
            messages.append(f"provider.log.jsonl line {index} has invalid status {entry.get('status')!r}")
