/**
 * Quick-fix helpers (M4). Pure logic, unit-tested separately; the CodeMirror
 * `action` wiring in ui/lint-extension.ts calls into this.
 */

import type { Finding, Term } from "./types.ts";

/**
 * Text to insert *after* a flagged first mention to satisfy the IAST rule —
 * e.g. "веда" → " (veda)" — or null if this finding has no such fix (wrong type,
 * or the term isn't in the dictionary).
 */
export function iastInsertion(finding: Finding, terms: Term[]): string | null {
  if (finding.type !== "missing_iast_on_first_mention" || !finding.term) return null;
  const term = terms.find((t) => t.ru === finding.term);
  if (!term || !term.iast) return null;
  return ` (${term.iast})`;
}
