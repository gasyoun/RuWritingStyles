"""H5071 — actual provider provenance through fallback, budgets and eval comparison.

Offline, deterministic: the provider-level fallback identity is proven in
tests/test_providers_deepseek.py; here we prove it survives into provider
logs, budget accounting, run manifests (suite/aggregate execution_conditions)
and that eval comparisons flag incompatible conditions instead of silently
pooling them.
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from ruwritingstyles.budget import BudgetController, generate_with_budget
from ruwritingstyles.config import BudgetMode
from ruwritingstyles.evals import (
    compare_eval_suites,
    render_eval_suite_comparison,
    run_eval_repeat,
    run_eval_suite,
)
from ruwritingstyles.provider_log import append_provider_log, load_provider_log
from ruwritingstyles.providers import ProviderCallProvenance, ProviderRequest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _suite_result(tmp: Path, name: str, conditions):
    suite_dir = tmp / name
    suite_dir.mkdir()
    suite = {
        "suite_id": name,
        "provider": "deepseek",
        "model": "deepseek-chat",
        "case_count": 1,
        "passed_count": 1,
        "failed_count": 0,
        "pass_rate": 1.0,
        "results": [
            {
                "case_id": "translit-mixed-scheme",
                "run_dir": f"runs/{name}-case",
                "result_path": f"runs/{name}-case/eval-result.json",
                "passed": True,
                "finding_count": 1,
                "verification_status": "passed",
                "changed_line_ratio": 0.0,
                "char_delta_ratio": 0.0,
            }
        ],
    }
    if conditions is not None:
        suite["execution_conditions"] = conditions
    path = suite_dir / "eval-suite-result.json"
    path.write_text(json.dumps(suite, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


class ProviderLogProvenanceTests(unittest.TestCase):
    def test_provenance_block_persisted_without_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            append_provider_log(
                run_dir=run_dir,
                task="style_review",
                provider="deepseek",
                model="deepseek-chat",
                artifact_path="runs/x/review.json",
                status="completed",
                duration_ms=5,
                provenance=ProviderCallProvenance(
                    requested_provider="deepseek",
                    requested_model="deepseek-chat",
                    actual_provider="openrouter",
                    actual_model="deepseek/deepseek-chat",
                    fallback_reason="deepseek_402_insufficient_balance",
                    outcome="completed_fallback",
                    usage_available=True,
                ).to_json(),
            )
            entries = load_provider_log(run_dir)
        self.assertEqual(len(entries), 1)
        provenance = entries[0]["provenance"]
        self.assertEqual(provenance["actual_provider"], "openrouter")
        self.assertEqual(provenance["requested_provider"], "deepseek")
        blob = json.dumps(entries)
        for secret in ("api_key", "Authorization", "Bearer"):
            self.assertNotIn(secret, blob)

    def test_legacy_entry_without_provenance_still_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            append_provider_log(
                run_dir=Path(tmp),
                task="style_review",
                provider="mock",
                model="mock",
                artifact_path="runs/x/review.json",
                status="completed",
                duration_ms=1,
            )
            entries = load_provider_log(Path(tmp))
        self.assertEqual(len(entries), 1)
        self.assertNotIn("provenance", entries[0])


class _FakeProvider:
    """Minimal provider double exposing provenance/usage for budget tests."""

    name = "deepseek"

    def __init__(self, actual_provider: str, actual_model: str) -> None:
        self._provenance = ProviderCallProvenance(
            requested_provider="deepseek",
            requested_model="deepseek-chat",
            actual_provider=actual_provider,
            actual_model=actual_model,
            fallback_reason="deepseek_402" if actual_provider != "deepseek" else None,
            outcome="completed_fallback" if actual_provider != "deepseek" else "completed_direct",
        ).to_json()
        self._usage = {
            "input_tokens": 5,
            "output_tokens": 2,
            "total_tokens": 7,
            "cost_estimate": 0.0,
        }

    def set_budget_controller(self, controller) -> None:
        self._controller = controller

    def budget_controller(self):
        return self._controller

    def generate_json(self, provider_request: ProviderRequest):
        return {"ok": True}

    def last_call_provenance(self):
        return self._provenance

    def last_usage(self):
        return self._usage


class BudgetServedRouteTests(unittest.TestCase):
    def _controller(self) -> BudgetController:
        return BudgetController(
            BudgetMode("test", (), 4, 100, 60),
            provider="deepseek",
            persist=lambda snapshot: None,
        )

    def test_direct_usage_billed_to_requested_provider(self) -> None:
        controller = self._controller()
        provider = _FakeProvider("deepseek", "deepseek-chat")
        provider.set_budget_controller(controller)
        generate_with_budget(
            provider, ProviderRequest(task="t", prompt="p", schema={}, metadata={})
        )
        snapshot = controller.snapshot()
        self.assertEqual(snapshot["consumption"]["served_routes"], {"deepseek/deepseek-chat": 7})

    def test_fallback_usage_attributed_to_actual_route(self) -> None:
        controller = self._controller()
        provider = _FakeProvider("openrouter", "deepseek/deepseek-chat")
        provider.set_budget_controller(controller)
        generate_with_budget(
            provider, ProviderRequest(task="t", prompt="p", schema={}, metadata={})
        )
        snapshot = controller.snapshot()
        # NOT billed to the requested 'deepseek' — the actually-served route.
        self.assertEqual(
            snapshot["consumption"]["served_routes"],
            {"openrouter/deepseek/deepseek-chat": 7},
        )


class SuiteExecutionConditionsTests(unittest.TestCase):
    @staticmethod
    def _cleanup_runs(prefix: str) -> None:
        for path in (REPO_ROOT / "runs").glob(f"{prefix}*"):
            shutil.rmtree(path, ignore_errors=True)

    def test_mock_suite_records_execution_conditions_and_validates(self) -> None:
        suite_id = "prov-conds-mock"
        self.addCleanup(self._cleanup_runs, suite_id)
        self._cleanup_runs(suite_id)
        result = run_eval_suite(
            repo_root=REPO_ROOT,
            provider_name="mock",
            model=None,
            suite_id=suite_id,
        )
        suite = json.loads(result.result_path.read_text(encoding="utf-8"))
        conditions = suite["execution_conditions"]
        self.assertEqual(conditions["requested_provider"], "mock")
        self.assertEqual(conditions["fallback_events"], 0)
        self.assertTrue(conditions["conditions_comparable"])
        self.assertGreater(conditions["executions"], 0)
        self.assertTrue(conditions["actual_routes"])
        self.assertTrue(all(route.startswith("mock/") for route in conditions["actual_routes"]))

    def test_repeat_aggregate_records_execution_conditions(self) -> None:
        agg_id = "prov-conds-agg"
        self.addCleanup(self._cleanup_runs, agg_id)
        self._cleanup_runs(agg_id)
        result = run_eval_repeat(
            repo_root=REPO_ROOT,
            case_id="translit-mixed-scheme",
            provider_name="mock",
            repeat=2,
            aggregate_id=agg_id,
        )
        data = json.loads(result.result_path.read_text(encoding="utf-8"))
        conditions = data["execution_conditions"]
        self.assertTrue(conditions["conditions_comparable"])
        # Each of the 2 runs logs multiple provider executions (review,
        # council, verification...), so count is a positive multiple of runs.
        self.assertGreaterEqual(conditions["executions"], 2)


class ComparisonConditionsGateTests(unittest.TestCase):
    def _compare(self, baseline_conditions, candidate_conditions):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            baseline = _suite_result(tmp_path, "suite-base", baseline_conditions)
            candidate = _suite_result(tmp_path, "suite-cand", candidate_conditions)
            comparison = compare_eval_suites(baseline, candidate)
            rendered = render_eval_suite_comparison(comparison)
        return comparison.data, rendered

    def test_identical_conditions_are_comparable(self) -> None:
        conditions = {
            "requested_provider": "deepseek",
            "requested_model": "deepseek-chat",
            "actual_routes": ["deepseek/deepseek-chat"],
            "fallback_events": 0,
            "executions": 3,
            "conditions_comparable": True,
        }
        data, rendered = self._compare(conditions, conditions)
        self.assertTrue(data["conditions_comparable"])
        self.assertEqual(data["condition_mismatches"], [])
        self.assertIn("Conditions comparable: yes", rendered)

    def test_fallback_poisoned_candidate_is_flagged_not_pooled(self) -> None:
        baseline = {
            "requested_provider": "deepseek",
            "requested_model": "deepseek-chat",
            "actual_routes": ["deepseek/deepseek-chat"],
            "fallback_events": 0,
            "executions": 3,
            "conditions_comparable": True,
        }
        candidate = {
            "requested_provider": "deepseek",
            "requested_model": "deepseek-chat",
            "actual_routes": ["deepseek/deepseek-chat", "openrouter/deepseek/deepseek-chat"],
            "fallback_events": 1,
            "executions": 3,
            "conditions_comparable": False,
        }
        data, rendered = self._compare(baseline, candidate)
        self.assertFalse(data["conditions_comparable"])
        self.assertTrue(data["condition_mismatches"])
        self.assertIn("NO — do not pool", rendered)
        self.assertIn("openrouter", rendered)

    def test_different_requested_model_is_flagged(self) -> None:
        def conditions(model: str) -> dict:
            return {
                "requested_provider": "deepseek",
                "requested_model": model,
                "actual_routes": [f"deepseek/{model}"],
                "fallback_events": 0,
                "executions": 2,
                "conditions_comparable": True,
            }

        data, _ = self._compare(conditions("deepseek-chat"), conditions("deepseek-reasoner"))
        self.assertFalse(data["conditions_comparable"])
        self.assertTrue(any("model differs" in row for row in data["condition_mismatches"]))

    def test_legacy_suites_report_unknown_not_false(self) -> None:
        data, rendered = self._compare(None, None)
        self.assertIsNone(data["conditions_comparable"])
        self.assertEqual(data["condition_mismatches"], [])
        self.assertIn("unknown", rendered)


if __name__ == "__main__":
    unittest.main()
