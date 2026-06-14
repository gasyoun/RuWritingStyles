/**
 * Tier 2 — full Council audit via the local RuWritingStyles engine.
 *
 * Posts the current note's text to `POST /runs/execute` (text-body intake), polls
 * until the run is terminal, then opens an accept/reject modal (apply to the note /
 * save to a sibling note / cancel). Requires the engine running (`rws web`, default
 * :8000) and a provider key.
 *
 * Pure helpers + the poll-decision state machine live in audit-core.ts (unit-tested);
 * this module is the Obsidian-bound orchestration (requestUrl + vault + UI).
 */

import { App, Modal, Notice, Setting, TFile, requestUrl } from "obsidian";

import {
  ClientConfigError,
  MAX_POLL_ATTEMPTS,
  POLL_INTERVAL_MS,
  RunNotFoundError,
  TransientError,
  auditHeaders,
  baseUrl,
  classifyHttpStatus,
  countChangeHunks,
  diffLines,
  executeBody,
  formatTraceMessage,
  isValidBackendUrl,
  reconstruct,
  sanitizeRunId,
  shouldAbortPolling,
  summarizeRun,
  validateExecuteResponse,
  validateRunDetails,
  wsUrl,
} from "./audit-core.ts";
import type { AbortReason, AuditSettings, DiffHunk, RunDetails } from "./audit-core.ts";

export type { AuditSettings, RunDetails } from "./audit-core.ts";

/** One audit at a time, app-wide — the command is fire-and-forget, so guard
 *  against overlapping polls/modals from a double trigger. */
let auditInProgress = false;

const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms));

function errorText(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

/** Obsidian's `resp.json` is a getter that THROWS on a non-JSON body (e.g. HTML
 *  from a misconfigured proxy); read it defensively. */
function readJson(resp: { json: unknown }): unknown {
  try {
    return resp.json;
  } catch {
    throw new Error("non-JSON response body");
  }
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
  return validateExecuteResponse(readJson(resp)).run_id;
}

async function getRun(s: AuditSettings, runId: string): Promise<RunDetails> {
  const resp = await requestUrl({
    url: `${baseUrl(s)}/runs/${runId}`,
    method: "GET",
    headers: auditHeaders(s),
    throw: false,
  });
  switch (classifyHttpStatus(resp.status)) {
    case "not_found":
      throw new RunNotFoundError(`run ${runId} not found`);
    case "client_config":
      throw new ClientConfigError(`HTTP ${resp.status}`);
    case "transient":
      throw new TransientError(`HTTP ${resp.status}`);
    default:
      // A 200 with a non-JSON / wrong-shape body is a persistent misconfiguration,
      // not a transient blip — classify it fatal so the loop stops promptly with a
      // config message instead of exhausting retries as "engine unavailable".
      try {
        return validateRunDetails(readJson(resp));
      } catch (e) {
        throw new ClientConfigError(errorText(e));
      }
  }
}

/** Russian message for a non-completed poll outcome. */
function abortMessage(reason: AbortReason, runId: string, base: string): string {
  switch (reason) {
    case "not_found":
      return `RuWritingStyles: прогон ${runId} не найден на движке (${base}).`;
    case "client_config":
      return `RuWritingStyles: ошибка конфигурации движка (HTTP 4xx). Проверьте адрес и токен.`;
    case "transient_exhausted":
      return `RuWritingStyles: движок недоступен (несколько ошибок подряд). Запущен ли rws web на ${base}?`;
    case "timeout":
      return `RuWritingStyles: Совет (${runId}) не завершился за отведённое время.`;
    default:
      return `RuWritingStyles: Совет (${runId}) — ${reason}.`;
  }
}

/**
 * Best-effort live "Thinking Trace": subscribe to /ws/{id} and feed formatted
 * lines to `onLine`. Purely additive — polling remains the source of truth — so
 * any WebSocket failure is swallowed. Returns a closer.
 */
function openTrace(settings: AuditSettings, runId: string, onLine: (line: string) => void): () => void {
  let socket: WebSocket | null = null;
  try {
    socket = new WebSocket(wsUrl(settings, runId));
    socket.onmessage = (ev: MessageEvent) => {
      try {
        const line = formatTraceMessage(JSON.parse(String(ev.data)));
        if (line) onLine(line);
      } catch {
        /* ignore non-JSON frames */
      }
    };
    socket.onerror = () => {
      /* best-effort; the poll loop is authoritative */
    };
  } catch {
    socket = null;
  }
  return () => {
    try {
      socket?.close();
    } catch {
      /* ignore */
    }
  };
}

/**
 * Run the full Council audit on `text` and present the result. Polls every
 * POLL_INTERVAL_MS up to MAX_POLL_ATTEMPTS, exiting early on a fatal error; a
 * best-effort WebSocket enriches the progress with the live trace.
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
  if (!isValidBackendUrl(settings.backendUrl)) {
    new Notice(
      "RuWritingStyles: неверный адрес движка в настройках — нужен http:// или https://.",
      10000
    );
    return;
  }
  if (auditInProgress) {
    new Notice("RuWritingStyles: аудит уже выполняется — дождитесь завершения.");
    return;
  }
  auditInProgress = true;
  const base = baseUrl(settings);
  const filename = file?.basename ?? "obsidian-note";
  const progress = new Notice("RuWritingStyles: запуск Совета…", 0);
  let closeTrace: () => void = () => {};

  try {
    let runId: string;
    try {
      runId = await postExecute(settings, text, filename);
    } catch (e) {
      // A config error (bad provider/profile/token) is the user's settings, not a
      // down engine — don't suggest "is the engine running?".
      if (e instanceof ClientConfigError) {
        new Notice(`RuWritingStyles: ошибка настроек — ${errorText(e)}.`, 12000);
      } else {
        new Notice(
          `RuWritingStyles: не удалось запустить Совет — ${errorText(e)}. ` +
            `Запущен ли движок (rws web) на ${base}?`,
          12000
        );
      }
      return;
    }

    progress.setMessage(`RuWritingStyles: Совет запущен (${runId})…`);
    closeTrace = openTrace(settings, runId, (line) =>
      progress.setMessage(`RuWritingStyles: ${runId} — ${line}`)
    );

    let details: RunDetails | null = null;
    let abortReason: AbortReason = "timeout";
    let consecutiveFailures = 0;

    for (let attempt = 1; attempt <= MAX_POLL_ATTEMPTS; attempt++) {
      let status: string | undefined;
      let current: RunDetails | null = null;
      let fatal: "not_found" | "client_config" | undefined;
      try {
        current = await getRun(settings, runId);
        status = current.status;
        consecutiveFailures = 0;
      } catch (e) {
        if (e instanceof RunNotFoundError) fatal = "not_found";
        else if (e instanceof ClientConfigError) fatal = "client_config";
        else consecutiveFailures++; // TransientError (5xx / 429) → retry
      }

      const decision = shouldAbortPolling({ status, attempt, consecutiveFailures, fatal });
      if (decision.abort) {
        abortReason = decision.reason ?? "timeout";
        if (abortReason === "completed") details = current;
        break;
      }
      progress.setMessage(`RuWritingStyles: Совет (${runId}) — ${status ?? "…"}`);
      // Poll the first attempt immediately; space out the rest.
      if (attempt < MAX_POLL_ATTEMPTS) await sleep(POLL_INTERVAL_MS);
    }

    if (!details) {
      new Notice(abortMessage(abortReason, runId, base), 12000);
      return;
    }
    if (details.status === "failed") {
      new Notice(`RuWritingStyles: прогон ${runId} завершился ошибкой — см. логи движка.`, 12000);
      return;
    }
    presentResult(app, file, details, details.status === "needs_human_review");
  } finally {
    closeTrace();
    progress.hide();
    auditInProgress = false;
  }
}

function presentResult(
  app: App,
  file: TFile | null,
  details: RunDetails,
  needsReview: boolean
): void {
  const revised = details.revised_text ?? "";
  if (!revised.trim()) {
    new Notice(`RuWritingStyles: ${summarizeRun(details)}. Правка не получена.`, 12000);
    return;
  }
  new AuditResultModal(app, file, details, needsReview).open();
}

/** Apply the revision into the original note (recoverable via Ctrl+Z / file
 *  history); falls back to a sibling note when there is no backing file. */
async function applyToNote(app: App, file: TFile | null, revised: string, details: RunDetails): Promise<void> {
  if (!file) {
    await writeSiblingNote(app, file, revised, details);
    return;
  }
  try {
    await app.vault.modify(file, revised);
    new Notice("RuWritingStyles: правка применена к заметке (Ctrl+Z для отмены).", 8000);
  } catch (e) {
    new Notice(`RuWritingStyles: не удалось применить правку — ${errorText(e)}`, 12000);
  }
}

/** Write the revision to a sibling note and open it for side-by-side comparison. */
async function writeSiblingNote(app: App, file: TFile | null, revised: string, details: RunDetails): Promise<void> {
  const folder = file?.parent && file.parent.path !== "/" ? `${file.parent.path}/` : "";
  const stem = file?.basename ?? "obsidian-note";
  let target = `${folder}${stem}.rws-revised.md`;
  if (app.vault.getAbstractFileByPath(target)) {
    target = `${folder}${stem}.rws-revised.${sanitizeRunId(details.id ?? "run")}.md`;
  }
  try {
    const created = await app.vault.create(target, revised);
    await app.workspace.getLeaf(true).openFile(created);
    new Notice(`RuWritingStyles: правка → ${target}`, 8000);
  } catch (e) {
    new Notice(`RuWritingStyles: не удалось записать правку — ${errorText(e)}`, 12000);
  }
}

/** Max change hunks to render with a toggle; any beyond this stay accepted. */
const MAX_RENDERED_HUNKS = 40;

/** Accept/reject dialog for a finished Council audit, with per-change toggles. */
class AuditResultModal extends Modal {
  private readonly hunks: DiffHunk[];
  /** Per change-hunk acceptance (indexed by change-hunk order); default all on. */
  private readonly accepted: boolean[];

  constructor(
    app: App,
    private readonly file: TFile | null,
    private readonly details: RunDetails,
    private readonly needsReview: boolean
  ) {
    super(app);
    this.hunks = diffLines(details.original_text ?? "", details.revised_text ?? "");
    this.accepted = new Array(countChangeHunks(this.hunks)).fill(true);
  }

  onOpen(): void {
    const { contentEl } = this;
    contentEl.createEl("h3", { text: "RuWritingStyles — результат Совета" });
    contentEl.createEl("p", { text: summarizeRun(this.details) });
    if (this.needsReview) {
      contentEl.createEl("p", {
        cls: "mod-warning",
        text: "Статус: нужна экспертная проверка — правка получена, но верификатор не дал полного подтверждения.",
      });
    }

    const warnings = this.details.verification?.warnings;
    if (Array.isArray(warnings) && warnings.length) {
      const det = contentEl.createEl("details");
      det.createEl("summary", { text: `Предупреждения верификатора (${warnings.length})` });
      const list = det.createEl("ul");
      for (const w of warnings.slice(0, 50)) {
        const message =
          w && typeof w === "object" && "message" in w
            ? String((w as { message: unknown }).message)
            : String(w);
        list.createEl("li", { text: message });
      }
    }

    const revised = this.details.revised_text ?? "";
    const changeCount = this.accepted.length;

    if (changeCount === 0) {
      contentEl.createEl("p", { text: "Изменений нет — правка совпадает с заметкой." });
      new Setting(contentEl).addButton((btn) =>
        btn.setButtonText("Закрыть").setCta().onClick(() => this.close())
      );
      return;
    }

    contentEl.createEl("p", {
      cls: "setting-item-description",
      text: "Отметьте изменения для применения; снятые останутся как в оригинале. «Применить выбранные» меняет текущую заметку (Ctrl+Z для отмены).",
    });
    this.renderHunks(contentEl);

    new Setting(contentEl)
      .addButton((btn) =>
        btn
          .setButtonText("Применить выбранные")
          .setCta()
          .onClick(async () => {
            const set = new Set<number>();
            this.accepted.forEach((on, i) => {
              if (on) set.add(i);
            });
            this.close();
            await applyToNote(this.app, this.file, reconstruct(this.hunks, set), this.details);
          })
      )
      .addButton((btn) =>
        btn.setButtonText("В отдельную заметку (полностью)").onClick(async () => {
          this.close();
          await writeSiblingNote(this.app, this.file, revised, this.details);
        })
      )
      .addButton((btn) => btn.setButtonText("Отмена").onClick(() => this.close()));
  }

  /** Render each change hunk with an accept toggle and a capped before/after. */
  private renderHunks(container: HTMLElement): void {
    const list = container.createEl("div", { cls: "rws-diff-list" });
    let changeIdx = 0;
    let rendered = 0;
    for (const hunk of this.hunks) {
      if (hunk.kind !== "change") continue;
      const idx = changeIdx++;
      if (rendered >= MAX_RENDERED_HUNKS) continue; // beyond cap: stays accepted by default
      rendered++;

      const row = list.createEl("div", { cls: "rws-diff-hunk" });
      new Setting(row).setName(`Изменение ${idx + 1}`).addToggle((toggle) => {
        toggle.setValue(true);
        toggle.onChange((value) => {
          this.accepted[idx] = value;
        });
      });
      const pre = row.createEl("pre", { cls: "rws-diff-pre" });
      for (const line of hunk.before.slice(0, 8)) {
        pre.createEl("div", { cls: "rws-diff-del", text: `− ${line}` });
      }
      for (const line of hunk.after.slice(0, 8)) {
        pre.createEl("div", { cls: "rws-diff-add", text: `+ ${line}` });
      }
      if (hunk.before.length > 8 || hunk.after.length > 8) {
        pre.createEl("div", { text: "…" });
      }
    }
    if (changeIdx > MAX_RENDERED_HUNKS) {
      container.createEl("p", {
        cls: "setting-item-description",
        text: `Показаны первые ${MAX_RENDERED_HUNKS} из ${changeIdx} изменений; остальные применяются по умолчанию.`,
      });
    }
  }

  onClose(): void {
    this.contentEl.empty();
  }
}
