_Created: 24-08-2026 · Last updated: 05-09-2026_

# RuWritingStyles Web Studio

React/Vite frontend for the RuWritingStyles FastAPI backend.

## Local Development

From `web/`:

```bash
npm install
npm run dev
```

The Vite dev server runs on `http://localhost:5173` and defaults to the current hostname on port 8000. Use the Settings button to change the backend URL or add an API token; both values are stored only in `sessionStorage`.

From the repository root, the CLI can launch both:

```bash
rws web
```

## Production Build

```bash
npm run lint
npm run build
```

The production bundle is written to `web/dist`. When `web/dist` exists, `python -m ruwritingstyles.api` serves it from the same FastAPI process that serves the API, so Web Studio defaults to its current origin.

## Current Views

- Audit workbench: original/revised text, findings, council decisions and verification warnings.
- Profile view: methodological compass and Bloom/council metadata.
- Syntax view: significant syntax shift artifacts.
- Compare view: multi-run profile comparison through `/api/compare`.

_Dr. Mārcis Gasūns_
