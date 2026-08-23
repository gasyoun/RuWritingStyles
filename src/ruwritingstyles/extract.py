"""Text-extraction sanity gate for harvested PDFs and HTML.

The gate is a pure function so that the bake-off harness
(`tools/benchmark_extractors.py`) and the production harvester score identically —
a benchmark that measured something other than what production checks would
settle nothing.

The failure mode this exists to catch is the one recorded in `.ai_state.md`: a
PDF whose embedded font encodings make `pdftotext` return blanks or mojibake
where Cyrillic should be. Such output is *shaped* like text — non-empty, with
spaces and punctuation — so a length check does not see it. Four cheap ratios do.

`word_hit_rate` deliberately uses a small committed heuristic (frequent function
words plus productive Russian affixes) rather than a downloaded dictionary: it
only has to separate real Russian from mojibake, not do morphology.

Thresholds live in `config.SANITY_THRESHOLDS`, calibrated by the 19-08-2026
bake-off — see `docs/BENCHMARK_pdf-extractors_ru_19-08-2026.md`.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

__all__ = [
    "sanity",
    "verdict_for",
    "SANITY_THRESHOLDS",
    "RUSSIAN_STOPWORDS",
    "RUSSIAN_AFFIXES",
    "ENGLISH_STOPWORDS",
    "ENGLISH_AFFIXES",
    "extract_html",
    "PDF_EXTRACTORS",
    "extract_pdf",
    "escalate_ocr",
    "extract_best",
]

# Calibrated on the 19-08-2026 bake-off; re-exported through `config` so callers
# have one import site. Kept here as well so `extract` stays self-contained and
# importable without the config layer.
SANITY_THRESHOLDS: dict[str, float] = {
    # Real Russian galleys measured 0.74–0.93; the only sub-0.55 readings were an
    # English article (0.06, correctly a language verdict) and total extraction
    # failure (0.00). Nothing observed sat between 0.06 and 0.74, so this is a
    # wide gap, not a knife edge.
    "min_cyrillic_ratio": 0.55,
    # Clean extractions of the two hardest corpus PDFs still carried 0.6–2.0 %
    # replacement/control characters (residual glyph gaps in the embedded fonts).
    # At the initial 0.01 this axis alone failed text that was 93 % Cyrillic with
    # a 0.55 word-hit rate — a false negative. It is raised to 0.03 to catch
    # catastrophic decoding only; garbling is caught by the two axes below, which
    # is why loosening this one does not let mojibake through (`pdftotext` on
    # these files scores 0.018 here and is still rejected at 0.00 Cyrillic).
    "max_replacement_ratio": 0.03,
    # Real text measured 0.43–0.62 under both the Russian and English heuristics;
    # mojibake measured 0.00. Set well below the observed floor so a legitimately
    # terse or heavily terminological article is not thrown away.
    "min_word_hit_rate": 0.20,
    # Below a couple of hundred words an article body did not come out, whatever
    # the ratios say — a title page alone can score perfectly.
    "min_words": 200,
}

# Frequent Russian function words. Short, closed-class and encoding-agnostic:
# mojibake practically never reproduces them, real prose cannot avoid them.
RUSSIAN_STOPWORDS: frozenset[str] = frozenset(
    """
    и в во не что он на я с со как а то все она так его но да ты к у же вы за бы по
    только ее мне было вот от меня еще нет о из ему теперь когда даже ну вдруг ли если
    уже или ни быть был него до вас нибудь опять уж вам сказал ведь там потом себя ничего
    ей может они тут где есть надо ней для мы тебя их чем была сам чтоб без будто чего
    раз тоже себе под будет ж тогда кто этот того потому этого какой совсем ним здесь
    этом один почти мой тем чтобы нее были куда зачем всех никогда можно при наконец два
    об другой хоть после над больше тот через эти нас про всего них какая много разве
    три эту моя впрочем хорошо свою этой перед иногда лучше чуть том нельзя такой им
    более всегда конечно всю между это которые которых которая который также этих таким
    свои своих является этому именно данной работы статье автор языка текста
    """.split()
)

# Productive Russian inflectional/derivational endings. A token ending in one of
# these is very likely a real word; mojibake runs hit them only by accident.
RUSSIAN_AFFIXES: tuple[str, ...] = (
    "ость", "ение", "ания", "ании", "аний", "ского", "ской", "ские", "ских",
    "ными", "ного", "ному", "ется", "ются", "ился", "илась", "овать", "ивать",
    "ация", "ации", "тель", "ник", "изм", "ист", "ов", "ев", "ин", "ый", "ий",
    "ой", "ая", "яя", "ое", "ее", "ые", "ие", "ам", "ям", "ах", "ях", "ом",
    "ем", "ми", "ть", "ла", "ло", "ли", "ет", "ут", "ют", "ит", "ат", "ят",
)

# The same trick in Latin script, for `expect_cyrillic=False`. Mojibake from a
# broken Cyrillic font is Latin-range too, so a Latin-expecting verdict still has
# to distinguish real English from noise — a length check would not.
ENGLISH_STOPWORDS: frozenset[str] = frozenset(
    """
    the of and to in is that it for as with on by this be are was were from at or an
    which has have had not but their its they we he she his her our your all can may
    more other such than then these those there here when where what who how also
    into between within during about after before over under both each any some many
    one two three first second new used using based case study article paper research
    language languages word words form forms text texts data analysis results
    """.split()
)

ENGLISH_AFFIXES: tuple[str, ...] = (
    "tion", "sion", "ment", "ness", "ance", "ence", "ical", "ally", "able", "ible",
    "ing", "ed", "ly", "es", "s", "er", "or", "al", "ic", "ity", "ive", "ous",
)

_CYRILLIC_RE = re.compile(r"[Ѐ-ӿԀ-ԯ]")
_LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)
_TOKEN_RE = re.compile(r"[^\W\d_]{2,}", re.UNICODE)
_MIN_TOKEN_SAMPLE = 20


def _is_control(ch: str) -> bool:
    """Control or unassigned character, excluding ordinary whitespace."""
    if ch in "\t\n\r\f\v":
        return False
    return unicodedata.category(ch) in {"Cc", "Cf", "Cn", "Co", "Cs"}


def _looks_russian(token: str) -> bool:
    low = token.lower()
    if low in RUSSIAN_STOPWORDS:
        return True
    return low.endswith(RUSSIAN_AFFIXES)


def _looks_english(token: str) -> bool:
    low = token.lower()
    if low in ENGLISH_STOPWORDS:
        return True
    return low.endswith(ENGLISH_AFFIXES)


def sanity(text: str | None, *, expect_cyrillic: bool = True) -> dict[str, Any]:
    """Score extracted text for Cyrillic-text plausibility.

    Returns the four ratios plus a ``verdict`` of ``"pass"`` or ``"fail"``.
    Empty or ``None`` input fails with all ratios at zero — never raises, because
    an extractor that crashed and one that returned rubbish must be comparable in
    the same matrix.

    ``expect_cyrillic=False`` waives the Cyrillic floor for a source known to be
    in another language. RCSI journals publish English articles alongside Russian
    ones — Acta Linguistica Petropolitana 21.1 is entirely English — and a
    cleanly extracted English article otherwise scores `cyrillic_ratio` 0.06 and
    fails, which would read as "no extractor could handle this PDF". Deciding
    *which* language to expect is article classification, not extraction: it
    belongs to the caller (`journal_scope.classify_article`, S1.4), which is why
    this is a parameter rather than an auto-detect here.
    """
    text = text or ""

    chars = len(text)
    letters = _LETTER_RE.findall(text)
    cyrillic = _CYRILLIC_RE.findall(text)
    bad_chars = sum(1 for ch in text if ch == "�" or _is_control(ch))
    tokens = _TOKEN_RE.findall(text)

    cyrillic_ratio = len(cyrillic) / len(letters) if letters else 0.0
    replacement_ratio = bad_chars / chars if chars else 0.0

    # Score only tokens that are actually Cyrillic: a Russian article's English
    # abstract and its reference list must not drag the hit rate down.
    scored = [t for t in tokens if _CYRILLIC_RE.search(t)] if expect_cyrillic else tokens
    looks_like = _looks_russian if expect_cyrillic else _looks_english
    if len(scored) >= _MIN_TOKEN_SAMPLE:
        word_hit_rate = sum(1 for t in scored if looks_like(t)) / len(scored)
    else:
        word_hit_rate = 0.0

    metrics: dict[str, Any] = {
        "cyrillic_ratio": round(cyrillic_ratio, 4),
        "replacement_ratio": round(replacement_ratio, 4),
        "word_hit_rate": round(word_hit_rate, 4),
        "words": len(tokens),
    }
    metrics["verdict"] = verdict_for(metrics, expect_cyrillic=expect_cyrillic)
    return metrics


def verdict_for(metrics: dict[str, Any], *, expect_cyrillic: bool = True) -> str:
    """Apply the current thresholds to already-computed metrics.

    Split out from `sanity` so a stored score matrix can be re-judged after a
    threshold is recalibrated without re-extracting every PDF — the four ratios
    are the measurement, the verdict is only an opinion about them.
    """
    t = SANITY_THRESHOLDS
    script_ok = (
        metrics["cyrillic_ratio"] >= t["min_cyrillic_ratio"]
        if expect_cyrillic
        else metrics["cyrillic_ratio"] <= 1.0 - t["min_cyrillic_ratio"]
    )
    return (
        "pass"
        if (
            script_ok
            and metrics["replacement_ratio"] <= t["max_replacement_ratio"]
            and metrics["word_hit_rate"] >= t["min_word_hit_rate"]
            and metrics["words"] >= t["min_words"]
        )
        else "fail"
    )


# --------------------------------------------------------------------------- #
# Extraction chain (S1.5; D07 HTML-first, D08 pinned winner, D14 OCR rung).
#
# The return contract everywhere below is `(text_or_None, provenance_dict)` —
# never an exception for a bad document, because a bad document is normal.
# Spike finding (23-08-2026): the Филологические науки article page carries only
# ~350 words of metadata block, and the RUDN pinned article publishes in
# English — so a sub-threshold HTML body means "try the PDF", not "quarantine",
# and language expectation comes from citation metadata via the caller.
# --------------------------------------------------------------------------- #

_ARTICLE_BODY_SELECTORS = (
    "article",
    "section.article-body",
    "div.article-body",
    "div.item.body",
)


def extract_html(html: str) -> tuple[str | None, dict[str, Any]]:
    """Strip the article body container off one OJS article page."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None, {"source": "html", "extractor": "none",
                      "note": "bs4 not installed — install the [harvest] extra"}
    soup = BeautifulSoup(html or "", "html.parser")
    node = None
    selector_used = ""
    for selector in _ARTICLE_BODY_SELECTORS:
        node = soup.select_one(selector)
        if node is not None:
            selector_used = selector
            break
    if node is None:
        return None, {"source": "html", "extractor": "none", "note": "no body container"}
    # Script/style content never survives get_text with these tags stripped;
    # OJS pages inline citation formatter JS inside <article> occasionally.
    for junk in node.find_all(["script", "style"]):
        junk.decompose()
    text = node.get_text(" ", strip=True)
    provenance = {
        "source": "html",
        "extractor": f"bs4-{selector_used}",
        "words": len(text.split()),
    }
    return (text if text else None), provenance


_PDF_EXTRACTOR_ORDER = ("pymupdf-text", "pdfminer.six", "pypdf")


def _pdf_pages_text(pdf_path: Path, extractor: str) -> str | None:
    try:
        if extractor == "pymupdf-text":
            import fitz

            doc = fitz.open(pdf_path)
            try:
                return "\n".join(page.get_text() for page in doc)
            finally:
                doc.close()
        if extractor == "pdfminer.six":
            from pdfminer.high_level import extract_text

            return extract_text(str(pdf_path))
        if extractor == "pypdf":
            from pypdf import PdfReader

            reader = PdfReader(str(pdf_path))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return None
    return None


PDF_EXTRACTORS: tuple[str, ...] = _PDF_EXTRACTOR_ORDER


def extract_pdf(pdf_path: Path) -> tuple[str | None, dict[str, Any]]:
    """Run the pinned wave-0 chain (minus its OCR tail) over one PDF."""
    for extractor in _PDF_EXTRACTOR_ORDER:
        text = _pdf_pages_text(pdf_path, extractor)
        if text and text.strip():
            return text, {"source": "pdf", "extractor": extractor}
    return None, {"source": "pdf", "extractor": "none"}


def escalate_ocr(pdf_path: Path, *, language: str = "rus+eng") -> tuple[str | None, dict[str, Any]]:
    """D14 last rung: rasterize + OCR via ocrmypydf/tesseract into a temp PDF.

    Measured 23-08-2026 on the Digital_Humanities-2023 sample: rc 0, verdict
    pass — the machinery works; PyMuPDF simply usually wins first.
    """
    import subprocess
    import tempfile

    try:
        with tempfile.TemporaryDirectory(prefix="rws-ocr-") as tmp:
            out_pdf = Path(tmp) / "ocr.pdf"
            result = subprocess.run(
                [
                    "ocrmypdf", "--language", language, "--force-ocr",
                    "--output-type", "pdf", str(pdf_path), str(out_pdf),
                ],
                capture_output=True,
                text=True,
                timeout=1200,
            )
            if result.returncode != 0 or not out_pdf.exists():
                return None, {"source": "ocr", "extractor": "ocrmypdf-tesseract", "note": f"rc={result.returncode}"}
            text = _pdf_pages_text(out_pdf, "pymupdf-text")
            return (text if text and text.strip() else None), {
                "source": "ocr",
                "extractor": "ocrmypdf-tesseract-rus",
            }
    except Exception as exc:
        return None, {"source": "ocr", "extractor": "ocrmypdf-tesseract", "note": str(exc)[:120]}


def extract_best(
    *,
    html: str | None,
    pdf_bytes: bytes | None,
    expect_cyrillic: bool = True,
) -> tuple[str | None, dict[str, Any]]:
    """Implement the D07/D14 order over one article's candidate sources.

    HTML body first; a failing gate escalates to the PDF galley, then to OCR;
    quarantine is the caller's business. The returned provenance records every
    attempt so the sidecar shows what was tried, not just what won.

    Language-flip retry (spike finding, 23-08-2026): the RUDN pinned article
    sits in a Russian journal whose page metadata still yields a decisively
    non-Cyrillic body. When the whole chain fails under the expected script and
    an attempt's own ratios are decisive the other way (>= 90 % Latin letters,
    >= 100 words), the chain runs once more with the opposite expectation and
    the flip is recorded in the won provenance.
    """
    def _run(expect_cyrillic_now: bool) -> tuple[str | None, dict[str, Any], list[dict[str, Any]]]:
        attempts: list[dict[str, Any]] = []

        def _scored(text: str | None, prov: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
            metrics = sanity(text, expect_cyrillic=expect_cyrillic_now)
            record = dict(prov)
            record["sanity"] = metrics
            record["verdict"] = metrics["verdict"]
            attempts.append(record)
            return metrics["verdict"] == "pass", record

        import tempfile

        if html:
            text, prov = extract_html(html)
            passed, _ = _scored(text, prov)
            if passed:
                return text, {"attempts": attempts, "won": attempts[-1]}, attempts
        else:
            attempts.append({"source": "html", "note": "no page html"})

        if pdf_bytes:
            with tempfile.TemporaryDirectory(prefix="rws-pdf-") as tmp:
                pdf_path = Path(tmp) / "galley.pdf"
                pdf_path.write_bytes(pdf_bytes)
                text, prov = extract_pdf(pdf_path)
                passed, _ = _scored(text, prov)
                if passed:
                    return text, {"attempts": attempts, "won": attempts[-1]}, attempts
                ocr_text, ocr_prov = escalate_ocr(pdf_path)
                passed_ocr, _ = _scored(ocr_text, ocr_prov)
                if passed_ocr:
                    return ocr_text, {"attempts": attempts, "won": attempts[-1]}, attempts
        else:
            attempts.append({"source": "pdf", "note": "no galley url or fetch failed"})
        return None, {"attempts": attempts, "won": None}, attempts

    def _decisive_other_script(attempts: list[dict[str, Any]]) -> bool | None:
        for attempt in attempts:
            metrics = attempt.get("sanity") or {}
            if int(metrics.get("words", 0)) < 100:
                continue
            ratio = float(metrics.get("cyrillic_ratio", 0.0))
            if ratio <= 0.10:
                return False
            if ratio >= 0.90:
                return True
        return None

    text, provenance, attempts = _run(expect_cyrillic)
    if text is not None:
        return text, provenance

    flip = _decisive_other_script(attempts)
    if flip is not None and flip != expect_cyrillic:
        text, provenance, _ = _run(flip)
        if text is not None:
            provenance.setdefault("won", {})["language_flipped_to"] = (
                "cyrillic" if flip else "latin"
            )
            return text, provenance
    return None, provenance
