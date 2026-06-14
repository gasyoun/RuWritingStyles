/**
 * Bundled data assets, synced from the engine's knowledge/ by
 * tools/export_plugin_assets.py (single source of truth; drift-checked in
 * tools/validate_project.py). esbuild inlines these JSON imports into main.js.
 */

import termsRaw from "./assets/sanskrit-terms.json";
import vya from "./assets/journals/vya.json";
import ppv from "./assets/journals/ppv.json";
import vestnikSpbu from "./assets/journals/vestnik-spbu.json";

import { filterTerms } from "./lint/types.ts";
import type { JournalProfile, Term } from "./lint/types.ts";

export const TERMS: Term[] = filterTerms(termsRaw as unknown[]);

export const JOURNALS: Record<string, JournalProfile> = {
  vya: vya as JournalProfile,
  ppv: ppv as JournalProfile,
  "vestnik-spbu": vestnikSpbu as JournalProfile,
};

/** Journal ids offered in settings, plus "none". */
export const JOURNAL_IDS = ["none", ...Object.keys(JOURNALS)] as const;
