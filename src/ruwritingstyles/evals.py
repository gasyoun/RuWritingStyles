"""Evaluation manifest helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .config import load_manifest, load_model_policy
from .council import create_council_bundle
from .diff import write_revision_diff
from .execution import (
    execute_council_artifact,
    execute_review_artifact,
    execute_revision_artifact,
    execute_verification_artifact,
)
from .providers import ProviderRequest, provider_from_name
from .report import write_run_report
from .review import create_review_bundle
from .revision import create_revision_bundle
from .runs import create_prepare_run
from .segment import normalize_document, read_document, segment_markdown
from .verification import create_verification_bundle


@dataclass(frozen=True)
class EvalCase:
    """One evaluation case from evals/manifest.json."""

    case_id: str
    input_path: Path
    purpose: str
    default_styles: tuple[str, ...]
    expected_risks: tuple[str, ...]


@dataclass(frozen=True)
class EvalRunResult:
    """Summary of one executed eval case."""

    run_dir: Path
    result_path: Path


def load_eval_cases(repo_root: Path) -> tuple[EvalCase, ...]:
    manifest_path = repo_root / "evals" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = data.get("cases") if isinstance(data.get("cases"), list) else []
    return tuple(_case(repo_root, item) for item in cases if isinstance(item, dict))


def run_eval_case(
    *,
    repo_root: Path,
    case_id: str,
    provider_name: str = "mock",
    model: str | None = None,
    run_id: str | None = None,
) -> EvalRunResult:
    case = _find_case(repo_root, case_id)
    manifest = load_manifest(repo_root)
    model_policy = load_model_policy(repo_root)
    provider = provider_from_name(provider_name)

    original_text = read_document(case.input_path)
    normalized_text = normalize_document(original_text)
    segments = segment_markdown(normalized_text)
    run_dir = create_prepare_run(
        repo_root=repo_root,
        input_path=case.input_path,
        original_text=original_text,
        normalized_text=normalized_text,
        segments=segments,
        manifest=manifest,
        model_policy=model_policy,
        run_id=run_id,
    )

    for style_id in case.default_styles:
        bundle = create_review_bundle(
            repo_root=repo_root,
            run_dir=run_dir,
            style_id=style_id,
            manifest=manifest,
        )
        execute_review_artifact(
            repo_root=repo_root,
            review_path=bundle.review_json,
            provider=provider,
            model=model,
        )

    council = create_council_bundle(repo_root=repo_root, run_dir=run_dir)
    execute_council_artifact(repo_root=repo_root, council_path=council.council_json, provider=provider, model=model)
    revision = create_revision_bundle(repo_root=repo_root, run_dir=run_dir)
    execute_revision_artifact(repo_root=repo_root, revision_path=revision.revision_json, provider=provider, model=model)
    write_revision_diff(run_dir)
    verification = create_verification_bundle(repo_root=repo_root, run_dir=run_dir)
    execute_verification_artifact(
        repo_root=repo_root,
        verification_path=verification.verification_json,
        provider=provider,
        model=model,
    )

    result_path = _write_eval_result(
        repo_root=repo_root,
        run_dir=run_dir,
        case=case,
        provider_name=provider.name,
        model=provider.effective_model(ProviderRequest(task="eval", prompt="", schema={}, metadata={}, model=model)),
    )
    write_run_report(run_dir)
    return EvalRunResult(run_dir=run_dir, result_path=result_path)


def _find_case(repo_root: Path, case_id: str) -> EvalCase:
    for case in load_eval_cases(repo_root):
        if case.case_id == case_id:
            return case
    available = ", ".join(case.case_id for case in load_eval_cases(repo_root))
    raise ValueError(f"unknown eval case {case_id!r}; available cases: {available}")


def _case(repo_root: Path, data: dict[str, Any]) -> EvalCase:
    case_id = str(data.get("id") or "")
    if not case_id:
        raise ValueError("eval case missing id")
    input_path = repo_root / str(data.get("input") or "")
    if not input_path.exists():
        raise FileNotFoundError(f"eval case {case_id} references missing input {input_path}")
    return EvalCase(
        case_id=case_id,
        input_path=input_path,
        purpose=str(data.get("purpose") or ""),
        default_styles=tuple(str(item) for item in data.get("default_styles", []) if item),
        expected_risks=tuple(str(item) for item in data.get("expected_risks", []) if item),
    )


def _write_eval_result(
    *,
    repo_root: Path,
    run_dir: Path,
    case: EvalCase,
    provider_name: str,
    model: str,
) -> Path:
    finding_types = _finding_types(run_dir)
    matched = sorted(set(case.expected_risks).intersection(finding_types))
    verification = _load_json(run_dir / "verification.json")
    result = {
        "case_id": case.case_id,
        "run_id": run_dir.name,
        "run_dir": _repo_relative(repo_root, run_dir),
        "input": _repo_relative(repo_root, case.input_path),
        "provider": provider_name,
        "model": model,
        "styles": list(case.default_styles),
        "expected_risks": list(case.expected_risks),
        "finding_count": _finding_count(run_dir),
        "finding_types": sorted(finding_types),
        "matched_expected_risks": matched,
        "verification_status": verification.get("status") or "missing",
    }
    path = run_dir / "eval-result.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _finding_types(run_dir: Path) -> set[str]:
    result: set[str] = set()
    for review_path in sorted((run_dir / "reviews").glob("*.review.json")):
        review = _load_json(review_path)
        findings = review.get("findings") if isinstance(review.get("findings"), list) else []
        for finding in findings:
            if isinstance(finding, dict) and finding.get("type"):
                result.add(str(finding["type"]))
    return result


def _finding_count(run_dir: Path) -> int:
    count = 0
    for review_path in sorted((run_dir / "reviews").glob("*.review.json")):
        review = _load_json(review_path)
        findings = review.get("findings") if isinstance(review.get("findings"), list) else []
        count += len(findings)
    return count


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)
