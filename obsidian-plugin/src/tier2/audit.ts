/**
 * Tier 2 — full Council audit via the local RuWritingStyles engine.
 *
 * Posts the current note's text to `POST /runs/execute` (text-body intake), polls
 * until the run is terminal, then writes the engine's revised text to a sibling
 * note (non-destructive) and reports a summary. Requires the engine running
 * (`rws web` / `python -m ruwritingstyles.api`, default :8000) and a configured
 * provider key (DeepSeek by default) — see the settings tab.
 *
 * Pure helpers live in audit-core.ts (unit-tested); this module is the
 * Obsidian-bound orchestration (requestUrl + vault).
 */

import { App, Notice, TFile, requestUrl } from "obsidian";

import {
  auditHeaders,
  baseUrl,
  executeBody,
  isTerminal,
  summarizeRun,
} from "./audit-core.ts";
import type { AuditSettings, RunDetails } from "./audit-core.ts";

export type { AuditSettings, RunDetails } from "./audit-core.ts";

const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

function errorText(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

async function postExecute(s: AuditSettings, text: string, filename: string): Promise<string> {
  const resp = await requestUrl({
    url: `${baseUrl(s)}/runs/execute`,
    method: "POST",
    headers: auditHeaders(s),
    body: JSON.stringify(executeBody(text, filename, s)),
    throw: false,
  });
  if (resp.status !== 200) {
    throw new Error(`HTTP ${resp.status}${resp.text ? ` — ${resp.text}` : ""}`);
  }
  const runId = resp.json?.run_id as string | undefined;
  if (!runId) throw new Error("ответ без run_id");
  return runId;
}

async function getRun(s: AuditSettings, runId: string): Promise<RunDetails> {
  const resp = await requestUrl({
    url: `${baseUrl(s)}/runs/${runId}`,
    method: "GET",
    headers: auditHeaders(s),
    throw: false,
  });
  if (resp.status !== 200) throw new Error(`HTTP ${resp.status}`);
  return resp.json as RunDetails;
}

/**
 * Run the full Council audit on `text` and present the result. Polls every ~3s
 * for up to ~15 min.
 */
export async function runCouncilAudit(
  app: App,
  file: TFile | null,
  text: string,
  settings: AuditSettings
): Promise<void> {
  if (!text.trim()) {
    new Notice("RuWritingStyles: пустая заметка — нечего отправлять Совету.");
    return;
  }
  const filename = file?.basename ?? "obsidian-note";
  const progress = new Notice("RuWritingStyles: запуск Совета…", 0);

  let runId: string;
  try {
    runId = await postExecute(settings, text, filename);
  } catch (e) {
    progress.hide();
    new Notice(
      `RuWritingStyles: не удалось запустить Совет — ${errorText(e)}. ` +
        `Запущен ли движок (rws web) на ${baseUrl(settings)}?`,
      12000
    );
    return;
  }

  progress.setMessage(`RuWritingStyles: Совет запущен (${runId})…`);
  let details: RunDetails | null = null;
  for (let attempt = 0; attempt < 300; attempt++) {
    await sleep(3000);
    let current: RunDetails;
    try {
      current = await getRun(settings, runId);
    } catch {
      continue; // transient; keep polling
    }
    progress.setMessage(`RuWritingStyles: Совет (${runId}) — ${current.status ?? "…"}`);
    if (isTerminal(current.status)) {
      details = current;
      break;
    }
  }
  progress.hide();

  if (!details) {
    new Notice(`RuWritingStyles: Совет (${runId}) не завершился за отведённое время.`, 12000);
    return;
  }
  if (details.status === "failed") {
    new Notice(`RuWritingStyles: прогон ${runId} завершился ошибкой — см. логи движка.`, 12000);
    return;
  }
  await presentResult(app, file, details);
}

async function presentResult(app: App, file: TFile | null, details: RunDetails): Promise<void> {
  const summary = summarizeRun(details);
  const revised = details.revised_text ?? "";
  if (!revised.trim()) {
    new Notice(`RuWritingStyles: ${summary}. Правка не получена.`, 12000);
    return;
  }
  // Non-destructive: write the revised text to a sibling note and open it for
  // side-by-side comparison rather than overwriting the original.
  const folder = file?.parent && file.parent.path !== "/" ? `${file.parent.path}/` : "";
  const stem = file?.basename ?? "obsidian-note";
  let target = `${folder}${stem}.rws-revised.md`;
  if (app.vault.getAbstractFileByPath(target)) {
    target = `${folder}${stem}.rws-revised.${details.id ?? "run"}.md`;
  }
  try {
    const created = await app.vault.create(target, revised);
    await app.workspace.getLeaf(true).openFile(created);
    new Notice(`RuWritingStyles: ${summary}. Правка → ${target}`, 12000);
  } catch (e) {
    new Notice(`RuWritingStyles: ${summary}. Не удалось записать правку — ${errorText(e)}`, 12000);
  }
}
