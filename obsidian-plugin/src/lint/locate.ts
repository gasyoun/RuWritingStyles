/**
 * Map a finding to a character range in the *editor* text.
 *
 * The linter runs on normalized text and reports `fragment` / `term` rather than
 * offsets (normalization shifts offsets, and inverting that mapping is brittle).
 * For inline highlighting we instead re-locate the finding directly in the live
 * editor text — robust to normalization, at the cost of picking the first
 * occurrence when a fragment repeats (acceptable for highlighting; refined later
 * if needed).
 */

import type { Finding, Term } from "./types.ts";
import { WORD_PATTERN, hasCyrillic, matchesRuTerm } from "./translit.ts";

export interface Range {
  from: number;
  to: number;
}

/** Returns the editor range for a finding, or null if it can't be located. */
export function locateFinding(text: string, finding: Finding, terms: Term[]): Range | null {
  // 1) Fragment-bearing findings (hybrid word, mixed-scheme HK word, orphan
  //    mātrā): the fragment is the exact substring to highlight.
  if (finding.fragment) {
    const idx = text.indexOf(finding.fragment);
    if (idx >= 0 && finding.fragment.length > 0) {
      return { from: idx, to: idx + finding.fragment.length };
    }
    return null;
  }

  // 2) missing_iast_on_first_mention: highlight the first Cyrillic word that
  //    inflects the term (same predicate the linter used).
  if (finding.type === "missing_iast_on_first_mention" && finding.term) {
    const re = new RegExp(WORD_PATTERN, "gu");
    let m: RegExpExecArray | null;
    while ((m = re.exec(text)) !== null) {
      const w = m[0];
      if (hasCyrillic(w) && matchesRuTerm(w, finding.term)) {
        return { from: m.index, to: m.index + w.length };
      }
    }
    return null;
  }

  // 3) inconsistent_term_rendering: highlight the first IAST form of the term.
  if (finding.type === "inconsistent_term_rendering" && finding.term) {
    const term = terms.find((t) => t.ru === finding.term);
    if (term) {
      const idx = text.toLowerCase().indexOf(term.iast.toLowerCase());
      if (idx >= 0) return { from: idx, to: idx + term.iast.length };
    }
    return null;
  }

  return null;
}

/** Locate every finding, attaching from/to where possible. */
export function locateFindings(text: string, findings: Finding[], terms: Term[]): Finding[] {
  return findings.map((f) => {
    const range = locateFinding(text, f, terms);
    return range ? { ...f, from: range.from, to: range.to } : { ...f };
  });
}
