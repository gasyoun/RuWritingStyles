"""Document input and decoding helpers for RuWritingStyles.

The project intentionally keeps runtime dependencies at zero, so this module
provides a conservative decoding boundary for Markdown and plain-text sources.
It accepts UTF-8 first, then falls back to Russian legacy encodings only when
the decoded text looks like plausible running text rather than binary data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


SUPPORTED_TEXT_SUFFIXES = frozenset({".md", ".txt"})
_CANDIDATE_ENCODINGS = ("utf-8-sig", "cp1251", "koi8-r", "utf-16", "utf-16-le", "utf-16-be")
_BOMS = (
    (b"\xff\xfe\x00\x00", "utf-32"),
    (b"\x00\x00\xfe\xff", "utf-32"),
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xff\xfe", "utf-16"),
    (b"\xfe\xff", "utf-16"),
)
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_COMMON_RUSSIAN_WORDS = {
    "а",
    "без",
    "бы",
    "в",
    "во",
    "для",
    "и",
    "из",
    "к",
    "как",
    "на",
    "не",
    "но",
    "о",
    "об",
    "от",
    "по",
    "при",
    "с",
    "со",
    "то",
    "у",
    "что",
}


class DocumentInputError(ValueError):
    """Raised when an input document cannot be read as supported text."""


@dataclass(frozen=True)
class DecodedDocument:
    """A decoded input document plus non-secret decoding metadata."""

    text: str
    encoding: str
    had_bom: bool
    replacement_count: int = 0


def read_text_document(path: Path, *, suffixes: frozenset[str] = SUPPORTED_TEXT_SUFFIXES) -> DecodedDocument:
    """Read a Markdown/TXT document and decode it with Russian-safe fallbacks.

    UTF-8 remains the canonical project encoding. CP1251 and KOI8-R are accepted
    as migration-friendly fallbacks for older Russian corpora, but binary-looking
    inputs or implausible decodings raise :class:`DocumentInputError`.
    """

    if path.suffix.lower() not in suffixes:
        allowed = ", ".join(sorted(suffixes))
        raise DocumentInputError(f"unsupported input type {path.suffix!r}; expected one of: {allowed}")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise DocumentInputError(f"could not read {path}: {exc}") from exc

    if not raw:
        return DecodedDocument(text="", encoding="utf-8", had_bom=False)
    utf16_like = _has_utf16_pattern(raw)
    if _looks_binary(raw):
        raise DocumentInputError(f"{path} looks like binary data, not Markdown/TXT text")

    bom_encoding = _bom_encoding(raw)
    if bom_encoding:
        return _decode_required(path, raw, bom_encoding, had_bom=True)

    strict_utf8 = None if utf16_like else _try_decode(raw, "utf-8-sig")
    if strict_utf8 is not None:
        return DecodedDocument(text=strict_utf8, encoding="utf-8", had_bom=False)

    candidates = []
    for encoding in _CANDIDATE_ENCODINGS[1:]:
        decoded = _try_decode(raw, encoding)
        if decoded is not None:
            candidates.append((_decode_score(decoded), encoding, decoded))
    if not candidates:
        raise DocumentInputError(f"{path} could not be decoded as UTF-8, CP1251, KOI8-R, or UTF-16")

    score, encoding, decoded = max(candidates, key=lambda item: item[0])
    if score < 0.35:
        raise DocumentInputError(f"{path} uses an unsupported or malformed text encoding")
    return DecodedDocument(text=decoded, encoding=encoding, had_bom=False)


def read_text(path: Path) -> str:
    """Return only the decoded text for callers that do not need metadata."""

    return read_text_document(path).text


def _decode_required(path: Path, raw: bytes, encoding: str, *, had_bom: bool) -> DecodedDocument:
    try:
        return DecodedDocument(text=raw.decode(encoding), encoding=encoding, had_bom=had_bom)
    except UnicodeDecodeError as exc:
        raise DocumentInputError(f"{path} declares {encoding} but could not be decoded") from exc


def _try_decode(raw: bytes, encoding: str) -> str | None:
    try:
        return raw.decode(encoding)
    except UnicodeDecodeError:
        return None


def _bom_encoding(raw: bytes) -> str | None:
    for marker, encoding in _BOMS:
        if raw.startswith(marker):
            return encoding
    return None


def _looks_binary(raw: bytes) -> bool:
    if _has_utf16_pattern(raw):
        return False
    controls = sum(1 for byte in raw if byte < 32 and byte not in {9, 10, 13})
    return (controls / max(1, len(raw))) > 0.05


def _has_utf16_pattern(raw: bytes) -> bool:
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return True
    if len(raw) < 8:
        return False
    return (
        _utf16_ascii_lane(raw, nul_offset=0, text_offset=1)
        or _utf16_ascii_lane(raw, nul_offset=1, text_offset=0)
        or _utf16_cyrillic_lane(raw, high_offset=0)
        or _utf16_cyrillic_lane(raw, high_offset=1)
    )


def _utf16_ascii_lane(raw: bytes, *, nul_offset: int, text_offset: int) -> bool:
    nul_ratio = _lane_ratio(raw, nul_offset, lambda byte: byte == 0)
    printable_ratio = _lane_ratio(raw, text_offset, lambda byte: byte in {9, 10, 13} or 32 <= byte <= 126)
    return nul_ratio > 0.35 and printable_ratio > 0.75


def _utf16_cyrillic_lane(raw: bytes, *, high_offset: int) -> bool:
    return _lane_ratio(raw, high_offset, lambda byte: byte in {0x04, 0x05}) > 0.35


def _lane_ratio(raw: bytes, offset: int, predicate) -> float:
    values = raw[offset::2]
    if not values:
        return 0.0
    return sum(1 for byte in values if predicate(byte)) / len(values)


def _decode_score(text: str) -> float:
    if not text:
        return 1.0
    length = len(text)
    controls = sum(1 for char in text if ord(char) < 32 and char not in "\n\r\t")
    replacements = text.count("\ufffd")
    cyrillic = sum(1 for char in text if _is_cyrillic(char))
    printable_ratio = max(0.0, 1.0 - ((controls + replacements) / max(1, length)))
    cyrillic_ratio = cyrillic / max(1, length)
    common_word_ratio = _common_word_ratio(text)
    return printable_ratio + cyrillic_ratio + common_word_ratio


def _common_word_ratio(text: str) -> float:
    words = [match.group(0).casefold() for match in _WORD_RE.finditer(text)]
    if not words:
        return 0.0
    hits = sum(1 for word in words if word in _COMMON_RUSSIAN_WORDS)
    return min(0.5, hits / max(1, len(words)))


def _is_cyrillic(char: str) -> bool:
    codepoint = ord(char)
    return 0x0400 <= codepoint <= 0x052F or 0x2DE0 <= codepoint <= 0x2DFF or 0xA640 <= codepoint <= 0xA69F
