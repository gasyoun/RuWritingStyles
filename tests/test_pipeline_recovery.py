import json
import shutil
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from ruwritingstyles.config import load_manifest, load_model_policy
from ruwritingstyles.db import Database
from ruwritingstyles.pipeline import (
    ExecutionMode,
    PipelineOptions,
    build_step_plan,
    core_pipeline,
)
from ruwritingstyles.runs import create_prepare_run, load_run_manifest
from ruwritingstyles.segment import normalize_document, segment_markdown


REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = "# Recovery\n\nКороткий тестовый текст.\n"


def _prepare(mode: ExecutionMode = ExecutionMode.EXECUTE):
    run_id = f"unittest-recovery-{uuid4().hex}"
    manifest = load_manifest(REPO_ROOT)
    policy = load_model_policy(REPO_ROOT)
    normalized = normalize_document(DOC)
    options = PipelineOptions(
        mode=mode,
        style_ids=tuple(manifest.mvp_style_ids),
    )
    run_dir = create_prepare_run(
        repo_root=REPO_ROOT,
        input_path=Path("recovery.md"),
        original_text=DOC,
        normalized_text=normalized,
        segments=segment_markdown(normalized),
        manifest=manifest,
        model_policy=policy,
        run_id=run_id,
        provider="mock",
        config={"provider": "mock", "profile": "researcher", "execute": True},
        pipeline_options=options.to_json(),
        step_plan=build_step_plan(options),
    )
    return run_dir, manifest, policy, options


def _cleanup(run_dir: Path) -> None:
    shutil.rmtree(run_dir, ignore_errors=True)
    Database(REPO_ROOT).delete_run(run_dir.name)


def test_prepare_and_prompt_modes_never_construct_a_provider() -> None:
    run_dir, manifest, policy, options = _prepare(ExecutionMode.PREPARE)
    try:
        assert options.mode is ExecutionMode.PREPARE
        prompt_options = PipelineOptions(
            mode=ExecutionMode.PROMPT,
            style_ids=tuple(manifest.mvp_style_ids),
        )
        with patch(
            "ruwritingstyles.pipeline.provider_from_name",
            side_effect=AssertionError("provider must not be constructed"),
        ):
            core_pipeline(
                REPO_ROOT,
                run_dir,
                provider_name="openai",
                manifest=manifest,
                model_policy=policy,
                options=prompt_options,
            )
        assert (run_dir / "council.json").exists()
        assert not (run_dir / "bias-audit.json").exists()
        durable = load_run_manifest(run_dir)
        assert durable["pipeline_options"]["mode"] == "prompt"
        assert all(not item["provider_backed"] for item in durable["step_plan"])
    finally:
        _cleanup(run_dir)


def test_invalid_iteration_count_fails_before_run_creation() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        PipelineOptions(max_iterations=0)


def test_completed_step_with_corrupt_artifact_is_rerun() -> None:
    run_dir, manifest, policy, options = _prepare()
    try:
        core_pipeline(
            REPO_ROOT,
            run_dir,
            provider_name="mock",
            manifest=manifest,
            model_policy=policy,
            options=options,
        )
        (run_dir / "council.json").write_text("{broken", encoding="utf-8")
        from ruwritingstyles import pipeline

        original = pipeline.create_council_bundle
        with patch("ruwritingstyles.pipeline.create_council_bundle", wraps=original) as rebuilt:
            core_pipeline(
                REPO_ROOT,
                run_dir,
                provider_name="mock",
                manifest=manifest,
                model_policy=policy,
                options=options,
            )
        assert rebuilt.call_count == 1
        assert json.loads((run_dir / "council.json").read_text(encoding="utf-8"))
    finally:
        _cleanup(run_dir)


def test_missing_database_row_is_rebuilt_from_run_json() -> None:
    run_dir, _manifest, _policy, _options = _prepare()
    try:
        database = Database(REPO_ROOT)
        durable = load_run_manifest(run_dir)
        database.delete_run(run_dir.name)
        assert database.get_run(run_dir.name) is None
        database.restore_run(durable)
        restored = database.get_run(run_dir.name)
        assert restored is not None
        assert restored["provider"] == "mock"
        assert restored["status"] == "prepared"
    finally:
        _cleanup(run_dir)


def test_malformed_existing_run_state_fails_clearly() -> None:
    run_dir, _manifest, _policy, _options = _prepare()
    try:
        (run_dir / "run.json").write_text("not json", encoding="utf-8")
        with pytest.raises(ValueError, match="malformed durable run state"):
            load_run_manifest(run_dir)
    finally:
        _cleanup(run_dir)


def test_index_failure_leaves_a_recoverable_published_run() -> None:
    run_id = f"unittest-index-failure-{uuid4().hex}"
    manifest = load_manifest(REPO_ROOT)
    policy = load_model_policy(REPO_ROOT)
    normalized = normalize_document(DOC)
    run_dir = REPO_ROOT / "runs" / run_id
    try:
        with patch.object(Database, "register_run", side_effect=RuntimeError("db offline")):
            with pytest.raises(RuntimeError, match="db offline"):
                create_prepare_run(
                    repo_root=REPO_ROOT,
                    input_path=Path("failure.md"),
                    original_text=DOC,
                    normalized_text=normalized,
                    segments=segment_markdown(normalized),
                    manifest=manifest,
                    model_policy=policy,
                    run_id=run_id,
                    provider="mock",
                )
        assert load_run_manifest(run_dir)["status"] == "prepared"
    finally:
        _cleanup(run_dir)
