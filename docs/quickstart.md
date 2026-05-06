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
  reviews/
  council.json
  revision.json
  revised.md
  verification.json
```

## 4. Validate artifacts

```bash
rws validate-run runs/demo-pseudo-etymology
```

The mock provider is deterministic and only proves that the pipeline works. Use a real provider for substantive findings:

```bash
set OPENAI_API_KEY=...
rws run examples/input/pseudo-etymology.md --execute --provider openai --model gpt-5.5
```

In PowerShell:

```powershell
$env:OPENAI_API_KEY='...'
rws run examples/input/pseudo-etymology.md --execute --provider openai --model gpt-5.5
```
