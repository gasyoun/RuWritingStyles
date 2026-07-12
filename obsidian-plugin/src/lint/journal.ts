/**
 * Journal-compliance check — a faithful TypeScript port of the engine's
 * report.journal_compliance() (src/ruwritingstyles/report.py). Same length /
 * abstract+keywords-presence logic and the same per-language markers; parity is
 * regression-tested against golden output from the engine
 * (tools/export_journal_fixtures.py → test/journal.test.ts).
 */

import type {
  JournalCompliance,
  JournalLangCheck,
  JournalProfile,
  Severity,
} from "./types.ts";

// Mirrors ABSTRACT_MARKERS / KEYWORDS_MARKERS in report.py — keep in sync.
const ABSTRACT_MARKERS: Record<string, string[]> = {
  ru: ["аннотац", "резюме"],
  en: ["abstract"],
};
const KEYWORDS_MARKERS: Record<string, string[]> = {
  ru: ["ключевые слова"],
  en: ["keywords", "key words"],
};

// A "word" is a maximal run of letters/digits — mirrors the engine's
// _WORD_RE = /[^\W_]+/u in report.py. Keep the two definitions equivalent.
const WORD_RE = /[\p{L}\p{N}]+/gu;
const ALPHA_RE = /\p{L}/u;
const ALNUM_RE = /[\p{L}\p{N}]/u;

/** Count words in an abstract body for one language — a faithful port of the
 *  engine's report._abstract_word_count(). Tuned for the inline
 *  «**Аннотация.** текст…» style; an abstract under its own heading with a
 *  blank line before the body is under-counted, which is safe for a maximum. */
function abstractWordCount(text: string, low: string, markers: string[]): number {
  let idx = -1;
  let mlen = 0;
  for (const m of markers) {
    const pos = low.indexOf(m);
    if (pos !== -1 && (idx === -1 || pos < idx)) {
      idx = pos;
      mlen = m.length;
    }
  }
  if (idx === -1) return 0;
  const end = text.indexOf("\n\n", idx);
  const block = end === -1 ? text.slice(idx) : text.slice(idx, end);
  let j = mlen;
  while (j < block.length && ALPHA_RE.test(block[j])) j++; // rest of the label word
  while (j < block.length && !ALNUM_RE.test(block[j])) j++; // punctuation / emphasis / space
  return (block.slice(j).match(WORD_RE) ?? []).length;
}

/** Run the journal-compliance check, or null when no journal is selected. */
export function checkJournal(
  text: string,
  profile: JournalProfile | null
): JournalCompliance | null {
  if (!profile || !profile.name) return null;
  const normalized = text.replace(/\r\n/g, "\n");
  const low = normalized.toLowerCase();

  const comp: JournalCompliance = {
    name: profile.name,
    length: null,
    // null (not undefined) to mirror the engine's JSON shape for absent fields.
    citationFormat: profile.citation_format ?? null,
    transliterationScheme: profile.transliteration_scheme ?? null,
    abstract: [],
    keywords: [],
  };

  if (typeof profile.max_chars === "number" && profile.max_chars > 0) {
    // Count code points to match Python len(); BMP-only text is unaffected.
    const current = [...normalized].length;
    comp.length = {
      current,
      max: profile.max_chars,
      over: Math.max(0, current - profile.max_chars),
    };
  }

  const maxWords =
    typeof profile.abstract_max_words === "number" && profile.abstract_max_words > 0
      ? profile.abstract_max_words
      : null;
  for (const lang of profile.abstract_required ?? []) {
    const markers = ABSTRACT_MARKERS[lang] ?? [];
    const present = markers.some((m) => low.includes(m));
    const item: JournalLangCheck = { lang, present };
    if (maxWords !== null && present) {
      const words = abstractWordCount(normalized, low, markers);
      item.words = words;
      item.max = maxWords;
      item.over = Math.max(0, words - maxWords);
    }
    comp.abstract.push(item);
  }
  const kwMaxWords =
    typeof profile.keywords_max_words === "number" && profile.keywords_max_words > 0
      ? profile.keywords_max_words
      : null;
  for (const lang of profile.keywords_required ?? []) {
    const markers = KEYWORDS_MARKERS[lang] ?? [];
    const present = markers.some((m) => low.includes(m));
    const item: JournalLangCheck = { lang, present };
    if (kwMaxWords !== null && present) {
      // Same block logic as the abstract — journals phrase the limit in words
      // («не может превышать 10 слов» — Восток/Oriens). Mirrors report.py.
      const words = abstractWordCount(normalized, low, markers);
      item.words = words;
      item.max = kwMaxWords;
      item.over = Math.max(0, words - kwMaxWords);
    }
    comp.keywords.push(item);
  }
  return comp;
}

export interface JournalGap {
  message: string;
  severity: Severity;
}

/** The actionable gaps (over-length, missing abstract/keywords by language)
 *  surfaced as warnings in the problems panel. Empty if fully compliant. */
export function journalGaps(comp: JournalCompliance): JournalGap[] {
  const gaps: JournalGap[] = [];
  if (comp.length && comp.length.over > 0) {
    gaps.push({
      severity: "warning",
      message:
        `Объём ${comp.length.current} знаков превышает лимит журнала ` +
        `«${comp.name}» (${comp.length.max}) на ${comp.length.over}.`,
    });
  }
  for (const a of comp.abstract) {
    if (!a.present) {
      gaps.push({
        severity: "warning",
        message: `Нет аннотации на языке «${a.lang}» (требует «${comp.name}»).`,
      });
    } else if (a.over && a.over > 0) {
      gaps.push({
        severity: "warning",
        message:
          `Аннотация «${a.lang}» — ${a.words} слов, превышает лимит журнала ` +
          `«${comp.name}» (${a.max}) на ${a.over}.`,
      });
    }
  }
  for (const k of comp.keywords) {
    if (!k.present) {
      gaps.push({
        severity: "warning",
        message: `Нет ключевых слов на языке «${k.lang}» (требует «${comp.name}»).`,
      });
    } else if (k.over && k.over > 0) {
      gaps.push({
        severity: "warning",
        message:
          `Ключевые слова «${k.lang}» — ${k.words} слов, превышает лимит журнала ` +
          `«${comp.name}» (${k.max}) на ${k.over}.`,
      });
    }
  }
  return gaps;
}

/** One-line checklist (incl. the passing items) for the command's Notice. */
export function summarizeJournal(comp: JournalCompliance): string {
  const parts: string[] = [];
  if (comp.length) {
    parts.push(
      `объём ${comp.length.current}/${comp.length.max}` +
        (comp.length.over > 0 ? ` (+${comp.length.over})` : " ✓")
    );
  }
  if (comp.abstract.length) {
    parts.push(
      "аннотация " +
        comp.abstract
          .map((a) => {
            const base = `${a.lang} ${a.present ? "✓" : "✗"}`;
            if (a.words === undefined) return base;
            return `${base} (${a.words}/${a.max}${a.over ? ` +${a.over}` : " ✓"})`;
          })
          .join(" ")
    );
  }
  if (comp.keywords.length) {
    parts.push(
      "ключевые слова " +
        comp.keywords
          .map((k) => {
            const base = `${k.lang} ${k.present ? "✓" : "✗"}`;
            if (k.words === undefined) return base;
            return `${base} (${k.words}/${k.max}${k.over ? ` +${k.over}` : " ✓"})`;
          })
          .join(" ")
    );
  }
  return `${comp.name}: ${parts.join("; ")}`;
}
