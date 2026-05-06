"""Execute prompt artifacts with a provider and update run artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .providers import BaseProvider, ProviderRequest, load_schema


def execute_review_artifact(*, repo_root: Path, review_path: Path, provider: BaseProvider, model: str | None = None) -> None:
    review = _load_json(review_path)
    prompt_path = repo_root / str(review["prompt_path"])
    segments = _load_json(review_path.parents[1] / "segments.json")
    output = provider.generate_json(
        ProviderRequest(
            task="review",
            prompt=prompt_path.read_text(encoding="utf-8"),
            schema=load_schema(repo_root, "schemas/review-output.schema.json"),
            metadata={
                "run_id": review["run_id"],
                "style_id": review["style_id"],
                "first_paragraph_span_id": _first_paragraph_span_id(segments),
            },
            model=model,
        )
    )
    review["status"] = "completed"
    review["summary"] = output.get("summary", "")
    review["findings"] = output.get("findings", [])
    _write_json(review_path, review)


def execute_council_artifact(*, repo_root: Path, council_path: Path, provider: BaseProvider, model: str | None = None) -> None:
    council = _load_json(council_path)
    prompt_path = repo_root / str(council["prompt_path"])
    finding_ids = []
    for relative in council.get("review_files", []):
        review = _load_json(repo_root / str(relative))
        for finding in review.get("findings", []):
            if isinstance(finding, dict) and finding.get("id"):
                finding_ids.append(str(finding["id"]))
    output = provider.generate_json(
        ProviderRequest(
            task="council",
            prompt=prompt_path.read_text(encoding="utf-8"),
            schema=load_schema(repo_root, "schemas/council-output.schema.json"),
            metadata={
                "run_id": council["run_id"],
                "finding_ids": finding_ids,
            },
            model=model,
        )
    )
    council["status"] = "completed"
    council["replies"] = output.get("replies", [])
    council["decisions"] = output.get("decisions", [])
    _write_json(council_path, council)


def execute_revision_artifact(*, repo_root: Path, revision_path: Path, provider: BaseProvider, model: str | None = None) -> None:
    revision = _load_json(revision_path)
    prompt_path = repo_root / str(revision["prompt_path"])
    source_path = repo_root / str(revision["source_document"])
    normalized_text = source_path.read_text(encoding="utf-8")
    output = provider.generate_json(
        ProviderRequest(
            task="revision",
            prompt=prompt_path.read_text(encoding="utf-8"),
            schema=load_schema(repo_root, "schemas/revision-output.schema.json"),
            metadata={
                "run_id": revision["run_id"],
                "normalized_text": normalized_text,
            },
            model=model,
        )
    )
    revised_path = revision_path.parent / "revised.md"
    revised_path.write_text(str(output.get("revised_document", normalized_text)), encoding="utf-8")
    revision["status"] = "completed"
    revision["revised_document_path"] = _repo_relative(repo_root, revised_path)
    revision["applied_changes"] = output.get("applied_changes", [])
    revision["unresolved"] = output.get("unresolved", [])
    _write_json(revision_path, revision)


def execute_verification_artifact(*, repo_root: Path, verification_path: Path, provider: BaseProvider, model: str | None = None) -> None:
    verification = _load_json(verification_path)
    prompt_path = repo_root / str(verification["prompt_path"])
    output = provider.generate_json(
        ProviderRequest(
            task="verification",
            prompt=prompt_path.read_text(encoding="utf-8"),
            schema=load_schema(repo_root, "schemas/verification-output.schema.json"),
            metadata={
                "run_id": verification["run_id"],
            },
            model=model,
        )
    )
    verification["status"] = output.get("status", "needs_human_review")
    verification["passed"] = output.get("passed", [])
    verification["warnings"] = output.get("warnings", [])
    _write_json(verification_path, verification)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _first_paragraph_span_id(segments_doc: dict[str, Any]) -> str:
    for segment in segments_doc.get("segments", []):
        if isinstance(segment, dict) and segment.get("type") == "paragraph":
            return str(segment["span_id"])
    for segment in segments_doc.get("segments", []):
        if isinstance(segment, dict) and segment.get("span_id"):
            return str(segment["span_id"])
    return "p001"


def _repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)
