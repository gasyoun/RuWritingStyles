import unittest
from unittest.mock import patch

from ruwritingstyles import providers
from ruwritingstyles.providers import AnthropicProvider, ProviderRequest
import ruwritingstyles.mcp_client as mcp_module


def _request(tools=None):
    return ProviderRequest(
        task="verification",
        prompt="Return JSON.",
        schema={"type": "object"},
        metadata={"run_id": "test-run"},
        tools=tools,
    )


TOOLS = [
    {
        "name": "search_bibliography",
        "description": "Look up a citation.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
    }
]


class AnthropicToolLoopTests(unittest.TestCase):
    def test_no_tools_is_single_turn(self) -> None:
        final = {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": '{"ok": true}'}],
            "usage": {"input_tokens": 5, "output_tokens": 2},
        }
        with patch.object(providers, "_post_json_with_retries", return_value=final) as post:
            provider = AnthropicProvider(api_key="test-key")
            result = provider.generate_json(_request())
        self.assertEqual(result, {"ok": True})
        self.assertEqual(post.call_count, 1)
        # No tools key in the request body.
        self.assertNotIn("tools", post.call_args.kwargs["body"])

    def test_tool_use_loop_executes_tool_then_returns_json(self) -> None:
        tool_turn = {
            "stop_reason": "tool_use",
            "content": [
                {"type": "tool_use", "id": "tu_1", "name": "search_bibliography", "input": {"query": "Zaliznyak"}}
            ],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        final_turn = {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": '{"grounded": true}'}],
            "usage": {"input_tokens": 8, "output_tokens": 3},
        }
        with patch.object(providers, "_post_json_with_retries", side_effect=[tool_turn, final_turn]) as post, \
                patch.object(mcp_module.mcp_client, "execute_tool", return_value={"hit": "found"}) as exec_tool:
            provider = AnthropicProvider(api_key="test-key")
            result = provider.generate_json(_request(tools=TOOLS))

        self.assertEqual(result, {"grounded": True})
        self.assertEqual(post.call_count, 2)
        # Tool was executed with the model-provided args.
        exec_tool.assert_called_once()
        args, kwargs = exec_tool.call_args
        self.assertEqual(args[0], "search_bibliography")
        self.assertEqual(args[1], {"query": "Zaliznyak"})
        self.assertEqual(kwargs["run_id"], "test-run")
        # The follow-up request carried a tool_result block back.
        second_body = post.call_args_list[1].kwargs["body"]
        last_msg = second_body["messages"][-1]
        self.assertEqual(last_msg["role"], "user")
        self.assertEqual(last_msg["content"][0]["type"], "tool_result")
        self.assertEqual(last_msg["content"][0]["tool_use_id"], "tu_1")
        # Tools are sent in Anthropic shape (input_schema, not parameters).
        first_body = post.call_args_list[0].kwargs["body"]
        self.assertIn("input_schema", first_body["tools"][0])

    def test_usage_accumulates_across_turns(self) -> None:
        tool_turn = {
            "stop_reason": "tool_use",
            "content": [{"type": "tool_use", "id": "tu_1", "name": "search_bibliography", "input": {}}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        final_turn = {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": "{}"}],
            "usage": {"input_tokens": 8, "output_tokens": 3},
        }
        with patch.object(providers, "_post_json_with_retries", side_effect=[tool_turn, final_turn]), \
                patch.object(mcp_module.mcp_client, "execute_tool", return_value={}):
            provider = AnthropicProvider(api_key="test-key")
            provider.generate_json(_request(tools=TOOLS))
            usage = provider.last_usage()
        self.assertEqual(usage["input_tokens"], 18)
        self.assertEqual(usage["output_tokens"], 8)
        self.assertEqual(usage["total_tokens"], 26)


if __name__ == "__main__":
    unittest.main()
