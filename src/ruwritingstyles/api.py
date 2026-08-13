"""FastAPI bridge for RuWritingStyles CLI."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Literal, Set

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, run_id: str, websocket: WebSocket):
        await websocket.accept()
        if run_id not in self.active_connections:
            self.active_connections[run_id] = set()
        self.active_connections[run_id].add(websocket)

    def disconnect(self, run_id: str, websocket: WebSocket):
        if run_id in self.active_connections:
            self.active_connections[run_id].discard(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]

    async def broadcast(self, run_id: str, message: dict):
        if run_id in self.active_connections:
            disconnected = []
            for connection in tuple(self.active_connections[run_id]):
                try:
                    await connection.send_json(message)
                except Exception:
                    disconnected.append(connection)
            for connection in disconnected:
                self.disconnect(run_id, connection)

import queue

class SharedState:
    def __init__(self):
        self.injections: Dict[str, queue.Queue] = {}

    def get_queue(self, run_id: str) -> queue.Queue:
        if run_id not in self.injections:
            self.injections[run_id] = queue.Queue()
        return self.injections[run_id]

    def add_injection(self, run_id: str, content: str):
        self.get_queue(run_id).put(content)

manager = ConnectionManager()
shared_state = SharedState()

from .config import Manifest, load_manifest, load_model_policy, repo_root_from
from .council import TEXT_DOMAINS
from .pipeline import ExecutionMode, PipelineOptions, build_step_plan, preflight_budget, run_full_pipeline
from .profiling import calculate_bloom_stats, calculate_methodological_compass, calculate_tension_heatmap
from .provider_status import provider_statuses, provider_statuses_json
from .runs import create_prepare_run, list_runs as list_run_ids, load_run_artifact
from .segment import read_document, normalize_document, segment_markdown
from .providers import provider_from_name
from .journals import list_journal_presets, load_journal_preset
from .project import set_journal_profile
import argparse
import json
from .io_utils import atomic_write_json


_CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    if origin.strip()
]

app = FastAPI(title="RuWritingStyles API")

# Middleware must be registered before routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


def _within(root: Path, path: Path) -> bool:
    """True if `path` is `root` itself or nested under it (both already resolved).
    The single path-containment primitive shared by `_run_dir`, the S3 input-path
    guard, and the S1 static-route guard — one source of truth so a later
    hardening tweak (symlinks, Windows case-folding) can't be applied to one
    guard and silently forgotten in another."""
    return path == root or root in path.parents


# --- S4: optional bearer-token auth (see docs/security-review-2026-06.md) ---
# Off by default so the loopback dev tool keeps working with no setup. Set
# RWS_API_TOKEN to require `Authorization: Bearer <token>` — the prerequisite,
# with RWS_BIND_HOST, for binding a public interface.
# DEFAULT-DENY: every route requires the token *except* the explicitly-listed
# static-frontend paths. A new data/API route is therefore protected
# automatically — nothing ships unauthenticated by forgetting to add it to a
# protected-prefix list.
_API_TOKEN = os.environ.get("RWS_API_TOKEN", "").strip()
_PUBLIC_PREFIXES = ("/assets/",)             # built SPA JS/CSS bundles (trailing slash: /assets../x stays protected)
_PUBLIC_PATHS = {"/", "/index.html", "/favicon.ico"}


def _bearer_ok(authorization: str | None) -> bool:
    if not _API_TOKEN:
        return True  # auth disabled
    if not authorization:
        return False
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return secrets.compare_digest(parts[1], _API_TOKEN)
    return False


def _is_public_request(method: str, path: str) -> bool:
    if method == "OPTIONS":  # never block CORS preflight
        return True
    return path in _PUBLIC_PATHS or any(path.startswith(p) for p in _PUBLIC_PREFIXES)


@app.middleware("http")
async def _require_token(request, call_next):
    if (
        _API_TOKEN
        and not _is_public_request(request.method, request.url.path)
        and not _bearer_ok(request.headers.get("authorization"))
    ):
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)


@app.get("/status")
async def get_status(provider: str = "google"):
    statuses = provider_statuses()
    return provider_statuses_json(statuses, provider=provider)


@app.get("/runs")
async def get_runs():
    from .db import Database
    repo_root = repo_root_from()
    db = Database(repo_root)
    return [r['run_id'] for r in db.list_runs()]


@app.get("/runs/{run_id}")
async def get_run_details(run_id: str):
    from .db import Database
    repo_root = repo_root_from()
    db = Database(repo_root)
    run_entry = db.get_run(run_id)
    if not run_entry:
        raise HTTPException(status_code=404, detail="Run not found in database")

    run_dir = _run_dir(repo_root, run_id)
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run directory not found")

    return {
        "id": run_id,
        "status": run_entry.get("status"),
        "original_text": _read_text(run_dir / "original.md"),
        "normalized_text": _read_text(run_dir / "normalized.md"),
        "revised_text": _read_text(run_dir / "revised.md"),
        "segments": load_run_artifact(run_dir, "segments.json"),
        "council": load_run_artifact(run_dir, "council.json"),
        "revision": load_run_artifact(run_dir, "revision.json"),
        "verification": load_run_artifact(run_dir, "verification.json"),
        "sentiment": load_run_artifact(run_dir, "sentiment.json"),
        "impact": load_run_artifact(run_dir, "impact.json"),
        "syntax": load_run_artifact(run_dir, "syntax.json"),
        "profile": run_entry.get("profile", {}),
        "bloom_stats": run_entry.get("bloom_stats", {}),
        "tension": run_entry.get("tension", {}),
        "bias_audit": run_entry.get("bias_audit", {}),
        "citation_stats": run_entry.get("citation_stats", {}),
    }


@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    if _API_TOKEN:
        # Browsers can't set headers on a WebSocket; accept ?token= too.
        query_token = websocket.query_params.get("token")
        authorized = _bearer_ok(websocket.headers.get("authorization")) or (
            bool(query_token) and secrets.compare_digest(query_token, _API_TOKEN)
        )
        if not authorized:
            await websocket.close(code=1008)  # policy violation
            return
    await manager.connect(run_id, websocket)
    try:
        while True:
            # Handle incoming messages (e.g., Socratic Injection)
            data = await websocket.receive_json()
            if data.get("type") == "human_injection":
                content = data.get("content")
                if content:
                    shared_state.add_injection(run_id, content)
                    await manager.broadcast(run_id, {
                        "type": "injection_received",
                        "status": "queued",
                        "content": content
                    })
    except WebSocketDisconnect:
        manager.disconnect(run_id, websocket)


@app.get("/runs/{run_id}/status")
async def get_run_step_status(run_id: str):
    from .db import Database
    repo_root = repo_root_from()
    db = Database(repo_root)
    run_entry = db.get_run(run_id)
    if not run_entry:
        raise HTTPException(status_code=404, detail="Run not found in database")
        
    steps = db.get_run_steps(run_id)
    return {
        "run_id": run_id,
        "overall_status": run_entry.get("status"),
        "steps": steps
    }


@app.get("/runs/{run_id}/concordance")
async def get_run_concordance(run_id: str):
    from .concordance import get_concordance_data
    from .knowledge import extract_keywords_from_reviews
    repo_root = repo_root_from()
    run_dir = _run_dir(repo_root, run_id)
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run not found")

    keywords = extract_keywords_from_reviews(run_dir)
    return get_concordance_data(repo_root, keywords)


class RunRequest(BaseModel):
    # Provide EITHER `text` (inline document body — preferred for editor clients
    # like the Obsidian plugin) OR `input_path` (a server-side file, allowlisted).
    input_path: str | None = None
    text: str | None = None
    filename: str | None = None  # label for the run id / source (text mode)
    provider: str = "google"
    model: str | None = None
    profile: str = "researcher"
    journal: str | None = None  # journal preset id; honoured by the pipeline
    execute: bool = True
    max_iterations: int = Field(default=1, ge=1)
    deliberate: bool = False
    scrutiny: bool = False
    lint_translit: bool = True
    budget_mode: Literal["smoke", "standard", "expensive"] = "standard"
    allow_expensive: bool = False
    # Closed vocabulary (same as `rws prepare --text-domain`). Default keeps
    # pre-H2576 clients on the neutral `unknown` row.
    text_domain: str = "unknown"


def _input_root(repo_root: Path) -> Path:
    """The directory `input_path` must resolve under (S3). Defaults to the repo
    root; widen with RWS_INPUT_ROOT (e.g. a documents folder) for legitimate
    out-of-repo inputs. Deny-by-default closes the arbitrary-file-read in the
    review — see docs/security-review-2026-06.md."""
    configured = os.environ.get("RWS_INPUT_ROOT")
    root = Path(configured).expanduser() if configured else repo_root
    return root.resolve()


def _max_text_chars() -> int:
    """Cap on an inline `text` submission, to bound memory/cost. Override with
    RWS_MAX_TEXT_CHARS."""
    try:
        return int(os.environ.get("RWS_MAX_TEXT_CHARS", "300000"))
    except ValueError:
        return 300000


def _resolve_execute_input(req: "RunRequest", repo_root: Path) -> tuple[Path, str]:
    """Resolve an execute request to (label_path, original_text).

    Text mode (`req.text`) reads nothing from disk — the body IS the document — so
    it is not subject to the input_path allowlist; the label_path is virtual, used
    only for the run-id slug and the source label. File mode keeps the S3 allowlist.
    """
    if req.text is not None:
        if len(req.text) > _max_text_chars():
            raise HTTPException(
                status_code=413,
                detail=f"text exceeds {_max_text_chars()} characters",
            )
        # Virtual label only (never created / read); strip any directory parts.
        label = Path(req.filename or "obsidian-note.md").name or "obsidian-note.md"
        return repo_root / "runs" / label, req.text

    if not req.input_path:
        raise HTTPException(status_code=400, detail="provide either 'text' or 'input_path'")

    input_path = Path(req.input_path).expanduser()
    if not input_path.is_absolute():
        input_path = repo_root / input_path
    input_path = input_path.resolve()
    if not _within(_input_root(repo_root), input_path):
        raise HTTPException(status_code=403, detail="input_path is outside the allowed root")
    if not input_path.exists():
        raise HTTPException(status_code=404, detail=f"Input file not found at: {req.input_path}")
    return input_path, read_document(input_path)


@app.post("/runs/execute")
async def execute_run(req: RunRequest, background_tasks: BackgroundTasks):
    repo_root = repo_root_from()
    input_path, original_text = _resolve_execute_input(req, repo_root)

    # Resolve the journal preset (if any) before creating the run so an unknown
    # id fails cleanly without leaving an orphan run directory.
    journal_profile = None
    if req.journal:
        journal_profile = load_journal_preset(repo_root, req.journal)
        if not journal_profile:
            raise HTTPException(
                status_code=400,
                detail=f"unknown journal '{req.journal}'; available: {list_journal_presets(repo_root)}",
            )

    if req.text_domain not in TEXT_DOMAINS:
        raise HTTPException(
            status_code=400,
            detail=f"unknown text_domain '{req.text_domain}'; available: {list(TEXT_DOMAINS)}",
        )

    manifest = load_manifest(repo_root)
    model_policy = load_model_policy(repo_root)
    options = PipelineOptions(
        mode=ExecutionMode.EXECUTE if req.execute else ExecutionMode.PREPARE,
        max_iterations=req.max_iterations,
        deliberate=req.deliberate,
        scrutiny=req.scrutiny,
        lint_translit=req.lint_translit,
        style_ids=tuple(manifest.mvp_style_ids),
        budget_mode=req.budget_mode,
        expensive_opt_in=req.allow_expensive,
    )
    if req.execute:
        from .budget import BudgetError
        try:
            preflight_budget(model_policy, options, req.provider)
        except BudgetError as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc

    normalized_text = normalize_document(original_text)
    segments = segment_markdown(normalized_text)

    run_dir = create_prepare_run(
        repo_root=repo_root,
        input_path=input_path,
        original_text=original_text,
        normalized_text=normalized_text,
        segments=segments,
        manifest=manifest,
        model_policy=model_policy,
        provider=req.provider,
        profile=req.profile,
        metadata={"text_domain": req.text_domain},
        config={
            "provider": req.provider,
            "model": req.model,
            "profile": req.profile,
            "execute": req.execute,
            "max_iterations": req.max_iterations,
            "deliberate": req.deliberate,
            "scrutiny": req.scrutiny,
            "no_lint_translit": not req.lint_translit,
            "budget_mode": req.budget_mode,
            "allow_expensive": req.allow_expensive,
            "text_domain": req.text_domain,
        },
        pipeline_options=options.to_json(),
        step_plan=build_step_plan(options),
    )

    # The pipeline (verifier / translit linter / report) honours the journal via
    # resolve_journal_profile(run_dir) → run_dir/project-context.json.
    if journal_profile:
        set_journal_profile(run_dir, journal_profile)

    if req.execute:
        import asyncio
        from .mcp_client import mcp_client
        loop = asyncio.get_event_loop()
        
        def on_update(msg):
            asyncio.run_coroutine_threadsafe(manager.broadcast(run_dir.name, msg), loop)
            
        def on_tool(run_id, msg):
            asyncio.run_coroutine_threadsafe(manager.broadcast(run_id, msg), loop)
            
        mcp_client.set_progress_callback(run_dir.name, on_tool)

        def run_pipeline_task():
            try:
                run_full_pipeline(
                    repo_root,
                    run_dir,
                    provider_name=req.provider,
                    model=req.model,
                    profile=req.profile,
                    on_update=on_update,
                    injection_queue=shared_state.get_queue(run_dir.name),
                    options=options,
                )
            finally:
                mcp_client.clear_progress_callback(run_dir.name)

        background_tasks.add_task(
            run_pipeline_task,
        )

    return {"run_id": run_dir.name}


class SelectionRequest(BaseModel):
    text: str
    provider: str = "google"
    profile: str = "researcher"

@app.post("/api/audit/selection")
async def audit_selection(req: SelectionRequest):
    """Instant audit for editor selections (Obsidian/Word)."""
    from .council import run_socratic_council
    from .generation import execute_revision_artifact
    from .config import load_model_policy

    repo_root = repo_root_from()
    provider = provider_from_name(req.provider)
    model_policy = load_model_policy(repo_root)
    model = model_policy.resolve_model("council", req.provider)
    
    # 1. Council deliberation
    findings = run_socratic_council(
        repo_root=repo_root,
        segments=[{"id": "selection", "content": req.text}],
        provider=provider,
        model=model,
        profile=req.profile
    )
    
    # 2. Immediate revision
    revision_id = "selection_revision"
    revision_prompt = f"Original: {req.text}\n\nCouncil Findings: {json.dumps(findings, ensure_ascii=False)}"
    
    # We mock a small revision artifact for the generator
    revised_text = execute_revision_artifact(
        repo_root=repo_root,
        revision_path=None, # Special mode for direct text
        provider=provider,
        model=model_policy.resolve_model("synthesis", req.provider),
        direct_input={"text": req.text, "findings": findings}
    )
    
    return {
        "original": req.text,
        "revised": revised_text,
        "findings": findings
    }


class ResolutionOverride(BaseModel):
    finding_id: str
    status: str
    human_comment: str

class ResolutionRequest(BaseModel):
    overrides: list[ResolutionOverride]

@app.post("/runs/{run_id}/resolve")
async def resolve_run(run_id: str, req: ResolutionRequest, background_tasks: BackgroundTasks):
    repo_root = repo_root_from()
    run_dir = _run_dir(repo_root, run_id)
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run not found")
        
    resolution_path = run_dir / "resolution.json"
    resolution_data = {
        "overrides": [dict(o) for o in req.overrides]
    }
    atomic_write_json(resolution_path, resolution_data)
    
    from .resolution import apply_resolution
    try:
        apply_resolution(run_dir, [dict(o) for o in req.overrides])
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
        
    # Re-run revision in background
    from .db import Database
    db = Database(repo_root)
    run_entry = db.get_run(run_id)
    provider = run_entry.get("provider", "google")
    model = run_entry.get("model")
    
    from .execution import execute_revision_artifact
    from .revision import create_revision_bundle
    from .diff import write_revision_diff
    from .runs import record_step_state, write_run_manifest
    import asyncio
    loop = asyncio.get_running_loop()

    def emit_revision(event: dict) -> None:
        asyncio.run_coroutine_threadsafe(manager.broadcast(run_id, event), loop)
    
    def background_revision():
        emit_revision(record_step_state(repo_root, run_dir, "revision", "executing"))
        try:
            revision = create_revision_bundle(repo_root=repo_root, run_dir=run_dir)
            model_policy = load_model_policy(repo_root)
            execute_revision_artifact(
                repo_root=repo_root,
                revision_path=revision.revision_json,
                provider=provider_from_name(provider),
                model=model or model_policy.resolve_model("synthesis", provider),
            )
            write_revision_diff(run_dir)
            emit_revision(record_step_state(
                repo_root, run_dir, "revision", "completed",
                artifact_path=revision.revision_json,
            ))
        except Exception as e:
            emit_revision(record_step_state(
                repo_root, run_dir, "revision", "failed", error=str(e),
            ))
            db.update_run_status(run_id, "failed", summary=str(e))
            write_run_manifest(repo_root, run_dir)
            emit_revision({"type": "run_status", "status": "failed", "error": str(e)})
            
    background_tasks.add_task(background_revision)
    return {"status": "resolutions applied, revision re-run queued"}

@app.post("/runs/{run_id}/finalize")
async def finalize_run(run_id: str):
    repo_root = repo_root_from()
    run_dir = _run_dir(repo_root, run_id)
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run not found")
        
    from .resolution import write_final_manuscript
    try:
        final_path = write_final_manuscript(run_dir)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"status": "finalized", "final_text": _read_text(final_path)}


@app.get("/api/compare")
async def compare_runs(run_ids: str):
    ids = run_ids.split(",")
    from .db import Database
    repo_root = repo_root_from()
    db = Database(repo_root)
    
    comparison = []
    for run_id in ids:
        run_data = db.get_run(run_id)
        if run_data:
            comparison.append({
                "run_id": run_id,
                "profile": run_data.get("profile", {}),
                "bloom_stats": run_data.get("bloom_stats", {}),
                "bias_score": run_data.get("bias_score"),
                "citation_stats": run_data.get("citation_stats"),
                "duration": run_data.get("duration_seconds"),
                "status": run_data.get("status")
            })
            
    return comparison


def _run_dir(repo_root: Path, run_id: str) -> Path:
    runs_dir = (repo_root / "runs").resolve()
    run_dir = (runs_dir / run_id).resolve()
    if not _within(runs_dir, run_dir):
        raise HTTPException(status_code=400, detail="Invalid run id")
    return run_dir


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Serve the built frontend if it exists
from .workspace import bundled_web_dist

try:
    frontend_path = bundled_web_dist()
except FileNotFoundError:
    frontend_path = Path("web/dist")
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=frontend_path / "assets"), name="assets")

    _frontend_root = frontend_path.resolve()

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("runs/") or full_path == "status":
            raise HTTPException(status_code=404)

        # Resolve and bounds-check before serving: the catch-all must never
        # escape web/dist/ (mirrors the _run_dir guard). Without this, a request
        # like GET /..%2f..%2f.env would read arbitrary files (LFI). See S1 in
        # docs/security-review-2026-06.md.
        file_path = (_frontend_root / full_path).resolve()
        if _within(_frontend_root, file_path) and file_path.is_file():
            return FileResponse(file_path)

        # Fallback to index.html for SPA routing
        return FileResponse(_frontend_root / "index.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    # Default to loopback; require an explicit opt-in to expose publicly. See S2
    # in docs/security-review-2026-06.md — the API ships no auth, so a routable
    # bind exposes unauthenticated run execution and local file reads.
    host = os.environ.get("RWS_BIND_HOST", "127.0.0.1")
    uvicorn.run(app, host=host, port=port)
