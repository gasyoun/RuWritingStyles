"""Static HTML summary rendering for run artifacts."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
from typing import Any
import difflib

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
        _commitments_section(council),
        _diff_section(run_dir, council),
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
      font-size: 1.1rem;
      font-weight: 600;
      letter-spacing: -0.01em;
    }}
    section {{ margin-top: 48px; }}
    a {{ 
      color: var(--accent); 
      text-decoration: none;
      transition: color 0.2s;
    }}
    a:hover {{ color: var(--ink); }}
    code {{
      padding: 0.15rem 0.35rem;
      border-radius: 4px;
      background: rgba(0,0,0,0.06);
      font-size: 0.9em;
    }}
    .muted {{ color: var(--muted); }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
      gap: 16px;
      margin-top: 32px;
    }}
    .metric, .finding, .panel, .decision-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }}
    .metric {{
      padding: 16px;
      min-height: 90px;
      transition: transform 0.2s, box-shadow 0.2s;
    }}
    .metric:hover {{
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }}
    .metric strong {{
      display: block;
      font-size: 1.6rem;
      line-height: 1.2;
      color: var(--accent);
    }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 0.85rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-top: 4px;
    }}
    .links {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    .links a {{
      display: inline-flex;
      align-items: center;
      min-height: 38px;
      padding: 6px 14px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      font-size: 0.9rem;
      font-weight: 500;
    }}
    .links a:hover {{
      background: var(--accent-soft);
      border-color: var(--accent);
    }}
    .finding {{
      padding: 20px;
      margin-top: 16px;
    }}
    .finding-head {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      margin-bottom: 12px;
    }}
    .tag {{
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      padding: 2px 10px;
      border-radius: 6px;
      background: var(--accent-soft);
      color: var(--accent);
      font-size: 0.78rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }}
    .tag.warn {{
      background: var(--warn-soft);
      color: var(--warn);
    }}
    .excerpt {{
      margin: 12px 0 16px;
      padding: 12px 16px;
      border-left: 4px solid var(--line);
      background: rgba(0,0,0,0.02);
      color: var(--muted);
      font-style: italic;
      border-radius: 0 8px 8px 0;
    }}
    .panel {{
      padding: 20px;
      overflow-x: auto;
    }}
    .diff-container {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      margin-top: 20px;
    }}
    .diff-box {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 20px;
      font-size: 0.95rem;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .diff-box h3 {{
      margin-top: 0;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--line);
      color: var(--muted);
    }}
    .decision-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 16px;
      margin-top: 16px;
    }}
    .decision-card {{
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .decision-card.accepted {{ border-left: 4px solid #2e7d32; }}
    .decision-card.rejected {{ border-left: 4px solid #c62828; }}
    .decision-status {{
      font-weight: 800;
      text-transform: uppercase;
      font-size: 0.75rem;
    }
    .accepted .decision-status { color: #2e7d32; }
    .rejected .decision-status { color: #c62828; }
    
    .diff-table {
      display: flex;
      flex-direction: column;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 13px;
      line-height: 20px;
    }
    .diff-line {
      display: grid;
      grid-template-columns: 1fr 1fr;
      border-bottom: 1px solid rgba(0,0,0,0.05);
    }
    .diff-line:last-child { border-bottom: none; }
    .diff-line > div {
      padding: 4px 8px;
      white-space: pre-wrap;
      word-break: break-all;
    }
    .diff-line .orig { border-right: 1px solid var(--line); background: rgba(0,0,0,0.01); }
    .diff-line.delete .orig { background: #ffeef0; }
    .diff-line.insert .rev { background: #e6ffed; }
    .diff-line.replace .orig { background: #fff5b1; }
    .diff-line.replace .rev { background: #e6ffed; }
    .del { background: #fdb8c0; text-decoration: line-through; }
    .ins { background: #acf2bd; font-weight: bold; cursor: pointer; transition: background 0.2s; position: relative; }
    .ins:hover { background: #96e0ab; }
    .ins:hover::after {
      content: "Click to Discard";
      position: absolute;
      bottom: 100%;
      left: 50%;
      transform: translateX(-50%);
      background: #333;
      color: #fff;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 10px;
      white-space: nowrap;
      z-index: 10;
    }
    .ins.discarded {
      background: #eee !important;
      color: #aaa;
      text-decoration: line-through;
      font-weight: normal;
    }
    .ins.discarded::after { content: "Click to Restore"; }

    .resolution-toolbar {
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: var(--panel);
      border: 2px solid var(--accent);
      border-radius: 12px;
      padding: 16px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.15);
      z-index: 1000;
      display: none;
      flex-direction: column;
      gap: 12px;
      width: 280px;
    }
    .resolution-toolbar.active { display: flex; }
    .btn-save {
      background: var(--accent);
      color: #fff;
      border: none;
      padding: 10px;
      border-radius: 8px;
      font-weight: bold;
      cursor: pointer;
    }
    .btn-save:hover { opacity: 0.9; }

    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 560px;
    }
    th, td {
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font-size: 0.8rem;
      text-transform: uppercase;
    }
    @media (max-width: 560px) {
      main {
        width: min(100% - 20px, 1120px);
        padding-top: 20px;
      }
      .metric strong { font-size: 1.25rem; }
      h1 { font-size: 2rem; }
      .panel { padding: 10px; }
    }
  </style>
</head>
<body>
  <main>
{body}
  </main>
  
  <div id="resolution-toolbar" class="resolution-toolbar">
    <h3 style="margin-bottom: 4px">Interactive Resolution</h3>
    <p class="muted" style="font-size: 12px">You have <span id="discard-count">0</span> discarded changes.</p>
    <button class="btn-save" onclick="exportResolution()">Download Resolution JSON</button>
  </div>

  <script>
    let discarded = new Set();
    
    function toggleChange(el, id) {
      if (discarded.has(id)) {
        discarded.delete(id);
        el.classList.remove('discarded');
      } else {
        discarded.add(id);
        el.classList.add('discarded');
      }
      
      const toolbar = document.getElementById('resolution-toolbar');
      const countEl = document.getElementById('discard-count');
      
      countEl.innerText = discarded.size;
      if (discarded.size > 0) {
        toolbar.classList.add('active');
      } else {
        // Keep it active once started? Or hide? Let's keep active if > 0
        toolbar.classList.add('active');
      }
    }
    
    function exportResolution() {
      const data = {
        run_id: document.querySelector('.muted code').innerText,
        discarded_indices: Array.from(discarded),
        timestamp: new Date().toISOString()
      };
      const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `resolution-${data.run_id}.json`;
      a.click();
    }

    // Auto-assign IDs to insertion spans for tracking
    document.querySelectorAll('.ins').forEach((el, index) => {
      const id = 'change-' + index;
      el.onclick = () => toggleChange(el, id);
    });
  </script>
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
    diff_metrics = eval_result.get("diff_metrics") if isinstance(eval_result.get("diff_metrics"), dict) else {}
    rows = [
        ("Case", str(eval_result.get("case_id") or "")),
        ("Provider", str(eval_result.get("provider") or "")),
        ("Model", str(eval_result.get("model") or "")),
        ("Finding count", str(eval_result.get("finding_count") or 0)),
        ("Verification", str(eval_result.get("verification_status") or "")),
        ("Matched risks", ", ".join(_strings(eval_result.get("matched_expected_risks")))),
        ("Scoring passed", str(scoring.get("passed") if scoring else "")),
        ("Required matches", str(scoring.get("required_match_count") if scoring else "")),
        ("Diff within limits", str(scoring.get("diff_within_limits") if scoring else "")),
        ("Changed line ratio", _value(diff_metrics.get("changed_line_ratio"))),
        ("Char delta ratio", _value(diff_metrics.get("char_delta_ratio"))),
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
    
    cards = []
    for decision in decisions:
        status = str(decision.get("status") or "pending").lower()
        cls = "accepted" if "accept" in status else "rejected" if "reject" in status else "pending"
        cards.append(f"""
        <div class="decision-card {cls}">
          <div class="decision-status">{_e(status)}</div>
          <h3>{_e(decision.get("finding_id") or "Finding")}</h3>
          <p>{_e(decision.get("reason") or "No reason provided.")}</p>
        </div>""")
        
    return f"""    <section>
      <h2>Council Decisions</h2>
      <div class="decision-grid">
{''.join(cards)}
      </div>
    </section>"""


def _diff_section(run_dir: Path, council: dict[str, Any]) -> str:
    original_path = run_dir / "normalized.md"
    revised_path = run_dir / "revised.md"
    
    if not revised_path.exists():
        return ""
        
    original_text = original_path.read_text(encoding="utf-8") if original_path.exists() else ""
    revised_text = revised_path.read_text(encoding="utf-8")
    
    # Simple line-by-line word-level diff
    orig_lines = original_text.splitlines()
    rev_lines = revised_text.splitlines()
    
    diff_html = []
    
    # We'll use a simple heuristic to align lines if they are mostly the same length
    # For a real robust diff, we'd use difflib.HtmlDiff, but we want custom styling.
    
    matcher = difflib.SequenceMatcher(None, orig_lines, rev_lines)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            for i in range(i1, i2):
                diff_html.append(_diff_row(orig_lines[i], rev_lines[j1 + (i - i1)], "equal"))
        elif tag == 'replace':
            # Highlight changes within lines if counts match
            if (i2 - i1) == (j2 - j1):
                for k in range(i2 - i1):
                    diff_html.append(_diff_row(orig_lines[i1 + k], rev_lines[j1 + k], "replace"))
            else:
                for i in range(i1, i2):
                    diff_html.append(_diff_row(orig_lines[i], "", "delete"))
                for j in range(j1, j2):
                    diff_html.append(_diff_row("", rev_lines[j], "insert"))
        elif tag == 'delete':
            for i in range(i1, i2):
                diff_html.append(_diff_row(orig_lines[i], "", "delete"))
        elif tag == 'insert':
            for j in range(j1, j2):
                diff_html.append(_diff_row("", rev_lines[j], "insert"))

    return f"""    <section>
      <h2>Visual Review</h2>
      <div class="panel">
        <div class="diff-table">
          {"".join(diff_html)}
        </div>
      </div>
    </section>"""


def _diff_row(orig: str, rev: str, tag: str) -> str:
    if tag == "equal":
        return f'<div class="diff-line equal"><div class="orig">{_e(orig)}</div><div class="rev">{_e(rev)}</div></div>'
    
    if tag == "replace":
        # Word-level highlight
        o_words = orig.split()
        r_words = rev.split()
        o_h, r_h = _word_diff(orig, rev)
        return f'<div class="diff-line replace"><div class="orig">{o_h}</div><div class="rev">{r_h}</div></div>'
        
    if tag == "delete":
        return f'<div class="diff-line delete"><div class="orig">{_e(orig)}</div><div class="rev"></div></div>'
        
    if tag == "insert":
        return f'<div class="diff-line insert"><div class="orig"></div><div class="rev">{_e(rev)}</div></div>'
    
    return ""


def _word_diff(orig: str, rev: str) -> tuple[str, str]:
    o_html = []
    r_html = []
    
    s = difflib.SequenceMatcher(None, orig, rev)
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == 'equal':
            o_html.append(_e(orig[i1:i2]))
            r_html.append(_e(rev[j1:j2]))
        elif tag == 'replace':
            o_html.append(f'<span class="del">{_e(orig[i1:i2])}</span>')
            r_html.append(f'<span class="ins">{_e(rev[j1:j2])}</span>')
        elif tag == 'delete':
            o_html.append(f'<span class="del">{_e(orig[i1:i2])}</span>')
        elif tag == 'insert':
            r_html.append(f'<span class="ins">{_e(rev[j1:j2])}</span>')
            
    return "".join(o_html), "".join(r_html)


def _commitments_section(council: dict[str, Any]) -> str:
    commitments = _dicts(council.get("stylistic_commitments"))
    if not commitments:
        return ""
    rows = [(c.get("term", ""), c.get("decision", ""), c.get("rationale", "")) for c in commitments]
    return _section_table("Stylistic Commitments", ("Term", "Decision", "Rationale"), rows)


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
            str(entry.get("retry_count") or 0),
            _value(entry.get("retry_delay_seconds")),
        )
        for entry in entries
    ]
    return _section_table(
        "Provider Log",
        ("Task", "Provider", "Model", "Status", "Duration ms", "Retries", "Retry delay s"),
        rows,
    )


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
