"""Span-patch reconstruction of the revised document.

The revision stage no longer trusts the model to re-emit the whole document
(which stochastically over-rewrites untouched prose). Instead the model emits
only per-span ``applied_changes`` (each ``{span_id, replacement_text, ...}``)
and the engine assembles ``revised.md`` here: untouched segments are copied
byte-for-byte from ``normalized.md`` and only changed spans are substituted.

Diff-fidelity becomes true *by construction* — an untouched span is
mathematically incapable of drifting because its exact source lines are copied.

The mapping is line-based against ``normalized.md``: every segment carries a
1-based ``start_line``/``end_line`` range (see :mod:`ruwritingstyles.segment`).
Lines outside any changed span — blank separators, headings, untouched
paragraphs — are always emitted verbatim, so a zero-change reconstruction
reproduces ``normalized.md`` exactly.
"""

from __future__ import annotations

import os
from typing import Any, Iterable

# Document-level growth budget for the revision governor: the net character
# growth of all applied span patches may not exceed this ratio of the source
# document length. Chosen with margin under the eval fidelity cap
# (max_char_delta_ratio default 0.5) so an engine-governed revision can never
# fail diff-fidelity on growth. Override with RWS_REVISION_MAX_GROWTH_RATIO.
DEFAULT_MAX_GROWTH_RATIO = 0.4


def max_growth_ratio() -> float:
    raw = os.environ.get("RWS_REVISION_MAX_GROWTH_RATIO")
    if raw is None or not str(raw).strip():
        return DEFAULT_MAX_GROWTH_RATIO
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_MAX_GROWTH_RATIO
    return value if value >= 0 else DEFAULT_MAX_GROWTH_RATIO


def govern_changes(
    normalized_text: str,
    segments: Iterable[Any],
    applied_changes: Iterable[Any],
    *,
    growth_ratio: float | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Enforce the document-level growth budget on span patches.

    Live models over-rewrite *inside* the span too — a 291-char paragraph comes
    back as an 864-char essay — so byte-copying untouched spans is not enough on
    short documents. This governor makes the fidelity budget true by
    construction end-to-end: patches are accepted until the total net character
    growth would exceed ``growth_ratio × len(normalized_text)``; beyond that the
    **largest-growth** patches are rejected (their spans stay untouched).

    Returns ``(accepted, rejected)``; each rejected entry is the original change
    dict plus a ``rejection_reason``. Shrinking or same-size patches are always
    accepted. Changes without a usable span/replacement pass through as
    accepted (reconstruction ignores them; the validator flags them).
    """
    budget = int((growth_ratio if growth_ratio is not None else max_growth_ratio()) * len(normalized_text))
    span_map = _segment_span_map(segments)

    sized: list[tuple[int, dict[str, Any]]] = []  # (growth, change)
    passthrough: list[dict[str, Any]] = []
    for change in applied_changes:
        if not isinstance(change, dict):
            continue
        span_id = change.get("span_id")
        segment = span_map.get(str(span_id)) if span_id is not None else None
        if segment is None or "replacement_text" not in change:
            passthrough.append(change)
            continue
        span_len = len(str(segment.get("text") or ""))
        growth = len(str(change["replacement_text"])) - span_len
        sized.append((growth, change))

    # Accept the cheapest growth first so a single runaway patch cannot evict
    # several surgical ones.
    sized.sort(key=lambda item: item[0])
    accepted: list[dict[str, Any]] = list(passthrough)
    rejected: list[dict[str, Any]] = []
    total_growth = 0
    for growth, change in sized:
        if growth > 0 and total_growth + growth > budget:
            rejected.append(
                {
                    **change,
                    "rejection_reason": (
                        f"replacement grows the span by {growth} chars; total growth "
                        f"would exceed the fidelity budget ({budget} chars = "
                        f"{growth_ratio if growth_ratio is not None else max_growth_ratio()} × document length)"
                    ),
                }
            )
            continue
        accepted.append(change)
        total_growth += max(0, growth)
    return accepted, rejected


def _segment_span_map(segments: Iterable[Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for segment in segments:
        if isinstance(segment, dict) and segment.get("span_id") is not None:
            out[str(segment["span_id"])] = segment
    return out


def _line_bounds(segment: dict[str, Any]) -> tuple[int, int] | None:
    try:
        start = int(segment["start_line"])
        end = int(segment["end_line"])
    except (KeyError, TypeError, ValueError):
        return None
    if start < 1 or end < start:
        return None
    return start, end


def reconstruct_revised(
    normalized_text: str,
    segments: Iterable[Any],
    applied_changes: Iterable[Any],
) -> str:
    """Rebuild the revised document from ``normalized_text`` + span patches.

    Untouched lines are copied verbatim; each accepted change replaces exactly
    the source lines of its segment with ``replacement_text``. Changes without a
    known ``span_id`` or without ``replacement_text`` are ignored (the segment is
    then left untouched, preserving fidelity). With no applicable changes the
    output is byte-identical to ``normalized_text``.
    """
    lines = normalized_text.split("\n")
    total = len(lines)
    span_map = _segment_span_map(segments)

    replacements: list[tuple[int, int, str]] = []
    for change in applied_changes:
        if not isinstance(change, dict):
            continue
        span_id = change.get("span_id")
        if span_id is None or "replacement_text" not in change:
            continue
        segment = span_map.get(str(span_id))
        if segment is None:
            continue
        bounds = _line_bounds(segment)
        if bounds is None:
            continue
        replacements.append((bounds[0], bounds[1], str(change["replacement_text"])))

    replacements.sort(key=lambda item: item[0])

    out: list[str] = []
    line_no = 1
    repl_idx = 0
    while line_no <= total:
        if repl_idx < len(replacements) and replacements[repl_idx][0] <= line_no:
            start, end, text = replacements[repl_idx]
            repl_idx += 1
            if start < line_no:
                # Overlapping / already-consumed span: keep the first winner.
                continue
            out.append(text)
            line_no = end + 1
            continue
        out.append(lines[line_no - 1])
        line_no += 1

    return "\n".join(out)


def reconstruction_errors(
    normalized_text: str,
    segments: Iterable[Any],
    applied_changes: Iterable[Any],
    revised_text: str,
) -> list[str]:
    """Validate that ``revised_text`` is a faithful span-patch reconstruction.

    Returns a list of human-readable problems (empty list == valid):

    * every ``applied_changes`` entry references a known ``span_id`` and carries
      ``replacement_text``;
    * ``revised_text`` equals the reconstruction — i.e. every non-referenced
      segment is byte-identical to ``normalized.md`` and each changed span holds
      exactly its ``replacement_text``.
    """
    errors: list[str] = []
    segments = list(segments)
    span_map = _segment_span_map(segments)

    changes = list(applied_changes)
    for index, change in enumerate(changes):
        if not isinstance(change, dict):
            errors.append(f"applied_changes[{index}] is not an object")
            continue
        span_id = change.get("span_id")
        if span_id is None:
            errors.append(f"applied_changes[{index}] missing span_id")
            continue
        if span_map and str(span_id) not in span_map:
            errors.append(
                f"applied_changes[{index}] references unknown span_id {span_id!r}"
            )
        if "replacement_text" not in change:
            errors.append(
                f"applied_changes[{index}] (span {span_id!r}) missing replacement_text"
            )

    expected = reconstruct_revised(normalized_text, segments, changes)
    if revised_text != expected:
        errors.append(
            "revised.md is not a faithful span-patch reconstruction of normalized.md "
            "(untouched spans must be copied byte-for-byte)"
        )
    return errors
