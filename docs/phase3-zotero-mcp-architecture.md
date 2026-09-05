_Created: 24-08-2026 · Last updated: 05-09-2026_

# Phase III Architecture: Zotero MCP Integration

## 1. Executive Summary
As part of Phase III (External Agent Integration), RuWritingStyles will transition from relying solely on static local JSON bibliographies to dynamically querying external academic libraries. By implementing the Model Context Protocol (MCP) to interface with Zotero, the Citation Verifier will be able to resolve and validate citations against a researcher's live, curated library.

## 2. Core Objectives
- **Dynamic Grounding**: Allow the Citation Verifier to ground hallucinated or missing citations by querying external sources.
- **MCP Client Integration**: Implement an MCP client layer within the RuWritingStyles execution pipeline to communicate with an external Zotero MCP Server.
- **Fall-Through Verification**: Establish a tiered verification strategy: Local `bibliography.json` → Local specialized collections (`novgorod_gramoty.json`) → External Zotero MCP.

## 3. Architectural Components

### 3.1 The Zotero MCP Server
We will require a dedicated MCP server that acts as a bridge between the standard Model Context Protocol and the Zotero Web API. 
- **Capabilities provided to the Agent**:
  - `search_bibliography(query: str)`: Searches the user's Zotero library for authors, titles, or tags.
  - `get_item_details(item_id: str)`: Retrieves the full BibTeX or JSON representation of a specific item.
  - `list_collections()`: Lists the specialized folders (e.g., "Structuralism", "Dialectology") within the Zotero account.

### 3.2 The RuWritingStyles MCP Client (`src/ruwritingstyles/mcp_client.py`)
A new module will be introduced to handle the client-side MCP lifecycle:
- Manages connection to the Zotero MCP server (via stdio or SSE).
- Exposes the MCP tools directly to the `provider.py` so that the LLM (Gemini/Claude) can actively call them during the Verification stage.

### 3.3 Updates to `citations.py` and `knowledge.py`
The current verification logic must be updated to support the MCP fallback:
1. Extract citations from the text.
2. `KnowledgeManager` attempts a local resolution.
3. If local resolution fails (marked as 'Missing/Hallucinated'), the pipeline triggers a specialized Verification Agent prompt.
4. The Verification Agent uses the `search_bibliography` MCP tool to query Zotero.
5. If found in Zotero, the citation is marked as **Verified (External)** and the metadata is cached locally.

## 4. Implementation Steps

### Step 1: Establish MCP Foundation
- Create `src/ruwritingstyles/mcp_client.py`.
- Implement a basic asynchronous client that can connect to a mock MCP server to ensure the pipeline doesn't block.

### Step 2: Agent Tooling Injection
- Update `src/ruwritingstyles/provider.py` to accept and serialize JSON Schema tool definitions from the MCP server.
- Ensure that the execution loop supports function calling (tool use) for the Verification stage.

### Step 3: Zotero Server Configuration
- Define the configuration schema in `model_policy.yml` to store the connection details for the Zotero MCP Server (e.g., API keys, User IDs, server paths).

### Step 4: Verification Pipeline Refactoring
- Refactor `citations.py` to be an agentic loop rather than a static string-matching script. If the initial static check fails, it must prompt the LLM to use its Zotero tools to resolve the discrepancy.

## 5. Security & Isolation (Sandbox Boundaries)
- The Zotero API key must **never** be exposed to the LLM. It remains securely within the environment variables accessed only by the MCP Server.
- The MCP Client will strictly validate all tool calls originating from the LLM before passing them to the server to prevent prompt injection attacks aimed at deleting or modifying Zotero libraries (Read-Only access enforced).

_Dr. Mārcis Gasūns_
