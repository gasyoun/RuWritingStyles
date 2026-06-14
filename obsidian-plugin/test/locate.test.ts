/**
 * Locator test: every finding the editor layer anchors to a range must point at
 * the right substring. The linter reports fragment/term (no offsets); the
 * locator re-finds them in the editor text. This guards against silent
 * mislocation — the failure mode that makes underlines land on the wrong word.
 *
 * Run: node --test test/locate.test.ts   (Node 24+, native TypeScript)
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

import { hasCyrillic, lintText, matchesRuTerm } from "../src/lint/translit.ts";
import { locateFindings } from "../src/lint/locate.ts";
import { filterTerms } from "../src/lint/types.ts";
import type { JournalProfile } from "../src/lint/types.ts";

const HERE = import.meta.dirname;
const FIXTURES = join(HERE, "fixtures");

const terms = filterTerms(
  JSON.parse(readFileSync(join(HERE, "../src/assets/sanskrit-terms.json"), "utf-8"))
);

interface ManifestEntry {
  name: string;
  profile: JournalProfile | null;
}
const manifest: ManifestEntry[] = JSON.parse(
  readFileSync(join(FIXTURES, "manifest.json"), "utf-8")
);

for (const entry of manifest) {
  test(`locate: ${entry.name}`, () => {
    const text = readFileSync(join(FIXTURES, `${entry.name}.md`), "utf-8");
    const findings = lintText(text, terms, entry.profile).findings;
    const located = locateFindings(text, findings, terms);

    for (const f of located) {
      if (f.from == null || f.to == null) continue; // unlocatable: allowed

      // Range invariants.
      assert.ok(f.from >= 0 && f.to <= text.length && f.from < f.to,
        `${entry.name}: bad range [${f.from},${f.to}] for ${f.type}`);

      const slice = text.slice(f.from, f.to);

      if (f.fragment) {
        assert.equal(slice, f.fragment,
          `${entry.name}: ${f.type} range should equal fragment`);
      } else if (f.type === "missing_iast_on_first_mention" && f.term) {
        assert.ok(hasCyrillic(slice) && matchesRuTerm(slice, f.term),
          `${entry.name}: range «${slice}» should be the Cyrillic mention of «${f.term}»`);
      } else if (f.type === "inconsistent_term_rendering" && f.term) {
        const term = terms.find((t) => t.ru === f.term);
        assert.ok(term, `${entry.name}: term «${f.term}» in dictionary`);
        assert.equal(slice.toLowerCase(), term!.iast.toLowerCase(),
          `${entry.name}: range should be the IAST form of «${f.term}»`);
      }
    }
  });
}
