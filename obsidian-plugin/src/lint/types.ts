/**
 * Shared types for the RuWritingStyles deterministic checks.
 * Mirrors the engine's translit-lint / journal-profile JSON shapes.
 */

/** One entry of knowledge/sanskrit-terms.json. */
export interface Term {
  ru: string;
  iast: string;
  source?: string;
  note?: string;
  proper_noun?: boolean;
}

/** A journal submission profile (knowledge/journals/<id>.json). */
export interface JournalProfile {
  id?: string;
  name?: string;
  max_chars?: number;
  citation_format?: string;
  transliteration_scheme?: string;
  first_mention_rule?: string;
  abstract_required?: string[];
  abstract_max_words?: number;
  keywords_required?: string[];
  notes?: string;
}

/** The five transliteration-lint finding types (engine FINDING_TYPES). */
export type FindingType =
  | "mixed_transliteration_scheme"
  | "inconsistent_term_rendering"
  | "missing_iast_on_first_mention"
  | "devanagari_nfc_issue"
  | "iast_in_cyrillic_word";

/** Ordered list of the finding types (for settings toggles, defaults). */
export const FINDING_TYPES: FindingType[] = [
  "mixed_transliteration_scheme",
  "inconsistent_term_rendering",
  "missing_iast_on_first_mention",
  "devanagari_nfc_issue",
  "iast_in_cyrillic_word",
];

/** Human (Russian) labels for the finding types, used in the settings tab. */
export const FINDING_TYPE_LABELS: Record<FindingType, string> = {
  mixed_transliteration_scheme: "Смешение схем транслитерации (IAST / Harvard-Kyoto)",
  inconsistent_term_rendering: "Непоследовательная передача термина",
  missing_iast_on_first_mention: "Нет IAST при первом упоминании",
  devanagari_nfc_issue: "Деванагари (NFC / OCR)",
  iast_in_cyrillic_word: "Латиница внутри кириллического слова",
};

export type Severity = "error" | "warning";

/** A lint finding. `from`/`to` are absolute offsets into the *original* note,
 *  added by the editor layer (M2); the core linter leaves them undefined. */
export interface Finding {
  span_id: string;
  type: FindingType;
  message: string;
  severity: Severity;
  fragment?: string;
  term?: string;
  from?: number;
  to?: number;
}

/** Presence of a required abstract/keywords block in one language. The word
 *  fields are present only for abstracts when the profile sets
 *  `abstract_max_words` and the block is present. */
export interface JournalLangCheck {
  lang: string;
  present: boolean;
  words?: number;
  max?: number;
  /** words over the limit; 0 = within limit. */
  over?: number;
}

export interface JournalLength {
  current: number;
  max: number;
  /** chars over the limit; 0 = within limit. */
  over: number;
}

/** Result of the journal-compliance check — mirrors the engine's
 *  report.journal_compliance() (camelCased). */
export interface JournalCompliance {
  name?: string;
  length: JournalLength | null;
  citationFormat: string | null;
  transliterationScheme: string | null;
  abstract: JournalLangCheck[];
  keywords: JournalLangCheck[];
}

export interface LintSummary {
  segments_checked: number;
  iast_word_count: number;
  hk_word_count: number;
  schemes_detected: string[];
  finding_counts: Record<FindingType, number>;
}

export interface LintResult {
  status: "completed";
  findings: Finding[];
  summary: LintSummary;
}

/** A segment of the note: prose (`p`/`h` span ids) or code (`c`, skipped). */
export interface Segment {
  span_id: string;
  text: string;
  /** Absolute start offset in the normalized text (for M2 range mapping). */
  start_offset: number;
}

/** Keep only well-formed term entries (engine load_sanskrit_terms). */
export function filterTerms(raw: unknown[]): Term[] {
  return (raw as Term[]).filter((t) => t && typeof t === "object" && t.ru && t.iast);
}
