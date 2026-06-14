import { Editor, MarkdownFileInfo, MarkdownView, Notice, Plugin } from "obsidian";

import { TERMS, JOURNALS } from "./assets.ts";
import { lintText } from "./lint/translit.ts";
import type { Finding } from "./lint/types.ts";

/**
 * RuWritingStyles — Obsidian plugin.
 *
 * M1: the deterministic transliteration linter (a faithful TypeScript port of
 * the engine's translit_lint.py, parity-tested against `rws lint-translit`) runs
 * on the current note and reports a summary. Inline highlighting and the side
 * panel are M2; journal-compliance is M3. See docs/obsidian-plugin-plan.md.
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

  async onload(): Promise<void> {
    await this.loadSettings();

    this.addCommand({
      id: "lint-current-note",
      name: "Lint current note (transliteration)",
      editorCallback: (editor: Editor, _ctx: MarkdownView | MarkdownFileInfo) => {
        this.lintEditor(editor);
      },
    });
  }

  onunload(): void {}

  private lintEditor(editor: Editor): void {
    const profile = JOURNALS[this.settings.journal] ?? null;
    const result = lintText(editor.getValue(), TERMS, profile);
    const findings = result.findings;

    if (findings.length === 0) {
      new Notice("RuWritingStyles: транслитерация — замечаний нет.");
      return;
    }
    const errors = findings.filter((f) => f.severity === "error").length;
    const warnings = findings.length - errors;
    new Notice(
      `RuWritingStyles: ${findings.length} замечани${plural(findings.length)} ` +
        `(${errors} ошиб., ${warnings} предупр.). Подробности — в консоли.`
    );
    // M2 will render these inline + in a side panel. For now, log them.
    console.log("[RuWritingStyles] findings:", findings.map(describe));
  }

  async loadSettings(): Promise<void> {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
  }
}

function describe(f: Finding): string {
  const where = f.fragment ? ` [${f.fragment}]` : f.term ? ` [${f.term}]` : "";
  return `${f.severity} ${f.type}: ${f.message}${where}`;
}

function plural(n: number): string {
  const d = n % 10;
  const dd = n % 100;
  if (d === 1 && dd !== 11) return "е";
  if (d >= 2 && d <= 4 && (dd < 12 || dd > 14)) return "я";
  return "й";
}
