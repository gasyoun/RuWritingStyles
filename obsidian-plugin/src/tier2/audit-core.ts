/**
 * Tier-2 audit — pure helpers, free of any `obsidian` import so they can be
 * unit-tested under Node. The Obsidian-bound orchestration lives in audit.ts.
 */

export interface AuditSettings {
  backendUrl: string;
  apiToken: string;
  provider: string;
  profile: string;
  /** Journal preset id, or "none" to omit. */
  journal: string;
}

// Keep in sync with PROVIDER_CHOICES in the engine's cli.py.
export const VALID_PROVIDERS = [
  "deepseek",
  "openai",
  "google",
  "anthropic",
  "openrouter",
  "local",
  "ollama",
  "mock",
];
export const VALID_PROFILES = ["researcher", "editor", "student"];

/** Polling cadence + caps (also the testable knobs for shouldAbortPolling). */
export const POLL_INTERVAL_MS = 3000;
export const MAX_POLL_ATTEMPTS = 300; // ~15 min at 3s
export const MAX_CONSECUTIVE_FAILURES = 3;

/** Body for POST /runs/execute (text-body intake). Throws on an invalid
 *  provider/profile so a typo surfaces before the request, not as a server 4xx. */
export function executeBody(text: string, filename: string, s: AuditSettings) {
  if (!VALID_PROVIDERS.includes(s.provider)) {
    throw new ClientConfigError(`unknown provider: ${s.provider}`);
  }
  if (!VALID_PROFILES.includes(s.profile)) {
    throw new ClientConfigError(`unknown profile: ${s.profile}`);
  }
  const body: Record<string, unknown> = {
    text,
    filename,
    provider: s.provider,
    profile: s.profile,
    execute: true,
  };
  if (s.journal && s.journal !== "none") body.journal = s.journal;
  return body;
}

/** Auth header set (bearer token only when configured). */
export function auditHeaders(s: AuditSettings): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (s.apiToken) headers["Authorization"] = `Bearer ${s.apiToken}`;
  return headers;
}

/** Terminal run states (the engine can also end on needs_human_review — a real
 *  finish with a revision, not a failure). */
export function isTerminal(status: string | undefined): boolean {
  return status === "completed" || status === "failed" || status === "needs_human_review";
}

export interface RunDetails {
  id?: string;
  status?: string;
  original_text?: string;
  revised_text?: string;
  council?: { decisions?: unknown[] };
  verification?: { warnings?: unknown[]; passed?: boolean; status?: string };
}

/** A 200 response whose body isn't the expected JSON (misconfigured proxy / wrong
 *  base URL) must fail loudly, not parse to undefined and poll forever. */
export function validateExecuteResponse(json: unknown): { run_id: string } {
  if (!json || typeof json !== "object") {
    throw new Error("execute: response is not a JSON object");
  }
  const runId = (json as Record<string, unknown>).run_id;
  if (typeof runId !== "string" || !runId) {
    throw new Error("execute: response missing run_id");
  }
  return { run_id: runId };
}

export function validateRunDetails(json: unknown): RunDetails {
  if (!json || typeof json !== "object") {
    throw new Error("run details: response is not a JSON object");
  }
  const o = json as Record<string, unknown>;
  if (o.status !== undefined && typeof o.status !== "string") {
    throw new Error("run details: status is not a string");
  }
  return o as RunDetails;
}

/** Number of warnings the verification produced (defensive against shape drift). */
function warningCount(d: RunDetails): number {
  return Array.isArray(d.verification?.warnings) ? d.verification!.warnings!.length : 0;
}

/** Human one-line summary of a finished run. Lengths are code-point counts to
 *  match the engine (Python len). */
export function summarizeRun(d: RunDetails): string {
  const decisions = Array.isArray(d.council?.decisions) ? d.council!.decisions!.length : 0;
  const verdict =
    d.verification?.passed === true
      ? "пройдена"
      : d.verification?.status
        ? String(d.verification.status)
        : "—";
  const origLen = d.original_text ? [...d.original_text].length : 0;
  const revLen = d.revised_text ? [...d.revised_text].length : 0;
  return `решений совета: ${decisions}; верификация: ${verdict}; предупреждений: ${warningCount(d)}; объём ${origLen}→${revLen}`;
}

export function baseUrl(s: AuditSettings): string {
  return s.backendUrl.replace(/\/+$/, "");
}

/** True for a usable engine URL (must carry an http/https scheme). */
export function isValidBackendUrl(url: string): boolean {
  return /^https?:\/\/.+/.test(url.trim());
}

// --- HTTP status classification + typed errors ------------------------------

export class RunNotFoundError extends Error {}
export class TransientError extends Error {}
export class ClientConfigError extends Error {}

export type HttpClass = "ok" | "not_found" | "transient" | "client_config";

/** Map an HTTP status to a polling policy class: 404 = the run is gone (fatal);
 *  429/5xx = retry; other 4xx = client misconfiguration (fatal). */
export function classifyHttpStatus(status: number): HttpClass {
  if (status >= 200 && status < 300) return "ok";
  if (status === 404) return "not_found";
  if (status === 429 || status >= 500) return "transient";
  return "client_config";
}

// --- Poll-loop decision (pure state machine) --------------------------------

export type AbortReason =
  | "completed"
  | "timeout"
  | "transient_exhausted"
  | "not_found"
  | "client_config";

/** Decide whether the poll loop should stop. `fatal` carries a typed-error class
 *  from the last attempt; `status` is the last run status seen. */
export function shouldAbortPolling(args: {
  status?: string;
  attempt: number;
  consecutiveFailures: number;
  fatal?: "not_found" | "client_config";
}): { abort: boolean; reason?: AbortReason } {
  if (args.fatal === "not_found") return { abort: true, reason: "not_found" };
  if (args.fatal === "client_config") return { abort: true, reason: "client_config" };
  if (isTerminal(args.status)) return { abort: true, reason: "completed" };
  if (args.consecutiveFailures >= MAX_CONSECUTIVE_FAILURES) {
    return { abort: true, reason: "transient_exhausted" };
  }
  if (args.attempt >= MAX_POLL_ATTEMPTS) return { abort: true, reason: "timeout" };
  return { abort: false };
}

/** Filesystem-safe form of a run id, for building a sibling-note filename
 *  (defense-in-depth — the id comes from the engine response). */
export function sanitizeRunId(id: string): string {
  return id.replace(/[^A-Za-z0-9._-]/g, "_") || "run";
}

// --- Live trace (WebSocket /ws/{id}) ----------------------------------------

/** WebSocket URL for the live "Thinking Trace": http→ws, https→wss, token as a
 *  query param (Electron WebSocket can't set headers; the engine accepts ?token=). */
export function wsUrl(s: AuditSettings, runId: string): string {
  const base = baseUrl(s).replace(/^http/, "ws"); // http→ws, https→wss
  const query = s.apiToken ? `?token=${encodeURIComponent(s.apiToken)}` : "";
  return `${base}/ws/${encodeURIComponent(runId)}${query}`;
}

/** Render a trace message from the engine into a short progress line, or null if
 *  there's nothing worth showing. Defensive — the broadcast shape varies
 *  ({type:run_status,status}, {type:step_update,step_id,status}, tool calls). */
export function formatTraceMessage(msg: unknown): string | null {
  if (!msg || typeof msg !== "object") return null;
  const m = msg as Record<string, unknown>;
  const status = typeof m.status === "string" ? m.status : "";
  if (m.type === "step_update") {
    const step = typeof m.step_id === "string" ? m.step_id : "шаг";
    return `${step}: ${status || "…"}`;
  }
  if (m.type === "run_status") return status || null;
  if (typeof m.tool === "string") return `инструмент: ${m.tool}`;
  if (typeof m.message === "string") return m.message;
  return status || null;
}

// --- Line diff + selective reconstruct (per-change accept) -------------------

export type DiffHunk =
  | { kind: "equal"; lines: string[] }
  | { kind: "change"; before: string[]; after: string[] };

function splitLines(text: string): string[] {
  return text.replace(/\r\n/g, "\n").split("\n");
}

/** Line-level diff (LCS) of two texts → equal/change hunks. Consecutive
 *  deletions+insertions coalesce into one `change` hunk (before = removed lines,
 *  after = added lines). */
export function diffLines(original: string, revised: string): DiffHunk[] {
  const a = splitLines(original);
  const b = splitLines(revised);
  const n = a.length;
  const m = b.length;

  // LCS length table.
  const dp: number[][] = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = a[i] === b[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }

  const hunks: DiffHunk[] = [];
  let eq: string[] = [];
  let before: string[] = [];
  let after: string[] = [];
  const flushEq = () => {
    if (eq.length) {
      hunks.push({ kind: "equal", lines: eq });
      eq = [];
    }
  };
  const flushChange = () => {
    if (before.length || after.length) {
      hunks.push({ kind: "change", before, after });
      before = [];
      after = [];
    }
  };

  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) {
      flushChange();
      eq.push(a[i]);
      i++;
      j++;
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      flushEq();
      before.push(a[i]);
      i++;
    } else {
      flushEq();
      after.push(b[j]);
      j++;
    }
  }
  while (i < n) {
    flushEq();
    before.push(a[i]);
    i++;
  }
  while (j < m) {
    flushEq();
    after.push(b[j]);
    j++;
  }
  flushChange();
  flushEq();
  return hunks;
}

/** Number of toggleable change hunks in a diff. */
export function countChangeHunks(hunks: DiffHunk[]): number {
  return hunks.filter((h) => h.kind === "change").length;
}

/** Rebuild the text taking the revised side for accepted change hunks (by their
 *  0-based change-hunk index) and the original side for the rest. Accept-all →
 *  the revised text; accept-none → the original. */
export function reconstruct(hunks: DiffHunk[], acceptedChangeIndices: Set<number>): string {
  const out: string[] = [];
  let changeIdx = 0;
  for (const h of hunks) {
    if (h.kind === "equal") {
      out.push(...h.lines);
    } else {
      out.push(...(acceptedChangeIndices.has(changeIdx) ? h.after : h.before));
      changeIdx++;
    }
  }
  return out.join("\n");
}
