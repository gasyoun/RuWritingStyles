# Quickstart

This quickstart runs the current RuWritingStyles pipeline without external API keys.

## 1. Install locally

```bash
python -m pip install -e .
```

If the installed `rws` script is not on `PATH`, use:

```bash
python -m ruwritingstyles.cli --help
```

## 2. Inspect styles

```bash
rws list-styles --mvp
```

## 3. Run the demo document

```bash
rws run examples/input/pseudo-etymology.md --run-id demo-pseudo-etymology --execute --provider mock
```

This creates:

```text
runs/demo-pseudo-etymology/
  original.md
  normalized.md
  segments.json
  report.md
  summary.html
  provider.log.jsonl
  reviews/
  council.json
  revision.json
  revised.md
  revision.diff
  verification.json
```

## 4. Validate artifacts

```bash
rws validate-run runs/demo-pseudo-etymology
```

To package the result:

```bash
rws html-report runs/demo-pseudo-etymology
rws export runs/demo-pseudo-etymology
```

`summary.html` is a local static summary with findings grouped by `span_id`; it is also included in the ZIP bundle.

To run the same document as an eval case:

```bash
rws eval-run --case pseudo-etymology --provider mock --run-id eval-pseudo-etymology
```

To run the full eval manifest:

```bash
rws eval-suite --provider mock --suite-id demo-suite
```

The suite writes `eval-suite-result.json` and `eval-suite-report.md`. Add `--strict` when failed cases should make scripts return exit code `1`.

The mock provider is deterministic and only proves that the pipeline works. Use a real provider for substantive findings:

```bash
cp .env.example .env
set OPENAI_API_KEY=...
rws provider-status --provider openai --strict
rws run examples/input/pseudo-etymology.md --execute --provider openai --model gpt-5.5
```

The CLI also accepts `--provider google` and `--provider anthropic` when the relevant API key is configured.

In PowerShell:

```powershell
Copy-Item .env.example .env
$env:OPENAI_API_KEY='...'
rws provider-status --provider openai --strict
rws run examples/input/pseudo-etymology.md --execute --provider openai --model gpt-5.5
```
