"""DeepSeek provider (OpenAI-compatible JSON mode) — mock-safe, no network."""

import os
import unittest
from unittest.mock import patch

from ruwritingstyles import providers
from ruwritingstyles.providers import (
    DeepSeekProvider,
    ProviderError,
    ProviderRequest,
    provider_from_name,
)


def _request(model=None) -> ProviderRequest:
    return ProviderRequest(
        task="style_review",
        prompt="Return JSON.",
        schema={"type": "object"},
        metadata={"run_id": "t"},
        model=model,
    )


def _ok(text='{"ok": true}') -> dict:
    return {
        "choices": [{"message": {"content": text}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
    }


class DeepSeekProviderTests(unittest.TestCase):
    def test_builds_request_and_parses_json(self) -> None:
        with patch.object(providers, "_post_json_with_retries", return_value=_ok()) as post:
            result = DeepSeekProvider(api_key="test-key").generate_json(_request())
        self.assertEqual(result, {"ok": True})
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["url"], "https://api.deepseek.com/v1/chat/completions")
        self.assertEqual(kwargs["body"]["model"], "deepseek-chat")
        self.assertEqual(kwargs["body"]["response_format"], {"type": "json_object"})
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")

    def test_request_model_overrides_default(self) -> None:
        with patch.object(providers, "_post_json_with_retries", return_value=_ok()) as post:
            DeepSeekProvider(api_key="k").generate_json(_request(model="deepseek-reasoner"))
        self.assertEqual(post.call_args.kwargs["body"]["model"], "deepseek-reasoner")

    def test_env_overrides_model_and_endpoint(self) -> None:
        with patch.dict(os.environ, {
            "RWS_DEEPSEEK_MODEL": "deepseek-reasoner",
            "RWS_DEEPSEEK_URL": "https://proxy.example/v1/chat/completions",
        }), patch.object(providers, "_post_json_with_retries", return_value=_ok()) as post:
            DeepSeekProvider(api_key="k").generate_json(_request())
        self.assertEqual(post.call_args.kwargs["body"]["model"], "deepseek-reasoner")
        self.assertEqual(post.call_args.kwargs["url"], "https://proxy.example/v1/chat/completions")

    def test_usage_recorded(self) -> None:
        with patch.object(providers, "_post_json_with_retries", return_value=_ok()):
            provider = DeepSeekProvider(api_key="k")
            provider.generate_json(_request())
            usage = provider.last_usage()
        self.assertEqual(usage["total_tokens"], 7)

    def test_missing_key_raises(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ProviderError):
                DeepSeekProvider()

    def test_unparseable_json_raises(self) -> None:
        with patch.object(providers, "_post_json_with_retries", return_value=_ok(text="not json")):
            with self.assertRaises(ProviderError):
                DeepSeekProvider(api_key="k").generate_json(_request())

    def test_truncated_content_retries_once_then_succeeds(self) -> None:
        # A 200 whose content is truncated mid-JSON (flaky-network failure mode
        # that crashed an eval case at the review stage) must be retried once;
        # the complete second response then parses. Regression guard for that.
        truncated = _ok(text='{"style_id": "lidova-commentary",')  # cut off mid-object
        complete = _ok(text='{"ok": true}')
        with patch.object(
            providers, "_post_json_with_retries", side_effect=[truncated, complete]
        ) as post:
            provider = DeepSeekProvider(api_key="k")
            result = provider.generate_json(_request())
        self.assertEqual(result, {"ok": True})
        self.assertEqual(post.call_count, 2)  # retried exactly once
        self.assertIn("truncated_json", provider.retry_telemetry()["retry_statuses"])

    def test_truncated_content_twice_raises_after_one_retry(self) -> None:
        truncated = _ok(text='{"style_id":')  # truncated on both attempts
        with patch.object(
            providers, "_post_json_with_retries", side_effect=[truncated, truncated]
        ) as post:
            with self.assertRaises(ProviderError):
                DeepSeekProvider(api_key="k").generate_json(_request())
        self.assertEqual(post.call_count, 2)  # one retry, then give up (no infinite loop)

    def test_temperature_env_pins_temperature(self) -> None:
        # RWS_DEEPSEEK_TEMPERATURE=0 (the eval reproducibility probe) must be
        # sent in the request body; unset must leave the body without it.
        with patch.dict(os.environ, {"RWS_DEEPSEEK_TEMPERATURE": "0"}), patch.object(
            providers, "_post_json_with_retries", return_value=_ok()
        ) as post:
            DeepSeekProvider(api_key="k").generate_json(_request())
        self.assertEqual(post.call_args.kwargs["body"]["temperature"], 0.0)
        with patch.object(providers, "_post_json_with_retries", return_value=_ok()) as post:
            DeepSeekProvider(api_key="k").generate_json(_request())
        self.assertNotIn("temperature", post.call_args.kwargs["body"])

    def test_read_timeout_is_retried(self) -> None:
        # A socket timeout while READING the response body escapes urlopen as a
        # bare TimeoutError (not URLError) — observed live 2026-07-03 killing a
        # whole benchmark batch. _post_json_with_retries must retry it.
        ok_response = unittest.mock.MagicMock()
        ok_response.read.return_value = b'{"choices": [{"message": {"content": "{}"}}]}'
        ok_response.__enter__ = lambda s: ok_response
        ok_response.__exit__ = lambda s, *a: False
        with patch.object(
            providers.request, "urlopen", side_effect=[TimeoutError("read timed out"), ok_response]
        ) as urlopen, patch.object(providers.time, "sleep"):
            data = providers._post_json_with_retries(
                provider_name="DeepSeek",
                url="https://api.deepseek.com/v1/chat/completions",
                body={},
                headers={},
            )
        self.assertEqual(urlopen.call_count, 2)
        self.assertIn("choices", data)

    def test_factory_resolves_deepseek(self) -> None:
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "k"}):
            self.assertIsInstance(provider_from_name("deepseek"), DeepSeekProvider)


class DeepSeekOpenRouterFallbackTests(unittest.TestCase):
    """H#### 'when DeepSeek balance runs out, use OpenRouter' — mock-safe."""

    def test_402_falls_back_to_openrouter_and_returns_result(self) -> None:
        quota_error = providers.ProviderQuotaExhaustedError(
            "DeepSeek API error 402 (insufficient balance): {}"
        )
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "or-key"}), patch.object(
            providers,
            "_post_json_with_retries",
            side_effect=[quota_error, _ok(text='{"fallback": true}')],
        ) as post:
            provider = DeepSeekProvider(api_key="k")
            result = provider.generate_json(_request())
        self.assertEqual(result, {"fallback": True})
        self.assertEqual(post.call_count, 2)
        # First call is the normal DeepSeek request.
        self.assertEqual(post.call_args_list[0].kwargs["url"], providers.DeepSeekProvider.endpoint)
        # Second call went out through OpenRouter's endpoint with a DeepSeek slug.
        second_kwargs = post.call_args_list[1].kwargs
        self.assertEqual(second_kwargs["url"], providers.OpenRouterProvider.endpoint)
        self.assertEqual(second_kwargs["body"]["model"], "deepseek/deepseek-chat")
        self.assertIn("Bearer or-key", second_kwargs["headers"]["Authorization"])
        statuses = provider.retry_telemetry()["retry_statuses"]
        self.assertTrue(any(s.startswith("deepseek_402_fallback_to_openrouter:") for s in statuses))

    def test_402_reasoner_model_maps_to_r1_slug(self) -> None:
        quota_error = providers.ProviderQuotaExhaustedError("402")
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "or-key"}), patch.object(
            providers,
            "_post_json_with_retries",
            side_effect=[quota_error, _ok()],
        ) as post:
            DeepSeekProvider(api_key="k").generate_json(_request(model="deepseek-reasoner"))
        self.assertEqual(post.call_args_list[1].kwargs["body"]["model"], "deepseek/deepseek-r1")

    def test_fallback_disabled_by_env_reraises_quota_error(self) -> None:
        quota_error = providers.ProviderQuotaExhaustedError("402")
        with patch.dict(
            os.environ, {"OPENROUTER_API_KEY": "or-key", "RWS_DEEPSEEK_OPENROUTER_FALLBACK": "0"}
        ), patch.object(providers, "_post_json_with_retries", side_effect=[quota_error]) as post:
            with self.assertRaises(providers.ProviderQuotaExhaustedError):
                DeepSeekProvider(api_key="k").generate_json(_request())
        self.assertEqual(post.call_count, 1)

    def test_no_openrouter_key_surfaces_original_402(self) -> None:
        quota_error = providers.ProviderQuotaExhaustedError(
            "DeepSeek API error 402 (insufficient balance): out of funds"
        )
        with patch.dict(os.environ, {}, clear=True), patch.object(
            providers, "_post_json_with_retries", side_effect=[quota_error]
        ):
            with self.assertRaises(ProviderError) as ctx:
                DeepSeekProvider(api_key="k").generate_json(_request())
        message = str(ctx.exception)
        self.assertIn("402", message)
        self.assertIn("OpenRouter fallback", message)

    def test_openrouter_fallback_model_env_override(self) -> None:
        quota_error = providers.ProviderQuotaExhaustedError("402")
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "or-key",
                "RWS_OPENROUTER_DEEPSEEK_FALLBACK_MODEL": "custom/slug",
            },
        ), patch.object(
            providers, "_post_json_with_retries", side_effect=[quota_error, _ok()]
        ) as post:
            DeepSeekProvider(api_key="k").generate_json(_request())
        self.assertEqual(post.call_args_list[1].kwargs["body"]["model"], "custom/slug")


class DeepSeekFallbackProvenanceTests(unittest.TestCase):
    """H5071 — actual vs requested provider identity through the 402 fallback.

    Offline only: the balance exhaustion is injected as a raised
    ProviderQuotaExhaustedError, the real fallback adapter runs against a
    mocked _post_json_with_retries. No secrets, no live calls."""

    def _quota_error(self) -> providers.ProviderQuotaExhaustedError:
        return providers.ProviderQuotaExhaustedError(
            "DeepSeek API error 402 (insufficient balance): Not enough balance"
        )

    def test_direct_call_records_requested_equals_actual(self) -> None:
        with patch.object(providers, "_post_json_with_retries", return_value=_ok()):
            provider = DeepSeekProvider(api_key="k")
            provider.generate_json(_request(model="deepseek-chat"))
        provenance = provider.last_call_provenance()
        self.assertEqual(provenance["requested_provider"], "deepseek")
        self.assertEqual(provenance["requested_model"], "deepseek-chat")
        self.assertEqual(provenance["actual_provider"], "deepseek")
        self.assertEqual(provenance["actual_model"], "deepseek-chat")
        self.assertIsNone(provenance["fallback_reason"])
        self.assertEqual(provenance["outcome"], "completed_direct")
        self.assertTrue(provenance["usage_available"])

    def test_same_model_fallback_records_actual_provider_and_reason(self) -> None:
        # deepseek-chat requested; OpenRouter serves the same underlying model
        # under its own slug — the identity change must be persisted.
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "or-key"}), patch.object(
            providers,
            "_post_json_with_retries",
            side_effect=[self._quota_error(), _ok()],
        ):
            provider = DeepSeekProvider(api_key="k")
            provider.generate_json(_request(model="deepseek-chat"))
        provenance = provider.last_call_provenance()
        self.assertEqual(provenance["requested_provider"], "deepseek")
        self.assertEqual(provenance["requested_model"], "deepseek-chat")
        self.assertEqual(provenance["actual_provider"], "openrouter")
        self.assertEqual(provenance["actual_model"], "deepseek/deepseek-chat")
        self.assertIn("402", provenance["fallback_reason"])
        self.assertEqual(provenance["outcome"], "completed_fallback")
        self.assertTrue(provenance["usage_available"])
        # Usage from the actually-serving provider is what the caller sees.
        self.assertEqual(provider.last_usage()["total_tokens"], 7)

    def test_different_model_fallback_records_actual_model(self) -> None:
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "or-key",
                "RWS_OPENROUTER_DEEPSEEK_FALLBACK_MODEL": "custom/slug",
            },
        ), patch.object(
            providers,
            "_post_json_with_retries",
            side_effect=[self._quota_error(), _ok()],
        ):
            provider = DeepSeekProvider(api_key="k")
            provider.generate_json(_request(model="deepseek-reasoner"))
        provenance = provider.last_call_provenance()
        self.assertEqual(provenance["requested_model"], "deepseek-reasoner")
        self.assertEqual(provenance["actual_provider"], "openrouter")
        self.assertEqual(provenance["actual_model"], "custom/slug")
        self.assertEqual(provenance["outcome"], "completed_fallback")

    def test_fallback_with_missing_usage_still_persists_provenance(self) -> None:
        response_without_usage = {"choices": [{"message": {"content": '{"ok": true}'}}]}
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "or-key"}), patch.object(
            providers,
            "_post_json_with_retries",
            side_effect=[self._quota_error(), response_without_usage],
        ):
            provider = DeepSeekProvider(api_key="k")
            result = provider.generate_json(_request())
        self.assertEqual(result, {"ok": True})
        provenance = provider.last_call_provenance()
        self.assertEqual(provenance["actual_provider"], "openrouter")
        self.assertEqual(provenance["outcome"], "completed_fallback")
        self.assertFalse(provenance["usage_available"])
        self.assertEqual(provider.last_usage()["total_tokens"], 0)

    def test_failed_fallback_keeps_attempt_provenance_and_reason(self) -> None:
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "or-key"}), patch.object(
            providers,
            "_post_json_with_retries",
            side_effect=[self._quota_error(), ProviderError("openrouter exploded")],
        ):
            provider = DeepSeekProvider(api_key="k")
            with self.assertRaises(ProviderError) as ctx:
                provider.generate_json(_request())
        self.assertIn("also failed", str(ctx.exception))
        provenance = provider.last_call_provenance()
        self.assertEqual(provenance["actual_provider"], "openrouter")
        self.assertEqual(provenance["actual_model"], "deepseek/deepseek-chat")
        self.assertIn("402", provenance["fallback_reason"])
        self.assertEqual(provenance["outcome"], "failed_fallback")


if __name__ == "__main__":
    unittest.main()
