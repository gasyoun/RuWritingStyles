"""LLM provider adapters for RuWritingStyles.

The mock provider is deterministic and used by tests. The OpenAI provider is a
minimal Responses API adapter that uses Structured Outputs when an
OPENAI_API_KEY is available.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib import request, error


@dataclass(frozen=True)
class ProviderRequest:
    """Input passed to a provider."""

    task: str
    prompt: str
    schema: dict[str, Any]
    metadata: dict[str, Any]
    model: str | None = None


class ProviderError(RuntimeError):
    """Raised when a provider cannot complete a request."""


class BaseProvider:
    name = "base"

    def generate_json(self, provider_request: ProviderRequest) -> dict[str, Any]:
        raise NotImplementedError


class MockProvider(BaseProvider):
    """Deterministic provider for local development and tests."""

    name = "mock"

    def generate_json(self, provider_request: ProviderRequest) -> dict[str, Any]:
        task = provider_request.task
        metadata = provider_request.metadata
        if task == "review":
            return self._review(metadata)
        if task == "council":
            return self._council(metadata)
        if task == "revision":
            return self._revision(metadata)
        if task == "verification":
            return self._verification(metadata)
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

    def _council(self, metadata: dict[str, Any]) -> dict[str, Any]:
        decisions = []
        for finding_id in metadata.get("finding_ids", []):
            decisions.append(
                {
                    "finding_id": finding_id,
                    "status": "informational",
                    "reason": "Mock council keeps placeholder findings informational.",
                }
            )
        return {
            "run_id": str(metadata["run_id"]),
            "status": "completed",
            "replies": [],
            "decisions": decisions,
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


class OpenAIProvider(BaseProvider):
    """Minimal OpenAI Responses API provider."""

    name = "openai"
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY is required for provider 'openai'")

    def generate_json(self, provider_request: ProviderRequest) -> dict[str, Any]:
        model = provider_request.model or os.environ.get("RWS_OPENAI_MODEL") or "gpt-5.5"
        body = {
            "model": model,
            "input": [
                {
                    "role": "user",
                    "content": provider_request.prompt,
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": _schema_name(provider_request.task),
                    "schema": _openai_schema(provider_request.schema),
                    "strict": True,
                }
            },
        }

        effort = os.environ.get("RWS_OPENAI_REASONING")
        if effort:
            body["reasoning"] = {"effort": effort}

        req = request.Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=120) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProviderError(f"OpenAI API error {exc.code}: {detail}") from exc
        except error.URLError as exc:
            raise ProviderError(f"OpenAI API request failed: {exc}") from exc

        text = _extract_output_text(data)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"OpenAI response did not contain parseable JSON: {text[:500]}") from exc


def provider_from_name(name: str) -> BaseProvider:
    if name == "mock":
        return MockProvider()
    if name == "openai":
        return OpenAIProvider()
    raise ProviderError(f"unknown provider {name!r}")


def load_schema(repo_root: Path, relative_path: str) -> dict[str, Any]:
    return json.loads((repo_root / relative_path).read_text(encoding="utf-8"))


def _schema_name(task: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", f"rws_{task}_output")


def _openai_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a conservative schema copy for OpenAI Structured Outputs.

    The project schemas include metadata keywords. OpenAI accepts a JSON Schema
    subset for Structured Outputs, so this strips nonessential metadata and
    local $ref values before sending the schema.
    """

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
    if isinstance(data.get("output_text"), str):
        return data["output_text"]

    chunks: list[str] = []
    for item in data.get("output", []):
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue
            if isinstance(content.get("text"), str):
                chunks.append(content["text"])
    if chunks:
        return "".join(chunks)
    raise ProviderError("OpenAI response did not include output text")
