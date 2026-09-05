_Created: 24-08-2026 · Last updated: 05-09-2026_

# RuWritingStyles Codex Manifest (v2.4.0)

This document provides a structured map of the repository for rapid indexing and cross-referencing by AI agents and automated auditors.

## 🧠 Core Engine (`src/ruwritingstyles/`)
- **Orchestration**: `council.py`, `execution.py`, `pipeline.py`
- **Retrieval**: `knowledge.py`, `mcp_client.py`, `db.py` (FTS5)
- **Review**: `review.py`, `verification.py`, `bias.py`
- **Output**: `report.py`, `html_summary.py`, `diff.py`, `citations.py`
- **System**: `api.py` (WebSocket/FastAPI), `cli.py`, `config.py`, `provider_status.py`

## 📚 Philological Data
- **Manifest**: `styles/manifest.yml` (Master index of clusters/passports)
- **Clusters**: `styles/clusters/*.yml` (School definitions)
- **Passports**: `styles/passports/*.yml` (Individual style parameters)
- **Instructions**: `ClaudeStyles/*.md` (Detailed agentic prompts)
- **Knowledge**: `knowledge/` (SQLite DB and reference metadata)

## 🌐 Web Studio (`web/`)
- **App Core**: `web/src/App.jsx` (Bi-directional WS logic, Trace UI)
- **Styles**: `web/src/index.css` (Glassmorphic design system)
- **Project**: `web/package.json` (Vite/React metadata)

## 📑 Documentation
- **Strategy**: `GEMINI_ROADMAP.md` (Current project state)
- **Onboarding**: `docs/onboarding.md` (Beginner guide)
- **Technical**: `docs/cli.md`, `docs/deployment.md`, `docs/scenarios.md`
- **History**: `CHANGELOG.md`

## 🛡️ Validation & Evals
- **Schemas**: `schemas/*.schema.json` (Output shapes for all agents)
- **Evals**: `evals/manifest.json`, `evals/cases/` (33 philological test cases)
- **Tools**: `tools/validate_project.py` (Structural integrity script)

## 🔌 Editor Integrations
- **Obsidian**: `docs/obsidian-integration-poc.js`
- **MS Word**: `docs/rws-word-manifest.xml`, `docs/rws-word-taskpane.html`

---
*Generated automatically for the v2.4.0 Agentic Evolution.*

_Dr. Mārcis Gasūns_
