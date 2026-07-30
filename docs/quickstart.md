# Quickstart

This quickstart runs the current RuWritingStyles pipeline without external API keys.

## 1. Install locally

```bash
python -m pip install -e .
```

```bash
python -m ruwritingstyles.cli --help
```

## 1.1 Launch Web Studio (Recommended)

The easiest way to use RuWritingStyles is through the Web Studio:

```bash
rws web
```

This launches a visual workbench at `http://localhost:5173`.

## 2. Inspect styles

```bash
rws list-styles --mvp
```

The MVP council set currently contains 6 style passports from `styles/manifest.yml`.

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
  impact.json
  syntax.json
```

Runs launched through the Web/API full pipeline also write scholarly artifacts such as `report.tex` and `references.bib`.

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

To run a regression check against the gold baseline:

```bash
rws eval-regression --provider mock
```

The suite currently runs 55 cases and writes `eval-suite-result.json` and `eval-suite-report.md`. Six deterministic cases pass under mock. `eval-regression` fails if a case is absent on either side, a protected pass regresses, or aggregate pass rate drops; new cases require an explicit baseline promotion.

The mock provider is deterministic. It is useful for checking schemas, file outputs, reports and orchestration; it is not a substantive philological quality signal.

## 5. Local verification checks

Before committing infrastructure or schema changes, run:

```bash
python -m compileall -q src tools tests
python tools/validate_project.py
python -m unittest discover -s tests
```

For Web Studio changes:

```bash
cd web
npm run lint
npm run build
```

Use a real provider for substantive findings:

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
