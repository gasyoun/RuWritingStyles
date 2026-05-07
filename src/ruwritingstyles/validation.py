"""Validation for run artifacts and style findings."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .schema_validation import validate_json_schema


@dataclass(frozen=True)
class ValidationResult:
    """Validation result for a run directory."""

    ok: bool
    messages: tuple[str, ...]


def validate_run_dir(run_dir: Path) -> ValidationResult:
    run_dir = run_dir.resolve()
    messages: list[str] = []
    schema_store = _load_schema_store(_repo_root_from_run_dir(run_dir), messages)

    segments = _load_json(run_dir / "segments.json", messages)
    if isinstance(segments, dict):
        _validate_segments(segments, messages)
    span_ids = _span_ids(segments)

    for required in ["original.md", "normalized.md", "report.md", "summary.html"]:
        if not (run_dir / required).exists():
            messages.append(f"missing {required}")

    review_paths = sorted((run_dir / "reviews").glob("*.review.json"))
    if not review_paths:
        messages.append("missing review JSON files")
    for path in review_paths:
        review = _load_json(path, messages)
        if isinstance(review, dict):
            _validate_with_schema(review, "review.schema.json", path.name, schema_store, messages)
            _validate_review(review, span_ids, messages, path)

    for artifact, schema_name in [
        ("council.json", "council.schema.json"),
        ("revision.json", "revision.schema.json"),
        ("verification.json", "verification.schema.json"),
    ]:
        data = _load_json(run_dir / artifact, messages)
        if isinstance(data, dict):
            _validate_with_schema(data, schema_name, artifact, schema_store, messages)
            _validate_common_status(data, messages, artifact)
    _validate_eval_result(run_dir / "eval-result.json", messages)
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
        for key in [
            "timestamp",
            "task",
            "provider",
            "model",
            "artifact",
            "status",
            "duration_ms",
            "retry_count",
            "retry_delay_seconds",
            "retry_statuses",
        ]:
            if key not in entry:
                messages.append(f"provider.log.jsonl line {index} missing {key}")
        if entry.get("status") not in {"completed", "error"}:
            messages.append(f"provider.log.jsonl line {index} has invalid status {entry.get('status')!r}")
        if not isinstance(entry.get("retry_count"), int):
            messages.append(f"provider.log.jsonl line {index} has invalid retry_count")
        if not isinstance(entry.get("retry_delay_seconds"), (int, float)):
            messages.append(f"provider.log.jsonl line {index} has invalid retry_delay_seconds")
        if not isinstance(entry.get("retry_statuses"), list):
            messages.append(f"provider.log.jsonl line {index} has invalid retry_statuses")


def _validate_eval_result(path: Path, messages: list[str]) -> None:
    if not path.exists():
        return
    data = _load_json(path, messages)
    if not isinstance(data, dict):
        return
    for key in ["case_id", "run_id", "provider", "model", "finding_count", "verification_status"]:
        if key not in data:
            messages.append(f"eval-result.json missing {key}")
    diff_metrics = data.get("diff_metrics")
    if not isinstance(diff_metrics, dict):
        messages.append("eval-result.json missing diff_metrics")
    else:
        for key in ["changed_line_ratio", "char_delta_ratio", "word_delta_ratio"]:
            if not isinstance(diff_metrics.get(key), (int, float)):
                messages.append(f"eval-result.json diff_metrics missing numeric {key}")
    scoring = data.get("scoring")
    if not isinstance(scoring, dict):
        messages.append("eval-result.json missing scoring")
    elif "diff_within_limits" not in scoring:
        messages.append("eval-result.json scoring missing diff_within_limits")


def _validate_with_schema(
    data: dict[str, Any],
    schema_name: str,
    artifact: str,
    schema_store: dict[str, dict[str, Any]],
    messages: list[str],
) -> None:
    schema = schema_store.get(schema_name)
    if schema is None:
        messages.append(f"missing schema {schema_name}")
        return
    for message in validate_json_schema(data, schema, schema_store=schema_store):
        messages.append(f"{artifact} schema {message}")


def _repo_root_from_run_dir(run_dir: Path) -> Path:
    if run_dir.parent.name == "runs":
        return run_dir.parent.parent
    return Path(__file__).resolve().parents[2]


def _load_schema_store(repo_root: Path, messages: list[str]) -> dict[str, dict[str, Any]]:
    schema_dir = repo_root / "schemas"
    if not schema_dir.exists():
        messages.append(f"missing schema directory {schema_dir}")
        return {}
    store: dict[str, dict[str, Any]] = {}
    for path in sorted(schema_dir.glob("*.json")):
        data = _load_json(path, messages)
        if isinstance(data, dict):
            store[path.name] = data
    return store
