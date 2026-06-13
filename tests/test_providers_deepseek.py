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

    def test_factory_resolves_deepseek(self) -> None:
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "k"}):
            self.assertIsInstance(provider_from_name("deepseek"), DeepSeekProvider)


if __name__ == "__main__":
    unittest.main()
