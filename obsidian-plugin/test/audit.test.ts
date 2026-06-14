/**
 * Tier-2 audit helpers (pure parts). The HTTP/vault orchestration needs a live
 * engine + Obsidian and isn't unit-tested here; these guard the request shape,
 * auth header, terminal check, and result summary.
 *
 * Run: node --test test/audit.test.ts   (Node 24+, native TypeScript)
 */

import { test } from "node:test";
import assert from "node:assert/strict";

import {
  auditHeaders,
  executeBody,
  isTerminal,
  summarizeRun,
} from "../src/tier2/audit-core.ts";
import type { AuditSettings } from "../src/tier2/audit-core.ts";

const settings: AuditSettings = {
  backendUrl: "http://127.0.0.1:8000",
  apiToken: "",
  provider: "deepseek",
  profile: "researcher",
};

test("executeBody carries text/filename/provider/profile and execute:true", () => {
  const body = executeBody("# T\n\nтекст", "note", settings);
  assert.deepEqual(body, {
    text: "# T\n\nтекст",
    filename: "note",
    provider: "deepseek",
    profile: "researcher",
    execute: true,
  });
});

test("auditHeaders omits Authorization without a token, includes it with one", () => {
  assert.equal(auditHeaders(settings).Authorization, undefined);
  const withToken = auditHeaders({ ...settings, apiToken: "secret" });
  assert.equal(withToken.Authorization, "Bearer secret");
});

test("isTerminal only for completed / failed", () => {
  assert.equal(isTerminal("completed"), true);
  assert.equal(isTerminal("failed"), true);
  assert.equal(isTerminal("executing"), false);
  assert.equal(isTerminal(undefined), false);
});

test("summarizeRun reads council decisions, verification, and length delta", () => {
  const summary = summarizeRun({
    original_text: "0123456789", // 10
    revised_text: "01234567", // 8
    council: { decisions: [{}, {}, {}] },
    verification: { passed: false, status: "needs_human_review", warnings: [{}, {}] },
  });
  assert.match(summary, /решений совета: 3/);
  assert.match(summary, /верификация: needs_human_review/);
  assert.match(summary, /предупреждений: 2/);
  assert.match(summary, /объём 10→8/);
});

test("summarizeRun is robust to missing artifacts", () => {
  const summary = summarizeRun({ status: "completed" });
  assert.match(summary, /решений совета: 0/);
  assert.match(summary, /предупреждений: 0/);
  assert.match(summary, /объём 0→0/);
});
