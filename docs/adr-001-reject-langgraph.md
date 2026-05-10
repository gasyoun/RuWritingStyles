# Architecture Decision Record (ADR) 001: Rejection of LangGraph and Future Phases Roadmap

**Date**: 2026-05-10  
**Status**: Accepted  
**Context**: Planning for Phase IV (Advanced Agentic Orchestration) and establishing the long-term roadmap (Phases V-VII).

## 1. The Decision: Rejecting LangGraph/Smolagents

### Context
During the Phase III architectural review, migrating the core pipeline routing to an established multi-agent framework like LangGraph or Smolagents was considered for Phase IV.

### Decision
We formally **reject** the adoption of LangGraph or any opaque third-party agentic orchestration framework. We will maintain and evolve our custom, SQLite-backed pipeline ("Harness Over Model").

### Rationale
1. **Determinism and Observability**: Our current linear pipeline (`Review` → `Council` → `Revision` → `Verification`) strictly logs every state transition, token cost, and intermediate artifact to `rws.db`. LangGraph introduces opaque cyclic graphs that are notoriously difficult to debug and resume if interrupted.
2. **Durable Execution (`rws resume`)**: We recently implemented a robust step-tracking system in SQLite. Porting this to LangGraph's state management would destroy our custom `ci-eval-gate` integrity.
3. **Philological Specificity**: The Socratic Council pattern (with its Conflict Matrix and Bloom Taxonomy labeling) is highly specialized. Generic frameworks force agents into conversational loops rather than our required strict, structured JSON schema validations.

---

## 2. Roadmap Confirmation (Phases V - VII)

The following trajectory has been officially approved for the RuWritingStyles project:

### Phase V: Real-Time Collaborative Workbench
- **Concept**: Transition the Web Studio from a static reporting dashboard into a live, collaborative environment.
- **Implementation**: Introduce WebSockets to stream the Socratic Council's deliberations in real-time, allowing human researchers to inject arguments or halt the process "on the fly."

### Phase VI: Deep Document Retrieval (RAG)
- **Concept**: Enhance the Knowledge Hub by ingesting primary literature.
- **Constraint**: **No PDF storage.** The system will rely exclusively on extracted `.txt` files to minimize storage overhead and parsing complexity.
- **Implementation**: Agents will extract exact quotes from these TXT files to ground their stylistic arguments with primary textual evidence.

### Phase VII: Editor Integrations (The Final Mile)
- **Concept**: Bring the RuWritingStyles engine directly to the researcher's drafting environment.
- **Integrations Approved**: **Obsidian** and **MS Word** plugins.
- **Integrations Rejected**: VS Code (deemed unnecessary for the target demographic of academic philologists).
- **Implementation**: Expose the FastAPI endpoints so a researcher can highlight a paragraph in Word/Obsidian, hit a hotkey, and have the Socratic Council rewrite it to match a specific stylistic passport (e.g., "Bakhtin" or "Zaliznyak") instantly.
