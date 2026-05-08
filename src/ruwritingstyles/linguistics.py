"""Russian-aware surface metrics used by deterministic style analysis.

These helpers deliberately avoid pretending to be a morphological analyzer.
They preserve philological details that matter for Russian texts, including
``ё``, combining stress marks, and historical Cyrillic letters, while exposing
small metrics that are cheap to compute for large corpora.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterator


COMBINING_MARKS = "\u0300-\u036f"
HYPHENS = "-\u2010\u2011\u2012\u2013"
HISTORICAL_CYRILLIC = frozenset("іІѣѢѳѲѵѴѫѪѧѦѭѬѯѮѱѰѡѠѕЅ")
_LETTER = r"[^\W\d_]"
_WORD_RE = re.compile(rf"{_LETTER}(?:{_LETTER}|[{COMBINING_MARKS}]|[{HYPHENS}](?={_LETTER}))*", re.UNICODE)
_SENTENCE_END_RE = re.compile(r"[.!?…]+(?:[\"')\]\u00bb]+)?(?=\s+|$)")


@dataclass(frozen=True)
class TextProfile:
    """Surface-level linguistic metrics for a document segment."""

    char_count: int
    word_count: int
    sentence_count: int
    cyrillic_word_count: int
    latin_word_count: int
    mixed_script_word_count: int
    historical_cyrillic_count: int
    yo_count: int
    accent_mark_count: int
    question_count: int
    exclamation_count: int
    long_sentence_count: int
    average_sentence_words: float

    def to_json(self) -> dict[str, int | float]:
        """Return a stable JSON-serializable profile."""

        return {
            "char_count": self.char_count,
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "cyrillic_word_count": self.cyrillic_word_count,
            "latin_word_count": self.latin_word_count,
            "mixed_script_word_count": self.mixed_script_word_count,
            "historical_cyrillic_count": self.historical_cyrillic_count,
            "yo_count": self.yo_count,
            "accent_mark_count": self.accent_mark_count,
            "question_count": self.question_count,
            "exclamation_count": self.exclamation_count,
            "long_sentence_count": self.long_sentence_count,
            "average_sentence_words": self.average_sentence_words,
        }


def iter_words(text: str) -> Iterator[str]:
    """Yield Unicode words, keeping Russian stress marks inside the token."""

    for match in _WORD_RE.finditer(text):
        yield match.group(0)


def iter_sentence_spans(text: str) -> Iterator[tuple[int, int]]:
    """Yield approximate sentence spans for review-size chunking.

    The splitter treats terminal punctuation as a boundary. It is intentionally
    conservative about Russian philology: it does not normalize abbreviations,
    stress marks, ``ё``, or historical spellings.
    """

    start = 0
    for match in _SENTENCE_END_RE.finditer(text):
        end = match.end()
        while start < end and text[start].isspace():
            start += 1
        if start < end:
            yield start, end
        start = end
    if start < len(text):
        while start < len(text) and text[start].isspace():
            start += 1
        if start < len(text):
            yield start, len(text)


def profile_text(text: str, *, long_sentence_words: int = 35) -> TextProfile:
    """Compute cheap Russian-aware surface metrics for ``text``.

    These metrics are suitable for routing, validation, and prompt context. They
    are not a substitute for lemmatization, syntax parsing, accentology, or
    source-critical philological judgment.
    """

    words = tuple(iter_words(text))
    cyrillic_words = 0
    latin_words = 0
    mixed_script_words = 0
    for word in words:
        has_cyrillic = any(is_cyrillic(char) for char in word)
        has_latin = any(is_latin(char) for char in word)
        if has_cyrillic:
            cyrillic_words += 1
        if has_latin:
            latin_words += 1
        if has_cyrillic and has_latin:
            mixed_script_words += 1

    sentence_spans = tuple(iter_sentence_spans(text))
    sentence_count = len(sentence_spans)
    long_sentence_count = sum(
        1
        for start, end in sentence_spans
        if sum(1 for _ in iter_words(text[start:end])) >= long_sentence_words
    )
    average_sentence_words = round(len(words) / sentence_count, 3) if sentence_count else 0.0

    return TextProfile(
        char_count=len(text),
        word_count=len(words),
        sentence_count=sentence_count,
        cyrillic_word_count=cyrillic_words,
        latin_word_count=latin_words,
        mixed_script_word_count=mixed_script_words,
        historical_cyrillic_count=sum(1 for char in text if char in HISTORICAL_CYRILLIC),
        yo_count=text.count("ё") + text.count("Ё"),
        accent_mark_count=sum(1 for char in text if "\u0300" <= char <= "\u036f"),
        question_count=text.count("?"),
        exclamation_count=text.count("!"),
        long_sentence_count=long_sentence_count,
        average_sentence_words=average_sentence_words,
    )


def is_cyrillic(char: str) -> bool:
    """Return whether ``char`` belongs to a Cyrillic Unicode block."""

    codepoint = ord(char)
    return 0x0400 <= codepoint <= 0x052F or 0x2DE0 <= codepoint <= 0x2DFF or 0xA640 <= codepoint <= 0xA69F


def is_latin(char: str) -> bool:
    """Return whether ``char`` belongs to a Latin Unicode block."""

    codepoint = ord(char)
    return 0x0041 <= codepoint <= 0x005A or 0x0061 <= codepoint <= 0x007A or 0x00C0 <= codepoint <= 0x024F
