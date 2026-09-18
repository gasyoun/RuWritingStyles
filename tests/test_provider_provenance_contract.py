"""H5097 — shared requested-vs-actual provenance contract across ALL provider
adapters and fallback/error routes.

Adapter/outcome inventory (every row is exercised by the tests below; all
transport is injected via ``providers._post_json_with_retries`` — fully
offline, no paid or credentialed calls):

| Adapter            | completed_direct      | failed_direct          | completed_fallback      | failed_fallback          | usage_available source        |
|--------------------|-----------------------|------------------------|-------------------------|--------------------------|-------------------------------|
| MockProvider       | test_all_adapters_*   | n/a (cannot fail)      | n/a                     | n/a                      | always False (no usage)       |
| OpenAIProvider     | test_all_adapters_*   | test_openai_*          | n/a                     | n/a                      | response ``usage``            |
| GoogleProvider     | test_all_adapters_*   | test_google_*          | n/a                     | n/a                      | response ``usageMetadata``    |
| AnthropicProvider  | test_all_adapters_*   | test_anthropic_*       | n/a                     | n/a                      | response ``usage``            |
| OpenRouterProvider | test_all_adapters_*   | test_openrouter_*      | n/a (leaf)              | n/a                      | response ``usage``            |
| LocalProvider      | test_all_adapters_*   | test_local_*           | n/a (leaf)              | n/a                      | response ``usage``            |
| OllamaProvider     | test_all_adapters_*   | test_ollama_*          | n/a (leaf)              | n/a                      | ``prompt_eval_count``/``eval_count`` |
| DeepSeekProvider   | test_all_adapters_*   | test_deepseek_*        | test_deepseek_fallback* | test_deepseek_fallback*  | response ``usage``            |

Downstream refusal coverage: ``test_strict_compare_*`` (CLI refuses
non-comparable/unknown conditions), ``test_leaderboard_*`` (multi-suite
pooling surface flags fallback/unknown suites), ``test_execution_log_*``
(provider.log.jsonl carries the truthful record on success AND failure).
Legacy compatibility: empty/default provenance stays valid and provider-log
entries without the block keep loading (H5071 behaviour preserved).
"""

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ruwritingstyles import cli as cli_module
from ruwritingstyles import providers as providers_module
from ruwritingstyles.evals import (
    compare_eval_suites,
    generate_leaderboard_report,
    render_eval_suite_comparison,
)
from ruwritingstyles.providers import (
    BaseProvider,
    DeepSeekProvider,
    ProviderCallProvenance,
    ProviderError,
    ProviderQuotaExhaustedError,
    ProviderRequest,
    provider_from_name,
)

OK_JSON = '{"ok": 1}'


def _request(model=None) -> ProviderRequest:
    # task="review": every real adapter ignores the task, and the mock
    # provider dispatches on it — this task is supported by all eight.
        return ProviderRequest(
            task="review",
            prompt="Return JSON.",
            schema={"type": "object"},
            metadata={"run_id": "t", "style_id": "test-style"},
            model=model,
        )


def _payload(provider_name: str, *, with_usage: bool, text: str = OK_JSON) -> dict:
    """Minimal truthful provider response per wire format."""
    usage_block: dict = {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}
    if provider_name == "google":
        data: dict = {"candidates": [{"content": {"parts": [{"text": text}]}}]}
        if with_usage:
            data["usageMetadata"] = {"promptTokenCount": 5, "candidatesTokenCount": 2}
        return data
    if provider_name == "anthropic":
        data = {"stop_reason": "end_turn", "content": [{"type": "text", "text": text}]}
        if with_usage:
            data["usage"] = {"input_tokens": 5, "output_tokens": 2}
        return data
    if provider_name == "ollama":
        data = {"message": {"content": text}}
        if with_usage:
            data["prompt_eval_count"] = 3
            data["eval_count"] = 5
        return data
    # openai / openrouter / local / deepseek share the OpenAI chat shape
    data = {"choices": [{"message": {"content": text}}]}
    if with_usage:
        data["usage"] = usage_block
    return data


def _broken_payload(provider_name: str) -> dict:
    """Response that makes the adapter raise (missing content/choices)."""
    if provider_name == "google":
        return {"candidates": []}
    if provider_name == "anthropic":
        return {"stop_reason": "end_turn", "content": []}
    if provider_name == "ollama":
        return {"message": {}}
    return {"choices": []}


_PROVIDER_ENV = {
    "OPENAI_API_KEY": "test-key",
    "GEMINI_API_KEY": "test-key",
    "ANTHROPIC_API_KEY": "test-key",
    "OPENROUTER_API_KEY": "test-key",
    "DEEPSEEK_API_KEY": "test-key",
}


def _provenance(provider) -> dict:
    return provider.last_call_provenance()


def _assert_identity_fields(provenance: dict, provider_name: str, model: str) -> None:
    """The shared contract: truthful requested AND actual identity."""
    assert provenance["requested_provider"] == provider_name, provenance
    assert provenance["requested_model"] == model, provenance
    assert provenance["actual_provider"], provenance  # known, never blank after a call
    assert provenance["outcome"] in ProviderCallProvenance.OUTCOMES, provenance


class SharedContractAllAdaptersTests(unittest.TestCase):
    """Every registered adapter must leave a truthful record after a call."""

    ALL_ADAPTERS = [
        "mock",
        "openai",
        "google",
        "anthropic",
        "openrouter",
        "local",
        "ollama",
        "deepseek",
    ]

    def _make(self, name: str):
        if name == "mock":
            return provider_from_name("mock")
        if name == "local":
            return provider_from_name("local")
        if name == "ollama":
            return provider_from_name("ollama")
        return provider_from_name(name)  # picks keys from patched env

    def test_every_adapter_records_completed_direct_on_success(self) -> None:
        for name in self.ALL_ADAPTERS:
            with self.subTest(adapter=name):
                with patch.dict("os.environ", _PROVIDER_ENV), patch.object(
                    providers_module, "_post_json_with_retries",
                    return_value=_payload(name, with_usage=True),
                ):
                    provider = self._make(name)
                    provider.generate_json(_request())
                    provenance = _provenance(provider)
                _assert_identity_fields(provenance, name, provider.effective_model(_request()))
                self.assertEqual(provenance["outcome"], "completed_direct")
                self.assertIsNone(provenance["fallback_reason"])
                if name == "mock":
                    # The mock never carries usage — False is the truthful value.
                    self.assertFalse(provenance["usage_available"])
                else:
                    self.assertTrue(provenance["usage_available"], provenance)

    def test_usage_absent_is_reported_truthfully(self) -> None:
        for name in self.ALL_ADAPTERS:
            if name == "mock":
                continue  # mock never has usage; covered by inventory test above
            with self.subTest(adapter=name):
                with patch.dict("os.environ", _PROVIDER_ENV), patch.object(
                    providers_module, "_post_json_with_retries",
                    return_value=_payload(name, with_usage=False),
                ):
                    provider = self._make(name)
                    provider.generate_json(_request())
                    provenance = _provenance(provider)
                self.assertEqual(provenance["outcome"], "completed_direct")
                self.assertFalse(provenance["usage_available"], provenance)

    def test_transport_failure_records_failed_direct(self) -> None:
        for name in self.ALL_ADAPTERS:
            if name == "mock":
                continue
            with self.subTest(adapter=name):
                with patch.dict("os.environ", _PROVIDER_ENV), patch.object(
                    providers_module, "_post_json_with_retries",
                    side_effect=ProviderError("connection reset"),
                ):
                    provider = self._make(name)
                    with self.assertRaises(ProviderError):
                        provider.generate_json(_request())
                    provenance = _provenance(provider)
                _assert_identity_fields(provenance, name, provider.effective_model(_request()))
                self.assertEqual(provenance["outcome"], "failed_direct")
                self.assertIsNone(provenance["fallback_reason"])
                self.assertFalse(provenance["usage_available"])

    def test_malformed_payload_records_failed_direct(self) -> None:
        for name in self.ALL_ADAPTERS:
            if name == "mock":
                continue
            with self.subTest(adapter=name):
                with patch.dict("os.environ", _PROVIDER_ENV), patch.object(
                    providers_module, "_post_json_with_retries",
                    return_value=_broken_payload(name),
                ):
                    provider = self._make(name)
                    with self.assertRaises(ProviderError):
                        provider.generate_json(_request())
                    provenance = _provenance(provider)
                self.assertEqual(provenance["outcome"], "failed_direct", provenance)
                self.assertEqual(provenance["requested_provider"], name)

    def test_unparseable_json_records_failed_direct(self) -> None:
        for name in ("openai", "openrouter", "local"):
            with self.subTest(adapter=name):
                with patch.dict("os.environ", _PROVIDER_ENV), patch.object(
                    providers_module, "_post_json_with_retries",
                    return_value=_payload(name, with_usage=True, text="not json"),
                ):
                    provider = self._make(name)
                    with self.assertRaises(ProviderError):
                        provider.generate_json(_request())
                    provenance = _provenance(provider)
                self.assertEqual(provenance["outcome"], "failed_direct", provenance)

    def test_outcome_vocabulary_is_respected_by_contract_helper(self) -> None:
        with self.assertRaises(ProviderError):
            providers_module.BaseProvider()._record_call_provenance(
                _request(), outcome="invented_outcome"
            )


class DeepSeekFallbackContractTests(unittest.TestCase):
    """The H5071 fallback routes must keep their truthful records — and the
    previously-lying direct-failure paths must now record failed_direct."""

    def test_direct_failure_records_failed_direct(self) -> None:
        # 500-class transport failure on the direct attempt (no 402, no fallback)
        with patch.object(
            providers_module, "_post_json_with_retries",
            side_effect=ProviderError("HTTP 500"),
        ):
            provider = DeepSeekProvider(api_key="k")
            with self.assertRaises(ProviderError):
                provider.generate_json(_request())
            provenance = _provenance(provider)
        self.assertEqual(provenance["outcome"], "failed_direct")
        self.assertEqual(provenance["requested_provider"], "deepseek")
        self.assertEqual(provenance["actual_provider"], "deepseek")
        self.assertIsNone(provenance["fallback_reason"])

    def test_unparseable_direct_response_records_failed_direct(self) -> None:
        with patch.object(
            providers_module, "_post_json_with_retries",
            return_value=_payload("deepseek", with_usage=True, text="garbage{"),
        ):
            provider = DeepSeekProvider(api_key="k")
            with self.assertRaises(ProviderError):
                provider.generate_json(_request())
            provenance = _provenance(provider)
        self.assertEqual(provenance["outcome"], "failed_direct", provenance)
        # Failure records never advertise usable usage — the call produced no
        # successful outcome to attach it to.
        self.assertFalse(provenance["usage_available"])

    def test_fallback_success_keeps_completed_fallback(self) -> None:
        exhausted = ProviderQuotaExhaustedError("HTTP 402 Insufficient Balance")
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "or-key"}), patch.object(
            providers_module, "_post_json_with_retries",
            side_effect=[exhausted, _payload("openrouter", with_usage=True)],
        ):
            provider = DeepSeekProvider(api_key="k")
            result = provider.generate_json(_request())
            provenance = _provenance(provider)
        self.assertEqual(result, {"ok": 1})
        self.assertEqual(provenance["outcome"], "completed_fallback")
        self.assertEqual(provenance["requested_provider"], "deepseek")
        self.assertEqual(provenance["actual_provider"], "openrouter")
        self.assertIn("402", provenance["fallback_reason"])
        self.assertTrue(provenance["usage_available"])

    def test_fallback_failure_keeps_failed_fallback(self) -> None:
        exhausted = ProviderQuotaExhaustedError("HTTP 402 Insufficient Balance")
        with patch.dict("os.environ", {"OPENROUTER_API_KEY": "or-key"}), patch.object(
            providers_module, "_post_json_with_retries",
            side_effect=[exhausted, ProviderError("openrouter down")],
        ):
            provider = DeepSeekProvider(api_key="k")
            with self.assertRaises(ProviderError):
                provider.generate_json(_request())
            provenance = _provenance(provider)
        self.assertEqual(provenance["outcome"], "failed_fallback")
        self.assertEqual(provenance["actual_provider"], "openrouter")
        self.assertIn("402", provenance["fallback_reason"])

    def test_fallback_disabled_records_failed_direct(self) -> None:
        exhausted = ProviderQuotaExhaustedError("HTTP 402 Insufficient Balance")
        with patch.dict("os.environ", {"RWS_DEEPSEEK_OPENROUTER_FALLBACK": "0"}), patch.object(
            providers_module, "_post_json_with_retries",
            side_effect=exhausted,
        ):
            provider = DeepSeekProvider(api_key="k")
            with self.assertRaises(ProviderQuotaExhaustedError):
                provider.generate_json(_request())
            provenance = _provenance(provider)
        self.assertEqual(provenance["outcome"], "failed_direct", provenance)
        self.assertIsNone(provenance["fallback_reason"])

    def test_unconfigured_fallback_records_failed_direct_not_completed(self) -> None:
        # 402 with NO fallback key configured: previously the optimistic
        # completed_direct marker survived the failure — the exact "requested
        # presented as actual" defect H5097 closes.
        exhausted = ProviderQuotaExhaustedError("HTTP 402 Insufficient Balance")
        clean_env = {k: v for k, v in _PROVIDER_ENV.items() if k != "OPENROUTER_API_KEY"}
        with patch.dict("os.environ", clean_env, clear=True), patch.object(
            providers_module, "_post_json_with_retries", side_effect=exhausted,
        ):
            provider = DeepSeekProvider(api_key="k")
            with self.assertRaises(ProviderError):
                provider.generate_json(_request())
            provenance = _provenance(provider)
        self.assertEqual(provenance["outcome"], "failed_direct", provenance)
        self.assertIsNone(provenance["fallback_reason"])


class _RaisingProvider(BaseProvider):
    name = "mock"

    def __init__(self) -> None:
        self._prov = ProviderCallProvenance(
            requested_provider="mock", requested_model="mock",
            actual_provider="mock", actual_model="mock", outcome="failed_direct",
        )

    def effective_model(self, provider_request):
        return "mock"

    def retry_telemetry(self):
        return {"retry_count": 0, "retry_delay_seconds": 0.0, "retry_statuses": []}

    def last_usage(self):
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_estimate": 0.0}

    def last_call_provenance(self):
        return self._prov.to_json()

    def budget_controller(self):
        return None

    def generate_json(self, provider_request):
        raise ProviderError("injected failure")


class ExecutionLogContractTests(unittest.TestCase):
    """provider.log.jsonl must carry the truthful record on success AND error."""

    def test_error_log_entry_carries_failed_provenance(self) -> None:
        from ruwritingstyles.execution import _generate_with_log

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            with self.assertRaises(ProviderError):
                _generate_with_log(
                    repo_root=run_dir,
                    run_dir=run_dir,
                    artifact_path=run_dir / "x.json",
                    provider=_RaisingProvider(),
                    provider_request=_request(),
                )
            from ruwritingstyles.provider_log import load_provider_log
            entries = load_provider_log(run_dir)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["status"], "error")
        self.assertEqual(entries[0]["provenance"]["outcome"], "failed_direct")


def _write_suite(tmp: Path, name: str, conditions) -> Path:
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


_CLEAN = {
    "requested_provider": "deepseek",
    "requested_model": "deepseek-chat",
    "actual_routes": ["deepseek/deepseek-chat"],
    "fallback_events": 0,
    "executions": 5,
    "conditions_comparable": True,
}
_FALLBACK = dict(_CLEAN, actual_routes=["deepseek/deepseek-chat", "openrouter/deepseek/deepseek-chat"],
                 fallback_events=2, conditions_comparable=False)


class ComparisonRefusalTests(unittest.TestCase):
    """Incompatible or unknown conditions can never gate a strict comparison."""

    def _run_cmd(self, baseline: Path, candidate: Path, strict: bool) -> int:
        args = argparse.Namespace(
            baseline=baseline, candidate=candidate,
            output=None, json_output=None, strict=strict,
        )
        return cli_module.cmd_eval_compare(args)

    def test_strict_refuses_unknown_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            baseline = _write_suite(tmp_path, "legacy", None)  # predates conditions
            candidate = _write_suite(tmp_path, "fresh", _CLEAN)
            comparison = compare_eval_suites(baseline, candidate)
            self.assertIsNone(comparison.data["conditions_comparable"])
            rendered = render_eval_suite_comparison(comparison)
            self.assertIn("unknown", rendered)
            self.assertEqual(self._run_cmd(baseline, candidate, strict=True), 1)

    def test_strict_refuses_mismatched_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            baseline = _write_suite(tmp_path, "clean", _CLEAN)
            candidate = _write_suite(tmp_path, "poisoned", _FALLBACK)
            comparison = compare_eval_suites(baseline, candidate)
            self.assertFalse(comparison.data["conditions_comparable"])
            rendered = render_eval_suite_comparison(comparison)
            self.assertIn("NO — do not pool", rendered)
            self.assertEqual(self._run_cmd(baseline, candidate, strict=True), 1)

    def test_strict_accepts_comparable_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            baseline = _write_suite(tmp_path, "base", _CLEAN)
            candidate = _write_suite(tmp_path, "cand", _CLEAN)
            comparison = compare_eval_suites(baseline, candidate)
            self.assertTrue(comparison.data["conditions_comparable"])
            self.assertEqual(self._run_cmd(baseline, candidate, strict=True), 0)

    def test_non_strict_still_renders_but_does_not_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            baseline = _write_suite(tmp_path, "legacy", None)
            candidate = _write_suite(tmp_path, "fresh", _CLEAN)
            self.assertEqual(self._run_cmd(baseline, candidate, strict=False), 0)


class LeaderboardPoolingTests(unittest.TestCase):
    def test_leaderboard_flags_fallback_and_unknown_suites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "runs").mkdir()  # generate_leaderboard_report writes here
            clean = _write_suite(tmp_path, "clean", _CLEAN)
            poisoned = _write_suite(tmp_path, "poisoned", _FALLBACK)
            legacy = _write_suite(tmp_path, "legacy", None)
            report_path = generate_leaderboard_report(tmp_path, [clean, poisoned, legacy])
            report = report_path.read_text(encoding="utf-8")
        self.assertIn("do not pool", report)
        self.assertIn("unknown (predates execution_conditions)", report)
        self.assertIn("Pooling verdict: NO", report)

    def test_leaderboard_clean_suites_do_not_trigger_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / "runs").mkdir()
            a = _write_suite(tmp_path, "a", _CLEAN)
            b = _write_suite(tmp_path, "b", _CLEAN)
            report_path = generate_leaderboard_report(tmp_path, [a, b])
            report = report_path.read_text(encoding="utf-8")
        self.assertNotIn("Pooling verdict", report)
        self.assertIn("clean", report)


class LegacyCompatibilityTests(unittest.TestCase):
    def test_default_provenance_still_serializes_and_stays_omitted(self) -> None:
        from ruwritingstyles.provider_log import append_provider_log, load_provider_log

        blob = ProviderCallProvenance().to_json()  # legacy default is still valid
        self.assertEqual(blob["outcome"], "not_started")
        with tempfile.TemporaryDirectory() as tmp:
            append_provider_log(
                run_dir=Path(tmp), task="t", provider="mock", model="mock",
                artifact_path="runs/x/a.json", status="completed", duration_ms=1,
                provenance=blob,
            )
            entries = load_provider_log(Path(tmp))
        self.assertNotIn("provenance", entries[0])  # empty identity omitted, as in H5071


if __name__ == "__main__":
    unittest.main()
