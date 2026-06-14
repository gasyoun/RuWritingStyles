import { App, PluginSettingTab, Setting } from "obsidian";

import { JOURNALS } from "./assets.ts";
import { FINDING_TYPES, FINDING_TYPE_LABELS } from "./lint/types.ts";
import type RuWritingStylesPlugin from "./main.ts";

/** Settings tab: journal profile (drives the IAST first-mention rule and the
 *  length / abstract / keywords compliance check) + per-check toggles. */
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

    new Setting(containerEl).setName("Проверки транслитерации").setHeading();
    for (const type of FINDING_TYPES) {
      new Setting(containerEl).setName(FINDING_TYPE_LABELS[type]).addToggle((toggle) => {
        toggle.setValue(this.plugin.settings.checks[type] !== false);
        toggle.onChange(async (value) => {
          this.plugin.settings.checks[type] = value;
          await this.plugin.saveSettings();
          this.plugin.relintAll();
        });
      });
    }
  }
}
