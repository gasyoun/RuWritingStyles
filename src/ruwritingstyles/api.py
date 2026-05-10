"""FastAPI bridge for RuWritingStyles CLI."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import Manifest, load_manifest, load_model_policy, repo_root_from
from .pipeline import run_full_pipeline
from .profiling import calculate_bloom_stats, calculate_methodological_compass, calculate_tension_heatmap
from .provider_status import provider_statuses, provider_statuses_json
from .runs import create_prepare_run, list_runs as list_run_ids, load_run_artifact
import argparse
import json


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
    input_path: str
    provider: str = "google"
    model: str | None = None
    profile: str = "researcher"
    execute: bool = True


@app.post("/runs/execute")
async def execute_run(req: RunRequest, background_tasks: BackgroundTasks):
    repo_root = repo_root_from()
    input_path = Path(req.input_path).expanduser()
    if not input_path.is_absolute():
        input_path = repo_root / input_path
    input_path = input_path.resolve()
    if not input_path.exists():
        raise HTTPException(status_code=404, detail=f"Input file not found at: {req.input_path}")

    original_text = read_document(input_path)
    manifest = load_manifest(repo_root)
    model_policy = load_model_policy(repo_root)

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
    )

    if req.execute:
        background_tasks.add_task(run_full_pipeline, repo_root, run_dir, provider_name=req.provider, model=req.model, profile=req.profile)

    return {"run_id": run_dir.name}


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
    resolution_path.write_text(json.dumps(resolution_data, ensure_ascii=False, indent=2), encoding="utf-8")
    
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
    
    def background_revision():
        db.update_step_status(run_id, "revision", "executing")
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
            db.update_step_status(run_id, "revision", "completed")
        except Exception as e:
            db.update_step_status(run_id, "revision", "failed", error=str(e))
            
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
    if runs_dir != run_dir and runs_dir not in run_dir.parents:
        raise HTTPException(status_code=400, detail="Invalid run id")
    return run_dir


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Serve the built frontend if it exists
frontend_path = Path("web/dist")
if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=frontend_path / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("runs/") or full_path == "status":
            raise HTTPException(status_code=404)
        
        # Check if file exists
        file_path = frontend_path / full_path
        if file_path.is_file():
            return FileResponse(file_path)
            
        # Fallback to index.html for SPA routing
        return FileResponse(frontend_path / "index.html")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
