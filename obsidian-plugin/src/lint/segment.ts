/**
 * Port of the engine's segment.py — normalize_document + segment_markdown.
 *
 * Scope: the blank-line / heading / fenced-code state machine, which is what the
 * transliteration linter consumes. The engine additionally sub-splits paragraphs
 * longer than 2400 chars via sentence spans (linguistics.iter_sentence_spans);
 * that path is intentionally NOT ported — it only affects span ids of very long
 * single paragraphs, and the parity fixtures stay under the threshold. See
 * docs/obsidian-plugin-plan.md §5.
 */

import type { Segment } from "./types.ts";

const FENCE_RE = /^[ \t]{0,3}(`{3,}|~{3,})/;
const HEADING_RE = /^[ \t]{0,3}#{1,6}(?:\s+|$)/;
// Control chars the engine strips: \x00-\x08, \x0b, \x0c, \x0e-\x1f.
const CONTROL_RE = /[\x00-\x08\x0b\x0c\x0e-\x1f]/g;

/** Engine normalize_document: NFC, line-ending + control-char + trailing-space
 *  cleanup, blank-line collapsing, and a single trailing newline. */
export function normalizeDocument(text: string, maxBlankLines = 2): string {
  let t = text.normalize("NFC");
  t = t.replace(/﻿/g, "");
  t = t.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  t = t.replace(CONTROL_RE, "");
  t = t
    .split("\n")
    .map((line) => line.replace(/[ \t]+$/, ""))
    .join("\n");
  if (maxBlankLines >= 0) {
    t = limitBlankLines(t, maxBlankLines);
  }
  return t.replace(/^\s+|\s+$/g, "") + "\n";
}

function limitBlankLines(text: string, maxBlankLines: number): string {
  const out: string[] = [];
  let blank = 0;
  for (const line of text.split("\n")) {
    if (line) {
      blank = 0;
      out.push(line);
      continue;
    }
    blank += 1;
    if (blank <= maxBlankLines) out.push(line);
  }
  return out.join("\n");
}

/** Python str.splitlines() over already-normalized text (only \n remains):
 *  split on \n and drop the trailing empty element from the final newline. */
function splitLines(text: string): string[] {
  const parts = text.split("\n");
  if (parts.length > 0 && parts[parts.length - 1] === "") parts.pop();
  return parts;
}

function closesFence(candidate: string, opener: string): boolean {
  return !!opener && candidate[0] === opener[0] && candidate.length >= opener.length;
}

/**
 * Segment normalized Markdown into headings (`h`), fenced code (`c`), and
 * paragraphs (`p`). Span ids are assigned `{prefix}{index:03d}` exactly as the
 * engine does. Each segment records its absolute start offset in `text`.
 */
export function segmentMarkdown(text: string): Segment[] {
  const lines = splitLines(text);
  // Precompute absolute offset of each line start in `text`.
  const lineOffsets: number[] = [];
  let off = 0;
  for (const line of lines) {
    lineOffsets.push(off);
    off += line.length + 1; // + the \n
  }

  interface Raw {
    type: "heading" | "paragraph" | "code";
    text: string;
    offset: number;
  }
  const raw: Raw[] = [];

  let paragraph: string[] = [];
  let paragraphStartLine = 0; // 0-based index into lines
  let inFence = false;
  let fenceMarker = "";
  let fence: string[] = [];
  let fenceStartLine = 0;

  const flushParagraph = (): void => {
    if (paragraph.length === 0) return;
    const content = paragraph.join("\n").replace(/^\s+|\s+$/g, "");
    if (content) {
      raw.push({ type: "paragraph", text: content, offset: lineOffsets[paragraphStartLine] ?? 0 });
    }
    paragraph = [];
  };

  const flushFence = (): void => {
    if (fence.length > 0) {
      raw.push({ type: "code", text: fence.join("\n"), offset: lineOffsets[fenceStartLine] ?? 0 });
    }
    fence = [];
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const stripped = line.replace(/^\s+|\s+$/g, "");
    const fenceMatch = FENCE_RE.exec(line);

    if (fenceMatch) {
      if (inFence) {
        fence.push(line);
        if (closesFence(fenceMatch[1], fenceMarker)) {
          flushFence();
          inFence = false;
          fenceMarker = "";
        }
      } else {
        flushParagraph();
        inFence = true;
        fenceMarker = fenceMatch[1];
        fenceStartLine = i;
        fence = [line];
      }
      continue;
    }

    if (inFence) {
      fence.push(line);
      continue;
    }

    if (!stripped) {
      flushParagraph();
      continue;
    }

    if (HEADING_RE.test(line)) {
      flushParagraph();
      raw.push({ type: "heading", text: stripped, offset: lineOffsets[i] ?? 0 });
      continue;
    }

    if (stripped.startsWith("<!--") && stripped.includes("rws:")) {
      // rws tag comment — consumed by the engine, not prose; skip.
      continue;
    }

    if (paragraph.length === 0) paragraphStartLine = i;
    paragraph.push(line);
  }

  if (inFence) flushFence();
  else flushParagraph();

  const prefix: Record<Raw["type"], string> = { heading: "h", paragraph: "p", code: "c" };
  return raw.map((seg, idx) => ({
    span_id: `${prefix[seg.type]}${String(idx + 1).padStart(3, "0")}`,
    text: seg.text,
    start_offset: seg.offset,
  }));
}
