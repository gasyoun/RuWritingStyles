_Created: 24-08-2026 · Last updated: 05-09-2026_

# Architectural Review: Phase II Completion & Phase III Design

**Date**: 2026-05-10
**Focus**: Assessment of Phase II implementation and critical review of Phase III (Zotero MCP) architecture.

## 1. Phase II Implementation Assessment

The completion of Phase II successfully transitioned the system from a prototype to a data-rich production environment. However, several pieces of technical debt were identified that must be resolved before executing the 595-run (17x35) full corpus audit.

### 1.1 Identified Technical Debt

1. **Inefficient JSON Parsing (`knowledge.py`)**
   - **Issue**: `KnowledgeManager.search()` parses large JSON arrays from disk using `json.loads()` on every query iteration. As the Birch Bark collection (`novgorod_gramoty.json`) expands, this will cause severe blocking I/O bottlenecks.
   - **Required Action**: Refactor `KnowledgeManager` to cache JSON data in memory upon instantiation (`__init__`) or migrate the collections into the SQLite `rws.db` using FTS5 (Full-Text Search).

2. **Synchronous Batching (`batch_analyzer.py`)**
   - **Issue**: The `run_multi_style_batch` function iterates over the 17 stylistic clusters synchronously (`for cluster_id in clusters:`). Processing a single document takes minutes; processing the entire corpus will take hours.
   - **Required Action**: Implement `asyncio.gather` or use a `ThreadPoolExecutor` to run the profiles concurrently. The underlying SQLite implementation in `db.py` handles concurrent writes adequately, allowing for safe parallelization.

3. **Brittle YAML Mutability (`style_evolution.py`)**
   - **Issue**: The automated style evolution mechanism modifies the YAML passport files using raw string manipulation (`content.replace("instructions: |", ...)`). This is highly unsafe and risks corrupting the YAML abstract syntax tree (AST).
   - **Required Action**: Transition from standard `str` operations to using `ruamel.yaml` to safely parse, modify, and dump the YAML structures while preserving comments and formatting.

---

## 2. Phase III Architecture Critique (Zotero & MCP)

The proposed architecture in `phase3-zotero-mcp-architecture.md` correctly identifies the Model Context Protocol (MCP) as the optimal solution for securely querying external academic libraries.

### 2.1 Approved Concepts
- **Security Isolation**: Keeping the Zotero Web API credentials confined to the external MCP Server ensures strict sandbox boundaries. The LLM cannot exfiltrate or hallucinate API keys.
- **Tiered Fallback**: The strategy of resolving citations locally first (Local Bibliography → Local Collections) before querying Zotero minimizes latency and LLM token costs.

### 2.2 Architectural Risks & Mandatory Revisions

1. **Tool-Calling Compatibility (`provider.py`)**
   - **Risk**: The architecture assumes seamless injection of MCP tools. Currently, the `LocalProvider` (Ollama/vLLM) and `MockProvider` are built around strict JSON-schema responses via `post_schema_validate`, not iterative function-calling loops.
   - **Constraint**: A formal `FunctionCallingProvider` interface must be introduced. If the active model lacks tool-use capabilities, the pipeline must gracefully degrade and rely solely on the local `KnowledgeManager`.

2. **Non-Deterministic Verification Boundaries**
   - **Risk**: The proposal suggests turning `citations.py` into an "agentic loop." The current `citations.py` is a fast, highly deterministic Python script. Handing open-ended control back to the LLM to "hunt" for citations introduces massive hallucination risks and unpredictable latency spikes.
   - **Constraint**: The LLM must not be allowed to "loop" indefinitely. The pipeline must execute a strictly constrained, single-turn prompt: *"Here is a missing citation: [X]. Here are your Zotero tools. Return the validated BibTeX or confirm it does not exist."*

3. **Rejection of LangGraph Orchestration**
   - **Risk**: The current project roadmap suggests migrating to LangGraph or Smolagents for Phase III orchestration. Our existing linear pipeline backed by SQLite provides superior observability, durable checkpointing (`rws resume`), and strict adherence to the "Harness Over Model" standard.
   - **Constraint**: **Do not migrate to LangGraph.** Maintain the custom harness. MCP routing and tool-use logic can be implemented directly within our existing `council.py` and `verification.py` nodes without abandoning the highly stable SQLite-backed infrastructure.

_Dr. Mārcis Gasūns_
