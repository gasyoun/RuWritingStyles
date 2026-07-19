"""Run artifact creation."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import Manifest, ModelPolicy
from .html_summary import write_html_report
from .report import write_run_report
from .segment import Segment
from .io_utils import atomic_write_json, atomic_write_text


def make_unique_id(
    label: str,
    now: datetime | None = None,
    unique_suffix: str | None = None,
) -> str:
    """Return a sortable, collision-resistant automatic artifact ID."""
    timestamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%d-%H%M%S-%f")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", label).strip("-").lower() or "artifact"
    suffix = unique_suffix or uuid4().hex[:8]
    return f"{timestamp}-{slug}-{suffix}"


def make_run_id(
    input_path: Path,
    now: datetime | None = None,
    unique_suffix: str | None = None,
) -> str:
    return make_unique_id(input_path.stem or "document", now, unique_suffix)


def create_prepare_run(
    *,
    repo_root: Path,
    input_path: Path,
    original_text: str,
    normalized_text: str,
    segments: list[Segment],
    manifest: Manifest,
    model_policy: ModelPolicy,
    run_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    provider: str = "google",
    archetype: str | None = None,
    profile: str | None = None,
    config: dict | None = None,
    pipeline_options: dict[str, Any] | None = None,
    step_plan: list[dict[str, Any]] | None = None,
) -> Path:
    actual_run_id = run_id or make_run_id(input_path)
    runs_dir = repo_root / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_dir = runs_dir / actual_run_id
    if run_dir.exists():
        raise FileExistsError(f"run directory already exists: {run_dir}")

    staging_dir = runs_dir / f".{actual_run_id}.tmp-{uuid4().hex}"
    staging_dir.mkdir(parents=False, exist_ok=False)
    try:
        if metadata:
            atomic_write_json(staging_dir / "metadata.json", metadata)

        atomic_write_text(staging_dir / "original.md", original_text)
        atomic_write_text(staging_dir / "normalized.md", normalized_text)
        atomic_write_json(
            staging_dir / "segments.json",
            {
                "run_id": actual_run_id,
                "input_path": _repo_relative(repo_root, input_path),
                "segment_count": len(segments),
                "segments": [segment.to_json() for segment in segments],
            },
        )
        write_run_report(staging_dir)
        write_html_report(staging_dir)

        now = datetime.now(timezone.utc).isoformat()
        atomic_write_json(
            staging_dir / "run.json",
            {
                "run_id": actual_run_id,
                "input_path": str(input_path),
                "provider": provider,
                "model": None,
                "archetype": archetype,
                "profile": profile,
                "status": "prepared",
                "created_at": now,
                "started_at": None,
                "finished_at": None,
                "duration_seconds": None,
                "updated_at": now,
                "summary": None,
                "text_domain": (metadata or {}).get("text_domain", "unknown"),
                "config": config,
                "pipeline_options": pipeline_options,
                "step_plan": step_plan or [],
                "metrics": {},
                "steps": [],
                "styles": _collect_style_audit(staging_dir),
            },
        )

        # Publishing a same-volume directory rename prevents readers from ever
        # observing a half-created run. The durable run precedes the SQLite
        # index, so an indexing failure remains recoverable from run.json.
        os.replace(staging_dir, run_dir)
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise

    from .db import Database
    db = Database(repo_root)
    db.register_run(
        run_id=actual_run_id,
        input_path=str(input_path),
        provider=provider,
        archetype=archetype,
        profile=profile,
        config=config,
    )
    write_run_manifest(
        repo_root,
        run_dir,
        pipeline_options=pipeline_options,
        step_plan=step_plan,
    )
    return run_dir


_RUN_COLUMNS = (
    "run_id", "input_path", "provider", "model", "archetype", "profile",
    "status", "created_at", "started_at", "finished_at", "duration_seconds",
    "updated_at", "summary",
)


# Council decision statuses (schemas/council.schema.json enum):
#   accepted / accepted_with_modification -> the style's finding was honored in the rewrite
#   rejected / deferred                   -> dissent the rewrite did not act on (the trace we want)
#   informational                         -> a note, neither honored nor overruled
_HONORED_STATUSES = {"accepted", "accepted_with_modification"}
_OVERRULED_STATUSES = {"rejected", "deferred"}


def _collect_style_audit(run_dir: Path) -> dict[str, Any]:
    """A style-intent audit trail for run.json (prompt-fidelity review F4).

    Synthesis stages (council/revision) work from distilled findings, so a run
    otherwise cannot show *which* styles judged it or *what was overruled*. This
    records that from the on-disk artifacts: the styles that actually produced a
    review, the council's accept/reject tally, the overruled findings (dissent
    that left no trace in the rewrite), and the terminological commitments the
    revision was meant to honor. Purely descriptive — reads artifacts, changes
    no prompt or pipeline behaviour. All fields degrade gracefully when a stage
    did not run (e.g. prompt-only mode)."""

    def _load(path: Path) -> Any:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    audit: dict[str, Any] = {
        "selected": [],
        "council_decisions": {"honored": 0, "overruled": 0, "informational": 0},
        "overruled": [],
        "stylistic_commitments": [],
    }

    reviews_dir = run_dir / "reviews"
    if reviews_dir.exists():
        selected = []
        for review_path in sorted(reviews_dir.glob("*.review.json")):
            review = _load(review_path)
            if isinstance(review, dict) and review.get("style_id"):
                findings = review.get("findings")
                selected.append({
                    "style_id": review["style_id"],
                    "status": review.get("status"),
                    "findings": len(findings) if isinstance(findings, list) else 0,
                })
        audit["selected"] = selected

    council = _load(run_dir / "council.json")
    if isinstance(council, dict):
        decisions = council.get("decisions")
        if isinstance(decisions, list):
            honored = informational = 0
            for decision in decisions:
                if not isinstance(decision, dict):
                    continue
                status = str(decision.get("status", "")).lower()
                if status in _HONORED_STATUSES:
                    honored += 1
                elif status in _OVERRULED_STATUSES:
                    audit["overruled"].append({
                        "finding_id": decision.get("finding_id"),
                        "status": decision.get("status"),
                        "primary_school": decision.get("primary_school"),
                        "reason": decision.get("reason"),
                    })
                else:
                    informational += 1
            audit["council_decisions"] = {
                "honored": honored,
                "overruled": len(audit["overruled"]),
                "informational": informational,
            }
        commitments = council.get("stylistic_commitments")
        if isinstance(commitments, list):
            audit["stylistic_commitments"] = [
                {"term": c.get("term"), "decision": c.get("decision")}
                for c in commitments
                if isinstance(c, dict)
            ]

    return audit


def load_run_manifest(run_dir: Path) -> dict[str, Any]:
    """Load and validate the durable state for a run."""

    path = run_dir / "run.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing durable run state: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"malformed durable run state: {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("run_id") != run_dir.name:
        raise ValueError(f"invalid durable run state in {path}: run_id mismatch")
    if not isinstance(value.get("steps", []), list):
        raise ValueError(f"invalid durable run state in {path}: steps must be a list")
    return value


def write_run_manifest(
    repo_root: Path,
    run_dir: Path,
    *,
    pipeline_options: dict[str, Any] | None = None,
    step_plan: list[dict[str, Any]] | None = None,
    budget: dict[str, Any] | None = None,
) -> Path | None:
    """Write a self-describing `run.json` (status, timestamps, config, metrics,
    steps) so a run directory does not depend on the gitignored `rws.db`. The DB
    stays the live source during a run; this is the durable on-disk snapshot, and
    makes the DB a rebuildable index over runs/."""
    from .db import Database

    db = Database(repo_root)
    run_id = run_dir.name
    run = db.get_run(run_id)
    if not run:
        return None

    metrics = {k: v for k, v in run.items() if k not in _RUN_COLUMNS and k != "config_json"}
    config = None
    raw_config = run.get("config_json")
    if raw_config:
        try:
            config = json.loads(raw_config)
        except (json.JSONDecodeError, TypeError):
            config = None

    text_domain = "unknown"
    meta_path = run_dir / "metadata.json"
    if meta_path.exists():
        try:
            text_domain = json.loads(meta_path.read_text(encoding="utf-8")).get("text_domain", "unknown")
        except (json.JSONDecodeError, OSError):
            pass

    previous: dict[str, Any] = {}
    if (run_dir / "run.json").exists():
        previous = load_run_manifest(run_dir)

    manifest: dict[str, Any] = {key: run.get(key) for key in _RUN_COLUMNS}
    manifest["text_domain"] = text_domain
    manifest["config"] = config
    manifest["pipeline_options"] = (
        pipeline_options if pipeline_options is not None else previous.get("pipeline_options")
    )
    manifest["step_plan"] = step_plan if step_plan is not None else previous.get("step_plan", [])
    manifest["budget"] = budget if budget is not None else previous.get("budget")
    manifest["metrics"] = metrics
    manifest["steps"] = db.get_run_steps(run_id)
    manifest["styles"] = _collect_style_audit(run_dir)

    atomic_write_json(run_dir / "run.json", manifest)
    return run_dir / "run.json"


def record_step_state(
    repo_root: Path,
    run_dir: Path,
    step_id: str,
    status: str,
    *,
    artifact_path: Path | str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Update the rebuildable index and immediately refresh durable state."""

    from .db import Database

    path_value = str(artifact_path) if artifact_path is not None else None
    Database(repo_root).update_step_status(
        run_dir.name,
        step_id,
        status,
        artifact_path=path_value,
        error=error,
    )
    write_run_manifest(repo_root, run_dir)
    event: dict[str, Any] = {
        "type": "step_update",
        "step_id": step_id,
        "status": status,
    }
    if path_value is not None:
        event["artifact_path"] = path_value
    if error is not None:
        event["error"] = error
    return event


def list_runs(repo_root: Path) -> list[str]:
    runs_dir = repo_root / "runs"
    if not runs_dir.exists():
        return []
    # Return directory names, sorted by creation time (newest first)
    dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
    dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    return [d.name for d in dirs]


def load_run_artifact(run_dir: Path, filename: str) -> dict[str, Any]:
    path = run_dir / filename
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)
