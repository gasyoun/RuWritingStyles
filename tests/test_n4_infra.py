"""Tests for the H588 N4 infra residue: wall-clock deadline + eval task routes."""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
import unittest
from pathlib import Path
from unittest import mock
from urllib import request

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from ruwritingstyles import providers  # noqa: E402
from ruwritingstyles.config import load_model_policy  # noqa: E402
from ruwritingstyles.evals import _STAGE_ROUTE_TASKS, run_eval_case  # noqa: E402


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class WallClockDeadlineTests(unittest.TestCase):
    def test_trickling_request_hits_wall_clock(self) -> None:
        """A hanging read must be abandoned at the wall-clock deadline and retried,
        then surface as ProviderError — not hang forever."""

        def hanging_urlopen(req, timeout=None):
            time.sleep(30)  # simulates a trickling connection; daemon thread abandons it
            raise AssertionError("should have been abandoned")

        telemetry = providers.ProviderRetryTelemetry()
        env = {
            "RWS_PROVIDER_WALLCLOCK_SECONDS": "1",
            "RWS_PROVIDER_MAX_ATTEMPTS": "2",
            "RWS_PROVIDER_RETRY_SECONDS": "0",
        }
        started = time.monotonic()
        with mock.patch.object(request, "urlopen", hanging_urlopen), \
                mock.patch.dict(os.environ, env):
            with self.assertRaises(providers.ProviderError) as ctx:
                providers._post_json_with_retries(
                    provider_name="test",
                    url="https://example.invalid/v1",
                    body={},
                    headers={},
                    telemetry=telemetry,
                )
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 10, "wall-clock guard did not fire")
        self.assertIn("wall-clock", str(ctx.exception))
        # First attempt recorded as a retryable wall-clock event, second raised.
        self.assertEqual(telemetry.retry_statuses, ["wall_clock_deadline"])

    def test_fast_response_passes_through(self) -> None:
        with mock.patch.object(request, "urlopen", lambda req, timeout=None: _FakeResponse({"ok": 1})), \
                mock.patch.dict(os.environ, {"RWS_PROVIDER_WALLCLOCK_SECONDS": "5"}):
            data = providers._post_json_with_retries(
                provider_name="test", url="https://example.invalid/v1", body={}, headers={},
            )
        self.assertEqual(data, {"ok": 1})

    def test_zero_disables_guard(self) -> None:
        with mock.patch.object(request, "urlopen", lambda req, timeout=None: _FakeResponse({"ok": 2})), \
                mock.patch.dict(os.environ, {"RWS_PROVIDER_WALLCLOCK_SECONDS": "0"}):
            data = providers._post_json_with_retries(
                provider_name="test", url="https://example.invalid/v1", body={}, headers={},
            )
        self.assertEqual(data, {"ok": 2})

    def test_worker_errors_reraise_in_caller(self) -> None:
        def failing_urlopen(req, timeout=None):
            raise providers.error.URLError("boom")

        env = {
            "RWS_PROVIDER_WALLCLOCK_SECONDS": "5",
            "RWS_PROVIDER_MAX_ATTEMPTS": "1",
            "RWS_PROVIDER_RETRY_SECONDS": "0",
        }
        with mock.patch.object(request, "urlopen", failing_urlopen), \
                mock.patch.dict(os.environ, env):
            with self.assertRaises(providers.ProviderError) as ctx:
                providers._post_json_with_retries(
                    provider_name="test", url="https://example.invalid/v1", body={}, headers={},
                )
        self.assertIn("request failed", str(ctx.exception))


class EvalRoutesTests(unittest.TestCase):
    def test_deepseek_routes_resolve_heavier_judgement_models(self) -> None:
        policy = load_model_policy(REPO_ROOT)
        self.assertEqual(policy.resolve_model("council", "deepseek"), "deepseek-v4-pro")
        self.assertEqual(policy.resolve_model("verification", "deepseek"), "deepseek-v4-pro")
        self.assertEqual(policy.resolve_model("style_review", "deepseek"), "deepseek-chat")
        self.assertEqual(policy.resolve_model("synthesis", "deepseek"), "deepseek-chat")

    def test_stage_route_map_covers_judgement_stages(self) -> None:
        self.assertEqual(
            set(_STAGE_ROUTE_TASKS),
            {"review", "deliberation", "council", "revision", "verification"},
        )

    def test_mock_run_with_routes_records_stage_models(self) -> None:
        run_id = "unittest-n4-routes"
        run_dir = REPO_ROOT / "runs" / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir)
        self.addCleanup(lambda: shutil.rmtree(run_dir, ignore_errors=True))

        result = run_eval_case(
            repo_root=REPO_ROOT,
            case_id="translit-mixed-scheme",
            provider_name="mock",
            run_id=run_id,
            use_routes=True,
        )
        data = json.loads(result.result_path.read_text(encoding="utf-8"))
        self.assertIn("stage_models", data)
        self.assertEqual(
            set(data["stage_models"]),
            {"review", "deliberation", "council", "revision", "verification"},
        )
        # mock has no task_routes -> falls back to the policy default model,
        # proving the resolution path executed rather than passing None through.
        policy = load_model_policy(REPO_ROOT)
        self.assertEqual(data["stage_models"]["council"], policy.resolve_model("council", "mock"))

    def test_explicit_model_wins_over_routes(self) -> None:
        run_id = "unittest-n4-model-wins"
        run_dir = REPO_ROOT / "runs" / run_id
        if run_dir.exists():
            shutil.rmtree(run_dir)
        self.addCleanup(lambda: shutil.rmtree(run_dir, ignore_errors=True))

        result = run_eval_case(
            repo_root=REPO_ROOT,
            case_id="translit-mixed-scheme",
            provider_name="mock",
            run_id=run_id,
            model="mock-pinned",
            use_routes=True,
        )
        data = json.loads(result.result_path.read_text(encoding="utf-8"))
        self.assertNotIn("stage_models", data)


if __name__ == "__main__":
    unittest.main()
