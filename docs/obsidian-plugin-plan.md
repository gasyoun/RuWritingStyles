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
   note text ──► segment(TS) ──► translitLint(TS) + journalCheck(TS) ──► locate ──► CM6 lint diagnostics
                  ▲ assets bundled: sanskrit-terms.json, journals/*.json (synced from engine)

Tier 2 (later) — full council audit via the existing engine, opt-in
   note text ──► POST http://127.0.0.1:8000/runs/execute ──► WS /ws/{run_id} (live trace)
              ──► GET /runs/{run_id} artifacts ──► findings + revised.md (accept into note)
                  requires: `rws web` running + DEEPSEEK_API_KEY + (optional) RWS_API_TOKEN
```

The two tiers share the **Finding** shape so both render through the same lint-diagnostics path.

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
    main.ts              # Plugin: register CM6 lint extension, command, status bar
    assets.ts            # imports the bundled term dict + journal profiles
    settings.ts          # settings tab + interface (M3/M4)
    lint/
      types.ts           # Finding, JournalProfile, Term, Segment
      segment.ts         # normalize + segment, offset-tracking
      translit.ts        # port of translit_lint
      locate.ts          # map a finding to an editor character range
      journal.ts         # journal-compliance check (M3)
    ui/
      lint-extension.ts  # CM6 @codemirror/lint source + status-bar sync
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

Findings surface through CodeMirror's **native lint system** (`@codemirror/lint`,
bundled by Obsidian) rather than a custom panel — chosen 2026-06-14 over a docked
`ItemView`. This gives, for free: wavy underlines, hover message bubbles, the
built-in toggleable problems panel, and F8 / next-diagnostic navigation.

- **A `linter()` source** runs the ported translit (+ journal, M3) checks on the
  current note continuously and debounced (~400 ms); the **locator**
  (`lint/locate.ts`) maps each finding to an editor range by re-finding its
  fragment/term in the live text (robust to the linter's internal normalization).
- **`RuWritingStyles: lint current note (show problems)`** — force an immediate
  re-lint and open the problems panel. Continuous linting makes a separate "clear"
  command unnecessary.
- **Inline**: error = red wavy underline, warning = amber, tied to Obsidian's
  `--text-error` / `--text-warning`; hover = the message.
- **Status-bar item**: `RWS ✗3 ⚠7` live counts for the focused note (`RWS ✓` when
  clean), synced via a CM6 `updateListener` + `active-leaf-change`.
- Findings that can't be anchored to a range (rare; e.g. document-level journal
  findings in M3) are reported via a Notice rather than shown inline, so they don't
  silently vanish.
- **Quick-fix** ✅ (M4): for `missing_iast_on_first_mention`, a lint `action`
  ("Вставить IAST") inserts ` (iast)` after the first mention, resolving the IAST
  from the term dictionary (`lint/quickfix.ts`; null for unknown terms — never
  fabricates).

## 8. Settings

- **Journal profile** ✅ (M3): `none` / `vya` / `ppv` / `vestnik-spbu`. Selecting one
  turns on the compliance check (length + abstract/keywords) and sets the
  `first_mention_rule` for the translit linter. Changing it re-lints all open notes.
- **Per-finding-type toggles** ✅ (M4): turn off, e.g., `inconsistent_term_rendering`;
  the linter, the status bar, and the command Notice all respect them.
- **Lint on save** — **dropped.** M2's native linter is already continuous and
  debounced, so a save-triggered mode would be redundant; the per-check toggles are
  the useful control instead.
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

**Progress:** M0 ✅ · M1 ✅ (parity **14/14**) · M2 ✅ (native CM6 lint diagnostics +
locator + status bar) · M3 ✅ (journal-compliance port + settings dropdown; engine
extracted a pure `journal_compliance()` helper) · M4 ✅ (IAST quick-fix + per-check
toggles) · M5 ✅ (release automation + packaging guide) · **Tier 2 ✅ first cut**
(text-body intake on `/runs/execute` + a Council-audit command; **41/41** tests).
**All milestones shipped; remaining = author release actions (see below) + Tier-2
refinements (§11).**

The **plugin is feature-complete (M0–M5).** The journal check reports, on the gúṇa
article vs *Вестник СПбГУ*, length OK (12114/40000), abstract ru ✓ en ✗, keywords
ru ✓ en ✗ — identical to the engine report. Journal gaps surface as native lint
diagnostics alongside the translit underlines; missing-first-mention findings offer
a one-click "Вставить IAST" fix.

**Author release actions (outward; not automated):** cut a release by pushing an
`obsidian-v0.1.0` tag (the workflow builds + attaches the assets); for official
community-directory submission, publish from a **dedicated repo** with root
`manifest.json` (the monorepo subdirectory can't be submitted directly). Full
steps + the dedicated-repo rationale: [`obsidian-plugin/RELEASE.md`](../obsidian-plugin/RELEASE.md).

> **Development note:** the work runs in a dedicated git **worktree** on
> `feat/obsidian-plugin` (an external actor repeatedly switches the main checkout's
> HEAD to `main`; the worktree isolates the plugin work and locks the branch).

| # | Milestone | Done when |
|---|---|---|
| **M0** ✅ | Scaffold | Plugin loads in Obsidian; `RWS: lint current note` exists as a no-op; build (`npm run build`) produces `main.js`. |
| **M1** ✅ | Port linter + segmentation + asset sync | `parity.test.ts` green vs Python fixtures; `export_plugin_assets.py` + drift check in place. |
| **M2** ✅ | Inline UI | Findings render via `@codemirror/lint` (underlines + hover + problems panel + F8 nav); locator maps findings to editor ranges; status-bar counts. |
| **M3** ✅ | Journal compliance | Journal dropdown drives `first_mention_rule`; length + abstract/keywords presence match the engine report on the gúṇa article (parity-tested via a pure `journal_compliance()` helper). |
| **M4** ✅ | Quick-fix + settings | First-mention IAST insertion (CM6 lint action, dictionary-resolved); per-finding-type toggles. (Lint-on-save dropped — M2's native linter is already continuous + debounced, so it's redundant.) |
| **M5** ✅ | Packaging | Release workflow (tag `obsidian-v*` → builds + tests + attaches `main.js`/`manifest.json`/`styles.css` + zip) and [`RELEASE.md`](../obsidian-plugin/RELEASE.md) (manual/BRAT install + the dedicated-repo path for official submission). The release/tag, BRAT add, and community PR are author actions — outward + need the repo-structure decision. |

M0–M3 are the MVP the author signed off on; M4–M5 are fast-follow.

## 11. Future work

### Full Council audit (Tier 2) — ✅ shipped (first cut)

Command **`Full council audit (run on engine)`** → `POST /runs/execute` on the local
engine, poll `/runs/{run_id}` until terminal, then write the engine's `revised.md` to a
**sibling note** (non-destructive) with a summary (council decisions / verification
verdict / warnings / length delta).

- **Backend (done):** `POST /runs/execute` now accepts a **text body** (`text` +
  `filename`) in addition to `input_path`. Text mode reads nothing from disk, so it's
  not subject to the input_path allowlist; bounded by `RWS_MAX_TEXT_CHARS`.
  `tests/test_api_text_intake.py`.
- **Client (done):** `src/tier2/audit-core.ts` (pure, unit-tested — **16 tests**) +
  `audit.ts` (Obsidian requestUrl + vault + modal). Settings: engine URL (scheme-
  validated), optional bearer token, provider (default `deepseek`, validated), profile.
  The user invoking the command is the authorization to send the draft to the provider.
- **Hardened** (two Ultracode review/verify workflows, 2026-06-14): typed HTTP errors +
  a pure `shouldAbortPolling` state machine (fast exit on 404/4xx/transient-exhaustion,
  not a silent 15-min timeout); non-JSON-200 guard on Obsidian's throwing `resp.json`
  getter; response-shape validation; `needs_human_review` treated as terminal;
  immediate first poll; concurrent-audit guard; try/catch around `vault.modify`;
  warnings listed in the modal; provider/profile + URL validation. 8 adversarially-
  confirmed bugs fixed.
- **Requires** the engine running (`rws web`) + a provider key. The live round-trip is
  not headless-testable; all request/parse/classify/poll-decision logic is unit-tested.

**Refinements done:** ✅ inline accept/reject — the result opens a modal (apply to the
note via `vault.modify` / save to a sibling note / cancel); ✅ journal pass-through —
`POST /runs/execute` takes a `journal` preset id, written into the run's
`project-context.json` so the pipeline honours it.

**Still open:** live "Thinking Trace" via `/ws/{run_id}` (currently polls `/runs/{id}`);
finer-grained per-change (diff) accept rather than whole-note replace.

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
