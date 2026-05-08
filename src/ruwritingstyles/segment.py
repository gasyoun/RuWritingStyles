"""Document normalization and segmentation.

This module is the deterministic front door of the review pipeline. It keeps
Markdown structure stable enough for human-facing span IDs while adding cheap
Russian-aware metrics that downstream reviewers can use without re-tokenizing
large corpora.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
import re
from pathlib import Path
import unicodedata
from typing import Any

from .document import read_text
from .linguistics import iter_sentence_spans, profile_text

_FENCE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
_HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}(?:\s+|$)")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


@dataclass(frozen=True)
class SegmentOptions:
    """Options controlling deterministic Markdown segmentation."""

    max_segment_chars: int = 2400
    split_long_paragraphs: bool = True
    profile_segments: bool = True


@dataclass(frozen=True)
class Segment:
    """A stable document segment addressed by style agents."""

    span_id: str
    segment_type: str
    text: str
    start_line: int
    end_line: int
    metrics: dict[str, Any] | None = None

    tags: tuple[str, ...] = ()

    def to_json(self) -> dict[str, object]:
        data: dict[str, object] = {
            "span_id": self.span_id,
            "type": self.segment_type,
            "text": self.text,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "tags": list(self.tags),
        }
        if self.metrics:
            data["metrics"] = self.metrics
        return data


def read_document(path: Path) -> str:
    """Read a supported text document with Russian corpus encoding fallbacks."""

    return read_text(path)


def normalize_document(text: str, *, max_blank_lines: int = 2) -> str:
    """Normalize line endings and Unicode without erasing philological detail.

    The normalizer preserves ``ё``, historical Cyrillic characters, and
    combining stress marks. It only removes control characters that cannot carry
    meaningful text in Markdown/TXT corpora.
    """

    text = unicodedata.normalize("NFC", text)
    text = text.replace("\ufeff", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_RE.sub("", text)
    text = "\n".join(line.rstrip(" \t") for line in text.split("\n"))
    if max_blank_lines >= 0:
        text = _limit_blank_lines(text, max_blank_lines)
    return text.strip() + "\n"


def segment_markdown(text: str, options: SegmentOptions | None = None) -> list[Segment]:
    """Segment Markdown/TXT into headings, fenced code blocks, and paragraphs."""

    actual_options = options or SegmentOptions()
    lines = text.splitlines()
    segments: list[Segment] = []
    paragraph: list[str] = []
    paragraph_start = 1
    in_fence = False
    fence_marker = ""
    fence: list[str] = []
    fence_start = 1
    pending_tags: list[str] = []

    def flush_paragraph(end_line: int) -> None:
        nonlocal paragraph, paragraph_start, pending_tags
        if not paragraph:
            return
        content = "\n".join(paragraph).strip()
        if content:
            segments.extend(
                _paragraph_segments(
                    content,
                    paragraph,
                    paragraph_start,
                    end_line,
                    tuple(pending_tags),
                    actual_options,
                )
            )
        paragraph = []
        pending_tags = []

    def flush_fence(end_line: int) -> None:
        nonlocal fence, fence_start, pending_tags
        if fence:
            segments.append(_segment("code", "\n".join(fence), fence_start, end_line, tuple(pending_tags), actual_options))
        fence = []
        pending_tags = []

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        fence_match = _FENCE_RE.match(line)

        if fence_match:
            if in_fence:
                if _closes_fence(fence_match.group(1), fence_marker):
                    fence.append(line)
                    flush_fence(index)
                    in_fence = False
                    fence_marker = ""
                else:
                    fence.append(line)
            else:
                flush_paragraph(index - 1)
                in_fence = True
                fence_marker = fence_match.group(1)
                fence_start = index
                fence = [line]
            continue

        if in_fence:
            fence.append(line)
            continue

        if not stripped:
            flush_paragraph(index - 1)
            continue

        if _HEADING_RE.match(line):
            flush_paragraph(index - 1)
            segments.append(_segment("heading", stripped, index, index, tuple(pending_tags), actual_options))
            pending_tags = []
            continue

        if stripped.startswith("<!--") and "rws:" in stripped:
            tag_match = re.search(r"rws:([\w,:-]+)", stripped)
            if tag_match:
                tags = tag_match.group(1).split(",")
                pending_tags.extend(t.strip() for t in tags)
            continue

        if not paragraph:
            paragraph_start = index
        paragraph.append(line)

    if in_fence:
        flush_fence(len(lines))
    else:
        flush_paragraph(len(lines))

    return [_renumber(segment, idx) for idx, segment in enumerate(segments, start=1)]


def _paragraph_segments(
    content: str,
    lines: list[str],
    start_line: int,
    end_line: int,
    tags: tuple[str, ...],
    options: SegmentOptions,
) -> list[Segment]:
    if not options.split_long_paragraphs or options.max_segment_chars <= 0 or len(content) <= options.max_segment_chars:
        return [_segment("paragraph", content, start_line, end_line, tags, options)]

    line_starts = _line_starts(lines)
    chunks = _split_for_review(content, options.max_segment_chars)
    return [
        _segment(
            "paragraph",
            chunk,
            start_line + _line_index(line_starts, chunk_start),
            start_line + _line_index(line_starts, max(chunk_start, chunk_end - 1)),
            tags,
            options,
        )
        for chunk, chunk_start, chunk_end in chunks
    ]


def _split_for_review(text: str, max_chars: int) -> list[tuple[str, int, int]]:
    spans = list(iter_sentence_spans(text)) or [(0, len(text))]
    chunks: list[tuple[str, int, int]] = []
    current_start: int | None = None
    current_end = 0
    current_texts: list[str] = []

    def flush() -> None:
        nonlocal current_start, current_end, current_texts
        if current_start is None or not current_texts:
            return
        chunk = " ".join(part.strip() for part in current_texts if part.strip()).strip()
        if chunk:
            chunks.append((chunk, current_start, current_end))
        current_start = None
        current_end = 0
        current_texts = []

    for start, end in spans:
        sentence = text[start:end].strip()
        if not sentence:
            continue
        if len(sentence) > max_chars:
            flush()
            chunks.extend(_hard_wrap(text, start, end, max_chars))
            continue
        candidate_len = len(" ".join([*current_texts, sentence]))
        if current_texts and candidate_len > max_chars:
            flush()
        if current_start is None:
            current_start = start
        current_end = end
        current_texts.append(sentence)
    flush()
    return chunks


def _hard_wrap(text: str, start: int, end: int, max_chars: int) -> list[tuple[str, int, int]]:
    wrapped: list[tuple[str, int, int]] = []
    current_start: int | None = None
    current_end = start
    current_words: list[str] = []

    def flush() -> None:
        nonlocal current_start, current_end, current_words
        if current_start is None or not current_words:
            return
        wrapped.append((" ".join(current_words), current_start, current_end))
        current_start = None
        current_end = start
        current_words = []

    for match in re.finditer(r"\S+", text[start:end]):
        word_start = start + match.start()
        word_end = start + match.end()
        word = match.group(0)
        candidate_len = len(" ".join([*current_words, word]))
        if current_words and candidate_len > max_chars:
            flush()
        if current_start is None:
            current_start = word_start
        current_end = word_end
        current_words.append(word)
    flush()
    return wrapped


def _segment(
    segment_type: str,
    text: str,
    start_line: int,
    end_line: int,
    tags: tuple[str, ...],
    options: SegmentOptions,
) -> Segment:
    metrics = profile_text(text).to_json() if options.profile_segments else None
    return Segment(
        span_id="pending",
        segment_type=segment_type,
        text=text,
        start_line=start_line,
        end_line=end_line,
        metrics=metrics,
        tags=tags,
    )


def _renumber(segment: Segment, index: int) -> Segment:
    prefix = {
        "heading": "h",
        "paragraph": "p",
        "code": "c",
    }.get(segment.segment_type, "s")

    return Segment(
        span_id=f"{prefix}{index:03d}",
        segment_type=segment.segment_type,
        text=segment.text,
        start_line=segment.start_line,
        end_line=segment.end_line,
        metrics=segment.metrics,
        tags=segment.tags,
    )


def _closes_fence(candidate: str, opener: str) -> bool:
    return bool(opener) and candidate[0] == opener[0] and len(candidate) >= len(opener)


def _limit_blank_lines(text: str, max_blank_lines: int) -> str:
    output: list[str] = []
    blank_count = 0
    for line in text.split("\n"):
        if line:
            blank_count = 0
            output.append(line)
            continue
        blank_count += 1
        if blank_count <= max_blank_lines:
            output.append(line)
    return "\n".join(output)


def _line_starts(lines: list[str]) -> list[int]:
    starts: list[int] = []
    offset = 0
    for line in lines:
        starts.append(offset)
        offset += len(line) + 1
    return starts or [0]


def _line_index(line_starts: list[int], offset: int) -> int:
    return max(0, bisect_right(line_starts, offset) - 1)
