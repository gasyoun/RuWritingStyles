_Created: 24-08-2026 · Last updated: 05-09-2026_

# RuWritingStyles — Obsidian plugin

Inline, **deterministic** philological checks for Russian Sanskrit-studies notes,
ported from the [RuWritingStyles](https://github.com/gasyoun/RuWritingStyles) engine.
Runs entirely inside Obsidian — **no Python, no server, no API key.**

The MVP surfaces, on the current note (no Python, no server, no API key):

- **Transliteration linting** — missing IAST on a term's first mention, IAST/Cyrillic
  hybrid words, mixed IAST ↔ Harvard-Kyoto schemes, inconsistent term rendering,
  Devanagari NFC problems. (Port of the engine's `translit_lint.py`.)
- **Journal compliance** — length vs the journal limit, and presence of the required
  abstract / keywords per language. (Port of the engine's report journal section.)
- **IAST quick-fix** — one-click insertion of the dictionary IAST after a flagged
  first mention.

**Tier 2 — full Council audit** (opt-in, needs the engine + a provider key): the
`Full council audit (run on engine)` command sends the note to the local engine
(`rws web`), runs the multi-agent Council, and writes the revised text to a sibling
note. Configure the engine URL / token / provider in settings.

See [`docs/obsidian-plugin-plan.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/obsidian-plugin-plan.md) for the full
implementation plan and milestones.

## Status

**M5 — feature-complete; release automation in place.**
Findings surface through the editor's native lint system (`@codemirror/lint`): wavy
underlines, hover bubbles, the built-in problems panel, and F8 / next-diagnostic
navigation, plus a status-bar count (`RWS ✗3 ⚠7`). Linting is continuous and
debounced; the `RuWritingStyles: lint current note (show problems)` command
force-relints, opens the panel, and shows a journal checklist.

A **settings tab** picks the journal profile (`vya` / `ppv` / `vestnik-spbu`) — which
drives the IAST first-mention rule and the length + abstract/keywords compliance
check (gaps show in the same panel) — and has a **toggle per transliteration check**.
Missing-first-mention findings offer a one-click **"Вставить IAST"** quick-fix that
inserts ` (iast)` from the term dictionary.

Both the transliteration linter and the journal check are parity-tested ports of the
engine — see [Testing](#testing). Releasing (tagging, BRAT, official submission) is
covered in [`RELEASE.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/obsidian-plugin/RELEASE.md); official community submission needs a dedicated
repo (a monorepo subdirectory can't be submitted directly).

## Development

```sh
cd obsidian-plugin
npm install
npm run build          # type-check + bundle to main.js
npm run dev            # watch mode
npm test               # parity test vs the Python engine (Node 24+)
```

## Testing

`npm test` runs all of `test/**/*.test.ts` (Node's native runner): **36 tests** —

- `parity.test.ts`: TS transliteration findings + summary identical to the engine's
  `rws lint-translit` golden output (regenerate: `python tools/export_lint_fixtures.py`).
- `journal.test.ts`: TS journal-compliance identical to the engine's
  `report.journal_compliance()` golden output, incl. the real gúṇa article vs
  *Вестник СПбГУ* (regenerate: `python tools/export_journal_fixtures.py`).
- `locate.test.ts`: every located finding's editor range slices to the right substring.
- `quickfix.test.ts`: the IAST quick-fix resolves from the dictionary (and only for
  missing-first-mention findings; null for unknown terms).

To test in Obsidian, symlink or copy this folder's `manifest.json`, `main.js`, and
`styles.css` into `<vault>/.obsidian/plugins/ruwritingstyles/`, then enable the plugin
in Settings → Community plugins.

The term dictionary and journal profiles under `src/assets/` are **synced from the
engine's** [`knowledge/`](../knowledge) (single source of truth) by
`tools/export_plugin_assets.py`; `python tools/validate_project.py` fails if they drift.

## License

Apache-2.0, matching the parent repository.

_Dr. Mārcis Gasūns_
