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
    throw new Error(`unknown provider: ${s.provider}`);
  }
  if (!VALID_PROFILES.includes(s.profile)) {
    throw new Error(`unknown profile: ${s.profile}`);
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
