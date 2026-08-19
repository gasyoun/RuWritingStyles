# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project nature

RuWritingStyles is two layered things in one repo:

1. A **catalog of Russian-language Custom Style prompts** (`ClaudeStyles/*-style.md`) modeled on philological writers (Зализняк, Тронский, Казанский, Лидова, Альбедиль). Each `.md` is a self-contained instruction meant to be pasted into Claude Custom Style.
2. An **agentic review pipeline** (`src/ruwritingstyles/`) that loads those styles as machine-readable passports and runs a multi-agent "Council" over a Markdown document: segment → independent style reviews → council deliberation → revision synthesis → verification.

Adding a new style requires updating both layers: the `.md` in `ClaudeStyles/`, a passport in `styles/passports/`, the `passports:` block of `styles/manifest.yml`, and the navigation/source tables in `README.md` (`README.md` documents this multi-place rule explicitly). `tools/validate_project.py` enforces that the `ClaudeStyles/*.md` set matches the passports' `source_prompt` set. (The former `available_style_sources` manifest block was redundant — nothing read it; `rws list-styles` derives the user-facing list from the passports via `load_passport_summaries` — so it was removed.)

## Common commands

Install for development:

```powershell
python -m pip install -e .
```

Without install, prefix every command with `$env:PYTHONPATH='src'` (PowerShell) or `PYTHONPATH=src` (bash). After install the `rws` script is on PATH.

Tests, validation, compile (mirror of `.github/workflows/ci.yml`):

```powershell
python -m compileall -q src tools tests
python tools/validate_project.py
python -m pytest -q
python scripts/ci-eval-gate.py
```

Run a single test method:

```powershell
python -m unittest tests.test_cli_pipeline.SegmentTests.test_segment_markdown_headings_paragraphs_and_code
```

Frontend gate (in `web/`): `npm ci`, `npm test`, `npm run lint`, `npm run build`. Obsidian gate (in `obsidian-plugin/`): `npm ci`, `npm run build`, `npm test`. Packaging builds wheel/sdist, rebuilds a wheel from the sdist and compares runtime manifests; clean-wheel consumers run on Ubuntu/Windows with Python 3.10/3.14, followed by Docker smoke. `rws web` serves the bundled production SPA/API on port 8000; `rws web --dev` adds Vite on 5173. GitHub branch protection requires stable `CI / Required gate`.

## Pipeline mental model

The `rws run` command is a chain over a single `runs/<run-id>/` directory. Each stage reads earlier artifacts and writes the next:

```
prepare        → original.md, normalized.md, segments.json
review         → reviews/<style>.prompt.md + .review.json (one per style)
council        → council.prompt.md, council.json
revise         → revision.prompt.md, revision.json, revised.md, revision.diff
verify         → verification.prompt.md, verification.json
translit_lint  → translit-lint.json (deterministic, no provider; findings also merged into verification.json warnings)
report         → report.md, summary.html, report.tex, references.bib, references-gost.md
```

Without `--execute`, every stage produces a prompt and a JSON shell with `status: prompt_ready`. With `--execute --provider <name>`, the provider adapter fills the JSON and updates `status: completed`. This split — prompt building is deterministic, model calls are opt-in — is load-bearing: it keeps the pipeline testable offline with `--provider mock` and lets `tests/` run without API keys or network.

`runs/` and `exports/` are gitignored; treat them as scratch.

## Span IDs are the anchor

Every segment in `segments.json` has a stable `span_id` (`p002`, `h004`, `c003` — type prefix + position). Every finding, council reply, applied revision change, and verifier warning references a `span_id`. When debugging cross-stage issues, follow span IDs through the JSON artifacts. `rws findings <run> --span p002` and `rws validate-run <run>` (which checks that findings reference known span IDs) are the right tools for this.

## Provider adapters

Real providers plus `mock` (`PROVIDER_CHOICES` in `cli.py`): `openai`, `google`, `anthropic`, `openrouter`, `deepseek` (+ `local`/`ollama` for OpenAI-compatible self-hosting). `deepseek` is the project's primary real provider (OpenAI-compatible JSON mode; `DEEPSEEK_API_KEY`; default `deepseek-chat`, `deepseek-reasoner` routed to council/verify in `model_policy.yml`; `RWS_DEEPSEEK_URL` overrides the base for an OpenRouter/proxy route). The `mock` provider is deterministic and is what tests use; never assume a real key is available.

Env vars are loaded from `.env` via `python-dotenv` at CLI import time. The `provider_status` module reports readiness without exposing keys; use `rws provider-status --provider <p> --strict` in scripts. Retry/backoff is centralized — `RWS_PROVIDER_MAX_ATTEMPTS`, `RWS_PROVIDER_RETRY_SECONDS`, and rate-limit headers (`Retry-After`, OpenAI `x-ratelimit-reset-*`, Anthropic `anthropic-ratelimit-*-reset`) feed the same retry layer; provider log entries record `retry_count`, `retry_delay_seconds`, `retry_statuses`.

`model_policy.yml` is the routing table — `task → (model, reasoning/thinking)` per provider. Adapters must not bake one vendor's parameter names into the style protocol; route lookups go through `load_model_routes`.

## Schemas as the contract

Every JSON artifact has a schema in `schemas/`: `segments.schema.json`, `review.schema.json`, `council.schema.json`, `revision.schema.json`, `verification.schema.json`, `translit-lint.schema.json`, `bibliography.schema.json`, `sanskrit-terms.schema.json`, `journal-profile.schema.json`, `project-context.schema.json`, `style.schema.json`, `model-policy.schema.json`, `provider-status.schema.json`, plus `eval-*` variants. `tools/validate_project.py` and `rws validate-run` apply these via the in-repo `schema_validation.py` — a deliberate JSON-Schema **subset** (no `allOf`/`oneOf`/`uniqueItems`/etc.); `schema_validation.lint_schema` makes `validate_project` fail if a schema uses an unsupported keyword, so add support before using one. `validate_project` also enforces bibliography cross-references (passport `provenance.sources` and `sanskrit-terms` `source` ids must exist in `knowledge/bibliography.json`). When you change an artifact shape, change its schema and the validator together — CI runs both.

## Eval suite

`evals/manifest.json` defines 60 comparison cases (`pseudo-etymology`, `register-shift`, `source-claim`, cluster/adversarial cases, the Sanskrit `GOLD_SANSKRIT` cases, and eight `GOLD_DICTIONARY` cases) that map to documents under `examples/input/`. Six `deterministic`-tagged cases are gated on the transliteration linter / citation grounding (which `run_eval_case` runs as provider-independent post-verification checks via `_run_deterministic_checks`) and pass identically on `mock`; the other 54 are LLM-judgment cases expected to fail under mock. The twelve `*-adversarial` cases (seven per-cluster refusal cases plus the five G-06 `adv-00N-*` temptation cases, H1833) are the **refusal** half of the suite: they score a *non*-edit — `strict_fidelity` **plus** `max_changed_line_ratio`/`max_char_delta_ratio` pinned to `0.0`, so any edit at all fails them — unlike the catch-the-error majority. Every required finding type must be declared under `checks` by one of that case's own reviewing styles (`evals/GOLD_PROTOCOL.md`); legacy labels live on as `accepted_finding_aliases`. Both invariants are pinned by `tests/test_eval_adversarial_refusal_cases.py`, whose registry must list every `*-adversarial` case — a new one that skips it fails CI. `rws eval-suite --provider mock --suite-id <id> --deliberate` runs all cases and writes `eval-suite-result.json` + `eval-suite-report.md`. Use `rws eval-compare A B --strict` to reject absent cases, protected-pass regressions, or a lower aggregate pass rate. New cases require an explicit `rws eval-promote` baseline refresh. `python scripts/ci-eval-gate.py` is the committed mock gate used by the Python CI job.

## Code organization in `src/ruwritingstyles/`

Roughly one module per pipeline stage: `segment`, `review`, `council`, `revision`, `verification`, plus orchestration (`pipeline`, `runs`, `execution`), reporting (`report`, `html_summary`, `findings`, `council_summary`, `provider_log`), eval (`evals`, `assess`, `scrutiny`, `peer_review`), tooling (`migration`, `dashboard`, `generation`, `styleguide`, `repl`), provider plumbing (`providers`, `provider_status`, `provider_log`, `config`), and a FastAPI surface (`api`) that the React frontend in `web/` consumes. The CLI `cli.py` is a thin argparse layer wiring those modules together (~80 subcommands).

## Windows / encoding notes

This repo is developed primarily on Windows; assume Windows by default.

- PowerShell is the default shell. Use native command parameters, not script blocks `{}` or subexpressions `$()`. Use `$env:VAR='value'` not `export VAR=value`. `rws web --dev` resolves npm explicitly and launches it without a shell.
- All Python scripts that emit text should use UTF-8: `sys.stdout.reconfigure(encoding='utf-8')`. The Russian-language style files (and corpus `.txt` extractions, when present) require this.
- Never commit `.env` (already gitignored). `.env.example` is the canonical template.

## Session state protocol (`.ai_state.md`)

This repo uses a single tracked file, `.ai_state.md`, as a session journal between Claude Code runs. Maintain it actively — do not let it go stale.

**During execution (micro-milestones).** Each time you finish a logical sub-task (a function fixed, a test passing), check it off in `.ai_state.md`. If you hit a persistent bug or change architectural approach, write the problem and your new hypothesis under `## 🧠 Dev Notes & Hypotheses`.

**Micro-commits.** When you have git access, commit after logical milestones with the prefix `ai-wip:` — don't wait for the whole feature.

**On session end / handoff (when asked to stop).** Tidy `.ai_state.md`: move finished items to `## ✅ Completed`, state blockers explicitly, and write concrete `## ➡️ Next Steps` for the next agent.

Maintain this exact section structure in `.ai_state.md`:

```
# Project Objective: [Global Goal]
## ➡️ Next Steps (Queue)
## 🚧 Current Work-In-Progress (WIP)
## 🧠 Dev Notes & Hypotheses (Bugs, ideas, context)
## ✅ Completed (Recent only)
```

## What not to touch casually

- `ClaudeStyles/*-style.md` — these are the human-facing product. Don't edit prose without a review reason; they are referenced from `README.md` and from passports.
- The research corpus (source PDFs/txt) lives in the **private sibling repo** `../RuWritingStyles-corpus/PDFtoTXT` — copyrighted texts must never be committed here (see `SOURCES.md`). `CorpusManager` resolves it via `RWS_CORPUS_DIR` or the sibling path. `PDFtoTXT/update.py` there is *not* a generic converter (it serves `AAZ_Zametki_2025` indices specifically).

## PDF text extraction — never reach for `pdftotext`

On this material poppler returns **zero Cyrillic**: the output has the right shape (spaces, punctuation, a plausible word count) with every Cyrillic run blanked, so a length or emptiness check does not catch it. It scored 1/8 in the 19-08-2026 bake-off against 8/8 for four other readers.

The trap has a second face: `pdftotext` is also the obvious way to read *someone else's* OCR output back (e.g. the text layer `ocrmypdf` writes). Doing that re-measures the poppler bug rather than the OCR engine and made OCR look useless at 1/8 when it was really 8/8. **Poppler must not appear anywhere in a pipeline over this corpus — not as the extractor, not as the reader at the end of another extractor.**

Sync rule: extraction order lives in `PDF_EXTRACTOR_CHAIN` and the accept/reject thresholds in `SANITY_THRESHOLDS`, both in `config.py`; the gate itself is `sanity()` in `extract.py`, shared by production and the bake-off harness so the two cannot drift. **Change a threshold or the chain ⇒ re-run `python tools/benchmark_extractors.py --report` and update [`docs/BENCHMARK_pdf-extractors_ru_19-08-2026.md`](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/BENCHMARK_pdf-extractors_ru_19-08-2026.md) in the same PR** — a pinned verdict with no matching matrix is a claim without evidence.

`sanity()` defaults to expecting Cyrillic. Sources known to be in another language must pass `expect_cyrillic=False`, or a cleanly extracted English article scores `cyrillic_ratio` 0.06 and is discarded as garbled.
- The `mvp_style_ids` list in `styles/manifest.yml` — `rws list-styles --mvp` and the default council set depend on it. The `councils:` block beside it defines named panels (`general` = `mvp_style_ids`, `sanskrit`, `indology`, `lexicography`) selectable via `rws run --council <name>` / `rws councils`; `validate_project` fails if a council names a non-existent passport, so edit ids carefully.
