"""Markdown report rendering for run artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_run_report(run_dir: Path) -> Path:
    """Render a human-readable report.md for a run directory."""

    run_dir = run_dir.resolve()
    report_path = run_dir / "report.md"
    report_path.write_text(render_run_report(run_dir), encoding="utf-8")
    return report_path


def render_run_report(run_dir: Path) -> str:
    run_dir = run_dir.resolve()
    segments_doc = _load_json(run_dir / "segments.json")
    reviews = [_load_json(path) for path in sorted((run_dir / "reviews").glob("*.review.json"))]
    council = _load_json(run_dir / "council.json")
    revision = _load_json(run_dir / "revision.json")
    verification = _load_json(run_dir / "verification.json")

    run_id = _run_id(run_dir, segments_doc, council, revision, verification)
    segments = segments_doc.get("segments", []) if isinstance(segments_doc.get("segments"), list) else []
    source = str(segments_doc.get("input_path") or "unknown")

    sections = [
        f"# Run Report: {run_id}",
        _input_section(source, segments),
        _status_section(reviews, council, revision, verification),
        _review_section(reviews),
        _findings_section(reviews),
        _council_section(council),
        _revision_section(revision),
        _verification_section(verification),
    ]
    return "\n\n".join(section for section in sections if section.strip()) + "\n"


def _input_section(source: str, segments: list[Any]) -> str:
    counts: dict[str, int] = {}
    for segment in segments:
        if isinstance(segment, dict):
            segment_type = str(segment.get("type") or "unknown")
            counts[segment_type] = counts.get(segment_type, 0) + 1

    count_lines = "\n".join(f"- {key}: {value}" for key, value in sorted(counts.items()))
    return f"""## Input

- Source: `{source}`
- Segment count: {len(segments)}

## Segment Types

{count_lines or "- none: 0"}"""


def _status_section(
    reviews: list[dict[str, Any]],
    council: dict[str, Any],
    revision: dict[str, Any],
    verification: dict[str, Any],
) -> str:
    review_status = _combined_review_status(reviews)
    rows = [
        ("review", review_status, f"{len(reviews)} review file(s)"),
        ("council", _status(council), "council.json"),
        ("revision", _status(revision), "revision.json"),
        ("verification", _status(verification), "verification.json"),
    ]
    return "## Pipeline Status\n\n" + _table(("Step", "Status", "Artifact"), rows)


def _review_section(reviews: list[dict[str, Any]]) -> str:
    if not reviews:
        return "## Reviews\n\nNo review artifacts yet."

    rows = []
    for review in reviews:
        rows.append(
            (
                str(review.get("style_id") or "unknown"),
                str(review.get("status") or "unknown"),
                str(len(_findings(review))),
                str(review.get("summary") or ""),
            )
        )
    return "## Reviews\n\n" + _table(("Style", "Status", "Findings", "Summary"), rows)


def _findings_section(reviews: list[dict[str, Any]]) -> str:
    rows = []
    for review in reviews:
        style_id = str(review.get("style_id") or "unknown")
        for finding in _findings(review):
            rows.append(
                (
                    style_id,
                    str(finding.get("severity") or "unknown"),
                    str(finding.get("span_id") or ""),
                    str(finding.get("finding") or ""),
                    str(finding.get("suggestion") or ""),
                    _value(finding.get("confidence")),
                )
            )
    if not rows:
        return "## Findings\n\nNo completed findings yet."
    return "## Findings\n\n" + _table(("Style", "Severity", "Span", "Finding", "Suggestion", "Confidence"), rows)


def _council_section(council: dict[str, Any]) -> str:
    if not council:
        return "## Council\n\nNo council artifact yet."

    decisions = council.get("decisions") if isinstance(council.get("decisions"), list) else []
    if not decisions:
        return f"## Council\n\nStatus: `{_status(council)}`\n\nNo council decisions yet."

    rows = []
    for decision in decisions:
        if not isinstance(decision, dict):
            continue
        rows.append(
            (
                str(decision.get("finding_id") or ""),
                str(decision.get("status") or ""),
                str(decision.get("reason") or ""),
            )
        )
    return f"## Council\n\nStatus: `{_status(council)}`\n\n" + _table(("Finding", "Decision", "Reason"), rows)


def _revision_section(revision: dict[str, Any]) -> str:
    if not revision:
        return "## Revision\n\nNo revision artifact yet."

    lines = [
        "## Revision",
        "",
        f"- Status: `{_status(revision)}`",
        f"- Revised document: `{revision.get('revised_document_path') or 'not written'}`",
        f"- Applied changes: {len(_list(revision.get('applied_changes')))}",
        f"- Unresolved items: {len(_list(revision.get('unresolved')))}",
    ]
    return "\n".join(lines)


def _verification_section(verification: dict[str, Any]) -> str:
    if not verification:
        return "## Verification\n\nNo verification artifact yet."

    warnings = _list(verification.get("warnings"))
    passed = _list(verification.get("passed"))
    lines = [
        "## Verification",
        "",
        f"- Status: `{_status(verification)}`",
        f"- Passed checks: {len(passed)}",
        f"- Warnings: {len(warnings)}",
    ]
    if warnings:
        rows = []
        for warning in warnings:
            if isinstance(warning, dict):
                rows.append((str(warning.get("span_id") or ""), str(warning.get("message") or warning)))
            else:
                rows.append(("", str(warning)))
        lines.extend(["", _table(("Span", "Message"), rows)])
    return "\n".join(lines)


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _run_id(run_dir: Path, *docs: dict[str, Any]) -> str:
    for doc in docs:
        if isinstance(doc.get("run_id"), str) and doc["run_id"]:
            return doc["run_id"]
    return run_dir.name


def _status(doc: dict[str, Any]) -> str:
    return str(doc.get("status") or "missing")


def _combined_review_status(reviews: list[dict[str, Any]]) -> str:
    if not reviews:
        return "missing"
    statuses = {str(review.get("status") or "unknown") for review in reviews}
    if statuses == {"completed"}:
        return "completed"
    if len(statuses) == 1:
        return next(iter(statuses))
    return "mixed"


def _findings(review: dict[str, Any]) -> list[dict[str, Any]]:
    findings = review.get("findings")
    if not isinstance(findings, list):
        return []
    return [finding for finding in findings if isinstance(finding, dict)]


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    if not rows:
        return ""
    header = "| " + " | ".join(headers) + " |"
    divider = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(_cell(value) for value in row) + " |" for row in rows]
    return "\n".join([header, divider, *body])


def _cell(value: str) -> str:
    return value.replace("\n", " ").replace("|", "\\|").strip()


def _value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
