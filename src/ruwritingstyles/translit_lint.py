"""Deterministic Sanskrit transliteration linter (Phase 1, W2).

Non-LLM pipeline check: flags mixed transliteration schemes (IAST vs
Harvard-Kyoto), inconsistent term rendering (русская передача vs IAST),
missing IAST on a term's first mention, Devanagari normalization problems,
and mixed-script words. Never rewrites text — findings only, anchored to
span ids. Term dictionary: knowledge/sanskrit-terms.json.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

IAST_DIACRITICS = frozenset("āīūṛṝḷḹṃḥṅñṭḍṇśṣĀĪŪṚṜḶḸṂḤṄÑṬḌṆŚṢ")

_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")
# A dependent vowel sign / virama with no preceding consonant is an OCR artifact.
_ORPHAN_MATRA_RE = re.compile(r"(?:^|[\s(«\"'])[ऺ-्ॢॣ]")
_WORD_RE = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", re.UNICODE)
# Harvard-Kyoto markers: capital letter after the first position, or doubled vowels.
_HK_MARKER_RE = re.compile(r".[AIURTDNSGJMHLZ]|aa|ii|uu")

# Russian nominal endings tolerated after a term stem (inflection window).
_RU_ENDINGS = frozenset(
    ["", "а", "я", "у", "ю", "е", "и", "ы", "о", "ой", "ей", "ам", "ям",
     "ах", "ях", "ом", "ем", "ов", "ев", "ами", "ями", "ах", "ях"]
)
_RU_VOWELS = "аеёиоуыэюя"

FINDING_TYPES = (
    "mixed_transliteration_scheme",
    "inconsistent_term_rendering",
    "missing_iast_on_first_mention",
    "devanagari_nfc_issue",
    "iast_in_cyrillic_word",
)


def load_sanskrit_terms(repo_root: Path) -> list[dict[str, Any]]:
    path = repo_root / "knowledge" / "sanskrit-terms.json"
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return [t for t in data if isinstance(t, dict) and t.get("ru") and t.get("iast")]
    except (json.JSONDecodeError, OSError):
        return []


def _has_cyrillic(word: str) -> bool:
    return any("Ѐ" <= ch <= "ӿ" for ch in word)


def _has_latin(word: str) -> bool:
    return any(("a" <= ch <= "z") or ("A" <= ch <= "Z") or ch in IAST_DIACRITICS for ch in word)


def _is_iast_word(word: str) -> bool:
    return any(ch in IAST_DIACRITICS for ch in word)


def _skeleton(word: str) -> str:
    """ASCII skeleton: lowercase, diacritics stripped (kṛṣṇa -> krsna)."""
    decomposed = unicodedata.normalize("NFD", word.lower())
    return "".join(ch for ch in decomposed if "a" <= ch <= "z")


def _ru_stem(ru: str) -> str:
    return ru[:-1] if ru and ru[-1] in _RU_VOWELS + "ь" else ru


def _matches_ru_term(word: str, term_ru: str) -> bool:
    word = word.lower()
    stem = _ru_stem(term_ru.lower())
    if not word.startswith(stem):
        return False
    return word[len(stem):] in _RU_ENDINGS


def _finding(span_id: str, ftype: str, message: str, severity: str,
             fragment: str = "", term: str = "") -> dict[str, Any]:
    item: dict[str, Any] = {
        "span_id": span_id,
        "type": ftype,
        "message": message,
        "severity": severity,
    }
    if fragment:
        item["fragment"] = fragment
    if term:
        item["term"] = term
    return item


def lint_segments(
    segments: list[dict[str, Any]],
    terms: list[dict[str, Any]],
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Lint pre-segmented text. Each segment: {span_id, text}. Code spans skipped.

    A journal `profile` tunes the rules: `first_mention_rule` decides whether a
    missing IAST gloss on first mention is reported (only `ru+iast` / `iast+ru`
    require it)."""
    first_mention_rule = (profile or {}).get("first_mention_rule", "ru+iast")
    require_iast_first_mention = first_mention_rule in ("ru+iast", "iast+ru")
    findings: list[dict[str, Any]] = []
    iast_examples: list[str] = []
    hk_examples: list[tuple[str, str]] = []  # (span_id, word)
    term_skeletons = {_skeleton(t["iast"]): t for t in terms}

    # Per-term state for first-mention and consistency tracking.
    ru_seen: dict[str, list[str]] = {t["ru"]: [] for t in terms}
    iast_seen: dict[str, list[str]] = {t["ru"]: [] for t in terms}
    first_mention_flagged: set[str] = set()

    prose = [
        s for s in segments
        if not str(s.get("span_id", "")).startswith("c") and s.get("text")
    ]

    for seg in prose:
        span_id = str(seg["span_id"])
        text = str(seg["text"])

        # Devanagari checks.
        if _DEVANAGARI_RE.search(text):
            if text != unicodedata.normalize("NFC", text):
                findings.append(_finding(
                    span_id, "devanagari_nfc_issue",
                    "Деванагари не в форме NFC: возможна потеря огласовок при поиске и сравнении.",
                    "error",
                ))
            orphan = _ORPHAN_MATRA_RE.search(text)
            if orphan:
                findings.append(_finding(
                    span_id, "devanagari_nfc_issue",
                    "Огласовка деванагари без опорного согласного (вероятный артефакт OCR).",
                    "error", fragment=orphan.group(0).strip(),
                ))

        for word in _WORD_RE.findall(text):
            cyr = _has_cyrillic(word)
            lat = _has_latin(word)

            if cyr and lat:
                findings.append(_finding(
                    span_id, "iast_in_cyrillic_word",
                    f"Смешение кириллицы и латиницы внутри словоформы: «{word}».",
                    "error", fragment=word,
                ))
                continue

            if lat and _is_iast_word(word):
                iast_examples.append(word)
            elif lat and _HK_MARKER_RE.search(word):
                # Narrow HK detection: only words resolving to a known term.
                if _skeleton(word) in term_skeletons:
                    hk_examples.append((span_id, word))

        # Term occurrence tracking.
        lowered = text.lower()
        for term in terms:
            ru = term["ru"]
            iast = term["iast"].lower()
            if iast in lowered:
                iast_seen[ru].append(span_id)
            ru_hit = any(
                _matches_ru_term(w, ru) for w in _WORD_RE.findall(lowered) if _has_cyrillic(w)
            )
            if ru_hit:
                ru_seen[ru].append(span_id)
                first_ever = len(ru_seen[ru]) == 1 and not iast_seen[ru]
                if require_iast_first_mention and first_ever and iast not in lowered and ru not in first_mention_flagged:
                    first_mention_flagged.add(ru)
                    findings.append(_finding(
                        span_id, "missing_iast_on_first_mention",
                        f"Первое упоминание термина «{ru}» без IAST в скобках: "
                        f"ожидается «{ru} ({term['iast']})».",
                        "warning", term=ru,
                    ))

    # Document-level: mixed schemes.
    if iast_examples and hk_examples:
        span_id, hk_word = hk_examples[0]
        findings.append(_finding(
            span_id, "mixed_transliteration_scheme",
            "В тексте смешаны схемы транслитерации: IAST "
            f"(напр., «{iast_examples[0]}») и Harvard-Kyoto (напр., «{hk_word}»). "
            "Приведите к одной схеме (для журналов — IAST).",
            "error", fragment=hk_word,
        ))

    # Document-level: free variation русская передача / IAST.
    for term in terms:
        ru = term["ru"]
        unpaired_iast = [s for s in iast_seen[ru] if s not in ru_seen[ru]]
        if len(ru_seen[ru]) >= 2 and len(unpaired_iast) >= 2:
            findings.append(_finding(
                unpaired_iast[0], "inconsistent_term_rendering",
                f"Термин передается то кириллицей («{ru}»), то латиницей "
                f"(«{term['iast']}») без системы; выберите основную форму, "
                "вторую давайте в скобках при первом упоминании.",
                "warning", term=ru,
            ))

    summary = {
        "segments_checked": len(prose),
        "iast_word_count": len(iast_examples),
        "hk_word_count": len(hk_examples),
        "schemes_detected": sorted(
            (["iast"] if iast_examples else []) + (["harvard-kyoto"] if hk_examples else [])
        ),
        "finding_counts": {
            ftype: sum(1 for f in findings if f["type"] == ftype)
            for ftype in FINDING_TYPES
        },
    }
    return {"status": "completed", "findings": findings, "summary": summary}


def lint_text(
    text: str,
    terms: list[dict[str, Any]],
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Segment markdown text and lint it (standalone `rws lint-translit`)."""
    from .segment import normalize_document, segment_markdown

    # NFC check must run on the raw input: normalize_document() itself
    # applies NFC, which would mask the problem in the source file.
    raw_nfc_issue = (
        _DEVANAGARI_RE.search(text) is not None
        and text != unicodedata.normalize("NFC", text)
    )

    normalized = normalize_document(text)
    segments = [
        {"span_id": s.span_id, "text": s.text} for s in segment_markdown(normalized)
    ]
    result = lint_segments(segments, terms, profile)

    if raw_nfc_issue:
        anchor = next(
            (s["span_id"] for s in segments if _DEVANAGARI_RE.search(s["text"])),
            segments[0]["span_id"] if segments else "p001",
        )
        result["findings"].insert(0, _finding(
            str(anchor), "devanagari_nfc_issue",
            "Исходный файл содержит деванагари не в форме NFC: "
            "нормализуйте файл (NFC), иначе поиск и сравнение строк ненадежны.",
            "error",
        ))
        result["summary"]["finding_counts"]["devanagari_nfc_issue"] += 1
    return result


def run_translit_lint(repo_root: Path, run_dir: Path) -> Path:
    """Pipeline step: lint revised.md (or normalized.md), write translit-lint.json,
    and mirror findings into verification.json warnings."""
    from .project import resolve_journal_profile

    source = run_dir / "revised.md"
    if not source.exists():
        source = run_dir / "normalized.md"
    terms = load_sanskrit_terms(repo_root)
    profile = resolve_journal_profile(run_dir)
    text = source.read_text(encoding="utf-8") if source.exists() else ""
    result = lint_text(text, terms, profile)
    result["source_file"] = source.name

    artifact = run_dir / "translit-lint.json"
    artifact.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if result["findings"]:
        _merge_into_verification(run_dir, result["findings"])
    return artifact


def _merge_into_verification(run_dir: Path, findings: list[dict[str, Any]]) -> None:
    verification_path = run_dir / "verification.json"
    if not verification_path.exists():
        return
    try:
        doc = json.loads(verification_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    warnings = doc.get("warnings")
    if not isinstance(warnings, list):
        warnings = []
    existing = {
        (w.get("span_id"), w.get("type"), w.get("message"))
        for w in warnings if isinstance(w, dict)
    }
    for f in findings:
        key = (f.get("span_id"), f.get("type"), f.get("message"))
        if key not in existing:
            warnings.append(dict(f, source="translit_lint"))
    doc["warnings"] = warnings
    verification_path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8"
    )
