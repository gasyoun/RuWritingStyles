"""Markdown report rendering for run artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .provider_log import load_provider_log


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
    eval_result = _load_json(run_dir / "eval-result.json")
    provider_log = load_provider_log(run_dir)

    run_id = _run_id(run_dir, segments_doc, council, revision, verification)
    segments = segments_doc.get("segments", []) if isinstance(segments_doc.get("segments"), list) else []
    source = str(segments_doc.get("input_path") or "unknown")

    sections = [
        f"# Run Report: {run_id}",
        _input_section(source, segments),
        _status_section(reviews, council, revision, verification),
        _eval_section(eval_result),
        _review_section(reviews),
        _findings_section(reviews),
        _provider_log_section(provider_log),
        _council_section(council),
        _revision_section(run_dir, revision),
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


def _eval_section(eval_result: dict[str, Any]) -> str:
    if not eval_result:
        return ""
    scoring = eval_result.get("scoring") if isinstance(eval_result.get("scoring"), dict) else {}
    diff_metrics = eval_result.get("diff_metrics") if isinstance(eval_result.get("diff_metrics"), dict) else {}
    rows = [
        ("case", str(eval_result.get("case_id") or "")),
        ("provider", str(eval_result.get("provider") or "")),
        ("model", str(eval_result.get("model") or "")),
        ("finding_count", str(eval_result.get("finding_count") or 0)),
        ("verification_status", str(eval_result.get("verification_status") or "")),
        ("matched_expected_risks", ", ".join(eval_result.get("matched_expected_risks") or [])),
        ("scoring_passed", str(scoring.get("passed", ""))),
        ("diff_within_limits", str(scoring.get("diff_within_limits", ""))),
        ("changed_line_ratio", _value(diff_metrics.get("changed_line_ratio"))),
        ("char_delta_ratio", _value(diff_metrics.get("char_delta_ratio"))),
    ]
    return "## Eval Result\n\n" + _table(("Field", "Value"), rows)


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


def _provider_log_section(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return "## Provider Log\n\nNo provider executions yet."
    rows = []
    for entry in entries:
        rows.append(
            (
                str(entry.get("task") or ""),
                str(entry.get("provider") or ""),
                str(entry.get("model") or ""),
                str(entry.get("status") or ""),
                str(entry.get("duration_ms") or 0),
            )
        )
    return "## Provider Log\n\n" + _table(("Task", "Provider", "Model", "Status", "Duration ms"), rows)


def _revision_section(run_dir: Path, revision: dict[str, Any]) -> str:
    if not revision:
        return "## Revision\n\nNo revision artifact yet."

    lines = [
        "## Revision",
        "",
        f"- Status: `{_status(revision)}`",
        f"- Revised document: `{revision.get('revised_document_path') or 'not written'}`",
        f"- Diff: `{_diff_path(run_dir, revision)}`",
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


def _diff_path(run_dir: Path, revision: dict[str, Any]) -> str:
    revised = revision.get("revised_document_path")
    if isinstance(revised, str) and revised and (run_dir / "revision.diff").exists():
        return "revision.diff"
    return "not written"


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
