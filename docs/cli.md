# CLI

RuWritingStyles CLI starts with a deliberately small command set. It prepares reproducible run artifacts, creates prompts for style agents, can execute them through a provider, and keeps Markdown plus static HTML reports for each run.

## Install for local development

From the repository root:

```bash
python -m pip install -e .
```

After that the `rws` command is available:

```bash
rws show-config
```

Without installation, use `PYTHONPATH=src`:

```bash
PYTHONPATH=src python -m ruwritingstyles.cli show-config
```

In PowerShell:

```powershell
$env:PYTHONPATH='src'
python -m ruwritingstyles.cli show-config
```

## Show configuration

```bash
rws show-config
```

This loads:

- `styles/manifest.yml`;
- MVP style passports from `styles/passports/`;
- `model_policy.yml`.

It prints the MVP styles and the default development model policy.

## Show Model Routes

```bash
rws model-routes
rws model-routes --provider openai --task style_review
```

This prints the task-to-model routes from `model_policy.yml`, including provider-specific reasoning or thinking settings.

## List styles

```bash
rws list-styles
```

To show only the first MVP styles:

```bash
rws list-styles --mvp
```

MVP styles are marked with `*`.

## List Eval Cases

```bash
rws eval-list
```

This reads `evals/manifest.json` and prints the current comparison cases, their input documents, default styles, and expected risks.

## Run An Eval Case

```bash
rws eval-run --case pseudo-etymology --provider mock
```

This executes the case through the current pipeline and writes `eval-result.json` into the run directory. Use real providers the same way once API keys are configured:

```bash
rws eval-run --case pseudo-etymology --provider openai --model gpt-5.5
```

`eval-result.json` includes finding types, matched expected risks, verification status, and a minimal pass/fail scoring block from `evals/manifest.json`.

## Prepare a document

```bash
rws prepare README.md
```

For deterministic smoke tests:

```bash
rws prepare README.md --run-id cli-smoke-readme
```

The command currently supports `.md` and `.txt` inputs. It creates:

```text
runs/<run-id>/
  original.md
  normalized.md
  segments.json
  report.md
  summary.html
```

`runs/` is ignored by Git because run artifacts are local outputs.

## Run the full offline pipeline

```bash
rws run README.md
```

For deterministic smoke tests:

```bash
rws run README.md --run-id cli-smoke-readme
```

By default, `rws run` uses the MVP style set from `styles/manifest.yml`. You can override it:

```bash
rws run README.md --style zalizniak-zametki
rws run README.md --styles zalizniak-ocherk,zalizniak-zametki
```

The command creates the same `runs/<run-id>/` directory as `prepare`, then adds review, council, revision, and verification artifacts.

To execute all generated prompts with the deterministic mock provider:

```bash
rws run README.md --run-id cli-smoke-readme --execute --provider mock
```

To execute with OpenAI, set `OPENAI_API_KEY` and choose `openai`:

```bash
rws run README.md --execute --provider openai --model gpt-5.5
```

OpenAI execution uses the Responses API with Structured Outputs. It is opt-in so local tests never require secrets or network access.

Other opt-in provider adapters use the same run artifacts:

```bash
rws run README.md --execute --provider google --model gemini-3.1-pro-preview
rws run README.md --execute --provider anthropic --model claude-sonnet-4-6
```

Provider environment variables:

- `openai`: `OPENAI_API_KEY`, optional `RWS_OPENAI_MODEL`, optional `RWS_OPENAI_REASONING`.
- `google`: `GEMINI_API_KEY` or `GOOGLE_API_KEY`, optional `RWS_GOOGLE_MODEL`.
- `anthropic`: `ANTHROPIC_API_KEY`, optional `RWS_ANTHROPIC_MODEL`, optional `RWS_ANTHROPIC_MAX_TOKENS`.

Transient provider failures are retried with exponential backoff. Configure this with `RWS_PROVIDER_MAX_ATTEMPTS` and `RWS_PROVIDER_RETRY_SECONDS`. When a provider returns rate-limit headers, the retry layer prefers `Retry-After`, then known OpenAI `x-ratelimit-reset-*` and Anthropic `anthropic-ratelimit-*-reset` headers for exhausted limits.

Each `run` refreshes:

```text
runs/<run-id>/report.md
runs/<run-id>/summary.html
```

The reports summarize segment counts, style review status, findings, council decisions, revision status, and verifier warnings. `summary.html` is a portable static view with findings grouped by `span_id`.
When `--execute` produces `revised.md`, `run` also writes `revision.diff`.
Provider executions are appended to `provider.log.jsonl` without API keys or request bodies.

To package the completed run:

```bash
rws export runs/cli-smoke-readme
```

This creates `runs/cli-smoke-readme/cli-smoke-readme-bundle.zip`.

## Segment format

`segments.json` contains stable `span_id` values:

```json
{
  "span_id": "p002",
  "type": "paragraph",
  "text": "...",
  "start_line": 3,
  "end_line": 3
}
```

These IDs are the future anchor points for style findings, council replies, synthesis changes, and verifier warnings.

## Create a review bundle

The `review` command creates a prompt bundle for one style agent. With `--execute`, it also calls the selected provider and writes completed findings.

```bash
rws review runs/cli-smoke-readme --style zalizniak-zametki
```

To execute the generated review prompt immediately:

```bash
rws review runs/cli-smoke-readme --style zalizniak-zametki --execute --provider mock
```

For several styles:

```bash
rws review runs/cli-smoke-readme --styles zalizniak-ocherk,zalizniak-zametki
```

For the first MVP council set:

```bash
rws review runs/cli-smoke-readme --mvp
```

The command creates:

```text
runs/cli-smoke-readme/reviews/
  zalizniak-zametki.prompt.md
  zalizniak-zametki.review.json
```

The prompt includes:

- the style passport;
- the full style instruction from `ClaudeStyles/`;
- `segments.json`;
- the normalized document;
- the required JSON output shape for future style findings.

The `.review.json` file starts with `status: prompt_ready` and an empty `findings` array. When `--execute` is used, it is updated to `status: completed` with a `summary` and `findings`.

## Create a council bundle

After review bundles exist:

```bash
rws council runs/cli-smoke-readme
```

To execute the council prompt:

```bash
rws council runs/cli-smoke-readme --execute --provider mock
```

The command creates:

```text
runs/cli-smoke-readme/
  council.prompt.md
  council.json
```

The council prompt includes all `reviews/*.review.json` files and `segments.json`. Without `--execute`, it creates `status: prompt_ready`; with `--execute`, it fills `replies` and `decisions`.

## Create a revision bundle

After a council artifact exists:

```bash
rws revise runs/cli-smoke-readme
```

To execute the revision prompt:

```bash
rws revise runs/cli-smoke-readme --execute --provider mock
```

The command creates:

```text
runs/cli-smoke-readme/
  revision.prompt.md
  revision.json
```

The revision prompt includes `normalized.md` and `council.json`. Without `--execute`, it creates `status: prompt_ready`; with `--execute`, it produces `revised.md` and updates the applied-change list.

When `--execute` is used, `revised.md` is written and `revision.json` is updated.

## Create a verification bundle

After a revision artifact exists:

```bash
rws verify runs/cli-smoke-readme
```

To execute the verification prompt:

```bash
rws verify runs/cli-smoke-readme --execute --provider mock
```

The command creates:

```text
runs/cli-smoke-readme/
  verification.prompt.md
  verification.json
```

The verification prompt includes the original document, normalized document, revision artifact, and revised document if one has already been produced. Without `--execute`, it creates `status: prompt_ready`; with `--execute`, it fills `passed` and `warnings`.

When `--execute` is used, `verification.json` is updated with a verifier status, passed checks, and warnings.

## Inspect findings

```bash
rws findings runs/cli-smoke-readme
rws findings runs/cli-smoke-readme --span p002
```

This prints completed style findings grouped by `span_id`, with the segment excerpt, severity, style id, finding, suggestion, and confidence.

## Render a run report

```bash
rws report runs/cli-smoke-readme
rws html-report runs/cli-smoke-readme
```

`rws report` refreshes both `report.md` and `summary.html` from the JSON artifacts already present in the run directory. `rws html-report` refreshes only the static HTML summary. These commands are useful after manual edits or after executing only part of the pipeline.

## Create a revision diff

```bash
rws diff runs/cli-smoke-readme
```

This writes `runs/cli-smoke-readme/revision.diff` as a unified diff from `normalized.md` to `revised.md`.

## Export a run bundle

```bash
rws export runs/cli-smoke-readme
```

The bundle includes `report.md`, `summary.html`, `provider.log.jsonl`, source and normalized documents, JSON artifacts, prompts, `revised.md` and `revision.diff` when present, and `bundle-manifest.json`.

Use `--output` to choose a different ZIP path:

```bash
rws export runs/cli-smoke-readme --output exports/cli-smoke-readme.zip
```

## Validate a run

```bash
rws validate-run runs/cli-smoke-readme
```

The command checks that run artifacts exist, parse as JSON where needed, pass the local JSON Schema subset for review/council/revision/verification artifacts, and that any completed style findings point to known `span_id` values.

## Validate the repository

```bash
python tools/validate_project.py
```

The validator currently checks:

- required docs/config/source files exist;
- JSON schemas parse;
- style manifest and passport paths resolve;
- `model_policy.yml` contains the required providers and model IDs;
- the lightweight JSON Schema validator module is present;
- `pyproject.toml` exposes the `rws` CLI.

## Run tests

```bash
python -m compileall -q src tools tests
python tools/validate_project.py
python -m unittest discover -s tests
```

The current tests cover Markdown segmentation, the full offline pipeline, mock provider execution, Markdown/HTML run reports, run export bundles, and the demo input document:

```text
rws run README.md --run-id unittest-readme
```
