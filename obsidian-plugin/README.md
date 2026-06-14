# RuWritingStyles — Obsidian plugin

Inline, **deterministic** philological checks for Russian Sanskrit-studies notes,
ported from the [RuWritingStyles](https://github.com/gasyoun/RuWritingStyles) engine.
Runs entirely inside Obsidian — **no Python, no server, no API key.**

The MVP surfaces, on the current note:

- **Transliteration linting** — missing IAST on a term's first mention, IAST/Cyrillic
  hybrid words, mixed IAST ↔ Harvard-Kyoto schemes, inconsistent term rendering,
  Devanagari NFC problems. (Port of the engine's `translit_lint.py`.)
- **Journal compliance** — length vs the journal limit, and presence of the required
  abstract / keywords per language. (Port of the engine's report journal section.)

The full multi-agent **Council audit** (an LLM pipeline) is a Tier-2 follow-on that
talks to the engine's local FastAPI; it is not part of the MVP.

See [`docs/obsidian-plugin-plan.md`](../docs/obsidian-plugin-plan.md) for the full
implementation plan and milestones.

## Status

**M2 — inline UI.** Findings surface through the editor's native lint system
(`@codemirror/lint`): wavy underlines, hover bubbles, the built-in problems panel,
and F8 / next-diagnostic navigation, plus a status-bar count (`RWS ✗3 ⚠7`). Linting
is continuous and debounced; the `RuWritingStyles: lint current note (show problems)`
command force-relints and opens the problems panel. Journal compliance is M3. The
deterministic linter underneath is the parity-tested port from M1 — see
[Testing](#testing).

## Development

```sh
cd obsidian-plugin
npm install
npm run build          # type-check + bundle to main.js
npm run dev            # watch mode
npm test               # parity test vs the Python engine (Node 24+)
```

## Testing

`npm test` runs `test/parity.test.ts` (Node's native runner): it lints the
fixtures with the TypeScript port and asserts the findings + summary are
identical to the golden output of the engine's `rws lint-translit`. Regenerate
the golden fixtures from the engine with `python tools/export_lint_fixtures.py`.

To test in Obsidian, symlink or copy this folder's `manifest.json`, `main.js`, and
`styles.css` into `<vault>/.obsidian/plugins/ruwritingstyles/`, then enable the plugin
in Settings → Community plugins.

The term dictionary and journal profiles under `src/assets/` are **synced from the
engine's** [`knowledge/`](../knowledge) (single source of truth) by
`tools/export_plugin_assets.py`; `python tools/validate_project.py` fails if they drift.

## License

Apache-2.0, matching the parent repository.
