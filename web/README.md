# RuWritingStyles Web Studio

React/Vite frontend for the RuWritingStyles FastAPI backend.

## Local Development

From `web/`:

```bash
npm install
npm run dev
```

The Vite dev server runs on `http://localhost:5173` and expects the backend on `http://localhost:8000`.

From the repository root, the CLI can launch both:

```bash
rws web
```

## Production Build

```bash
npm run lint
npm run build
```

The production bundle is written to `web/dist`. When `web/dist` exists, `python -m ruwritingstyles.api` serves it from the same FastAPI process that serves the API.

## Current Views

- Audit workbench: original/revised text, findings, council decisions and verification warnings.
- Profile view: methodological compass and Bloom/council metadata.
- Syntax view: significant syntax shift artifacts.
- Compare view: multi-run profile comparison through `/api/compare`.
