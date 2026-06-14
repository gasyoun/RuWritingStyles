/**
 * Journal-compliance check — a faithful TypeScript port of the engine's
 * report.journal_compliance() (src/ruwritingstyles/report.py). Same length /
 * abstract+keywords-presence logic and the same per-language markers; parity is
 * regression-tested against golden output from the engine
 * (tools/export_journal_fixtures.py → test/journal.test.ts).
 */

import type {
  JournalCompliance,
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

  for (const lang of profile.abstract_required ?? []) {
    const markers = ABSTRACT_MARKERS[lang] ?? [];
    comp.abstract.push({ lang, present: markers.some((m) => low.includes(m)) });
  }
  for (const lang of profile.keywords_required ?? []) {
    const markers = KEYWORDS_MARKERS[lang] ?? [];
    comp.keywords.push({ lang, present: markers.some((m) => low.includes(m)) });
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
    }
  }
  for (const k of comp.keywords) {
    if (!k.present) {
      gaps.push({
        severity: "warning",
        message: `Нет ключевых слов на языке «${k.lang}» (требует «${comp.name}»).`,
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
        comp.abstract.map((a) => `${a.lang} ${a.present ? "✓" : "✗"}`).join(" ")
    );
  }
  if (comp.keywords.length) {
    parts.push(
      "ключевые слова " +
        comp.keywords.map((k) => `${k.lang} ${k.present ? "✓" : "✗"}`).join(" ")
    );
  }
  return `${comp.name}: ${parts.join("; ")}`;
}
