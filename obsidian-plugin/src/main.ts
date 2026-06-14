import { Editor, MarkdownFileInfo, MarkdownView, Notice, Plugin } from "obsidian";

/**
 * RuWritingStyles — Obsidian plugin.
 *
 * M0 (this commit): scaffold only. Registers the command surface and settings
 * shell so the plugin loads and the command appears in the palette. The actual
 * deterministic linter (transliteration + journal compliance) is a TypeScript
 * port of the engine's translit_lint.py / report journal section and lands in
 * M1–M3 — see docs/obsidian-plugin-plan.md.
 */

export interface RwsSettings {
  /** Journal profile id ("none" | "vya" | "ppv" | "vestnik-spbu"). Drives the
   *  first-mention rule and the compliance section. */
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

    // Displayed in the palette as "RuWritingStyles: Lint current note …"
    // (Obsidian prefixes the plugin name automatically).
    this.addCommand({
      id: "lint-current-note",
      name: "Lint current note (transliteration + journal)",
      editorCallback: (_editor: Editor, _ctx: MarkdownView | MarkdownFileInfo) => {
        // M0 stub: no checks yet. M1 wires the ported linter here.
        new Notice(
          "RuWritingStyles: linter not wired yet (M0 scaffold). " +
            "See docs/obsidian-plugin-plan.md."
        );
      },
    });
  }

  onunload(): void {}

  async loadSettings(): Promise<void> {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
  }
}
