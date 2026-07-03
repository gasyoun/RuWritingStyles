"""Validation for run artifacts and style findings."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .schema_validation import validate_json_schema


@dataclass(frozen=True)
class ValidationResult:
    """Validation result for a run directory."""

    ok: bool
    messages: tuple[str, ...]


def validate_run_dir(run_dir: Path) -> ValidationResult:
    run_dir = run_dir.resolve()
    messages: list[str] = []
    schema_store = _load_schema_store(_repo_root_from_run_dir(run_dir), messages)

    segments = _load_json(run_dir / "segments.json", messages)
    if isinstance(segments, dict):
        _validate_with_schema(segments, "segments.schema.json", "segments.json", schema_store, messages)
        _validate_segments(segments, messages)
    span_ids = _span_ids(segments)

    run_json_path = run_dir / "run.json"
    if run_json_path.exists():
        run_data = _load_json(run_json_path, messages)
        if isinstance(run_data, dict):
            _validate_with_schema(run_data, "run.schema.json", "run.json", schema_store, messages)

    for required in ["original.md", "normalized.md", "report.md", "summary.html"]:
        if not (run_dir / required).exists():
            messages.append(f"missing {required}")

    review_paths = sorted((run_dir / "reviews").glob("*.review.json"))
    if not review_paths:
        messages.append("missing review JSON files")
    for path in review_paths:
        review = _load_json(path, messages)
        if isinstance(review, dict):
            _validate_with_schema(review, "review.schema.json", path.name, schema_store, messages)
            _validate_review(review, span_ids, messages, path)

    for artifact, schema_name in [
        ("council.json", "council.schema.json"),
        ("revision.json", "revision.schema.json"),
        ("verification.json", "verification.schema.json"),
    ]:
        data = _load_json(run_dir / artifact, messages)
        if isinstance(data, dict):
            _validate_with_schema(data, schema_name, artifact, schema_store, messages)
            _validate_common_status(data, messages, artifact)
            if artifact == "council.json":
                _validate_council(data, review_paths, messages)
            elif artifact == "revision.json":
                _validate_revision_spans(data, span_ids, messages)
    translit_path = run_dir / "translit-lint.json"
    if translit_path.exists():
        translit = _load_json(translit_path, messages)
        if isinstance(translit, dict):
            _validate_with_schema(
                translit, "translit-lint.schema.json", "translit-lint.json", schema_store, messages
            )
            # Span ids are only comparable to segments.json when the lint ran
            # on normalized.md; revised.md is re-segmented and may renumber.
            if translit.get("source_file") == "normalized.md":
                for index, finding in enumerate(translit.get("findings", []) or []):
                    if isinstance(finding, dict) and span_ids and finding.get("span_id") not in span_ids:
                        messages.append(
                            f"translit-lint.json findings[{index}] references unknown span_id "
                            f"{finding.get('span_id')!r}"
                        )

    _validate_eval_result(run_dir / "eval-result.json", schema_store, messages)
    _validate_provider_log(run_dir / "provider.log.jsonl", messages)

    return ValidationResult(ok=not messages, messages=tuple(messages))


def validate_eval_suite_dir(suite_dir: Path) -> ValidationResult:
    suite_dir = suite_dir.resolve()
    messages: list[str] = []
    repo_root = _repo_root_from_run_dir(suite_dir)
    schema_store = _load_schema_store(repo_root, messages)

    result_path = suite_dir / "eval-suite-result.json"
    data = _load_json(result_path, messages)
    if isinstance(data, dict):
        _validate_with_schema(data, "eval-suite-result.schema.json", "eval-suite-result.json", schema_store, messages)
        _validate_eval_suite_result(repo_root, data, messages)

    if not (suite_dir / "eval-suite-report.md").exists():
        messages.append("missing eval-suite-report.md")

    return ValidationResult(ok=not messages, messages=tuple(messages))


def validate_eval_comparison_file(comparison_path: Path) -> ValidationResult:
    comparison_path = comparison_path.resolve()
    messages: list[str] = []
    repo_root = _repo_root_from_artifact(comparison_path)
    schema_store = _load_schema_store(repo_root, messages)
    data = _load_json(comparison_path, messages)
    if isinstance(data, dict):
        _validate_with_schema(
            data,
            "eval-suite-comparison.schema.json",
            comparison_path.name,
            schema_store,
            messages,
        )
        _validate_eval_comparison_result(data, messages)
    return ValidationResult(ok=not messages, messages=tuple(messages))


def validate_eval_aggregate_file(aggregate_path: Path) -> ValidationResult:
    """Validate an eval-aggregate.json artifact (schema + recomputed statistics)."""
    aggregate_path = aggregate_path.resolve()
    if aggregate_path.is_dir():
        aggregate_path = aggregate_path / "eval-aggregate.json"
    messages: list[str] = []
    repo_root = _repo_root_from_artifact(aggregate_path)
    schema_store = _load_schema_store(repo_root, messages)
    data = _load_json(aggregate_path, messages)
    if isinstance(data, dict):
        _validate_with_schema(
            data, "eval-aggregate.schema.json", aggregate_path.name, schema_store, messages
        )
        _validate_eval_aggregate_result(repo_root, data, messages)
    elif data is not None:
        messages.append(f"{aggregate_path.name} must contain a JSON object")
    return ValidationResult(ok=not messages, messages=tuple(messages))


def _validate_eval_aggregate_result(repo_root: Path, data: dict[str, Any], messages: list[str]) -> None:
    cases = data.get("cases")
    if not isinstance(cases, list):
        messages.append("eval-aggregate.json cases must be a list")
        return
    if data.get("case_count") != len(cases):
        messages.append("eval-aggregate.json case_count does not match cases length")

    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            messages.append(f"eval-aggregate.json cases[{index}] must be an object")
            continue
        label = str(case.get("case_id") or f"cases[{index}]")
        runs = case.get("runs") if isinstance(case.get("runs"), list) else []
        if case.get("repeat") != len(runs):
            messages.append(f"eval-aggregate.json {label} repeat does not match runs length")
        pass_count = sum(1 for row in runs if isinstance(row, dict) and row.get("passed") is True)
        detection_count = sum(1 for row in runs if isinstance(row, dict) and row.get("detected") is True)
        if case.get("pass_count") != pass_count:
            messages.append(f"eval-aggregate.json {label} pass_count does not match runs")
        if case.get("detection_count") != detection_count:
            messages.append(f"eval-aggregate.json {label} detection_count does not match runs")
        expected_rate = round(pass_count / max(1, len(runs)), 6)
        if isinstance(case.get("pass_rate"), (int, float)) and abs(float(case["pass_rate"]) - expected_rate) > 0.000001:
            messages.append(f"eval-aggregate.json {label} pass_rate does not match pass_count/repeat")
        distribution = case.get("verification_status_distribution")
        if isinstance(distribution, dict):
            recomputed: dict[str, int] = {}
            for row in runs:
                if isinstance(row, dict):
                    status = str(row.get("verification_status") or "missing")
                    recomputed[status] = recomputed.get(status, 0) + 1
            if distribution != recomputed:
                messages.append(f"eval-aggregate.json {label} verification_status_distribution does not match runs")
        for row in runs:
            if isinstance(row, dict):
                result_path = _repo_path(repo_root, row.get("result_path"))
                if result_path is not None and not result_path.exists():
                    messages.append(f"eval-aggregate.json {label} references missing result_path {result_path}")


def validate_provider_status_file(status_path: Path) -> ValidationResult:
    status_path = status_path.resolve()
    messages: list[str] = []
    repo_root = _repo_root_from_artifact(status_path)
    schema_store = _load_schema_store(repo_root, messages)
    data = _load_json(status_path, messages)
    if isinstance(data, list):
        schema = schema_store.get("provider-status.schema.json")
        if schema is None:
            messages.append("missing schema provider-status.schema.json")
        else:
            for message in validate_json_schema(data, schema, schema_store=schema_store):
                messages.append(f"{status_path.name} schema {message}")
        _validate_provider_status_result(data, messages)
    elif data is not None:
        messages.append(f"{status_path.name} must contain a JSON array")
    return ValidationResult(ok=not messages, messages=tuple(messages))


def _load_json(path: Path, messages: list[str]) -> Any:
    if not path.exists():
        messages.append(f"missing {path.name}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        messages.append(f"invalid JSON in {path}: {exc}")
        return None


def _validate_segments(data: dict[str, Any], messages: list[str]) -> None:
    segments = data.get("segments")
    if not isinstance(segments, list):
        messages.append("segments.json must contain a list in `segments`")
        return
    if data.get("segment_count") != len(segments):
        messages.append("segments.json segment_count does not match segments length")
    for segment in segments:
        if not isinstance(segment, dict):
            messages.append("segments.json contains a non-object segment")
            continue
        for key in ["span_id", "type", "text", "start_line", "end_line"]:
            if key not in segment:
                messages.append(f"segment missing {key}")


def _span_ids(data: Any) -> set[str]:
    if not isinstance(data, dict) or not isinstance(data.get("segments"), list):
        return set()
    return {
        str(segment.get("span_id"))
        for segment in data["segments"]
        if isinstance(segment, dict) and segment.get("span_id")
    }


def _validate_review(data: dict[str, Any], span_ids: set[str], messages: list[str], path: Path) -> None:
    for key in ["run_id", "style_id", "status", "prompt_path", "segment_count", "findings"]:
        if key not in data:
            messages.append(f"{path.name} missing {key}")
    if data.get("status") not in {"prompt_ready", "completed"}:
        messages.append(f"{path.name} has invalid status {data.get('status')!r}")
    findings = data.get("findings")
    if not isinstance(findings, list):
        messages.append(f"{path.name} findings must be a list")
        return
    for finding in findings:
        _validate_finding(finding, span_ids, messages, path)


def _validate_finding(finding: Any, span_ids: set[str], messages: list[str], path: Path) -> None:
    if not isinstance(finding, dict):
        messages.append(f"{path.name} contains a non-object finding")
        return
    for key in ["id", "style_id", "span_id", "severity", "type", "finding", "suggestion", "confidence"]:
        if key not in finding:
            messages.append(f"{path.name} finding missing {key}")
    if finding.get("severity") not in {"blocker", "major", "minor", "note"}:
        messages.append(f"{path.name} finding {finding.get('id')} has invalid severity")
    if finding.get("span_id") not in span_ids:
        messages.append(f"{path.name} finding {finding.get('id')} references unknown span_id {finding.get('span_id')!r}")
    confidence = finding.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        messages.append(f"{path.name} finding {finding.get('id')} has invalid confidence")


def _validate_revision_spans(data: dict[str, Any], span_ids: set[str], messages: list[str]) -> None:
    """Revision applied_changes reference the original segmentation (segments.json),
    so their span_ids must be known. (verification.json warnings are NOT checked:
    they mix the LLM verifier's segment-based span_ids with merged translit-lint
    findings whose span_ids come from the re-segmented revised.md.)"""
    changes = data.get("applied_changes")
    if not isinstance(changes, list):
        return
    for index, change in enumerate(changes):
        if isinstance(change, dict):
            span = change.get("span_id")
            if span is not None and span_ids and span not in span_ids:
                messages.append(
                    f"revision.json applied_changes[{index}] references unknown span_id {span!r}"
                )


def _validate_common_status(data: dict[str, Any], messages: list[str], artifact: str) -> None:
    if "status" not in data:
        messages.append(f"{artifact} missing status")
    if "run_id" not in data:
        messages.append(f"{artifact} missing run_id")


def _validate_council(data: dict[str, Any], review_paths: list[Path], messages: list[str]) -> None:
    finding_ids = _review_finding_ids(review_paths, messages)
    for label, rows in [
        ("replies", data.get("replies")),
        ("decisions", data.get("decisions")),
    ]:
        if not isinstance(rows, list):
            messages.append(f"council.json {label} must be a list")
    replies = data.get("replies") if isinstance(data.get("replies"), list) else []
    decisions = data.get("decisions") if isinstance(data.get("decisions"), list) else []
    for index, reply in enumerate(replies):
        if isinstance(reply, dict):
            reply_to = reply.get("reply_to")
            if finding_ids and reply_to not in finding_ids:
                messages.append(f"council.json replies[{index}] references unknown finding {reply_to!r}")
    for index, decision in enumerate(decisions):
        if isinstance(decision, dict):
            finding_id = decision.get("finding_id")
            if finding_ids and finding_id not in finding_ids:
                messages.append(f"council.json decisions[{index}] references unknown finding {finding_id!r}")


def _review_finding_ids(review_paths: list[Path], messages: list[str]) -> set[str]:
    finding_ids: set[str] = set()
    for path in review_paths:
        data = _load_json(path, messages)
        findings = data.get("findings") if isinstance(data, dict) and isinstance(data.get("findings"), list) else []
        for finding in findings:
            if isinstance(finding, dict) and finding.get("id"):
                finding_ids.add(str(finding["id"]))
    return finding_ids


def _validate_provider_log(path: Path, messages: list[str]) -> None:
    if not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        messages.append(f"could not read provider.log.jsonl: {exc}")
        return
    for index, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            messages.append(f"provider.log.jsonl line {index} invalid JSON: {exc}")
            continue
        if not isinstance(entry, dict):
            messages.append(f"provider.log.jsonl line {index} must be an object")
            continue
        for key in [
            "timestamp",
            "task",
            "provider",
            "model",
            "artifact",
            "status",
            "duration_ms",
            "retry_count",
            "retry_delay_seconds",
            "retry_statuses",
        ]:
            if key not in entry:
                messages.append(f"provider.log.jsonl line {index} missing {key}")
        if entry.get("status") not in {"completed", "error"}:
            messages.append(f"provider.log.jsonl line {index} has invalid status {entry.get('status')!r}")
        if not isinstance(entry.get("retry_count"), int):
            messages.append(f"provider.log.jsonl line {index} has invalid retry_count")
        if not isinstance(entry.get("retry_delay_seconds"), (int, float)):
            messages.append(f"provider.log.jsonl line {index} has invalid retry_delay_seconds")
        if not isinstance(entry.get("retry_statuses"), list):
            messages.append(f"provider.log.jsonl line {index} has invalid retry_statuses")


def _validate_eval_result(path: Path, schema_store: dict[str, dict[str, Any]], messages: list[str]) -> None:
    if not path.exists():
        return
    data = _load_json(path, messages)
    if not isinstance(data, dict):
        return
    _validate_with_schema(data, "eval-result.schema.json", "eval-result.json", schema_store, messages)
    for key in ["case_id", "run_id", "provider", "model", "finding_count", "verification_status"]:
        if key not in data:
            messages.append(f"eval-result.json missing {key}")
    diff_metrics = data.get("diff_metrics")
    if not isinstance(diff_metrics, dict):
        messages.append("eval-result.json missing diff_metrics")
    else:
        for key in ["changed_line_ratio", "char_delta_ratio", "word_delta_ratio"]:
            if not isinstance(diff_metrics.get(key), (int, float)):
                messages.append(f"eval-result.json diff_metrics missing numeric {key}")
    scoring = data.get("scoring")
    if not isinstance(scoring, dict):
        messages.append("eval-result.json missing scoring")
    elif "diff_within_limits" not in scoring:
        messages.append("eval-result.json scoring missing diff_within_limits")
    matched_required = scoring.get("matched_required_finding_types") if isinstance(scoring, dict) else None
    required_match_count = scoring.get("required_match_count") if isinstance(scoring, dict) else None
    if isinstance(matched_required, list) and required_match_count != len(matched_required):
        messages.append("eval-result.json scoring required_match_count does not match matched_required_finding_types")


def _validate_eval_suite_result(repo_root: Path, data: dict[str, Any], messages: list[str]) -> None:
    results = data.get("results")
    if not isinstance(results, list):
        messages.append("eval-suite-result.json results must be a list")
        return

    case_count = len(results)
    passed_count = sum(1 for row in results if isinstance(row, dict) and row.get("passed") is True)
    failed_count = case_count - passed_count
    expected_pass_rate = round(passed_count / max(1, case_count), 6)

    if data.get("case_count") != case_count:
        messages.append("eval-suite-result.json case_count does not match results length")
    if data.get("passed_count") != passed_count:
        messages.append("eval-suite-result.json passed_count does not match passed results")
    if data.get("failed_count") != failed_count:
        messages.append("eval-suite-result.json failed_count does not match failed results")
    if isinstance(data.get("pass_rate"), (int, float)) and abs(float(data["pass_rate"]) - expected_pass_rate) > 0.000001:
        messages.append("eval-suite-result.json pass_rate does not match passed_count/case_count")

    for index, row in enumerate(results):
        if not isinstance(row, dict):
            messages.append(f"eval-suite-result.json results[{index}] must be an object")
            continue
        _validate_eval_suite_row(repo_root, index, row, messages)


def _validate_eval_suite_row(repo_root: Path, index: int, row: dict[str, Any], messages: list[str]) -> None:
    label = str(row.get("case_id") or f"results[{index}]")
    run_dir = _repo_path(repo_root, row.get("run_dir"))
    result_path = _repo_path(repo_root, row.get("result_path"))

    if run_dir is None:
        messages.append(f"eval-suite-result.json {label} missing run_dir")
        return
    if result_path is None:
        messages.append(f"eval-suite-result.json {label} missing result_path")
        return
    if not run_dir.exists():
        messages.append(f"eval-suite-result.json {label} references missing run_dir {run_dir}")
        return
    if not result_path.exists():
        messages.append(f"eval-suite-result.json {label} references missing result_path {result_path}")
        return
    if result_path.resolve() != (run_dir / "eval-result.json").resolve():
        messages.append(f"eval-suite-result.json {label} result_path does not match run_dir/eval-result.json")

    child = _load_json(result_path, messages)
    if isinstance(child, dict):
        _compare_eval_suite_row(label, row, child, messages)

    child_result = validate_run_dir(run_dir)
    for message in child_result.messages:
        messages.append(f"eval-suite-result.json {label} run invalid: {message}")


def _compare_eval_suite_row(label: str, row: dict[str, Any], child: dict[str, Any], messages: list[str]) -> None:
    scoring = child.get("scoring") if isinstance(child.get("scoring"), dict) else {}
    diff_metrics = child.get("diff_metrics") if isinstance(child.get("diff_metrics"), dict) else {}
    expected = {
        "case_id": child.get("case_id"),
        "passed": scoring.get("passed"),
        "finding_count": child.get("finding_count"),
        "verification_status": child.get("verification_status"),
        "changed_line_ratio": diff_metrics.get("changed_line_ratio"),
        "char_delta_ratio": diff_metrics.get("char_delta_ratio"),
    }
    for key, value in expected.items():
        if row.get(key) != value:
            messages.append(f"eval-suite-result.json {label} {key} does not match child eval-result.json")


def _validate_eval_comparison_result(data: dict[str, Any], messages: list[str]) -> None:
    results = data.get("results")
    if not isinstance(results, list):
        messages.append("eval-suite-comparison.json results must be a list")
        return

    newly_passed = sorted(row["case_id"] for row in results if isinstance(row, dict) and row.get("status") == "newly_passed")
    regressed = sorted(row["case_id"] for row in results if isinstance(row, dict) and row.get("status") == "regressed")
    if sorted(data.get("newly_passed", [])) != newly_passed:
        messages.append("eval-suite-comparison.json newly_passed does not match result rows")
    if sorted(data.get("regressed", [])) != regressed:
        messages.append("eval-suite-comparison.json regressed does not match result rows")
    if data.get("case_count") != len(results):
        messages.append("eval-suite-comparison.json case_count does not match results length")
    baseline = data.get("baseline_pass_rate")
    candidate = data.get("candidate_pass_rate")
    delta = data.get("pass_rate_delta")
    if isinstance(baseline, (int, float)) and isinstance(candidate, (int, float)) and isinstance(delta, (int, float)):
        expected = round(float(candidate) - float(baseline), 6)
        if abs(float(delta) - expected) > 0.000001:
            messages.append("eval-suite-comparison.json pass_rate_delta does not match candidate-baseline")


def _validate_provider_status_result(data: list[Any], messages: list[str]) -> None:
    seen: set[str] = set()
    for index, row in enumerate(data):
        if not isinstance(row, dict):
            messages.append(f"provider-status.json results[{index}] must be an object")
            continue
        provider = row.get("provider")
        if isinstance(provider, str):
            if provider in seen:
                messages.append(f"provider-status.json duplicate provider {provider}")
            seen.add(provider)
        api_key_env = row.get("api_key_env")
        missing_env = row.get("missing_env")
        configured_env = row.get("configured_env")
        ready = row.get("ready")
        if ready is True and missing_env:
            messages.append(f"provider-status.json {provider} is ready but has missing_env")
        if ready is False and not missing_env:
            messages.append(f"provider-status.json {provider} is not ready but missing_env is empty")
        if configured_env and isinstance(api_key_env, list) and configured_env not in api_key_env:
            messages.append(f"provider-status.json {provider} configured_env is not listed in api_key_env")


def _validate_with_schema(
    data: dict[str, Any],
    schema_name: str,
    artifact: str,
    schema_store: dict[str, dict[str, Any]],
    messages: list[str],
) -> None:
    schema = schema_store.get(schema_name)
    if schema is None:
        messages.append(f"missing schema {schema_name}")
        return
    for message in validate_json_schema(data, schema, schema_store=schema_store):
        messages.append(f"{artifact} schema {message}")


def _repo_root_from_run_dir(run_dir: Path) -> Path:
    if run_dir.parent.name == "runs":
        return run_dir.parent.parent
    return Path(__file__).resolve().parents[2]


def _repo_root_from_artifact(path: Path) -> Path:
    for parent in [path.parent, *path.parents]:
        if parent.name == "runs":
            return parent.parent
    return Path(__file__).resolve().parents[2]


def _load_schema_store(repo_root: Path, messages: list[str]) -> dict[str, dict[str, Any]]:
    schema_dir = repo_root / "schemas"
    if not schema_dir.exists():
        messages.append(f"missing schema directory {schema_dir}")
        return {}
    store: dict[str, dict[str, Any]] = {}
    for path in sorted(schema_dir.glob("*.json")):
        data = _load_json(path, messages)
        if isinstance(data, dict):
            store[path.name] = data
    return store


def _repo_path(repo_root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return repo_root / path
