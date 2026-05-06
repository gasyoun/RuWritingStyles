# CLI

RuWritingStyles CLI starts with a deliberately small command set. The first implementation layer prepares reproducible run artifacts for later style reviewers; it does not call LLM providers yet.

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

The command supports `.md` and `.txt` inputs in the first implementation layer. It creates:

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

The first `review` implementation is offline. It creates a prompt bundle for one style agent but does not call an LLM provider yet.

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

The `.review.json` file starts with `status: prompt_ready` and an empty `findings` array. A later provider adapter will replace this with completed findings.

When `--execute` is used, `.review.json` is updated to `status: completed` and receives a `summary` and `findings`.

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

The council prompt includes all `reviews/*.review.json` files and `segments.json`. The first implementation layer creates `status: prompt_ready`; a later provider adapter will fill `replies` and `decisions`.

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

The revision prompt includes `normalized.md` and `council.json`. The first implementation layer creates `status: prompt_ready`; a later provider adapter will produce the revised Markdown and applied-change list.

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

The verification prompt includes the original document, normalized document, revision artifact, and revised document if one has already been produced. The first implementation layer creates `status: prompt_ready`; a later provider adapter will fill `passed` and `warnings`.

When `--execute` is used, `verification.json` is updated with a verifier status, passed checks, and warnings.

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

The current tests cover Markdown segmentation and the full offline pipeline:

```text
rws run README.md --run-id unittest-readme
```
