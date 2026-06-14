# Obsidian plugin — implementation plan (lightweight inline checks MVP)

> **Кратко (рус.):** план плагина для Obsidian. **MVP** — лёгкие детерминированные
> проверки прямо в редакторе: транслитерационный линтер (IAST/русская передача) и
> соответствие журналу (объём, аннотация, ключевые слова). Без Python, без сервера,
> без API-ключа — порт детерминированного слоя на TypeScript. Полный аудит «Совета»
> (LLM) подключается позже через локальный FastAPI. Эта правка не привязана к версии:
> это проектный документ, не релиз.

Status: **plan** (no code yet). Scope chosen with the author: *lightweight inline
checks, plan doc first*. This document is the contract the plugin is built against.

---

## 1. Goal and non-goals

**Goal.** A first-class Obsidian plugin that runs RuWritingStyles' **deterministic**
philological checks on the current note and surfaces them inline — the same checks
the engine already ships (`rws lint-translit`, the report's journal-compliance
section), reimplemented natively so the plugin is useful with **nothing installed**:
no Python, no running backend, no DeepSeek key.

**Non-goals for the MVP** (deferred, see [§11](#11-future-work)):

- The full multi-agent **Council audit** (review → council → revision → verification).
  That is an LLM pipeline; it stays in the Python engine and is reached later over the
  local FastAPI (`POST /runs/execute` + `/ws/{run_id}`).
- Style **rewriting** ("write this note in the Зализняк-очерк voice").
- A **Word / Office.js** add-in (a separate, larger target — no native Markdown).

The MVP deliberately ports only the parts that are *fast, key-free, and
text-deterministic*, because that is the robust 80% and it needs no trust decision
about sending drafts to a provider.

## 2. Why Obsidian first, why lightweight first

- **Markdown is the native format.** A note *is* the Markdown the engine already
  ingests — no `.docx` ↔ Markdown bridge (the thing that makes Word the harder target).
- **The deterministic layer is already isolated** in the engine
  ([`src/ruwritingstyles/translit_lint.py`](../src/ruwritingstyles/translit_lint.py)
  and the journal section of
  [`src/ruwritingstyles/report.py`](../src/ruwritingstyles/report.py)). It has no LLM
  dependency, so it ports cleanly to TypeScript.
- **Instant feedback loop.** Inline highlights as you write beat a multi-minute
  council run for the everyday "did I gloss every term on first mention?" question.

## 3. Architecture

Two tiers, only the first is in the MVP:

```
Tier 1 (MVP)  — native TypeScript, runs inside Obsidian, zero setup
   note text ──► segment(TS) ──► translitLint(TS) + journalCheck(TS) ──► CM6 marks + side panel
                  ▲ assets bundled: sanskrit-terms.json, journals/*.json (synced from engine)

Tier 2 (later) — full council audit via the existing engine, opt-in
   note text ──► POST http://127.0.0.1:8000/runs/execute ──► WS /ws/{run_id} (live trace)
              ──► GET /runs/{run_id} artifacts ──► findings + revised.md (accept into note)
                  requires: `rws web` running + DEEPSEEK_API_KEY + (optional) RWS_API_TOKEN
```

The two tiers share the **Finding** shape so the side panel renders both identically.

## 4. The checks to port (source of truth + exact semantics)

The port must be **behaviour-identical** to the engine. Source of truth and parity
target is the Python, enforced by golden fixtures ([§9](#9-parity-testing-keep-ts--python)).

### 4.1 Transliteration linter

Port of [`translit_lint.py`](../src/ruwritingstyles/translit_lint.py). Five finding
types (the `FINDING_TYPES` tuple), unchanged:

| type | severity | scope | rule (Python ref) |
|---|---|---|---|
| `missing_iast_on_first_mention` | warning | per term | First Cyrillic mention of a dictionary term with no IAST in the same segment, **only** when the journal `first_mention_rule ∈ {ru+iast, iast+ru}`; proper nouns skipped. `lint_segments` term-tracking block. |
| `iast_in_cyrillic_word` | error | per word | A hyphen-free sub-token that *fuses* Cyrillic + Latin in one piece (`бхāшья`). Hyphenated mono-script parts (`IAST-транслитерация`, `сноски-bhāṣya`) are **legitimate** — `_has_fused_mixed_token`. |
| `mixed_transliteration_scheme` | error | document | Both IAST words *and* Harvard-Kyoto-marker words that resolve to a known term skeleton are present. `_HK_MARKER_RE` + `_skeleton` ∈ term skeletons. |
| `inconsistent_term_rendering` | warning | per term | A term appears ≥2× in Cyrillic **and** ≥2× as unpaired IAST (free variation without system). |
| `devanagari_nfc_issue` | error | per segment + raw | Devanagari text not in NFC, or an orphan mātrā/virāma with no base consonant (OCR artifact). The **raw-input** NFC check runs before normalization (`lint_text`). |

Helpers to port verbatim (all pure-string, all portable to JS):

- `IAST_DIACRITICS` (the diacritic set), `_has_cyrillic` (range `Ѐ`–`ӿ`), `_has_latin`,
  `_is_iast_word`.
- `_has_fused_mixed_token` (split on `' ’ - ‐ ‑ ‒ –`, flag a sub-token that is both).
- `_skeleton` (NFD-decompose, keep `a`–`z` → `kṛṣṇa → krsna`).
- `_ru_stem` + `_matches_ru_term` + `_RU_ENDINGS` (the Russian inflection window).
- `_HK_MARKER_RE` = `/.[AIURTDNSGJMHLZ]|aa|ii|uu/`, `_WORD_RE`, `_DEVANAGARI_RE`,
  `_ORPHAN_MATRA_RE`, `_RU_VOWELS`.

**JS porting notes (the only non-mechanical bits):**

- Python `re.UNICODE` `[^\W\d_]+` → JS `/[^\W\d_]+/u` won't match Cyrillic; use
  `\p{L}` with the `u` flag: `/\p{L}+(?:['’-]\p{L}+)*/gu`.
- `unicodedata.normalize("NFD"/"NFC")` → `str.normalize('NFD'/'NFC')` (identical).
- Devanagari ranges and the HK/ASCII regexes translate 1:1.

### 4.2 Journal-compliance presence check

Port of `_journal_section` in [`report.py`](../src/ruwritingstyles/report.py). Given a
selected journal profile it reports, **deterministically**:

- **Length:** `chars / max_chars` with an over-limit flag. *Parity caveat:* Python
  `len(text)` counts Unicode **code points**; JS `String.length` counts UTF-16 units.
  Use `[...text].length` (or `Array.from`) so a note with astral glyphs matches.
- **Abstract / keywords present per language** — lower-case marker search, same table:
  - `abstract_required` → ru: `аннотац`, `резюме`; en: `abstract`.
  - `keywords_required` → ru: `ключевые слова`; en: `keywords`, `key words`.
  Each required language renders `✓` / `⚠ нет`, exactly as the engine's report does.

The profile's `first_mention_rule` also feeds the linter (§4.1).

### 4.3 Shared data assets and sync

The plugin bundles copies of:

- [`knowledge/sanskrit-terms.json`](../knowledge/sanskrit-terms.json) — the term
  dictionary (`{ru, iast, source, note?, proper_noun?}`; currently 61 terms).
- [`knowledge/journals/*.json`](../knowledge/journals) — the journal profiles
  (`vya`, `ppv`, `vestnik-spbu`).

**Single source of truth = the engine's `knowledge/`.** A small generator
`tools/export_plugin_assets.py` copies those files into `obsidian-plugin/src/assets/`,
and a CI / `validate_project` check asserts they are byte-identical so the plugin can
never silently drift from the engine's dictionary. (No new authoritative copy.)

## 5. From span_ids to editor ranges

The engine anchors every finding to a `span_id` (`p002`/`h004`/`c003`). Obsidian needs
**character ranges** for CodeMirror 6 decorations instead. The port:

1. Reimplements `normalize_document` (NFC + line-ending/blank-line normalization) and
   `segment_markdown` (headings `h`, fenced code `c`, paragraphs `p`), but each segment
   also records its **absolute start offset** in the note.
2. The linter still finds the offending `word` / `fragment`; the plugin computes the
   absolute range = `segmentStart + indexOf(fragment)` and emits `{from, to}`.
3. Code segments (`c`-prefixed) are skipped, exactly as in the engine.

Document-level findings (`mixed_transliteration_scheme`,
`inconsistent_term_rendering`) anchor to the first relevant occurrence, as the engine
already does.

## 6. Plugin project layout

A new top-level directory in this repo (monorepo, alongside `web/`):

```
obsidian-plugin/
  manifest.json          # id "ruwritingstyles", isDesktopOnly:false, minAppVersion
  versions.json
  package.json           # esbuild + typescript + obsidian types
  esbuild.config.mjs
  tsconfig.json
  src/
    main.ts              # Plugin: register commands, settings, CM6 extension
    settings.ts          # settings tab + interface
    lint/
      types.ts           # Finding, JournalProfile, Term
      segment.ts         # normalize + segment, offset-tracking
      translit.ts        # port of translit_lint
      journal.ts         # journal-compliance check
    ui/
      decorations.ts     # CM6 ViewPlugin: inline marks (underline by severity)
      panel.ts           # ItemView side panel: grouped findings, click → jump
    assets/              # synced from ../knowledge (see §4.3)
      sanskrit-terms.json
      journals/*.json
  test/
    parity.test.ts       # TS findings == Python golden fixtures (§9)
    fixtures/            # *.md inputs + *.expected.json
  styles.css
  README.md
```

License Apache-2.0 (matches the repo / `CITATION.cff`).

## 7. Commands and UX

- **`RWS: lint current note`** — run translit + journal checks, populate the side
  panel, paint inline marks. The primary command.
- **`RWS: clear lint highlights`**.
- **Side panel** (`ItemView`): findings grouped by severity, each row shows
  type · message · term/fragment; clicking scrolls to and selects the range.
- **Inline marks** (CM6 `Decoration.mark`): error = red wavy underline, warning =
  amber; hover tooltip = the message.
- **Status-bar item**: `⚠ 3 · ⓘ 2` live counts for the active note.
- **Quick-fix (M4):** for `missing_iast_on_first_mention`, an action to insert
  ` (iast)` after the first mention from the term dictionary.

## 8. Settings

- **Journal profile**: `none` / `vya` / `ppv` / `vestnik-spbu`. Selecting one enables
  the compliance section and sets `first_mention_rule`.
- **Per-finding-type toggles** (turn off, e.g., `inconsistent_term_rendering`).
- **Lint on save** (debounced; **off** by default).
- **(Tier 2, hidden until built)** Backend URL (`http://127.0.0.1:8000`) + bearer
  token (`RWS_API_TOKEN`) for the full audit command.

## 9. Parity testing (keep TS == Python)

The one real risk is the TS port drifting from the engine. Mitigation:

1. `tools/export_lint_fixtures.py` runs `rws lint-translit --json` over a fixed set of
   `examples/input/*.md` (and a few hand-written edge cases) and writes
   `obsidian-plugin/test/fixtures/<name>.expected.json`.
2. `parity.test.ts` runs the TS port over the same inputs and asserts the finding sets
   match on `(type, term, fragment, severity)` — **ignoring `span_id`** (anchoring
   differs by design; ranges are checked separately on a couple of fixtures).
3. CI runs both the Python eval smoke and the TS parity test; a `validate_project`
   addition asserts the bundled assets equal `knowledge/`.

This turns "did the port stay faithful?" into a red/green check on every change.

## 10. Milestones (with acceptance criteria)

| # | Milestone | Done when |
|---|---|---|
| **M0** | Scaffold | Plugin loads in Obsidian; `RWS: lint current note` exists as a no-op; build (`npm run build`) produces `main.js`. |
| **M1** | Port linter + segmentation + asset sync | `parity.test.ts` green vs Python fixtures; `export_plugin_assets.py` + drift check in place. |
| **M2** | Inline UI | Findings render as CM6 marks + side panel; click → jump to range; status-bar counts. |
| **M3** | Journal compliance | Journal dropdown drives `first_mention_rule`; length + abstract/keywords presence match the engine report on the gúṇa article. |
| **M4** | Quick-fix + lint-on-save + polish | First-mention IAST insertion; debounced on-save lint; settings complete. |
| **M5** | Packaging | Release zip (`main.js`, `manifest.json`, `styles.css`); BRAT beta; community-plugin PR opened. |

M0–M3 are the MVP the author signed off on; M4–M5 are fast-follow.

## 11. Future work

### Full Council audit (Tier 2)

Command **`RWS: run full audit`** → `POST /runs/execute` on the local engine, subscribe
`/ws/{run_id}` for the live "Thinking Trace", then read `/runs/{run_id}` artifacts and
render findings + `revised.md` with an **accept-into-note** action.

**Backend change required (flagged now):** `POST /runs/execute` currently takes an
`input_path` confined to `RWS_INPUT_ROOT` (repo root by default) — it cannot ingest an
arbitrary note's *text*. Tier 2 needs either a **text-body intake** on `/runs/execute`
(or a new `/runs/execute-text`) or a documented temp-file-under-allowed-root flow. This
is the single API addition the plugin would drive; it is out of MVP scope.

### Word / Office.js add-in

Reuse the `lint/` core as a shared package behind an Office.js taskpane. Word has no
native Markdown, so it needs an Office-body-text → checks adapter; bigger lift, second
priority.

## 12. Open decisions

1. **Char-count parity** — adopt `[...text].length` (decided above) to match Python
   code-point counting.
2. **Asset sync enforcement** — *decided:* fold the drift check into
   `validate_project.py`. CI runs Python only (`ci.yml` has no Node job; the `web/`
   build is a local release check), and `validate_project` is already the repo's sync
   gate (ClaudeStyles↔passports, bibliography cross-refs). A standalone Node CI step
   just to diff JSON would be redundant tooling. Lands in M1 with the assets.
3. **Plugin id / display name / author** — *decided:* id `ruwritingstyles`, display
   name `RuWritingStyles`, author M. Yu. Gasuns (matches `CITATION.cff`).
4. **Mobile** — the MVP is pure TS, so `isDesktopOnly:false` should hold; verify CM6
   decorations behave on mobile before claiming support.

## 13. Where this sits

This operationalizes the roadmap item that v2.9.2 honestly re-labelled: the
Obsidian/Word plugins are *deferred prototypes* with only the FastAPI API layer built.
This plan is the path from "API layer only" to a shipped, zero-setup Obsidian plugin,
with the full Council audit as the documented Tier-2 follow-on.
