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
