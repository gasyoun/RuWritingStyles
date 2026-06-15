/**
 * Tier-2 audit helpers (pure parts, audit-core.ts). The HTTP/vault/modal
 * orchestration in audit.ts needs a live engine + Obsidian and isn't unit-tested;
 * these guard the request shape, auth, status classification, the poll-decision
 * state machine, response validation, and input sanitization.
 *
 * Run: node --test test/audit.test.ts   (Node 24+, native TypeScript)
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  ClientConfigError,
  MAX_CONSECUTIVE_FAILURES,
  MAX_POLL_ATTEMPTS,
  RunNotFoundError,
  TransientError,
  auditHeaders,
  classifyHttpStatus,
  countChangeHunks,
  detectEol,
  diffLines,
  executeBody,
  formatTraceMessage,
  isTerminal,
  isValidBackendUrl,
  reconstruct,
  sanitizeRunId,
  shouldAbortPolling,
  summarizeRun,
  validateExecuteResponse,
  validateRunDetails,
  wsUrl,
} from "../src/tier2/audit-core.ts";
import type { AuditSettings } from "../src/tier2/audit-core.ts";

function acceptedSet(...idx: number[]): Set<number> {
  return new Set(idx);
}
function allChangeIndices(hunks: ReturnType<typeof diffLines>): Set<number> {
  return new Set(Array.from({ length: countChangeHunks(hunks) }, (_, i) => i));
}

const settings: AuditSettings = {
  backendUrl: "http://127.0.0.1:8000",
  apiToken: "",
  provider: "deepseek",
  profile: "researcher",
  journal: "none",
};

// --- executeBody / auditHeaders ---------------------------------------------

test("executeBody carries fields and execute:true; omits journal when none", () => {
  assert.deepEqual(executeBody("# T\n\nтекст", "note", settings), {
    text: "# T\n\nтекст",
    filename: "note",
    provider: "deepseek",
    profile: "researcher",
    execute: true,
  });
});

test("executeBody includes journal when a preset is selected", () => {
  const body = executeBody("t", "note", { ...settings, journal: "vestnik-spbu" });
  assert.equal((body as { journal?: string }).journal, "vestnik-spbu");
});

test("executeBody rejects an unknown provider / profile with ClientConfigError", () => {
  assert.throws(() => executeBody("t", "n", { ...settings, provider: "bogus" }), ClientConfigError);
  assert.throws(() => executeBody("t", "n", { ...settings, provider: "bogus" }), /unknown provider/);
  assert.throws(() => executeBody("t", "n", { ...settings, profile: "bogus" }), ClientConfigError);
});

test("auditHeaders omits Authorization without a token, includes it with one", () => {
  assert.equal(auditHeaders(settings).Authorization, undefined);
  assert.equal(auditHeaders({ ...settings, apiToken: "secret" }).Authorization, "Bearer secret");
});

// --- isTerminal -------------------------------------------------------------

test("isTerminal: completed / failed / needs_human_review are terminal", () => {
  assert.equal(isTerminal("completed"), true);
  assert.equal(isTerminal("failed"), true);
  assert.equal(isTerminal("needs_human_review"), true);
  assert.equal(isTerminal("executing"), false);
  assert.equal(isTerminal(undefined), false);
});

// --- response validation ----------------------------------------------------

test("validateExecuteResponse requires a string run_id", () => {
  assert.equal(validateExecuteResponse({ run_id: "20260614-x" }).run_id, "20260614-x");
  assert.throws(() => validateExecuteResponse(undefined), /not a JSON object/);
  assert.throws(() => validateExecuteResponse("<html>"), /not a JSON object/);
  assert.throws(() => validateExecuteResponse({}), /missing run_id/);
});

test("validateRunDetails accepts an object, rejects non-objects and bad status", () => {
  assert.equal(validateRunDetails({ status: "completed" }).status, "completed");
  assert.throws(() => validateRunDetails(undefined), /not a JSON object/);
  assert.throws(() => validateRunDetails({ status: 5 }), /status is not a string/);
});

// --- HTTP classification ----------------------------------------------------

test("classifyHttpStatus: 2xx ok, 404 not_found, 429/5xx transient, other 4xx config", () => {
  assert.equal(classifyHttpStatus(200), "ok");
  assert.equal(classifyHttpStatus(404), "not_found");
  assert.equal(classifyHttpStatus(429), "transient");
  assert.equal(classifyHttpStatus(503), "transient");
  assert.equal(classifyHttpStatus(401), "client_config");
  assert.equal(classifyHttpStatus(400), "client_config");
});

test("typed errors are instanceof-distinct", () => {
  assert.ok(new RunNotFoundError("x") instanceof RunNotFoundError);
  assert.ok(new TransientError("x") instanceof TransientError);
  assert.ok(new ClientConfigError("x") instanceof ClientConfigError);
  assert.ok(!(new TransientError("x") instanceof RunNotFoundError));
});

// --- poll decision ----------------------------------------------------------

test("shouldAbortPolling: terminal status completes", () => {
  assert.deepEqual(
    shouldAbortPolling({ status: "completed", attempt: 1, consecutiveFailures: 0 }),
    { abort: true, reason: "completed" }
  );
});

test("shouldAbortPolling: fatal errors stop immediately", () => {
  assert.equal(shouldAbortPolling({ attempt: 1, consecutiveFailures: 0, fatal: "not_found" }).reason, "not_found");
  assert.equal(
    shouldAbortPolling({ attempt: 1, consecutiveFailures: 0, fatal: "client_config" }).reason,
    "client_config"
  );
});

test("shouldAbortPolling: transient exhaustion and timeout", () => {
  assert.equal(
    shouldAbortPolling({ status: "executing", attempt: 5, consecutiveFailures: MAX_CONSECUTIVE_FAILURES }).reason,
    "transient_exhausted"
  );
  assert.equal(
    shouldAbortPolling({ status: "executing", attempt: MAX_POLL_ATTEMPTS, consecutiveFailures: 0 }).reason,
    "timeout"
  );
  assert.equal(shouldAbortPolling({ status: "executing", attempt: 1, consecutiveFailures: 0 }).abort, false);
});

// --- url / id helpers -------------------------------------------------------

test("isValidBackendUrl requires an http(s) scheme", () => {
  assert.equal(isValidBackendUrl("http://127.0.0.1:8000"), true);
  assert.equal(isValidBackendUrl("https://x.example"), true);
  assert.equal(isValidBackendUrl("127.0.0.1:8000"), false);
  assert.equal(isValidBackendUrl(""), false);
});

test("sanitizeRunId strips path separators (no traversal); dots kept", () => {
  assert.equal(sanitizeRunId("20260614-note"), "20260614-note");
  const s = sanitizeRunId("../../etc/passwd");
  assert.ok(!s.includes("/"), "no path separator survives");
  assert.equal(s, ".._.._etc_passwd");
  assert.equal(sanitizeRunId(""), "run"); // empty → fallback
});

// --- summary ----------------------------------------------------------------

test("summarizeRun reads council/verification and counts length in code points", () => {
  const summary = summarizeRun({
    original_text: "गुण", // 3 code points
    revised_text: "गु", // 2 code points
    council: { decisions: [{}, {}, {}] },
    verification: { passed: false, status: "needs_human_review", warnings: [{}, {}] },
  });
  assert.match(summary, /решений совета: 3/);
  assert.match(summary, /верификация: needs_human_review/);
  assert.match(summary, /предупреждений: 2/);
  assert.match(summary, /объём 3→2/);
});

test("summarizeRun is robust to missing artifacts", () => {
  const summary = summarizeRun({ status: "completed" });
  assert.match(summary, /решений совета: 0/);
  assert.match(summary, /объём 0→0/);
});

// --- live trace -------------------------------------------------------------

test("wsUrl maps http→ws / https→wss and adds token query", () => {
  assert.equal(wsUrl(settings, "r1"), "ws://127.0.0.1:8000/ws/r1");
  assert.equal(wsUrl({ ...settings, backendUrl: "https://x.example/" }, "r1"), "wss://x.example/ws/r1");
  assert.equal(
    wsUrl({ ...settings, apiToken: "tok en" }, "r1"),
    "ws://127.0.0.1:8000/ws/r1?token=tok%20en"
  );
});

test("formatTraceMessage renders known shapes; null for noise", () => {
  assert.equal(formatTraceMessage({ type: "step_update", step_id: "council", status: "executing" }), "council: executing");
  assert.equal(formatTraceMessage({ type: "run_status", status: "completed" }), "completed");
  assert.equal(formatTraceMessage({ tool: "search_scholar" }), "инструмент: search_scholar");
  assert.equal(formatTraceMessage({}), null);
  assert.equal(formatTraceMessage("nope"), null);
});

// --- diff + selective reconstruct -------------------------------------------

const ORIG = "line1\nline2\nline3\nline4";
const REV = "line1\nLINE-2\nline3\nline4-new";

test("reconstruct: accept-all === revised, accept-none === original", () => {
  const hunks = diffLines(ORIG, REV);
  assert.equal(countChangeHunks(hunks), 2);
  assert.equal(reconstruct(hunks, allChangeIndices(hunks)), REV);
  assert.equal(reconstruct(hunks, acceptedSet()), ORIG);
});

test("reconstruct: selective accept mixes original and revised per hunk", () => {
  const hunks = diffLines(ORIG, REV);
  // accept only the first change (LINE-2), reject the second (line4-new)
  assert.equal(reconstruct(hunks, acceptedSet(0)), "line1\nLINE-2\nline3\nline4");
  // accept only the second
  assert.equal(reconstruct(hunks, acceptedSet(1)), "line1\nline2\nline3\nline4-new");
});

test("reconstruct preserves CRLF when given the original's eol", () => {
  const origCrlf = "a\r\nb\r\nc";
  const revCrlf = "a\r\nB\r\nc";
  const hunks = diffLines(origCrlf, revCrlf);
  // default LF would flatten CRLF; passing the detected eol keeps it
  assert.equal(reconstruct(hunks, allChangeIndices(hunks), "\r\n"), "a\r\nB\r\nc");
  assert.equal(reconstruct(hunks, acceptedSet(), "\r\n"), "a\r\nb\r\nc");
  assert.equal(detectEol(origCrlf), "\r\n");
  assert.equal(detectEol("a\nb"), "\n");
});

test("diffLines handles pure insert / pure delete / identical", () => {
  assert.equal(countChangeHunks(diffLines("a\nb", "a\nb")), 0);
  const ins = diffLines("a\nc", "a\nb\nc");
  assert.equal(reconstruct(ins, allChangeIndices(ins)), "a\nb\nc");
  assert.equal(reconstruct(ins, acceptedSet()), "a\nc");
  const del = diffLines("a\nb\nc", "a\nc");
  assert.equal(reconstruct(del, allChangeIndices(del)), "a\nc");
  assert.equal(reconstruct(del, acceptedSet()), "a\nb\nc");
});
