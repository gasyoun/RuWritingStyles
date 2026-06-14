/**
 * Tier-2 audit — pure helpers, free of any `obsidian` import so they can be
 * unit-tested under Node. The Obsidian-bound orchestration lives in audit.ts.
 */

export interface AuditSettings {
  backendUrl: string;
  apiToken: string;
  provider: string;
  profile: string;
}

/** Body for POST /runs/execute (text-body intake). */
export function executeBody(text: string, filename: string, s: AuditSettings) {
  return {
    text,
    filename,
    provider: s.provider,
    profile: s.profile,
    execute: true,
  };
}

/** Auth header set (bearer token only when configured). */
export function auditHeaders(s: AuditSettings): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (s.apiToken) headers["Authorization"] = `Bearer ${s.apiToken}`;
  return headers;
}

/** A run is terminal once the engine marks it completed or failed. */
export function isTerminal(status: string | undefined): boolean {
  return status === "completed" || status === "failed";
}

export interface RunDetails {
  id?: string;
  status?: string;
  original_text?: string;
  revised_text?: string;
  council?: { decisions?: unknown[] };
  verification?: { warnings?: unknown[]; passed?: boolean; status?: string };
}

/** Human one-line summary of a finished run. */
export function summarizeRun(d: RunDetails): string {
  const decisions = Array.isArray(d.council?.decisions) ? d.council!.decisions!.length : 0;
  const warnings = Array.isArray(d.verification?.warnings) ? d.verification!.warnings!.length : 0;
  const verdict =
    d.verification?.passed === true
      ? "пройдена"
      : d.verification?.status
        ? String(d.verification.status)
        : "—";
  const origLen = d.original_text?.length ?? 0;
  const revLen = d.revised_text?.length ?? 0;
  return `решений совета: ${decisions}; верификация: ${verdict}; предупреждений: ${warnings}; объём ${origLen}→${revLen}`;
}

export function baseUrl(s: AuditSettings): string {
  return s.backendUrl.replace(/\/+$/, "");
}
