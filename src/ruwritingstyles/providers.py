"""LLM provider adapters for RuWritingStyles.

The mock provider is deterministic and used by tests. Real providers are
opt-in adapters for OpenAI, Google Gemini, and Anthropic Claude.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import re
import time
from typing import Any
from urllib.parse import quote
from urllib import request, error


@dataclass(frozen=True)
class ProviderRequest:
    """Input passed to a provider."""

    task: str
    prompt: str
    schema: dict[str, Any]
    metadata: dict[str, Any]
    model: str | None = None
    tools: list[dict[str, Any]] | None = None
    injection_queue: Any | None = None


@dataclass
class ProviderRetryTelemetry:
    """Retry details from the most recent provider HTTP request."""

    retry_count: int = 0
    retry_delay_seconds: float = 0.0
    retry_statuses: list[str] | None = None

    def record(self, status: str, delay_seconds: float) -> None:
        self.retry_count += 1
        self.retry_delay_seconds += delay_seconds
        if self.retry_statuses is None:
            self.retry_statuses = []
        self.retry_statuses.append(status)

    def to_json(self) -> dict[str, Any]:
        return {
            "retry_count": self.retry_count,
            "retry_delay_seconds": round(self.retry_delay_seconds, 3),
            "retry_statuses": list(self.retry_statuses or []),
        }


@dataclass
class ProviderUsage:
    """Token usage and cost estimates from a provider response."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost_estimate: float = 0.0

    def to_json(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_estimate": self.cost_estimate,
        }


class ProviderError(RuntimeError):
    """Raised when a provider cannot complete a request."""


class BaseProvider:
    name = "base"

    def generate_json(self, provider_request: ProviderRequest) -> dict[str, Any]:
        raise NotImplementedError

    def effective_model(self, provider_request: ProviderRequest) -> str:
        return provider_request.model or ""

    def retry_telemetry(self) -> dict[str, Any]:
        return getattr(self, "_last_retry_telemetry", ProviderRetryTelemetry().to_json())

    def _set_retry_telemetry(self, telemetry: ProviderRetryTelemetry) -> None:
        self._last_retry_telemetry = telemetry.to_json()

    def last_usage(self) -> dict[str, Any]:
        return getattr(self, "_last_usage", ProviderUsage().to_json())

    def _set_usage(self, usage: ProviderUsage) -> None:
        self._last_usage = usage.to_json()


class MockProvider(BaseProvider):
    """Deterministic provider for local development and tests."""

    name = "mock"

    def effective_model(self, provider_request: ProviderRequest) -> str:
        return provider_request.model or "mock"

    def generate_json(self, provider_request: ProviderRequest) -> dict[str, Any]:
        self._set_retry_telemetry(ProviderRetryTelemetry())
        self._set_usage(ProviderUsage())
        task = provider_request.task
        metadata = provider_request.metadata
        
        # Simulate tool usage for verification if tools are present
        if task == "verification" and provider_request.tools:
            from .mcp_client import mcp_client
            run_id = str(metadata.get("run_id", "mock-run"))
            # Simulate a search for a common philological authority
            mcp_client.execute_tool("search_bibliography", {"query": "Uspensky 1987"}, run_id=run_id, task=task)
            # Simulate a fallback search for an unknown reference
            mcp_client.execute_tool("search_scholar", {"query": "Unknown Author 2024 citation"}, run_id=run_id, task=task)

        if task == "review":
            return self._review(metadata)
        if task == "council":
            return self._council(metadata)
        if task == "revision":
            return self._revision(metadata)
        if task == "verification":
            return self._verification(metadata)
        if task == "assessment":
            return self._assessment(metadata)
        if task == "syntax_assessment":
            return self._syntax(metadata)
        if task == "deliberation":
            return self._deliberation(metadata)
        if task == "scrutiny":
            return self._scrutiny(metadata)
        if task == "migration":
            return self._migration(metadata)
        if task == "gallery":
            return self._gallery(metadata)
        if task == "peer_review":
            return self._peer_review(metadata)
        if task == "audit":
            return self._audit(metadata)
        if task == "bias_audit":
            return self._bias_audit(metadata)
        raise ProviderError(f"mock provider does not support task {task!r}")

    def _review(self, metadata: dict[str, Any]) -> dict[str, Any]:
        style_id = str(metadata["style_id"])
        span_id = str(metadata.get("first_paragraph_span_id") or "p001")
        return {
            "style_id": style_id,
            "summary": f"Mock review completed for {style_id}.",
            "findings": [
                {
                    "id": "finding-001",
                    "style_id": style_id,
                    "span_id": span_id,
                    "severity": "note",
                    "type": "mock_observation",
                    "finding": "Mock provider placeholder finding for pipeline validation.",
                    "suggestion": "Replace the mock provider with a real provider to get substantive review findings.",
                    "confidence": 0.1,
                }
            ],
        }

    def _deliberation(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "replies": [
                {
                    "style_id": str(metadata.get("style_id", "mock")),
                    "comment": "Mock deliberation debate reply.",
                }
            ]
        }

    def _scrutiny(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "findings": [
                {
                    "id": "scrutiny-001",
                    "term": "mock-term",
                    "issue": "mock-issue",
                    "recommendation": "mock-recommendation"
                }
            ]
        }

    def _council(self, metadata: dict[str, Any]) -> dict[str, Any]:
        decisions = []
        replies = []
        finding_ids = metadata.get("finding_ids", [])
        if not finding_ids:
            finding_ids = ["finding-001"]
            
        for finding_id in finding_ids:
            replies.append({
                "reply_to": finding_id,
                "style_id": "mock-style",
                "bloom_level": "Analyze",
                "position": "agree",
                "comment": "Mock analysis of finding.",
            })
            decisions.append({
                "finding_id": finding_id,
                "bloom_level": "Evaluate",
                "status": "informational",
                "primary_school": "ling_iesh",
                "influence": {"ling_iesh": 0.8, "ling_mss": 0.2},
                "reason": "Mock council keeps placeholder findings informational.",
            })
        return {
            "run_id": str(metadata["run_id"]),
            "status": "completed",
            "replies": replies,
            "decisions": decisions,
            "stylistic_commitments": [
                {
                    "term": "Mock Term",
                    "decision": "Keep it as is.",
                    "rationale": "Mock provider uses a stable placeholder commitment for schema validation.",
                }
            ],
        }

    def _revision(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": str(metadata["run_id"]),
            "status": "completed",
            "revised_document": str(metadata.get("normalized_text") or ""),
            "applied_changes": [],
            "unresolved": [
                {
                    "reason": "Mock provider copied the normalized document without substantive revision."
                }
            ],
        }

    def _verification(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": str(metadata["run_id"]),
            "status": "needs_human_review",
            "passed": ["artifacts_parse"],
            "warnings": [
                {
                    "message": "Mock provider cannot verify factual fidelity; run a real provider for substantive verification."
                }
            ],
        }

    def _assessment(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": str(metadata["run_id"]),
            "status": "completed",
            "assessments": [
                {
                    "span_id": "p001",
                    "tag": "mock-tag",
                    "impact": "positive",
                    "passed": True,
                    "comment": "Mock assessment.",
                }
            ],
        }

    def _syntax(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": str(metadata["run_id"]),
            "shifts": [
                {
                    "type": "passive_to_active",
                    "original_span": "The text was written by mock.",
                    "revised_span": "Mock wrote the text.",
                    "comment": "Mock syntax shift.",
                }
            ],
        }

    def _migration(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "migration_summary": "Mock migration summary.",
            "revised_text": "Mock migrated text."
        }

    def _gallery(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "transformed_text": f"Mock transformed text for {metadata.get('style_id')}.",
            "accent_description": "Mock accent description."
        }

    def _peer_review(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "reviewer_archetype": metadata.get("archetype", "mock"),
            "overall_score": 8,
            "comments": [
                {"id": "pr001", "type": "praise", "text": "Mock peer review praise."}
            ],
            "recommendation": "accept"
        }

    def _audit(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "completed",
            "audit_summary": "Mock audit summary.",
            "violations": [],
            "passed_commitments": ["Mock Term"]
        }

    def _bias_audit(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "completed",
            "bias_score": 1,
            "primary_bias_detected": "none",
            "findings": [
                {
                    "id": "bias-001",
                    "severity": "note",
                    "issue": "Mock bias audit: council is impartial.",
                    "recommendation": "Maintain methodological diversity."
                }
            ],
            "methodological_critique": "Mock critique."
        }


class OpenAIProvider(BaseProvider):
    """Minimal OpenAI Responses API provider."""

    name = "openai"
    endpoint = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY is required for provider 'openai'")

    def effective_model(self, provider_request: ProviderRequest) -> str:
        return provider_request.model or os.environ.get("RWS_OPENAI_MODEL") or "gpt-4o"

    def generate_json(self, provider_request: ProviderRequest) -> dict[str, Any]:
        model = self.effective_model(provider_request)
        messages = [
            {
                "role": "user",
                "content": provider_request.prompt,
            }
        ]
        
        max_turns = 5
        total_input_tokens = 0
        total_output_tokens = 0
        telemetry = ProviderRetryTelemetry()
        
        for turn in range(max_turns):
            body = {
                "model": model,
                "messages": messages,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": _schema_name(provider_request.task),
                        "schema": _provider_schema(provider_request.schema),
                        "strict": True,
                    }
                },
            }
            
            if provider_request.tools:
                # OpenAI format: {"type": "function", "function": {"name": ..., "description": ..., "parameters": ...}}
                body["tools"] = [{"type": "function", "function": t} for t in provider_request.tools]
                
            effort = os.environ.get("RWS_OPENAI_REASONING")
            if effort and "o1" in model:
                body["reasoning_effort"] = effort

            # Check for human injections between turns
            if provider_request.injection_queue:
                while not provider_request.injection_queue.empty():
                    try:
                        injection = provider_request.injection_queue.get_nowait()
                        messages.append({
                            "role": "user",
                            "content": f"RESEARCHER_INJECTION: {injection}"
                        })
                    except Exception:
                        break

            try:
                data = _post_json_with_retries(
                    provider_name="OpenAI",
                    url=self.endpoint,
                    body=body,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    telemetry=telemetry,
                )
            finally:
                self._set_retry_telemetry(telemetry)

            usage = data.get("usage", {})
            total_input_tokens += usage.get("prompt_tokens", 0)
            total_output_tokens += usage.get("completion_tokens", 0)
            self._set_usage(ProviderUsage(
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                total_tokens=total_input_tokens + total_output_tokens,
                cost_estimate=0.0
            ))

            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            tool_calls = message.get("tool_calls", [])
            
            if not tool_calls:
                text = message.get("content")
                if not text:
                    raise ProviderError("OpenAI response did not include output text")
                try:
                    return json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ProviderError(f"OpenAI response did not contain parseable JSON: {text[:500]}") from exc

            # Append assistant message with tool calls
            messages.append(message)
            
            # Execute tools
            from .mcp_client import mcp_client
            run_id = str(provider_request.metadata.get("run_id", "unknown"))
            task = provider_request.task
            for tc in tool_calls:
                func = tc.get("function", {})
                tool_name = func.get("name")
                args_str = func.get("arguments", "{}")
                
                try:
                    args = json.loads(args_str)
                    result = mcp_client.execute_tool(tool_name, args, run_id=run_id, task=task)
                except Exception as e:
                    result = {"error": str(e)}
                    
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id"),
                    "name": tool_name,
                    "content": json.dumps(result)
                })
                
        raise ProviderError(f"OpenAI exceeded {max_turns} tool call turns without producing final JSON.")


class GoogleProvider(BaseProvider):
    """Minimal Google Gemini API provider."""

    name = "google"
    endpoint_template = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ProviderError("GEMINI_API_KEY or GOOGLE_API_KEY is required for provider 'google'")

    def effective_model(self, provider_request: ProviderRequest) -> str:
        return provider_request.model or os.environ.get("RWS_GOOGLE_MODEL") or "gemini-1.5-pro"

    def generate_json(self, provider_request: ProviderRequest) -> dict[str, Any]:
        model = self.effective_model(provider_request)
        messages = [
            {
                "role": "user",
                "parts": [{"text": provider_request.prompt}],
            }
        ]
        
        max_turns = 5
        total_input_tokens = 0
        total_output_tokens = 0
        telemetry = ProviderRetryTelemetry()
        
        for turn in range(max_turns):
            body = {
                "contents": messages,
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseJsonSchema": _provider_schema(provider_request.schema),
                },
            }
            if provider_request.tools:
                # Gemini format: {"functionDeclarations": [{"name": ..., "description": ..., "parameters": ...}]}
                body["tools"] = [{"functionDeclarations": provider_request.tools}]
                
            # Check for human injections between turns
            if provider_request.injection_queue:
                while not provider_request.injection_queue.empty():
                    try:
                        injection = provider_request.injection_queue.get_nowait()
                        messages.append({
                            "role": "user",
                            "parts": [{"text": f"RESEARCHER_INJECTION: {injection}"}]
                        })
                    except Exception:
                        break

            try:
                data = _post_json_with_retries(
                    provider_name="Google Gemini",
                    url=self.endpoint_template.format(model=quote(model, safe=""), api_key=quote(self.api_key, safe="")),
                    body=body,
                    headers={"Content-Type": "application/json"},
                    telemetry=telemetry,
                )
            finally:
                self._set_retry_telemetry(telemetry)

            usage = data.get("usageMetadata", {})
            total_input_tokens += usage.get("promptTokenCount", 0)
            total_output_tokens += usage.get("candidatesTokenCount", 0)
            self._set_usage(ProviderUsage(
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                total_tokens=total_input_tokens + total_output_tokens
            ))

            if not data.get("candidates"):
                raise ProviderError(f"Google Gemini returned no candidates: {data}")

            candidate = data["candidates"][0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])
            
            # Check for function calls
            function_calls = [p["functionCall"] for p in parts if "functionCall" in p]
            
            if not function_calls:
                # No tool calls, assume it's the final JSON response
                text = _extract_gemini_text(data)
                try:
                    return json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ProviderError(f"Google Gemini response did not contain parseable JSON: {text[:500]}") from exc
            
            # 1. Append the model's function call to history
            messages.append({
                "role": "model",
                "parts": parts
            })
            
            # 2. Execute tools and append function responses
            from .mcp_client import mcp_client
            run_id = str(provider_request.metadata.get("run_id", "unknown"))
            task = provider_request.task
            tool_responses = []
            for fc in function_calls:
                tool_name = fc.get("name")
                args = fc.get("args", {})
                try:
                    result = mcp_client.execute_tool(tool_name, args, run_id=run_id, task=task)
                except Exception as e:
                    result = {"error": str(e)}
                    
                tool_responses.append({
                    "functionResponse": {
                        "name": tool_name,
                        "response": result
                    }
                })
                
            messages.append({
                "role": "user",
                "parts": tool_responses
            })
            
        raise ProviderError(f"Google Gemini exceeded {max_turns} tool call turns without producing final JSON.")


class AnthropicProvider(BaseProvider):
    """Minimal Anthropic Messages API provider."""

    name = "anthropic"
    endpoint = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ProviderError("ANTHROPIC_API_KEY is required for provider 'anthropic'")

    def effective_model(self, provider_request: ProviderRequest) -> str:
        return provider_request.model or os.environ.get("RWS_ANTHROPIC_MODEL") or "claude-3-5-sonnet-20240620"

    def generate_json(self, provider_request: ProviderRequest) -> dict[str, Any]:
        model = self.effective_model(provider_request)
        max_tokens = int(os.environ.get("RWS_ANTHROPIC_MAX_TOKENS", "8192"))
        max_turns = 5
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": provider_request.prompt}
        ]
        # Anthropic tools use input_schema where the OpenAI shape uses parameters.
        anthropic_tools = None
        if provider_request.tools:
            anthropic_tools = [
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "input_schema": t.get("parameters") or {"type": "object", "properties": {}},
                }
                for t in provider_request.tools
            ]

        telemetry = ProviderRetryTelemetry()
        total_input_tokens = 0
        total_output_tokens = 0

        for _turn in range(max_turns):
            # Check for human injections between turns.
            if provider_request.injection_queue:
                while not provider_request.injection_queue.empty():
                    try:
                        injection = provider_request.injection_queue.get_nowait()
                        messages.append({"role": "user", "content": f"RESEARCHER_INJECTION: {injection}"})
                    except Exception:
                        break

            body: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": messages,
                "system": "Respond only with a JSON object strictly following the provided schema. Use the available tools to ground citations and facts when helpful; once you have what you need, return the final JSON object as your text response.",
            }
            if anthropic_tools:
                body["tools"] = anthropic_tools

            try:
                data = _post_json_with_retries(
                    provider_name="Anthropic",
                    url=self.endpoint,
                    body=body,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": os.environ.get("ANTHROPIC_VERSION", "2023-06-01"),
                        "content-type": "application/json",
                    },
                    telemetry=telemetry,
                )
            finally:
                self._set_retry_telemetry(telemetry)

            usage = data.get("usage", {})
            total_input_tokens += usage.get("input_tokens", 0)
            total_output_tokens += usage.get("output_tokens", 0)
            self._set_usage(ProviderUsage(
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                total_tokens=total_input_tokens + total_output_tokens,
            ))

            content_blocks = data.get("content", []) or []
            tool_use_blocks = [
                b for b in content_blocks
                if isinstance(b, dict) and b.get("type") == "tool_use"
            ]

            if data.get("stop_reason") != "tool_use" or not tool_use_blocks:
                text = _extract_anthropic_text(data)
                try:
                    return json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ProviderError(f"Anthropic response did not contain parseable JSON: {text[:500]}") from exc

            # Carry the assistant turn (including the tool_use blocks) forward,
            # then answer each tool_use with a tool_result block.
            messages.append({"role": "assistant", "content": content_blocks})

            from .mcp_client import mcp_client
            run_id = str(provider_request.metadata.get("run_id", "unknown"))
            task = provider_request.task
            tool_results = []
            for block in tool_use_blocks:
                tool_name = block.get("name")
                args = block.get("input") or {}
                try:
                    result = mcp_client.execute_tool(tool_name, args, run_id=run_id, task=task)
                except Exception as exc:
                    result = {"error": str(exc)}
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.get("id"),
                    "content": json.dumps(result, ensure_ascii=False),
                })
            messages.append({"role": "user", "content": tool_results})

        raise ProviderError(f"Anthropic exceeded {max_turns} tool call turns without producing final JSON.")


class OpenRouterProvider(BaseProvider):
    """OpenRouter / Nous Portal API provider (OpenAI-compatible)."""

    name = "openrouter"
    endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY") or os.environ.get("NOUS_PORTAL_API_KEY")
        if not self.api_key:
            raise ProviderError("OPENROUTER_API_KEY or NOUS_PORTAL_API_KEY is required for provider 'openrouter'")

    def effective_model(self, provider_request: ProviderRequest) -> str:
        return provider_request.model or os.environ.get("RWS_OPENROUTER_MODEL") or "google/gemini-2.0-flash-exp:free"

    def generate_json(self, provider_request: ProviderRequest) -> dict[str, Any]:
        model = self.effective_model(provider_request)
        body = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": provider_request.prompt,
                }
            ],
            "response_format": {"type": "json_object"},
        }

        telemetry = ProviderRetryTelemetry()
        try:
            data = _post_json_with_retries(
                provider_name="OpenRouter",
                url=self.endpoint,
                body=body,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/gasyoun/RuWritingStyles",
                    "X-Title": "RuWritingStyles Philological Engine",
                },
                telemetry=telemetry,
            )
        finally:
            self._set_retry_telemetry(telemetry)

        usage = data.get("usage", {})
        self._set_usage(ProviderUsage(
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0)
        ))

        if "choices" not in data or not data["choices"]:
            raise ProviderError(f"OpenRouter response missing choices: {data}")
            
        text = data["choices"][0]["message"]["content"]
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"OpenRouter response did not contain parseable JSON: {text[:500]}") from exc


class LocalProvider(BaseProvider):
    """Local LLM provider (Ollama, vLLM, etc.) using OpenAI-compatible API."""

    name = "local"

    def __init__(self, endpoint: str | None = None, api_key: str = "no-key") -> None:
        self.endpoint = endpoint or os.environ.get("RWS_LOCAL_LLM_URL") or "http://localhost:8000/v1/chat/completions"
        self.api_key = api_key

    def effective_model(self, provider_request: ProviderRequest) -> str:
        return provider_request.model or os.environ.get("RWS_LOCAL_LLM_MODEL") or "local-model"

    def generate_json(self, provider_request: ProviderRequest) -> dict[str, Any]:
        model = self.effective_model(provider_request)
        body = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": provider_request.prompt,
                }
            ],
            "response_format": {"type": "json_object"},
        }

        telemetry = ProviderRetryTelemetry()
        try:
            data = _post_json_with_retries(
                provider_name="Local LLM",
                url=self.endpoint,
                body=body,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                telemetry=telemetry,
            )
        finally:
            self._set_retry_telemetry(telemetry)

        usage = data.get("usage", {})
        self._set_usage(ProviderUsage(
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0)
        ))

        if "choices" not in data or not data["choices"]:
            raise ProviderError(f"Local LLM response missing choices: {data}")
            
        text = data["choices"][0]["message"]["content"]
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Local LLM response did not contain parseable JSON: {text[:500]}") from exc


class OllamaProvider(BaseProvider):
    """Specific Ollama API provider."""

    name = "ollama"

    def __init__(self, endpoint: str | None = None) -> None:
        self.endpoint = endpoint or os.environ.get("RWS_OLLAMA_URL") or "http://localhost:11434/api/chat"

    def effective_model(self, provider_request: ProviderRequest) -> str:
        return provider_request.model or os.environ.get("RWS_OLLAMA_MODEL") or "llama3"

    def generate_json(self, provider_request: ProviderRequest) -> dict[str, Any]:
        model = self.effective_model(provider_request)
        body = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": provider_request.prompt,
                }
            ],
            "stream": False,
            "format": "json",
        }

        telemetry = ProviderRetryTelemetry()
        try:
            data = _post_json_with_retries(
                provider_name="Ollama",
                url=self.endpoint,
                body=body,
                headers={"Content-Type": "application/json"},
                telemetry=telemetry,
            )
        finally:
            self._set_retry_telemetry(telemetry)

        # Ollama doesn't always provide token usage in the chat response unless requested
        self._set_usage(ProviderUsage(
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
        ))

        if "message" not in data or "content" not in data["message"]:
            raise ProviderError(f"Ollama response missing content: {data}")
            
        text = data["message"]["content"]
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Ollama response did not contain parseable JSON: {text[:500]}") from exc


class DeepSeekProvider(BaseProvider):
    """DeepSeek provider (OpenAI-compatible JSON mode).

    Direct ``api.deepseek.com`` by default; set ``RWS_DEEPSEEK_URL`` to route the
    same key through a proxy or an OpenRouter-style endpoint. Default model
    ``deepseek-chat`` (V3); use ``deepseek-reasoner`` (R1) via ``--model`` or
    ``model_policy.yml`` for the heavier judgement stages. DeepSeek's JSON mode
    requires the word "json" in the prompt — the RWS stage prompts already ask
    for JSON output, so this is satisfied by construction."""

    name = "deepseek"
    endpoint = "https://api.deepseek.com/v1/chat/completions"

    def __init__(self, api_key: str | None = None, endpoint: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ProviderError("DEEPSEEK_API_KEY is required for provider 'deepseek'")
        self.endpoint = endpoint or os.environ.get("RWS_DEEPSEEK_URL") or self.endpoint

    def effective_model(self, provider_request: ProviderRequest) -> str:
        return provider_request.model or os.environ.get("RWS_DEEPSEEK_MODEL") or "deepseek-chat"

    def generate_json(self, provider_request: ProviderRequest) -> dict[str, Any]:
        model = self.effective_model(provider_request)
        body = {
            "model": model,
            "messages": [{"role": "user", "content": provider_request.prompt}],
            "response_format": {"type": "json_object"},
        }

        telemetry = ProviderRetryTelemetry()
        try:
            data = _post_json_with_retries(
                provider_name="DeepSeek",
                url=self.endpoint,
                body=body,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                telemetry=telemetry,
            )
        finally:
            self._set_retry_telemetry(telemetry)

        usage = data.get("usage", {})
        self._set_usage(ProviderUsage(
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
        ))

        if "choices" not in data or not data["choices"]:
            raise ProviderError(f"DeepSeek response missing choices: {data}")

        text = data["choices"][0]["message"]["content"]
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"DeepSeek response did not contain parseable JSON: {text[:500]}") from exc


def provider_from_name(name: str) -> BaseProvider:
    if name == "mock":
        return MockProvider()
    if name == "openai":
        return OpenAIProvider()
    if name == "google":
        return GoogleProvider()
    if name == "anthropic":
        return AnthropicProvider()
    if name == "openrouter":
        return OpenRouterProvider()
    if name == "deepseek":
        return DeepSeekProvider()
    if name == "local":
        return LocalProvider()
    if name == "ollama":
        return OllamaProvider()
    raise ProviderError(f"unknown provider {name!r}")


def load_schema(repo_root: Path, relative_path: str) -> dict[str, Any]:
    return json.loads((repo_root / relative_path).read_text(encoding="utf-8"))


def _schema_name(task: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", f"rws_{task}_output")


def _provider_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a conservative schema copy for provider structured outputs."""
    def clean(value: Any) -> Any:
        if isinstance(value, dict):
            cleaned: dict[str, Any] = {}
            for key, item in value.items():
                if key in {"$schema", "$id", "title", "$ref"}:
                    continue
                cleaned[key] = clean(item)
            return cleaned
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value
    return clean(schema)


def _extract_output_text(data: dict[str, Any]) -> str:
    # Handle both new 'responses' and old 'chat/completions' style OpenAI formats
    if "choices" in data and data["choices"]:
        return data["choices"][0]["message"]["content"]
    
    chunks: list[str] = []
    for item in data.get("output", []):
        if not isinstance(item, dict): continue
        for content in item.get("content", []):
            if not isinstance(content, dict): continue
            if isinstance(content.get("text"), str):
                chunks.append(content["text"])
    if chunks: return "".join(chunks)
    raise ProviderError("Provider response did not include output text")


def _extract_gemini_text(data: dict[str, Any]) -> str:
    chunks: list[str] = []
    for candidate in data.get("candidates", []):
        if not isinstance(candidate, dict): continue
        content = candidate.get("content")
        if not isinstance(content, dict): continue
        for part in content.get("parts", []):
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                chunks.append(part["text"])
    if chunks: return "".join(chunks)
    raise ProviderError("Google Gemini response did not include output text")


def _extract_anthropic_text(data: dict[str, Any]) -> str:
    chunks: list[str] = []
    for content in data.get("content", []):
        if isinstance(content, dict) and isinstance(content.get("text"), str):
            chunks.append(content["text"])
    if chunks: return "".join(chunks)
    raise ProviderError("Anthropic response did not include output text")


def _post_json_with_retries(
    *,
    provider_name: str,
    url: str,
    body: dict[str, Any],
    headers: dict[str, str],
    telemetry: ProviderRetryTelemetry | None = None,
    timeout: int = 120,
) -> dict[str, Any]:
    attempts = _provider_attempt_count()
    delay = _provider_retry_delay()
    encoded = json.dumps(body).encode("utf-8")
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        sleep_for = delay
        req = request.Request(url, data=encoded, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            last_error = ProviderError(f"{provider_name} API error {exc.code}: {detail}")
            if not _is_retryable_status(exc.code) or attempt == attempts:
                raise last_error from exc
            sleep_for = _retry_delay_from_headers(exc.headers, delay)
            if telemetry is not None: telemetry.record(str(exc.code), sleep_for)
        except error.URLError as exc:
            last_error = ProviderError(f"{provider_name} API request failed: {exc}")
            if attempt == attempts: raise last_error from exc
            if telemetry is not None: telemetry.record("url_error", sleep_for)
        time.sleep(sleep_for)
        delay *= 2
    raise last_error or ProviderError(f"{provider_name} API request failed")


def _provider_attempt_count() -> int:
    try: return max(1, int(os.environ.get("RWS_PROVIDER_MAX_ATTEMPTS", "3")))
    except ValueError: return 3

def _provider_retry_delay() -> float:
    try: return max(0.0, float(os.environ.get("RWS_PROVIDER_RETRY_SECONDS", "1.0")))
    except ValueError: return 1.0

def _is_retryable_status(status: int) -> bool:
    return status in {429, 500, 502, 503, 504}

def _retry_delay_from_headers(headers: Any, fallback_delay: float, now: datetime | None = None) -> float:
    retry_after = _parse_retry_after(_header_value(headers, "retry-after"), now=now)
    if retry_after is not None:
        return retry_after

    delays = _exhausted_reset_delays(
        headers,
        [
            ("x-ratelimit-remaining-requests", "x-ratelimit-reset-requests"),
            ("x-ratelimit-remaining-tokens", "x-ratelimit-reset-tokens"),
            ("anthropic-ratelimit-requests-remaining", "anthropic-ratelimit-requests-reset"),
            ("anthropic-ratelimit-tokens-remaining", "anthropic-ratelimit-tokens-reset"),
            ("anthropic-ratelimit-input-tokens-remaining", "anthropic-ratelimit-input-tokens-reset"),
            ("anthropic-ratelimit-output-tokens-remaining", "anthropic-ratelimit-output-tokens-reset"),
        ],
        now=now,
    )
    if delays:
        return max(delays)
    return fallback_delay


def _exhausted_reset_delays(
    headers: Any,
    pairs: list[tuple[str, str]],
    now: datetime | None = None,
) -> list[float]:
    delays: list[float] = []
    for remaining_header, reset_header in pairs:
        if not _is_exhausted_remaining_header(_header_value(headers, remaining_header)):
            continue
        delay = _parse_reset_delay(_header_value(headers, reset_header), now=now)
        if delay is not None:
            delays.append(delay)
    return delays


def _parse_retry_after(value: str | None, now: datetime | None = None) -> float | None:
    if not value:
        return None
    stripped = value.strip()
    delay = _parse_positive_float(stripped)
    if delay is not None:
        return delay
    return _parse_datetime_delay(stripped, now=now)


def _parse_reset_delay(value: str | None, now: datetime | None = None) -> float | None:
    if not value:
        return None
    stripped = value.strip()
    delay = _parse_openai_duration(stripped)
    if delay is not None:
        return delay
    delay = _parse_positive_float(stripped)
    if delay is not None:
        return delay
    return _parse_datetime_delay(stripped, now=now)


def _parse_openai_duration(value: str) -> float | None:
    matches = re.findall(r"([0-9]+(?:\.[0-9]+)?)(ms|s|m|h)", value)
    if not matches:
        return None
    unit_seconds = {
        "ms": 0.001,
        "s": 1.0,
        "m": 60.0,
        "h": 3600.0,
    }
    return sum(float(amount) * unit_seconds[unit] for amount, unit in matches)


def _parse_datetime_delay(value: str, now: datetime | None = None) -> float | None:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None
    actual_now = now or datetime.now(timezone.utc)
    if actual_now.tzinfo is None:
        actual_now = actual_now.replace(tzinfo=timezone.utc)
    return max(0.0, (parsed - actual_now).total_seconds())


def _parse_datetime(value: str) -> datetime | None:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_positive_float(value: str) -> float | None:
    try:
        return max(0.0, float(value))
    except ValueError:
        return None


def _is_exhausted_remaining_header(value: str | None) -> bool:
    if value is None:
        return False
    try:
        return float(value.strip()) <= 0
    except ValueError:
        return False


def _header_value(headers: Any, name: str) -> str | None:
    if headers is None:
        return None
    # Support both list-of-tuples and dictionary-like headers
    if hasattr(headers, "get"):
        value = headers.get(name)
        if value is not None:
            return str(value)
        # Try case-insensitive
        lower_name = name.lower()
        for key, val in headers.items():
            if str(key).lower() == lower_name:
                return str(val)
    return None
