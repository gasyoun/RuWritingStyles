"""Document normalization and segmentation."""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path


@dataclass(frozen=True)
class Segment:
    """A stable document segment addressed by style agents."""

    span_id: str
    segment_type: str
    text: str
    start_line: int
    end_line: int

    def to_json(self) -> dict[str, object]:
        return {
            "span_id": self.span_id,
            "type": self.segment_type,
            "text": self.text,
            "start_line": self.start_line,
            "end_line": self.end_line,
        }


def read_document(path: Path) -> str:
    if path.suffix.lower() not in {".md", ".txt"}:
        raise ValueError("only .md and .txt inputs are supported in the first CLI layer")
    return path.read_text(encoding="utf-8")


def normalize_document(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip() + "\n"


def segment_markdown(text: str) -> list[Segment]:
    """Segment Markdown/TXT into headings, fenced code blocks, and paragraphs."""

    lines = text.splitlines()
    segments: list[Segment] = []
    paragraph: list[str] = []
    paragraph_start = 1
    in_fence = False
    fence: list[str] = []
    fence_start = 1

    def flush_paragraph(end_line: int) -> None:
        nonlocal paragraph, paragraph_start
        if not paragraph:
            return
        content = "\n".join(paragraph).strip()
        if content:
            segments.append(_segment("paragraph", content, paragraph_start, end_line))
        paragraph = []

    def flush_fence(end_line: int) -> None:
        nonlocal fence, fence_start
        if fence:
            segments.append(_segment("code", "\n".join(fence), fence_start, end_line))
        fence = []

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_fence:
                fence.append(line)
                flush_fence(index)
                in_fence = False
            else:
                flush_paragraph(index - 1)
                in_fence = True
                fence_start = index
                fence = [line]
            continue

        if in_fence:
            fence.append(line)
            continue

        if not stripped:
            flush_paragraph(index - 1)
            continue

        if stripped.startswith("#"):
            flush_paragraph(index - 1)
            segments.append(_segment("heading", stripped, index, index))
            continue

        if not paragraph:
            paragraph_start = index
        paragraph.append(line)

    if in_fence:
        flush_fence(len(lines))
    else:
        flush_paragraph(len(lines))

    return [_renumber(segment, idx) for idx, segment in enumerate(segments, start=1)]


def _segment(segment_type: str, text: str, start_line: int, end_line: int) -> Segment:
    return Segment(
        span_id="pending",
        segment_type=segment_type,
        text=text,
        start_line=start_line,
        end_line=end_line,
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
    )
