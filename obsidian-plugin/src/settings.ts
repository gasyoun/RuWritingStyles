import { App, Notice, PluginSettingTab, Setting } from "obsidian";

import { JOURNALS } from "./assets.ts";
import { FINDING_TYPES, FINDING_TYPE_LABELS } from "./lint/types.ts";
import { isValidBackendUrl } from "./tier2/audit-core.ts";
import type RuWritingStylesPlugin from "./main.ts";

const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";

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

    new Setting(containerEl).setName("Совет (полный аудит, Tier 2)").setHeading();
    containerEl.createEl("p", {
      cls: "setting-item-description",
      text:
        "Команда «Full council audit» отправляет текст заметки локальному движку " +
        "(rws web), который прогоняет мультиагентный Совет через выбранного провайдера. " +
        "Движок должен быть запущен; правка сохраняется в соседнюю заметку.",
    });

    new Setting(containerEl)
      .setName("Адрес движка")
      .setDesc("URL локального API RuWritingStyles.")
      .addText((text) => {
        text.setPlaceholder(DEFAULT_BACKEND_URL);
        text.setValue(this.plugin.settings.backendUrl);
        text.onChange(async (value) => {
          const trimmed = value.trim();
          if (trimmed && !isValidBackendUrl(trimmed)) {
            new Notice("RuWritingStyles: адрес движка должен начинаться с http:// или https://");
            this.plugin.settings.backendUrl = DEFAULT_BACKEND_URL;
          } else {
            this.plugin.settings.backendUrl = trimmed || DEFAULT_BACKEND_URL;
          }
          await this.plugin.saveSettings();
        });
      });

    new Setting(containerEl)
      .setName("Токен API")
      .setDesc("Только если движок запущен с RWS_API_TOKEN. Иначе оставьте пустым.")
      .addText((text) => {
        text.inputEl.type = "password";
        text.setValue(this.plugin.settings.apiToken);
        text.onChange(async (value) => {
          this.plugin.settings.apiToken = value;
          await this.plugin.saveSettings();
        });
      });

    new Setting(containerEl)
      .setName("Провайдер")
      .setDesc("LLM-провайдер для Совета (по умолчанию DeepSeek).")
      .addDropdown((dropdown) => {
        for (const id of ["deepseek", "openai", "google", "anthropic", "openrouter", "local", "ollama", "mock"]) {
          dropdown.addOption(id, id);
        }
        dropdown.setValue(this.plugin.settings.auditProvider);
        dropdown.onChange(async (value) => {
          this.plugin.settings.auditProvider = value;
          await this.plugin.saveSettings();
        });
      });

    new Setting(containerEl)
      .setName("Профиль")
      .setDesc("Профиль пользователя для прогона.")
      .addDropdown((dropdown) => {
        for (const id of ["researcher", "editor", "student"]) {
          dropdown.addOption(id, id);
        }
        dropdown.setValue(this.plugin.settings.auditProfile);
        dropdown.onChange(async (value) => {
          this.plugin.settings.auditProfile = value;
          await this.plugin.saveSettings();
        });
      });
  }
}
