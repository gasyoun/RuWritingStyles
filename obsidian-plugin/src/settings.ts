import { App, PluginSettingTab, Setting } from "obsidian";

import { JOURNALS } from "./assets.ts";
import type RuWritingStylesPlugin from "./main.ts";

/** Settings tab: pick the journal profile (drives the IAST first-mention rule and
 *  the length / abstract / keywords compliance check). */
export class RwsSettingTab extends PluginSettingTab {
  private readonly plugin: RuWritingStylesPlugin;

  constructor(app: App, plugin: RuWritingStylesPlugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display(): void {
    const { containerEl } = this;
    containerEl.empty();

    new Setting(containerEl)
      .setName("Журнал")
      .setDesc(
        "Профиль журнала задаёт правило первого упоминания (IAST) и проверку " +
          "объёма, аннотации и ключевых слов. «Без журнала» отключает проверку соответствия."
      )
      .addDropdown((dropdown) => {
        dropdown.addOption("none", "— без журнала —");
        for (const [id, profile] of Object.entries(JOURNALS)) {
          dropdown.addOption(id, profile?.name ?? id);
        }
        dropdown.setValue(this.plugin.settings.journal);
        dropdown.onChange(async (value) => {
          this.plugin.settings.journal = value;
          await this.plugin.saveSettings();
          this.plugin.relintAll();
        });
      });
  }
}
