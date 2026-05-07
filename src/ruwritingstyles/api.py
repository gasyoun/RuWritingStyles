"""FastAPI bridge for RuWritingStyles CLI."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .provider_status import provider_statuses, provider_statuses_json

app = FastAPI(title="RuWritingStyles API")

@app.get("/status")
async def get_status(provider: str = "google"):
    statuses = provider_statuses()
    return provider_statuses_json(statuses, provider=provider)

# Enable CORS for the Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class RunRequest(BaseModel):
    input_path: str
    provider: str = "google"
    archetype: str | None = None
    execute: bool = True

@app.get("/runs")
async def list_runs():
    repo_root = Path.cwd()
    runs_dir = repo_root / "runs"
    if not runs_dir.exists():
        return []
    return [d.name for d in runs_dir.iterdir() if d.is_dir()]

@app.get("/runs/{run_id}")
async def get_run_data(run_id: str):
    repo_root = Path.cwd()
    run_dir = repo_root / "runs" / run_id
    
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="Run not found")
        
    # Read segments, revision, etc.
    data = {}
    for filename in ["segments.json", "revision.json", "verification.json", "sentiment.json"]:
        p = run_dir / filename
        if p.exists():
            import json
            data[filename.replace(".json", "")] = json.loads(p.read_text(encoding="utf-8"))
            
    # Also load original and revision text
    for name, filename in [("original_text", "original.md"), ("revised_text", "revision.md")]:
        p = run_dir / filename
        if p.exists():
            data[name] = p.read_text(encoding="utf-8")
            
    return data

@app.post("/runs/execute")
async def execute_run(req: RunRequest):
    # Call the CLI as a subprocess
    cmd = [
        "python", "-m", "ruwritingstyles.cli", "run", 
        req.input_path, 
        "--provider", req.provider
    ]
    if req.execute:
        cmd.append("--execute")
    if req.archetype:
        cmd.extend(["--archetype", req.archetype])
        
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return {"status": "success", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"CLI Error: {e.stderr}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
