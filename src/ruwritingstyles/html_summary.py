"""Static HTML summary rendering for run artifacts."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Any

from .provider_log import load_provider_log


def write_html_report(run_dir: Path) -> Path:
    """Render summary.html for a run directory."""

    run_dir = run_dir.resolve()
    report_path = run_dir / "summary.html"
    report_path.write_text(render_html_report(run_dir), encoding="utf-8")
    return report_path


def render_html_report(run_dir: Path) -> str:
    run_dir = run_dir.resolve()
    segments_doc = _load_json(run_dir / "segments.json")
    reviews = [_load_json(path) for path in sorted((run_dir / "reviews").glob("*.review.json"))]
    council = _load_json(run_dir / "council.json")
    revision = _load_json(run_dir / "revision.json")
    verification = _load_json(run_dir / "verification.json")
    eval_result = _load_json(run_dir / "eval-result.json")
    provider_log = load_provider_log(run_dir)

    run_id = _run_id(run_dir, segments_doc, council, revision, verification, eval_result)
    segments = _dicts(segments_doc.get("segments"))
    findings = _finding_rows(reviews, segments)
    source = str(segments_doc.get("input_path") or "unknown")

    body = [
        _hero(run_id, source, segments, reviews, findings, council, revision, verification, eval_result),
        _artifact_links(run_dir),
        _eval_section(eval_result),
        _finding_section(findings),
        _review_section(reviews),
        _council_section(council),
        _revision_section(revision),
        _verification_section(verification),
        _provider_log_section(provider_log),
    ]

    return _page(f"RuWritingStyles Run {run_id}", "\n".join(section for section in body if section))


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_e(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f7f3;
      --ink: #242424;
      --muted: #666b73;
      --line: #d9d8cf;
      --panel: #ffffff;
      --accent: #245c73;
      --accent-soft: #e5f1f4;
      --warn: #8a4b13;
      --warn-soft: #fff3df;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }}
    main {{
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 32px 0 48px;
    }}
    header {{
      padding: 28px 0 18px;
      border-bottom: 1px solid var(--line);
    }}
    h1, h2, h3, p {{ margin-top: 0; }}
    h1 {{
      margin-bottom: 8px;
      font-size: 2.8rem;
      line-height: 1.05;
      letter-spacing: 0;
    }}
    h2 {{
      margin-bottom: 14px;
      font-size: 1.3rem;
      letter-spacing: 0;
    }}
    h3 {{
      margin-bottom: 8px;
      font-size: 1rem;
      letter-spacing: 0;
    }}
    section {{ margin-top: 28px; }}
    a {{ color: var(--accent); }}
    code {{
      padding: 0.1rem 0.25rem;
      border-radius: 4px;
      background: #ecebe4;
    }}
    .muted {{ color: var(--muted); }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 10px;
      margin-top: 20px;
    }}
    .metric, .finding, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .metric {{
      padding: 12px;
      min-height: 80px;
    }}
    .metric strong {{
      display: block;
      font-size: 1.45rem;
      line-height: 1.2;
    }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 0.88rem;
    }}
    .links {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .links a {{
      display: inline-flex;
      align-items: center;
      min-height: 34px;
      padding: 6px 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel);
      text-decoration: none;
    }}
    .finding {{
      padding: 14px;
      margin-top: 12px;
    }}
    .finding-head {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      margin-bottom: 8px;
    }}
    .tag {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 2px 7px;
      border-radius: 4px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 0.82rem;
      font-weight: 650;
    }}
    .tag.warn {{
      background: var(--warn-soft);
      color: var(--warn);
    }}
    .excerpt {{
      margin: 8px 0 12px;
      padding-left: 12px;
      border-left: 3px solid var(--line);
      color: var(--muted);
    }}
    .panel {{
      padding: 14px;
      overflow-x: auto;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 560px;
    }}
    th, td {{
      padding: 8px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-size: 0.8rem;
      text-transform: uppercase;
    }}
    @media (max-width: 560px) {{
      main {{
        width: min(100% - 20px, 1120px);
        padding-top: 20px;
      }}
      .metric strong {{ font-size: 1.25rem; }}
      h1 {{ font-size: 2rem; }}
      .panel {{ padding: 10px; }}
    }}
  </style>
</head>
<body>
  <main>
{body}
  </main>
</body>
</html>
"""


def _hero(
    run_id: str,
    source: str,
    segments: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    findings: list[dict[str, str]],
    council: dict[str, Any],
    revision: dict[str, Any],
    verification: dict[str, Any],
    eval_result: dict[str, Any],
) -> str:
    scoring = eval_result.get("scoring") if isinstance(eval_result.get("scoring"), dict) else {}
    scoring_status = "n/a" if not scoring else str(scoring.get("passed"))
    metrics = [
        ("Segments", str(len(segments))),
        ("Reviews", str(len(reviews))),
        ("Findings", str(len(findings))),
        ("Council", _status(council)),
        ("Revision", _status(revision)),
        ("Verification", _status(verification)),
        ("Eval Scoring", scoring_status),
    ]
    metric_html = "\n".join(
        f"""      <div class="metric"><strong>{_e(value)}</strong><span>{_e(label)}</span></div>"""
        for label, value in metrics
    )
    return f"""    <header>
      <h1>Run Summary</h1>
      <p class="muted">Run <code>{_e(run_id)}</code> from <code>{_e(source)}</code>.</p>
      <div class="metrics">
{metric_html}
      </div>
    </header>"""


def _artifact_links(run_dir: Path) -> str:
    links = [
        ("report.md", "Markdown report"),
        ("original.md", "Original"),
        ("normalized.md", "Normalized"),
        ("revised.md", "Revised"),
        ("revision.diff", "Diff"),
        ("segments.json", "Segments JSON"),
        ("eval-result.json", "Eval result"),
        ("provider.log.jsonl", "Provider log"),
    ]
    rendered = []
    for relative, label in links:
        if (run_dir / relative).exists():
            rendered.append(f'<a href="{_attr(relative)}">{_e(label)}</a>')
    if not rendered:
        return ""
    return f"""    <section>
      <h2>Artifacts</h2>
      <div class="links">{"".join(rendered)}</div>
    </section>"""


def _eval_section(eval_result: dict[str, Any]) -> str:
    if not eval_result:
        return ""
    scoring = eval_result.get("scoring") if isinstance(eval_result.get("scoring"), dict) else {}
    rows = [
        ("Case", str(eval_result.get("case_id") or "")),
        ("Provider", str(eval_result.get("provider") or "")),
        ("Model", str(eval_result.get("model") or "")),
        ("Finding count", str(eval_result.get("finding_count") or 0)),
        ("Verification", str(eval_result.get("verification_status") or "")),
        ("Matched risks", ", ".join(_strings(eval_result.get("matched_expected_risks")))),
        ("Scoring passed", str(scoring.get("passed") if scoring else "")),
        ("Required matches", str(scoring.get("required_match_count") if scoring else "")),
    ]
    return _section_table("Eval Result", ("Field", "Value"), rows)


def _finding_section(findings: list[dict[str, str]]) -> str:
    if not findings:
        return """    <section>
      <h2>Findings By Span</h2>
      <p class="muted">No completed findings yet.</p>
    </section>"""

    groups: dict[str, list[dict[str, str]]] = {}
    for finding in findings:
        groups.setdefault(finding["span_id"], []).append(finding)

    rendered_groups = []
    for span_id, group in groups.items():
        excerpt = group[0].get("segment_excerpt", "")
        items = []
        for finding in group:
            items.append(
                f"""        <article class="finding">
          <div class="finding-head">
            <span class="tag">{_e(finding["style_id"])}</span>
            <span class="tag warn">{_e(finding["severity"])}</span>
            <span class="tag">{_e(finding["finding_type"])}</span>
            <span class="muted">confidence {_e(finding["confidence"])}</span>
          </div>
          <h3>{_e(finding["finding"])}</h3>
          <p>{_e(finding["suggestion"])}</p>
        </article>"""
            )
        rendered_groups.append(
            f"""      <div id="span-{_attr(span_id)}">
        <h3><code>{_e(span_id)}</code></h3>
        <p class="excerpt">{_e(excerpt)}</p>
{''.join(items)}
      </div>"""
        )

    return f"""    <section>
      <h2>Findings By Span</h2>
{''.join(rendered_groups)}
    </section>"""


def _review_section(reviews: list[dict[str, Any]]) -> str:
    if not reviews:
        return ""
    rows = []
    for review in reviews:
        rows.append(
            (
                str(review.get("style_id") or "unknown"),
                str(review.get("status") or "unknown"),
                str(len(_dicts(review.get("findings")))),
                str(review.get("summary") or ""),
            )
        )
    return _section_table("Reviews", ("Style", "Status", "Findings", "Summary"), rows)


def _council_section(council: dict[str, Any]) -> str:
    if not council:
        return ""
    decisions = _dicts(council.get("decisions"))
    if not decisions:
        return f"""    <section>
      <h2>Council</h2>
      <p class="muted">Status: <code>{_e(_status(council))}</code>; no decisions yet.</p>
    </section>"""
    rows = [
        (
            str(decision.get("finding_id") or ""),
            str(decision.get("status") or ""),
            str(decision.get("reason") or ""),
        )
        for decision in decisions
    ]
    return _section_table("Council", ("Finding", "Decision", "Reason"), rows)


def _revision_section(revision: dict[str, Any]) -> str:
    if not revision:
        return ""
    rows = [
        ("Status", _status(revision)),
        ("Revised document", str(revision.get("revised_document_path") or "not written")),
        ("Applied changes", str(len(_list(revision.get("applied_changes"))))),
        ("Unresolved items", str(len(_list(revision.get("unresolved"))))),
    ]
    return _section_table("Revision", ("Field", "Value"), rows)


def _verification_section(verification: dict[str, Any]) -> str:
    if not verification:
        return ""
    warnings = _list(verification.get("warnings"))
    rows = [
        ("Status", _status(verification)),
        ("Passed checks", str(len(_list(verification.get("passed"))))),
        ("Warnings", str(len(warnings))),
    ]
    warning_rows = []
    for warning in warnings:
        if isinstance(warning, dict):
            warning_rows.append((str(warning.get("span_id") or ""), str(warning.get("message") or "")))
        else:
            warning_rows.append(("", str(warning)))
    warning_html = ""
    if warning_rows:
        warning_html = "\n" + _table(("Span", "Message"), warning_rows)
    return f"""    <section>
      <h2>Verification</h2>
      <div class="panel">
{_table(("Field", "Value"), rows)}
{warning_html}
      </div>
    </section>"""


def _provider_log_section(entries: list[dict[str, Any]]) -> str:
    if not entries:
        return """    <section>
      <h2>Provider Log</h2>
      <p class="muted">No provider executions yet.</p>
    </section>"""
    rows = [
        (
            str(entry.get("task") or ""),
            str(entry.get("provider") or ""),
            str(entry.get("model") or ""),
            str(entry.get("status") or ""),
            str(entry.get("duration_ms") or 0),
        )
        for entry in entries
    ]
    return _section_table("Provider Log", ("Task", "Provider", "Model", "Status", "Duration ms"), rows)


def _section_table(title: str, headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    return f"""    <section>
      <h2>{_e(title)}</h2>
      <div class="panel">
{_table(headers, rows)}
      </div>
    </section>"""


def _table(headers: tuple[str, ...], rows: list[tuple[str, ...]]) -> str:
    head = "".join(f"<th>{_e(header)}</th>" for header in headers)
    body = "\n".join(
        "<tr>" + "".join(f"<td>{_e(value)}</td>" for value in row) + "</tr>" for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _finding_rows(reviews: list[dict[str, Any]], segments: list[dict[str, Any]]) -> list[dict[str, str]]:
    segment_text = {
        str(segment.get("span_id")): str(segment.get("text") or "")
        for segment in segments
        if segment.get("span_id")
    }
    segment_order = {str(segment.get("span_id")): index for index, segment in enumerate(segments)}
    rows: list[dict[str, str]] = []
    for review in reviews:
        style_id = str(review.get("style_id") or "unknown")
        for finding in _dicts(review.get("findings")):
            span_id = str(finding.get("span_id") or "")
            rows.append(
                {
                    "style_id": style_id,
                    "severity": str(finding.get("severity") or "unknown"),
                    "span_id": span_id,
                    "finding_type": str(finding.get("type") or ""),
                    "finding": str(finding.get("finding") or ""),
                    "suggestion": str(finding.get("suggestion") or ""),
                    "confidence": _value(finding.get("confidence")),
                    "segment_excerpt": _excerpt(segment_text.get(span_id, "")),
                }
            )
    return sorted(rows, key=lambda item: (segment_order.get(item["span_id"], 10**9), item["style_id"]))


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


def _dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _excerpt(text: str, limit: int = 180) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _e(value: str) -> str:
    return escape(value, quote=False)


def _attr(value: str) -> str:
    return escape(value, quote=True)
