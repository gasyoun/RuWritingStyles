import { Editor, MarkdownFileInfo, MarkdownView, Notice, Plugin } from "obsidian";
import type { EditorView } from "@codemirror/view";
import { forEachDiagnostic, forceLinting, openLintPanel } from "@codemirror/lint";
import type { Diagnostic } from "@codemirror/lint";

import { JOURNALS, TERMS } from "./assets.ts";
import { lintText } from "./lint/translit.ts";
import { locateFindings } from "./lint/locate.ts";
import { checkJournal, summarizeJournal } from "./lint/journal.ts";
import { RwsSettingTab } from "./settings.ts";
import type { JournalProfile, Term } from "./lint/types.ts";
import {
  RWS_SOURCE,
  countRwsDiagnostics,
  makeRwsLintExtension,
} from "./ui/lint-extension.ts";

/**
 * RuWritingStyles — Obsidian plugin.
 *
 * Findings surface through the editor's native lint system (@codemirror/lint) —
 * wavy underlines, hover bubbles, the built-in problems panel, and F8 navigation,
 * plus a status-bar count. The deterministic transliteration linter (M1/M2) and
 * the journal-compliance check (M3) are parity-tested ports of the engine; a
 * settings tab picks the journal profile. See docs/obsidian-plugin-plan.md.
 */

export interface RwsSettings {
  /** Journal profile id ("none" | "vya" | "ppv" | "vestnik-spbu"). Drives the
   *  first-mention rule (and, in M3, the compliance section). */
  journal: string;
  /** Re-lint on save (debounced). Off by default. */
  lintOnSave: boolean;
}

export const DEFAULT_SETTINGS: RwsSettings = {
  journal: "none",
  lintOnSave: false,
};

export default class RuWritingStylesPlugin extends Plugin {
  settings: RwsSettings = DEFAULT_SETTINGS;
  readonly terms: Term[] = TERMS;
  private statusBar: HTMLElement | null = null;

  async onload(): Promise<void> {
    await this.loadSettings();

    this.statusBar = this.addStatusBarItem();
    this.statusBar.addClass("rws-statusbar");

    // Native-lint editor extension: continuous (debounced) underlines + panel.
    this.registerEditorExtension(
      makeRwsLintExtension({
        getLintConfig: () => ({ terms: this.terms, journal: this.currentJournal() }),
        reportCounts: (errors, warnings) => this.setStatus(errors, warnings),
      })
    );

    this.addSettingTab(new RwsSettingTab(this.app, this));

    // Command: re-lint now and open the problems panel.
    this.addCommand({
      id: "lint-current-note",
      name: "Lint current note (show problems)",
      editorCallback: (editor: Editor, _ctx: MarkdownView | MarkdownFileInfo) =>
        this.showProblems(editor),
    });

    // Keep the status bar synced when switching or closing notes.
    this.registerEvent(
      this.app.workspace.on("active-leaf-change", () => this.refreshStatus())
    );
    this.refreshStatus();
  }

  onunload(): void {}

  /** Resolve the active journal profile (or null for "none"). */
  currentJournal(): JournalProfile | null {
    return JOURNALS[this.settings.journal] ?? null;
  }

  /** Obsidian's Editor wraps a CM6 EditorView, exposed (untyped) as `.cm`. */
  private cmOf(editor: Editor): EditorView | null {
    return (editor as unknown as { cm?: EditorView }).cm ?? null;
  }

  private showProblems(editor: Editor): void {
    const cm = this.cmOf(editor);
    if (cm) {
      forceLinting(cm);
      openLintPanel(cm);
    }
    const text = editor.getValue();
    const profile = this.currentJournal();
    const findings = lintText(text, this.terms, profile).findings;

    const lines: string[] = [];
    if (findings.length === 0) {
      lines.push("транслитерация — замечаний нет");
    } else {
      // Most findings anchor to a range and show inline; surface any that don't.
      const located = locateFindings(text, findings, this.terms).filter(
        (f) => f.from != null && f.to != null
      ).length;
      lines.push(`транслитерация — ${findings.length} замечани${plural(findings.length)}`);
      if (located < findings.length) {
        lines.push(`${findings.length - located} без точной привязки (не показаны в тексте)`);
      }
    }

    // Journal compliance checklist (incl. the passing items the panel omits).
    const compliance = checkJournal(text, profile);
    if (compliance) lines.push(summarizeJournal(compliance));

    new Notice("RuWritingStyles: " + lines.join(" · "), 12000);
  }

  /** Re-lint every open markdown editor (after a settings change). */
  relintAll(): void {
    for (const leaf of this.app.workspace.getLeavesOfType("markdown")) {
      const cm = this.cmOf((leaf.view as MarkdownView).editor);
      if (cm) forceLinting(cm);
    }
    this.refreshStatus();
  }

  private setStatus(errors: number, warnings: number): void {
    if (!this.statusBar) return;
    this.statusBar.setText(
      errors === 0 && warnings === 0 ? "RWS ✓" : `RWS ✗${errors} ⚠${warnings}`
    );
  }

  /** Recount from the active note's editor (covers leaf switches). */
  private refreshStatus(): void {
    const view = this.app.workspace.getActiveViewOfType(MarkdownView);
    const cm = view ? this.cmOf(view.editor) : null;
    if (!cm) {
      this.statusBar?.setText("");
      return;
    }
    const collected: Diagnostic[] = [];
    forEachDiagnostic(cm.state, (d) => {
      if (d.source === RWS_SOURCE) collected.push(d);
    });
    const { errors, warnings } = countRwsDiagnostics(collected);
    this.setStatus(errors, warnings);
  }

  async loadSettings(): Promise<void> {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
  }
}

/** Russian plural suffix for «замечание/замечания/замечаний». */
function plural(n: number): string {
  const d = n % 10;
  const dd = n % 100;
  if (d === 1 && dd !== 11) return "е";
  if (d >= 2 && d <= 4 && (dd < 12 || dd > 14)) return "я";
  return "й";
}
