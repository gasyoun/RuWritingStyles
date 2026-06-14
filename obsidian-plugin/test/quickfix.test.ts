/**
 * Quick-fix helper test (M4): the IAST insertion offered on a missing-first-mention
 * finding must resolve from the term dictionary, and only for that finding type.
 *
 * Run: node --test test/quickfix.test.ts   (Node 24+, native TypeScript)
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { iastInsertion } from "../src/lint/quickfix.ts";
import { filterTerms } from "../src/lint/types.ts";
import type { Finding } from "../src/lint/types.ts";

const HERE = import.meta.dirname;
const terms = filterTerms(
  JSON.parse(readFileSync(join(HERE, "../src/assets/sanskrit-terms.json"), "utf-8"))
);

function finding(over: Partial<Finding>): Finding {
  return {
    span_id: "p001",
    type: "missing_iast_on_first_mention",
    message: "",
    severity: "warning",
    ...over,
  };
}

test("missing-IAST finding → ' (iast)' from the dictionary", () => {
  const term = terms[0]; // any real entry
  const text = iastInsertion(finding({ term: term.ru }), terms);
  assert.equal(text, ` (${term.iast})`);
});

test("other finding types → null", () => {
  assert.equal(iastInsertion(finding({ type: "iast_in_cyrillic_word", fragment: "бхāшья" }), terms), null);
});

test("unknown term → null (no fabrication)", () => {
  assert.equal(iastInsertion(finding({ term: "несуществующийтермин" }), terms), null);
});

test("missing-IAST without a term → null", () => {
  assert.equal(iastInsertion(finding({ term: undefined }), terms), null);
});
