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
