"""Evaluation manifest helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from .config import load_manifest, load_model_policy
from .council import create_council_bundle
from .diff import calculate_revision_diff_metrics, write_revision_diff
from .assess import create_impact_bundle
from .execution import (
    execute_council_artifact,
    execute_review_artifact,
    execute_deliberation_artifact,
    execute_revision_artifact,
    execute_verification_artifact,
    execute_impact_artifact,
)
from .providers import ProviderRequest, provider_from_name
from .report import write_run_report
from .review import create_review_bundle, create_deliberation_bundle
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
    required_finding_types: tuple[str, ...]
    min_required_matches: int
    allowed_verification_statuses: tuple[str, ...]
    max_changed_line_ratio: float
    max_char_delta_ratio: float
    strict_fidelity: bool
    max_finding_count: int | None


@dataclass(frozen=True)
class EvalRunResult:
    """Summary of one executed eval case."""

    run_dir: Path
    result_path: Path


@dataclass(frozen=True)
class EvalSuiteResult:
    """Summary of a full eval manifest run."""

    suite_dir: Path
    result_path: Path
    report_path: Path


@dataclass(frozen=True)
class EvalSuiteComparison:
    """Comparison between two eval suite result files."""

    baseline_path: Path
    candidate_path: Path
    data: dict[str, Any]


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
    deliberate: bool = False,
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

    if deliberate:
        for style_id in case.default_styles:
            bundle = create_deliberation_bundle(
                repo_root=repo_root,
                run_dir=run_dir,
                style_id=style_id,
                manifest=manifest,
            )
            execute_deliberation_artifact(
                repo_root=repo_root,
                delib_path=bundle.deliberation_json,
                provider=provider,
                model=model,
            )

    # Fact-Checking Loop (up to 3 iterations)
    for iteration in range(1, 4):
        verification_feedback = None
        if iteration > 1:
            prev_verification = run_dir / "verification.json"
            if prev_verification.exists():
                verification_feedback = json.loads(prev_verification.read_text(encoding="utf-8"))

        council = create_council_bundle(
            repo_root=repo_root,
            run_dir=run_dir,
            manifest=manifest,
            verification_feedback=verification_feedback,
        )
        execute_council_artifact(repo_root=repo_root, council_path=council.council_json, provider=provider, model=model)
        revision = create_revision_bundle(repo_root=repo_root, run_dir=run_dir)
        execute_revision_artifact(
            repo_root=repo_root, revision_path=revision.revision_json, provider=provider, model=model
        )
        write_revision_diff(run_dir)
        verification = create_verification_bundle(repo_root=repo_root, run_dir=run_dir)
        execute_verification_artifact(
            repo_root=repo_root,
            verification_path=verification.verification_json,
            provider=provider,
            model=model,
        )

        impact = create_impact_bundle(repo_root=repo_root, run_dir=run_dir)
        execute_impact_artifact(
            repo_root=repo_root,
            impact_path=impact.impact_json,
            provider=provider,
            model=model,
        )

        # Check if we should loop
        v_doc = json.loads(verification.verification_json.read_text(encoding="utf-8"))
        i_doc = json.loads(impact.impact_json.read_text(encoding="utf-8"))

        v_warnings = v_doc.get("warnings", [])
        i_warnings = [
            f"Impact failure in {a['span_id']} ({a['tag']}): {a['comment']}"
            for a in i_doc.get("assessments", []) if not a.get("passed")
        ]
        combined_warnings = v_warnings + i_warnings

        if not combined_warnings or iteration == 3:
            break
        else:
            merged_feedback = {"warnings": combined_warnings}
            (run_dir / "verification.json").write_text(json.dumps(merged_feedback, ensure_ascii=False, indent=2), encoding="utf-8")

    result_path = _write_eval_result(
        repo_root=repo_root,
        run_dir=run_dir,
        case=case,
        provider_name=provider.name,
        model=provider.effective_model(ProviderRequest(task="eval", prompt="", schema={}, metadata={}, model=model)),
    )
    write_run_report(run_dir)
    return EvalRunResult(run_dir=run_dir, result_path=result_path)


def run_eval_suite(
    *,
    repo_root: Path,
    provider_name: str = "mock",
    model: str | None = None,
    suite_id: str | None = None,
    deliberate: bool = False,
) -> EvalSuiteResult:
    actual_suite_id = suite_id or _make_suite_id(provider_name)
    suite_dir = repo_root / "runs" / actual_suite_id
    suite_dir.mkdir(parents=True, exist_ok=False)

    rows: list[dict[str, Any]] = []
    for case in load_eval_cases(repo_root):
        case_run_id = f"{actual_suite_id}-{case.case_id}"
        result = run_eval_case(
            repo_root=repo_root,
            case_id=case.case_id,
            provider_name=provider_name,
            model=model,
            run_id=case_run_id,
            deliberate=deliberate,
        )
        data = _load_json(result.result_path)
        scoring = data.get("scoring") if isinstance(data.get("scoring"), dict) else {}
        diff_metrics = data.get("diff_metrics") if isinstance(data.get("diff_metrics"), dict) else {}
        rows.append(
            {
                "case_id": case.case_id,
                "run_dir": _repo_relative(repo_root, result.run_dir),
                "result_path": _repo_relative(repo_root, result.result_path),
                "passed": bool(scoring.get("passed")),
                "finding_count": data.get("finding_count", 0),
                "verification_status": data.get("verification_status", "missing"),
                "changed_line_ratio": diff_metrics.get("changed_line_ratio"),
                "char_delta_ratio": diff_metrics.get("char_delta_ratio"),
            }
        )

    passed_count = sum(1 for row in rows if row["passed"])
    suite = {
        "suite_id": actual_suite_id,
        "provider": provider_name,
        "model": model or "",
        "case_count": len(rows),
        "passed_count": passed_count,
        "failed_count": len(rows) - passed_count,
        "pass_rate": round(passed_count / max(1, len(rows)), 6),
        "results": rows,
    }
    result_path = suite_dir / "eval-suite-result.json"
    result_path.write_text(json.dumps(suite, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = suite_dir / "eval-suite-report.md"
    report_path.write_text(render_eval_suite_report(suite), encoding="utf-8")
    return EvalSuiteResult(suite_dir=suite_dir, result_path=result_path, report_path=report_path)


def render_eval_suite_report(suite: dict[str, Any]) -> str:
    """Render a Markdown report for eval-suite-result.json."""

    rows = suite.get("results") if isinstance(suite.get("results"), list) else []
    lines = [
        f"# Eval Suite: {suite.get('suite_id') or ''}",
        "",
        f"- Provider: `{suite.get('provider') or ''}`",
        f"- Model: `{suite.get('model') or ''}`",
        f"- Cases: {suite.get('case_count') or 0}",
        f"- Passed: {suite.get('passed_count') or 0}",
        f"- Failed: {suite.get('failed_count') or 0}",
        f"- Pass rate: {suite.get('pass_rate') or 0}",
        "",
        "| Case | Passed | Findings | Verification | Changed line ratio | Char delta ratio | Result |",
        "|---|---:|---:|---|---:|---:|---|",
    ]
    for row in rows:
        if not isinstance(row, dict):
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(str(row.get("case_id") or "")),
                    "yes" if row.get("passed") else "no",
                    _cell(str(row.get("finding_count") or 0)),
                    _cell(str(row.get("verification_status") or "")),
                    _cell(_value(row.get("changed_line_ratio"))),
                    _cell(_value(row.get("char_delta_ratio"))),
                    _cell(str(row.get("result_path") or "")),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def compare_eval_suites(baseline: Path, candidate: Path) -> EvalSuiteComparison:
    """Compare two eval-suite-result.json files or suite directories."""

    baseline_path = _suite_result_path(baseline)
    candidate_path = _suite_result_path(candidate)
    baseline_data = _load_json(baseline_path)
    candidate_data = _load_json(candidate_path)
    baseline_rows = _rows_by_case(baseline_data)
    candidate_rows = _rows_by_case(candidate_data)
    case_ids = sorted(set(baseline_rows).union(candidate_rows))

    rows: list[dict[str, Any]] = []
    for case_id in case_ids:
        baseline_row = baseline_rows.get(case_id)
        candidate_row = candidate_rows.get(case_id)
        rows.append(_comparison_row(case_id, baseline_row, candidate_row))

    newly_passed = [row["case_id"] for row in rows if row["status"] == "newly_passed"]
    regressed = [row["case_id"] for row in rows if row["status"] == "regressed"]
    baseline_pass_rate = _number(baseline_data.get("pass_rate"))
    candidate_pass_rate = _number(candidate_data.get("pass_rate"))
    data = {
        "baseline": _suite_summary(baseline_data, baseline_path),
        "candidate": _suite_summary(candidate_data, candidate_path),
        "case_count": len(case_ids),
        "baseline_pass_rate": baseline_pass_rate,
        "candidate_pass_rate": candidate_pass_rate,
        "pass_rate_delta": round(candidate_pass_rate - baseline_pass_rate, 6),
        "newly_passed": newly_passed,
        "regressed": regressed,
        "results": rows,
    }
    return EvalSuiteComparison(baseline_path=baseline_path, candidate_path=candidate_path, data=data)


def render_eval_suite_comparison(comparison: EvalSuiteComparison) -> str:
    """Render a Markdown comparison between two eval suites."""

    data = comparison.data
    baseline = data["baseline"]
    candidate = data["candidate"]
    lines = [
        "# Eval Suite Comparison",
        "",
        f"- Baseline: `{baseline['suite_id']}` ({baseline['provider']}/{baseline['model']})",
        f"- Candidate: `{candidate['suite_id']}` ({candidate['provider']}/{candidate['model']})",
        f"- Cases: {data['case_count']}",
        f"- Baseline pass rate: {data['baseline_pass_rate']}",
        f"- Candidate pass rate: {data['candidate_pass_rate']}",
        f"- Pass rate delta: {_signed(data['pass_rate_delta'])}",
        f"- Newly passed: {len(data['newly_passed'])}",
        f"- Regressed: {len(data['regressed'])}",
        "",
        "| Case | Status | Baseline | Candidate | Finding delta | Changed line delta | Char delta |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in data["results"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _cell(str(row["case_id"])),
                    _cell(str(row["status"])),
                    _pass_cell(row["baseline_passed"]),
                    _pass_cell(row["candidate_passed"]),
                    _cell(_signed_or_blank(row["finding_delta"])),
                    _cell(_signed_or_blank(row["changed_line_ratio_delta"])),
                    _cell(_signed_or_blank(row["char_delta_ratio_delta"])),
                ]
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


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
        required_finding_types=_required_finding_types(data),
        min_required_matches=_min_required_matches(data),
        allowed_verification_statuses=_allowed_verification_statuses(data),
        max_changed_line_ratio=_scoring_float(data, "max_changed_line_ratio", 0.75),
        max_char_delta_ratio=_scoring_float(data, "max_char_delta_ratio", 0.5),
        strict_fidelity=_scoring_bool(data, "strict_fidelity", False),
        max_finding_count=_scoring_int_or_none(data, "max_finding_count"),
    )


def _required_finding_types(data: dict[str, Any]) -> tuple[str, ...]:
    scoring = data.get("scoring") if isinstance(data.get("scoring"), dict) else {}
    values = scoring.get("required_finding_types") if isinstance(scoring.get("required_finding_types"), list) else []
    if not values:
        values = data.get("expected_risks") if isinstance(data.get("expected_risks"), list) else []
    return tuple(str(item) for item in values if item)


def _min_required_matches(data: dict[str, Any]) -> int:
    scoring = data.get("scoring") if isinstance(data.get("scoring"), dict) else {}
    value = scoring.get("min_required_matches")
    return value if isinstance(value, int) and value >= 0 else 1


def _allowed_verification_statuses(data: dict[str, Any]) -> tuple[str, ...]:
    scoring = data.get("scoring") if isinstance(data.get("scoring"), dict) else {}
    values = scoring.get("allowed_verification_statuses")
    if not isinstance(values, list) or not values:
        values = ["passed", "needs_human_review"]
    return tuple(str(item) for item in values if item)


def _scoring_float(data: dict[str, Any], key: str, default: float) -> float:
    scoring = data.get("scoring") if isinstance(data.get("scoring"), dict) else {}
    value = scoring.get(key)
    return float(value) if isinstance(value, (int, float)) and value >= 0 else default


def _scoring_bool(data: dict[str, Any], key: str, default: bool) -> bool:
    scoring = data.get("scoring") if isinstance(data.get("scoring"), dict) else {}
    value = scoring.get(key)
    return bool(value) if value is not None else default


def _scoring_int_or_none(data: dict[str, Any], key: str) -> int | None:
    scoring = data.get("scoring") if isinstance(data.get("scoring"), dict) else {}
    value = scoring.get(key)
    return int(value) if isinstance(value, int) else None


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
    verification_status = str(verification.get("status") or "missing")
    required_matches = sorted(set(case.required_finding_types).intersection(finding_types))
    diff_metrics = calculate_revision_diff_metrics(run_dir)
    diff_within_limits = (
        diff_metrics["changed_line_ratio"] <= case.max_changed_line_ratio
        and diff_metrics["char_delta_ratio"] <= case.max_char_delta_ratio
    )
    finding_count = _finding_count(run_dir)
    finding_count_within_limits = case.max_finding_count is None or finding_count <= case.max_finding_count
    fidelity_passed = not case.strict_fidelity or not verification.get("warnings")

    passed = (
        len(required_matches) >= case.min_required_matches
        and verification_status in set(case.allowed_verification_statuses)
        and diff_within_limits
        and finding_count_within_limits
        and fidelity_passed
    )
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
        "verification_status": verification_status,
        "diff_metrics": diff_metrics,
        "scoring": {
            "passed": passed,
            "required_finding_types": list(case.required_finding_types),
            "matched_required_finding_types": required_matches,
            "required_match_count": len(required_matches),
            "min_required_matches": case.min_required_matches,
            "allowed_verification_statuses": list(case.allowed_verification_statuses),
            "diff_within_limits": diff_within_limits,
            "max_changed_line_ratio": case.max_changed_line_ratio,
            "max_char_delta_ratio": case.max_char_delta_ratio,
            "strict_fidelity": case.strict_fidelity,
            "fidelity_passed": fidelity_passed,
            "max_finding_count": case.max_finding_count,
            "finding_count": finding_count,
            "finding_count_within_limits": finding_count_within_limits,
        },
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


def _make_suite_id(provider_name: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    provider_slug = re.sub(r"[^a-zA-Z0-9]+", "-", provider_name).strip("-").lower() or "provider"
    return f"{timestamp}-eval-suite-{provider_slug}"


def _suite_result_path(path: Path) -> Path:
    path = path.resolve()
    if path.is_dir():
        path = path / "eval-suite-result.json"
    if not path.exists():
        raise FileNotFoundError(f"missing eval suite result {path}")
    return path


def _rows_by_case(suite: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = suite.get("results") if isinstance(suite.get("results"), list) else []
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict) and row.get("case_id"):
            result[str(row["case_id"])] = row
    return result


def _comparison_row(case_id: str, baseline: dict[str, Any] | None, candidate: dict[str, Any] | None) -> dict[str, Any]:
    baseline_passed = _passed(baseline)
    candidate_passed = _passed(candidate)
    return {
        "case_id": case_id,
        "status": _comparison_status(baseline_passed, candidate_passed),
        "baseline_passed": baseline_passed,
        "candidate_passed": candidate_passed,
        "finding_delta": _delta(candidate, baseline, "finding_count"),
        "changed_line_ratio_delta": _delta(candidate, baseline, "changed_line_ratio"),
        "char_delta_ratio_delta": _delta(candidate, baseline, "char_delta_ratio"),
    }


def _comparison_status(baseline_passed: bool | None, candidate_passed: bool | None) -> str:
    if baseline_passed is None:
        return "missing_baseline"
    if candidate_passed is None:
        return "missing_candidate"
    if not baseline_passed and candidate_passed:
        return "newly_passed"
    if baseline_passed and not candidate_passed:
        return "regressed"
    if baseline_passed and candidate_passed:
        return "unchanged_passed"
    return "unchanged_failed"


def _suite_summary(suite: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "suite_id": str(suite.get("suite_id") or path.parent.name),
        "provider": str(suite.get("provider") or ""),
        "model": str(suite.get("model") or ""),
        "path": str(path),
    }


def _passed(row: dict[str, Any] | None) -> bool | None:
    if row is None:
        return None
    value = row.get("passed")
    return value if isinstance(value, bool) else None


def _delta(candidate: dict[str, Any] | None, baseline: dict[str, Any] | None, key: str) -> float | int | None:
    if candidate is None or baseline is None:
        return None
    candidate_value = candidate.get(key)
    baseline_value = baseline.get(key)
    if not isinstance(candidate_value, (int, float)) or not isinstance(baseline_value, (int, float)):
        return None
    value = candidate_value - baseline_value
    if isinstance(candidate_value, int) and isinstance(baseline_value, int):
        return value
    return round(value, 6)


def _number(value: Any) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _pass_cell(value: bool | None) -> str:
    if value is None:
        return "-"
    return "yes" if value else "no"


def _signed(value: float | int) -> str:
    if value > 0:
        return f"+{value}"
    return str(value)


def _signed_or_blank(value: float | int | None) -> str:
    if value is None:
        return ""
    return _signed(value)


def _cell(value: str) -> str:
    return value.replace("\n", " ").replace("|", "\\|").strip()


def _value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
