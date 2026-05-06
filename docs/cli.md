# CLI

RuWritingStyles CLI starts with a deliberately small command set. It prepares reproducible run artifacts, creates prompts for style agents, can execute them through a provider, and keeps a Markdown report for each run.

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

## List styles

```bash
rws list-styles
```

To show only the first MVP styles:

```bash
rws list-styles --mvp
```

MVP styles are marked with `*`.

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

Each `run` refreshes:

```text
runs/<run-id>/report.md
```

The report summarizes segment counts, style review status, findings, council decisions, revision status, and verifier warnings.

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

## Render a run report

```bash
rws report runs/cli-smoke-readme
```

This refreshes `runs/cli-smoke-readme/report.md` from the JSON artifacts already present in the run directory. It is useful after manual edits or after executing only part of the pipeline.

## Validate a run

```bash
rws validate-run runs/cli-smoke-readme
```

The command checks that run artifacts exist, parse as JSON where needed, and that any completed style findings point to known `span_id` values.

## Validate the repository

```bash
python tools/validate_project.py
```

The validator currently checks:

- required docs/config/source files exist;
- JSON schemas parse;
- style manifest and passport paths resolve;
- `model_policy.yml` contains the required providers and model IDs;
- `pyproject.toml` exposes the `rws` CLI.

## Run tests

```bash
python -m compileall -q src tools tests
python tools/validate_project.py
python -m unittest discover -s tests
```

The current tests cover Markdown segmentation, the full offline pipeline, mock provider execution, run reports, and the demo input document:

```text
rws run README.md --run-id unittest-readme
```
