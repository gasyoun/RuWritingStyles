"""Subject classifier for RCSI journal/article selection (D04).

The term list is data, not code: ``knowledge/rcsi/subject_terms.json`` holds
three positive groups (``linguistics``, ``philology``, ``oriental``) plus a
``negative`` group for the general-science noise Вестник РАН otherwise
contributes (physics, biology, medicine, geology). Terms are prefixes: a term
matches when the haystack contains it as a substring, which lets
"лингвист" style stems cover the productive Russian derivation family without
a morphology engine.

Verdicts:
- a positive hit with no negative hit → ``include``
- a negative-only hit → ``exclude``
- everything else → ``uncertain``

Language expectation is a classification output too: an English-language
article must be scored by the sanity gate with ``expect_cyrillic=False``
(Acta Linguistica Petropolitana publishes in English), so
:class:`classify_article` also reports ``expect_cyrillic`` derived from the
citation metadata, never from the extracted text itself.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import repo_root_from

__all__ = ["classify_article", "classify_journal", "load_subject_terms"]

_POSITIVE_GROUPS = ("linguistics", "philology", "oriental")
_NEGATIVE_GROUP = "negative"


@lru_cache(maxsize=1)
def load_subject_terms(repo_root_str: str | None = None) -> dict[str, Any]:
    root = Path(repo_root_str) if repo_root_str else repo_root_from()
    path = root / "knowledge" / "rcsi" / "subject_terms.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _haystack(record: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title_ru", "title_en", "title"):
        value = record.get(key)
        if isinstance(value, str) and value:
            parts.append(value)
    for key in ("keywords_ru", "keywords_en", "keywords", "subject", "subjects"):
        value = record.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif isinstance(value, str) and value:
            parts.append(value)
    return " \u00b7 ".join(parts).lower()


def _matched(terms: list[str], haystack: str) -> list[str]:
    return [term for term in terms if term.lower() in haystack]


def classify_journal(scope_text: str) -> dict[str, Any]:
    """Classify a journal's declared scope text."""
    terms = load_subject_terms()["groups"]
    hay = scope_text.lower()
    positives: list[str] = []
    for group in _POSITIVE_GROUPS:
        positives.extend(_matched(terms.get(group, {}).get("ru", []) + terms.get(group, {}).get("en", []), hay))
    negatives = _matched(terms.get(_NEGATIVE_GROUP, {}).get("ru", []) + terms.get(_NEGATIVE_GROUP, {}).get("en", []), hay)
    if positives and not negatives:
        verdict = "include"
    elif negatives and not positives:
        verdict = "exclude"
    else:
        verdict = "uncertain"
    return {"verdict": verdict, "positive": positives[:8], "negative": negatives[:8]}


def _expect_cyrillic_from_meta(meta: dict[str, Any]) -> bool:
    language = str(meta.get("language", "") or "").lower()
    if language.startswith("en"):
        return False
    if language.startswith("ru"):
        return True
    # No usable citation_language: fall back to the title scripts. A title with
    # no Cyrillic at all is treated as an English-language article; anything
    # mixed stays Cyrillic-expecting (Russian articles commonly carry Latin
    # author names and DOIs).
    title = str(meta.get("title_ru") or meta.get("title") or "")
    return any("\u0400" <= ch <= "\u04FF" for ch in title)


def classify_article(meta_or_record: dict[str, Any], *, selection_record: dict[str, Any] | None = None) -> dict[str, Any]:
    """Classify one article record; returns verdict, matched terms, expect_cyrillic.

    ``meta_or_record`` is an ``rcsi.article_meta`` result (title/keywords keys);
    ``selection_record`` may carry OAI Dublin Core ``subject`` values that the
    article page lacked.
    """
    record = dict(meta_or_record)
    if selection_record:
        for key in ("subject", "description"):
            extra = selection_record.get(key)
            if extra and key not in record:
                record[key] = extra
    terms = load_subject_terms()["groups"]
    hay = _haystack(record)
    positives: list[str] = []
    for group in _POSITIVE_GROUPS:
        positives.extend(_matched(terms.get(group, {}).get("ru", []) + terms.get(group, {}).get("en", []), hay))
    negatives = _matched(terms.get(_NEGATIVE_GROUP, {}).get("ru", []) + terms.get(_NEGATIVE_GROUP, {}).get("en", []), hay)
    if positives and not negatives:
        verdict = "include"
    elif negatives and not positives:
        verdict = "exclude"
    else:
        verdict = "uncertain"
    return {
        "verdict": verdict,
        "matched_terms": positives[:8],
        "negative_terms": negatives[:8],
        "expect_cyrillic": _expect_cyrillic_from_meta(record),
    }
