"""FastAPI bridge for RuWritingStyles CLI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import Manifest, load_manifest, load_model_policy, repo_root_from
from .pipeline import run_full_pipeline
from .profiling import calculate_bloom_stats, calculate_methodological_compass, calculate_tension_heatmap
from .provider_status import provider_statuses, provider_statuses_json
from .runs import create_prepare_run, list_runs as list_run_ids, load_run_artifact
from .segment import normalize_document, read_document, segment_markdown

app = FastAPI(title="RuWritingStyles API")


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
    )

    if req.execute:
        background_tasks.add_task(run_full_pipeline, repo_root, run_dir, provider_name=req.provider, model=req.model, profile=req.profile)

    return {"run_id": run_dir.name}


# Enable CORS for the Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
