"""Finding summary helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FindingSummary:
    """Compact finding view for CLI display."""

    style_id: str
    severity: str
    span_id: str
    finding_type: str
    finding: str
    suggestion: str
    confidence: str
    segment_excerpt: str


def load_finding_summaries(run_dir: Path, span_id: str | None = None) -> tuple[FindingSummary, ...]:
    run_dir = run_dir.resolve()
    segments = _segments_by_id(run_dir / "segments.json")
    summaries: list[FindingSummary] = []

    for review_path in sorted((run_dir / "reviews").glob("*.review.json")):
        review = _load_json(review_path)
        style_id = str(review.get("style_id") or review_path.stem.replace(".review", ""))
        findings = review.get("findings") if isinstance(review.get("findings"), list) else []
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            actual_span_id = str(finding.get("span_id") or "")
            if span_id and actual_span_id != span_id:
                continue
            summaries.append(
                FindingSummary(
                    style_id=style_id,
                    severity=str(finding.get("severity") or ""),
                    span_id=actual_span_id,
                    finding_type=str(finding.get("type") or ""),
                    finding=str(finding.get("finding") or ""),
                    suggestion=str(finding.get("suggestion") or ""),
                    confidence=_value(finding.get("confidence")),
                    segment_excerpt=_excerpt(segments.get(actual_span_id, "")),
                )
            )
    return tuple(summaries)


def render_finding_summaries(summaries: tuple[FindingSummary, ...]) -> str:
    if not summaries:
        return "no findings"

    lines: list[str] = []
    current_span = ""
    for summary in summaries:
        if summary.span_id != current_span:
            current_span = summary.span_id
            lines.append(summary.span_id or "unknown-span")
            if summary.segment_excerpt:
                lines.append(f"  segment: {summary.segment_excerpt}")
        lines.append(f"  - [{summary.severity}] {summary.style_id} / {summary.finding_type}")
        lines.append(f"    finding: {summary.finding}")
        lines.append(f"    suggestion: {summary.suggestion}")
        if summary.confidence:
            lines.append(f"    confidence: {summary.confidence}")
    return "\n".join(lines)


def _segments_by_id(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = _load_json(path)
    segments = data.get("segments") if isinstance(data.get("segments"), list) else []
    result: dict[str, str] = {}
    for segment in segments:
        if isinstance(segment, dict) and segment.get("span_id"):
            result[str(segment["span_id"])] = str(segment.get("text") or "")
    return result


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _excerpt(text: str, limit: int = 120) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
