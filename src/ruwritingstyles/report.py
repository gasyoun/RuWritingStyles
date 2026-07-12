"""Markdown report rendering for run artifacts."""

from __future__ import annotations

import json
import re
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
        _sentiment_section(run_dir),
        _peer_review_section(run_dir),
        _eval_section(eval_result),
        _review_section(reviews),
        _findings_section(reviews),
        _provider_log_section(provider_log),
        _council_section(council),
        _bias_audit_section(run_dir),
        _revision_section(run_dir, revision),
        _verification_section(verification),
        _citation_section(run_dir),
        _journal_section(run_dir),
        _translit_lint_section(run_dir),
    ]
    return "\n\n".join(section for section in sections if section.strip()) + "\n"


# Per-language presence markers for the journal abstract / keywords check.
# Mirrored verbatim in the Obsidian plugin port (obsidian-plugin/src/lint/journal.ts);
# the plugin's parity test regenerates its golden output from journal_compliance(),
# so any change here must stay in sync.
ABSTRACT_MARKERS = {"ru": ("аннотац", "резюме"), "en": ("abstract",)}
KEYWORDS_MARKERS = {"ru": ("ключевые слова",), "en": ("keywords", "key words")}

# A "word" is a maximal run of letters/digits (underscore excluded). Mirrored in
# the Obsidian port as /[\p{L}\p{N}]+/u — keep the two definitions equivalent.
_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)


def _abstract_word_count(text: str, low: str, markers: tuple) -> int:
    """Count words in an abstract body for one language.

    Locates the first marker, takes the paragraph it opens (up to the next blank
    line), drops the label token (e.g. «Аннотация.»), and counts word runs.
    Tuned for the inline «**Аннотация.** текст…» style used by the target
    journals. An abstract placed under its own heading with a blank line before
    the body is under-counted (only the heading sits in the block) — that is
    safe, because the limit is a *maximum*, so under-counting can never raise a
    false over-limit warning. Mirrored in obsidian-plugin/src/lint/journal.ts.
    """
    best: tuple | None = None
    for m in markers:
        pos = low.find(m)
        if pos != -1 and (best is None or pos < best[0]):
            best = (pos, len(m))
    if best is None:
        return 0
    idx, mlen = best
    end = text.find("\n\n", idx)
    block = text[idx:] if end == -1 else text[idx:end]
    j, n = mlen, len(block)
    while j < n and block[j].isalpha():  # rest of the label word
        j += 1
    while j < n and not block[j].isalnum():  # punctuation / emphasis / space
        j += 1
    return len(_WORD_RE.findall(block[j:]))


def journal_compliance(text: str, profile: dict) -> dict:
    """Pure journal-compliance check shared by the report and the Obsidian port.

    `text` is the document; both the length and the abstract/keywords presence
    test are computed from it. Returns a structured result (no formatting) so the
    same logic can be mirrored in TypeScript and checked for parity. Line endings
    are normalized so the character count is stable across LF/CRLF checkouts.
    """
    text = text.replace("\r\n", "\n")
    low = text.lower()
    result: dict = {
        "name": profile.get("name"),
        "length": None,
        "citation_format": profile.get("citation_format"),
        "transliteration_scheme": profile.get("transliteration_scheme"),
        "abstract": [],
        "keywords": [],
    }
    max_chars = profile.get("max_chars")
    if isinstance(max_chars, int) and max_chars > 0:
        current = len(text)
        result["length"] = {
            "current": current,
            "max": max_chars,
            "over": max(0, current - max_chars),
        }
    max_words = profile.get("abstract_max_words")
    has_word_limit = isinstance(max_words, int) and max_words > 0
    abstract_langs = profile.get("abstract_required")
    if isinstance(abstract_langs, list):
        for lang in abstract_langs:
            markers = ABSTRACT_MARKERS.get(lang, ())
            present = any(m in low for m in markers)
            item = {"lang": lang, "present": present}
            if has_word_limit and present:
                words = _abstract_word_count(text, low, markers)
                item["words"] = words
                item["max"] = max_words
                item["over"] = max(0, words - max_words)
            result["abstract"].append(item)
    kw_max_words = profile.get("keywords_max_words")
    has_kw_limit = isinstance(kw_max_words, int) and kw_max_words > 0
    keyword_langs = profile.get("keywords_required")
    if isinstance(keyword_langs, list):
        for lang in keyword_langs:
            markers = KEYWORDS_MARKERS.get(lang, ())
            present = any(m in low for m in markers)
            item = {"lang": lang, "present": present}
            if has_kw_limit and present:
                # Same block logic as the abstract: journals phrase the limit in
                # words («не может превышать 10 слов» — Восток/Oriens), so count
                # word runs in the keywords block, label excluded.
                words = _abstract_word_count(text, low, markers)
                item["words"] = words
                item["max"] = kw_max_words
                item["over"] = max(0, words - kw_max_words)
            result["keywords"].append(item)
    return result


def _journal_section(run_dir: Path) -> str:
    from .project import resolve_journal_profile

    profile = resolve_journal_profile(run_dir)
    if not profile or not profile.get("name"):
        return ""

    doc_text = ""
    for cand in ("revised.md", "normalized.md", "original.md"):
        candidate = run_dir / cand
        if candidate.exists():
            doc_text = candidate.read_text(encoding="utf-8")
            break

    comp = journal_compliance(doc_text, profile)
    lines = [f"## Соответствие журналу: {comp['name']}", ""]
    if comp["length"]:
        length = comp["length"]
        flag = "OK" if length["over"] == 0 else f"⚠ превышение на {length['over']}"
        lines.append(f"- Объем: {length['current']} / {length['max']} знаков — {flag}")
    if comp["citation_format"]:
        lines.append(f"- Список литературы: {comp['citation_format']}")
    if comp["transliteration_scheme"]:
        lines.append(f"- Транслитерация: {comp['transliteration_scheme']}")
    for label, items in (("Аннотация", comp["abstract"]), ("Ключевые слова", comp["keywords"])):
        if items:
            langs = [it["lang"] for it in items]
            parts = []
            for it in items:
                mark = "✓" if it["present"] else "⚠ нет"
                if "words" in it:
                    wflag = "OK" if it["over"] == 0 else f"⚠ +{it['over']} сверх лимита"
                    mark = f"{mark} ({it['words']}/{it['max']} слов — {wflag})"
                parts.append(f"{it['lang']} {mark}")
            lines.append(f"- {label} ({', '.join(langs)}): {', '.join(parts)}")
    return "\n".join(lines)


def _translit_lint_section(run_dir: Path) -> str:
    path = run_dir / "translit-lint.json"
    if not path.exists():
        return ""
    data = _load_json(path)
    findings = data.get("findings") if isinstance(data.get("findings"), list) else []
    summary = data.get("summary", {}) if isinstance(data.get("summary"), dict) else {}
    lines = ["## Транслитерация санскрита (детерминированный линтер)", ""]
    schemes = summary.get("schemes_detected") or []
    lines.append(f"Схемы в тексте: {', '.join(schemes) if schemes else 'не обнаружены'}")
    if not findings:
        lines.append("\nЗамечаний нет.")
        return "\n".join(lines)
    rows = [
        (str(f.get("span_id", "")), str(f.get("type", "")), str(f.get("message", "")))
        for f in findings
    ]
    lines.append("")
    lines.append(_table(("Span", "Тип", "Сообщение"), rows))
    return "\n".join(lines)


def _sentiment_section(run_dir: Path) -> str:
    sentiment_path = run_dir / "sentiment.json"
    if not sentiment_path.exists():
        return ""
    
    data = json.loads(sentiment_path.read_text(encoding="utf-8"))
    orig = data.get("original", {})
    rev = data.get("revised", {})
    deltas = data.get("deltas", {})
    
    rows = [
        ("Academic Distance", str(orig.get("distance", 0)), str(rev.get("distance", 0)), str(deltas.get("distance", 0))),
        ("Certainty", str(orig.get("certainty", 0)), str(rev.get("certainty", 0)), str(deltas.get("certainty", 0))),
        ("Complexity", str(orig.get("complexity", 0)), str(rev.get("complexity", 0)), str(deltas.get("complexity", 0))),
        ("Politeness", str(orig.get("politeness", 0)), str(rev.get("politeness", 0)), str(deltas.get("politeness", 0))),
    ]
    
    lines = [
        "## Philological Sentiment Analysis",
        "",
        _table(("Dimension", "Original", "Revised", "Delta"), rows),
        "",
        f"**Justification**: {data.get('justification', '')}"
    ]
    return "\n".join(lines)



def _peer_review_section(run_dir: Path) -> str:
    pr_path = run_dir / "peer-review.json"
    if not pr_path.exists():
        return ""
    
    data = json.loads(pr_path.read_text(encoding="utf-8"))
    comments = data.get("comments", [])
    
    rows = []
    for c in comments:
        rows.append((str(c.get("type", "")), str(c.get("text", ""))))
        
    lines = [
        "## Philological Peer Review",
        f"- **Reviewer Archetype**: {data.get('reviewer_archetype', 'unknown')}",
        f"- **Overall Score**: {data.get('overall_score', 0)}/10",
        f"- **Recommendation**: **{data.get('recommendation', 'none').upper()}**",
        "",
        _table(("Type", "Comment"), rows)
    ]
    return "\n".join(lines)


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


def _bias_audit_section(run_dir: Path) -> str:
    bias_path = run_dir / "bias-audit.json"
    if not bias_path.exists():
        return ""
    
    data = json.loads(bias_path.read_text(encoding="utf-8"))
    findings = data.get("findings", [])
    
    lines = [
        "## Methodological Bias Audit",
        f"- **Bias Score**: {data.get('bias_score', 0)}/10",
        f"- **Primary Bias**: {data.get('primary_bias_detected', 'none').upper()}",
        "",
        f"**Critique**: {data.get('methodological_critique', '')}",
        ""
    ]
    
    if findings:
        rows = []
        for f in findings:
            rows.append((str(f.get("severity", "")), str(f.get("issue", "")), str(f.get("recommendation", ""))))
        lines.append(_table(("Severity", "Issue", "Recommendation"), rows))
        
    return "\n".join(lines)


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
                str(entry.get("retry_count") or 0),
                _value(entry.get("retry_delay_seconds")),
            )
        )
    return "## Provider Log\n\n" + _table(
        ("Task", "Provider", "Model", "Status", "Duration ms", "Retries", "Retry delay s"),
        rows,
    )


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


def _citation_section(run_dir: Path) -> str:
    cite_path = run_dir / "citations.json"
    if not cite_path.exists():
        return ""
    
    data = json.loads(cite_path.read_text(encoding="utf-8"))
    verified = data.get("verified", [])
    not_in_bibliography = data.get("not_in_bibliography", [])

    lines = [
        "## Scholarly Grounding (Citations)",
        f"- **Status**: `{data.get('status', 'unknown')}`",
        f"- **Verified Citations**: {len(verified)}",
        f"- **Not in Bibliography**: {len(not_in_bibliography)}",
        ""
    ]

    if verified:
        lines.append("### Verified Sources")
        rows = [(v.get("citation", ""), v.get("source_file", "")) for v in verified]
        lines.append(_table(("Citation", "Source Collection"), rows))
        lines.append("")

    if not_in_bibliography:
        lines.append("### Citations not in local bibliography")
        rows = [(h.get("citation", ""), h.get("reason", "")) for h in not_in_bibliography]
        lines.append(_table(("Citation", "Note"), rows))
        lines.append("")
        
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
