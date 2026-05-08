"""Execute prompt artifacts with a provider and update run artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

from .provider_log import append_provider_log
from .providers import BaseProvider, ProviderRequest, load_schema


def execute_review_artifact(*, repo_root: Path, review_path: Path, provider: BaseProvider, model: str | None = None) -> None:
    review = _load_json(review_path)
    prompt_path = repo_root / str(review["prompt_path"])
    segments = _load_json(review_path.parents[1] / "segments.json")
    output = _generate_with_log(
        repo_root=repo_root,
        run_dir=review_path.parents[1],
        artifact_path=review_path,
        provider=provider,
        provider_request=ProviderRequest(
            task="review",
            prompt=prompt_path.read_text(encoding="utf-8"),
            schema=load_schema(repo_root, "schemas/review-output.schema.json"),
            metadata={
                "run_id": review["run_id"],
                "style_id": review["style_id"],
                "first_paragraph_span_id": _first_paragraph_span_id(segments),
            },
            model=model,
        ),
    )
    review["status"] = "completed"
    review["summary"] = output.get("summary", "")
    review["findings"] = output.get("findings", [])
    _write_json(review_path, review)


def execute_deliberation_artifact(*, repo_root: Path, delib_path: Path, provider: BaseProvider, model: str | None = None) -> None:
    delib = _load_json(delib_path)
    prompt_path = repo_root / str(delib["prompt_path"])
    output = _generate_with_log(
        repo_root=repo_root,
        run_dir=delib_path.parents[1],
        artifact_path=delib_path,
        provider=provider,
        provider_request=ProviderRequest(
            task="deliberation",
            prompt=prompt_path.read_text(encoding="utf-8"),
            schema=load_schema(repo_root, "schemas/deliberation-output.schema.json"),
            metadata={
                "run_id": delib["run_id"],
                "style_id": delib["style_id"],
            },
            model=model,
        ),
    )
    delib["status"] = "completed"
    delib["replies"] = output.get("replies", [])
    _write_json(delib_path, delib)


def execute_council_artifact(*, repo_root: Path, council_path: Path, provider: BaseProvider, model: str | None = None) -> None:
    council = _load_json(council_path)
    prompt_path = repo_root / str(council["prompt_path"])
    finding_ids = []
    for relative in council.get("review_files", []):
        review = _load_json(repo_root / str(relative))
        for finding in review.get("findings", []):
            if isinstance(finding, dict) and finding.get("id"):
                finding_ids.append(str(finding["id"]))
    output = _generate_with_log(
        repo_root=repo_root,
        run_dir=council_path.parent,
        artifact_path=council_path,
        provider=provider,
        provider_request=ProviderRequest(
            task="council",
            prompt=prompt_path.read_text(encoding="utf-8"),
            schema=load_schema(repo_root, "schemas/council-output.schema.json"),
            metadata={
                "run_id": council["run_id"],
                "finding_ids": finding_ids,
            },
            model=model,
        ),
    )
    council["status"] = "completed"
    council["replies"] = output.get("replies", [])
    council["decisions"] = output.get("decisions", [])
    council["stylistic_commitments"] = output.get("stylistic_commitments", [])
    _write_json(council_path, council)


def execute_revision_artifact(*, repo_root: Path, revision_path: Path, provider: BaseProvider, model: str | None = None) -> None:
    revision = _load_json(revision_path)
    prompt_path = repo_root / str(revision["prompt_path"])
    source_path = repo_root / str(revision["source_document"])
    normalized_text = source_path.read_text(encoding="utf-8")
    output = _generate_with_log(
        repo_root=repo_root,
        run_dir=revision_path.parent,
        artifact_path=revision_path,
        provider=provider,
        provider_request=ProviderRequest(
            task="revision",
            prompt=prompt_path.read_text(encoding="utf-8"),
            schema=load_schema(repo_root, "schemas/revision-output.schema.json"),
            metadata={
                "run_id": revision["run_id"],
                "normalized_text": normalized_text,
            },
            model=model,
        ),
    )
    revised_path = revision_path.parent / "revised.md"
    revised_path.write_text(str(output.get("revised_document", normalized_text)), encoding="utf-8")
    revision["status"] = "completed"
    revision["revised_document_path"] = _repo_relative(repo_root, revised_path)
    revision["applied_changes"] = output.get("applied_changes", [])
    revision["unresolved"] = output.get("unresolved", [])
    _write_json(revision_path, revision)


def execute_scrutiny_artifact(*, repo_root: Path, scrutiny_path: Path, provider: BaseProvider, model: str | None = None) -> None:
    scrutiny = _load_json(scrutiny_path)
    prompt_path = repo_root / str(scrutiny["prompt_path"])
    output = _generate_with_log(
        repo_root=repo_root,
        run_dir=scrutiny_path.parent.parent,
        artifact_path=scrutiny_path,
        provider=provider,
        provider_request=ProviderRequest(
            task="scrutiny",
            prompt=prompt_path.read_text(encoding="utf-8"),
            schema=load_schema(repo_root, "schemas/scrutiny-output.schema.json"),
            metadata={
                "run_id": scrutiny["run_id"],
            },
            model=model,
        ),
    )
    scrutiny["status"] = "completed"
    scrutiny["findings"] = output.get("findings", [])
    _write_json(scrutiny_path, scrutiny)


def execute_verification_artifact(*, repo_root: Path, verification_path: Path, provider: BaseProvider, model: str | None = None) -> None:
    verification = _load_json(verification_path)
    prompt_path = repo_root / str(verification["prompt_path"])
    output = _generate_with_log(
        repo_root=repo_root,
        run_dir=verification_path.parent,
        artifact_path=verification_path,
        provider=provider,
        provider_request=ProviderRequest(
            task="verification",
            prompt=prompt_path.read_text(encoding="utf-8"),
            schema=load_schema(repo_root, "schemas/verification-output.schema.json"),
            metadata={
                "run_id": verification["run_id"],
            },
            model=model,
        ),
    )
    verification["status"] = output.get("status", "needs_human_review")
    verification["passed"] = output.get("passed", [])
    verification["warnings"] = output.get("warnings", [])
    _write_json(verification_path, verification)


def execute_impact_artifact(*, repo_root: Path, impact_path: Path, provider: BaseProvider, model: str | None = None) -> None:
    impact = _load_json(impact_path)
    if impact.get("status") != "prompt_ready":
        return
    prompt_path = repo_root / str(impact["prompt_path"])
    output = _generate_with_log(
        repo_root=repo_root,
        run_dir=impact_path.parent,
        artifact_path=impact_path,
        provider=provider,
        provider_request=ProviderRequest(
            task="assessment",
            prompt=prompt_path.read_text(encoding="utf-8"),
            schema=load_schema(repo_root, "schemas/impact-output.schema.json"),
            metadata={
                "run_id": impact["run_id"],
            },
            model=model,
        ),
    )
    impact["status"] = output.get("status", "completed")
    impact["assessments"] = output.get("assessments", [])
    _write_json(impact_path, impact)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _generate_with_log(
    *,
    repo_root: Path,
    run_dir: Path,
    artifact_path: Path,
    provider: BaseProvider,
    provider_request: ProviderRequest,
) -> dict[str, Any]:
    start = perf_counter()
    model = provider.effective_model(provider_request)
    try:
        output = provider.generate_json(provider_request)
    except Exception as exc:
        telemetry = provider.retry_telemetry()
        append_provider_log(
            run_dir=run_dir,
            task=provider_request.task,
            provider=provider.name,
            model=model,
            artifact_path=_repo_relative(repo_root, artifact_path),
            status="error",
            duration_ms=_elapsed_ms(start),
            retry_count=_int(telemetry.get("retry_count")),
            retry_delay_seconds=_float(telemetry.get("retry_delay_seconds")),
            retry_statuses=_strings(telemetry.get("retry_statuses")),
            error=str(exc),
        )
        raise

    telemetry = provider.retry_telemetry()
    append_provider_log(
        run_dir=run_dir,
        task=provider_request.task,
        provider=provider.name,
        model=model,
        artifact_path=_repo_relative(repo_root, artifact_path),
        status="completed",
        duration_ms=_elapsed_ms(start),
        retry_count=_int(telemetry.get("retry_count")),
        retry_delay_seconds=_float(telemetry.get("retry_delay_seconds")),
        retry_statuses=_strings(telemetry.get("retry_statuses")),
    )
    return output


def _elapsed_ms(start: float) -> int:
    return max(0, round((perf_counter() - start) * 1000))


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


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _float(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _strings(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []
