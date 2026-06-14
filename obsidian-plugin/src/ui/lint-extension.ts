/**
 * CodeMirror 6 editor extension that drives RuWritingStyles findings through the
 * editor's *native* lint system (@codemirror/lint, bundled by Obsidian).
 *
 * Using the native linter gives us, for free: wavy underlines, hover message
 * bubbles, the built-in toggleable problems panel, and F8 / next-diagnostic
 * navigation. We just supply a `linter()` source that runs the ported
 * deterministic checks and reports counts back to the host for the status bar.
 */

import { EditorView, keymap } from "@codemirror/view";
import type { Extension } from "@codemirror/state";
import { forEachDiagnostic, linter, lintKeymap } from "@codemirror/lint";
import type { Diagnostic } from "@codemirror/lint";

import { lintText } from "../lint/translit.ts";
import { locateFindings } from "../lint/locate.ts";
import { checkJournal, journalGaps } from "../lint/journal.ts";
import { iastInsertion } from "../lint/quickfix.ts";
import type { FindingType, JournalProfile, Term } from "../lint/types.ts";

/** `source` tag on our diagnostics, so we count only our own. */
export const RWS_SOURCE = "RuWritingStyles";

export interface LintConfig {
  terms: Term[];
  journal: JournalProfile | null;
  /** Per-finding-type enable map; a type is on unless explicitly false. */
  enabledChecks: Record<string, boolean>;
}

/** Whether a finding type is enabled (default on). */
function isEnabled(checks: Record<string, boolean>, type: FindingType): boolean {
  return checks[type] !== false;
}

export interface RwsLintHost {
  /** Read live so a settings change (journal) takes effect on the next lint. */
  getLintConfig(): LintConfig;
  /** Report this editor's RWS error/warning counts for the status bar. */
  reportCounts(errors: number, warnings: number): void;
}

/** Tally RWS diagnostics in a CM6 state into error/warning counts. */
export function countRwsDiagnostics(
  diagnostics: Iterable<Diagnostic>
): { errors: number; warnings: number } {
  let errors = 0;
  let warnings = 0;
  for (const d of diagnostics) {
    if (d.source !== RWS_SOURCE) continue;
    if (d.severity === "error") errors++;
    else if (d.severity === "warning") warnings++;
  }
  return { errors, warnings };
}

export function makeRwsLintExtension(host: RwsLintHost): Extension {
  const lintSource = (view: EditorView): Diagnostic[] => {
    const { terms, journal, enabledChecks } = host.getLintConfig();
    const text = view.state.doc.toString();
    const result = lintText(text, terms, journal);
    const located = locateFindings(text, result.findings, terms);

    const diagnostics: Diagnostic[] = [];
    for (const f of located) {
      // Respect the per-type toggles (M4) and only show anchored findings.
      if (!isEnabled(enabledChecks, f.type)) continue;
      if (f.from == null || f.to == null || f.to <= f.from) continue;
      const diagnostic: Diagnostic = {
        from: f.from,
        to: f.to,
        severity: f.severity === "error" ? "error" : "warning",
        message: f.message,
        source: RWS_SOURCE,
      };
      // Quick-fix (M4): insert " (iast)" after a flagged first mention.
      const insertion = iastInsertion(f, terms);
      if (insertion) {
        diagnostic.actions = [
          {
            name: "Вставить IAST",
            apply: (editorView, _from, to) => {
              editorView.dispatch({ changes: { from: to, insert: insertion } });
            },
          },
        ];
      }
      diagnostics.push(diagnostic);
    }

    // Journal-compliance gaps are document-level; anchor them to the first line
    // (where article metadata lives) so they show in the same problems panel.
    if (text.length > 0) {
      const compliance = checkJournal(text, journal);
      if (compliance) {
        const newline = text.indexOf("\n");
        const end = newline > 0 ? newline : text.length;
        for (const gap of journalGaps(compliance)) {
          diagnostics.push({
            from: 0,
            to: end,
            severity: gap.severity === "error" ? "error" : "warning",
            message: gap.message,
            source: RWS_SOURCE,
          });
        }
      }
    }
    return diagnostics;
  };

  // Keep the status bar in sync with the focused editor's diagnostics. The lint
  // source dispatches its own transaction when results change, which re-fires
  // this listener, so counts converge after the debounce.
  const statusSync = EditorView.updateListener.of((update) => {
    if (!update.view.hasFocus) return;
    const collected: Diagnostic[] = [];
    forEachDiagnostic(update.state, (d) => collected.push(d));
    const { errors, warnings } = countRwsDiagnostics(collected);
    host.reportCounts(errors, warnings);
  });

  return [linter(lintSource, { delay: 400 }), keymap.of(lintKeymap), statusSync];
}
