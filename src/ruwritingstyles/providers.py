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


class MockProvider(BaseProvider):
    """Deterministic provider for local development and tests."""

    name = "mock"

    def effective_model(self, provider_request: ProviderRequest) -> str:
        return provider_request.model or "mock"

    def generate_json(self, provider_request: ProviderRequest) -> dict[str, Any]:
        self._set_retry_telemetry(ProviderRetryTelemetry())
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
        if task == "assessment":
            return self._assessment(metadata)
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

    def _assessment(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": str(metadata["run_id"]),
            "status": "completed",
            "assessments": [],
        }


class OpenAIProvider(BaseProvider):
    """Minimal OpenAI Responses API provider."""

    name = "openai"
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY is required for provider 'openai'")

    def effective_model(self, provider_request: ProviderRequest) -> str:
        return provider_request.model or os.environ.get("RWS_OPENAI_MODEL") or "gpt-5.5"

    def generate_json(self, provider_request: ProviderRequest) -> dict[str, Any]:
        model = self.effective_model(provider_request)
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
                    "schema": _provider_schema(provider_request.schema),
                    "strict": True,
                }
            },
        }

        effort = os.environ.get("RWS_OPENAI_REASONING")
        if effort:
            body["reasoning"] = {"effort": effort}

        telemetry = ProviderRetryTelemetry()
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

        text = _extract_output_text(data)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"OpenAI response did not contain parseable JSON: {text[:500]}") from exc


class GoogleProvider(BaseProvider):
    """Minimal Google Gemini API provider."""

    name = "google"
    endpoint_template = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ProviderError("GEMINI_API_KEY or GOOGLE_API_KEY is required for provider 'google'")

    def effective_model(self, provider_request: ProviderRequest) -> str:
        return provider_request.model or os.environ.get("RWS_GOOGLE_MODEL") or "gemini-3.1-pro-preview"

    def generate_json(self, provider_request: ProviderRequest) -> dict[str, Any]:
        model = self.effective_model(provider_request)
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": provider_request.prompt}],
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseJsonSchema": _provider_schema(provider_request.schema),
            },
        }

        telemetry = ProviderRetryTelemetry()
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

        text = _extract_gemini_text(data)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Google Gemini response did not contain parseable JSON: {text[:500]}") from exc


class AnthropicProvider(BaseProvider):
    """Minimal Anthropic Messages API provider."""

    name = "anthropic"
    endpoint = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ProviderError("ANTHROPIC_API_KEY is required for provider 'anthropic'")

    def effective_model(self, provider_request: ProviderRequest) -> str:
        return provider_request.model or os.environ.get("RWS_ANTHROPIC_MODEL") or "claude-sonnet-4-6"

    def generate_json(self, provider_request: ProviderRequest) -> dict[str, Any]:
        model = self.effective_model(provider_request)
        max_tokens = int(os.environ.get("RWS_ANTHROPIC_MAX_TOKENS", "8192"))
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": provider_request.prompt,
                }
            ],
            "output_config": {
                "format": {
                    "type": "json_schema",
                    "schema": _provider_schema(provider_request.schema),
                }
            },
        }

        telemetry = ProviderRetryTelemetry()
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

        text = _extract_anthropic_text(data)
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Anthropic response did not contain parseable JSON: {text[:500]}") from exc


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

        # OpenRouter returns standard OpenAI chat completion format
        if "choices" not in data or not data["choices"]:
            raise ProviderError(f"OpenRouter response missing choices: {data}")
            
        text = data["choices"][0]["message"]["content"]
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ProviderError(f"OpenRouter response did not contain parseable JSON: {text[:500]}") from exc


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
    raise ProviderError(f"unknown provider {name!r}")


def load_schema(repo_root: Path, relative_path: str) -> dict[str, Any]:
    return json.loads((repo_root / relative_path).read_text(encoding="utf-8"))


def _schema_name(task: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", f"rws_{task}_output")


def _provider_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a conservative schema copy for provider structured outputs.

    The project schemas include metadata keywords and local references. Provider
    structured-output features accept JSON Schema subsets, so this strips
    nonessential metadata and local $ref values before sending the schema.
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


def _extract_gemini_text(data: dict[str, Any]) -> str:
    chunks: list[str] = []
    for candidate in data.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content")
        if not isinstance(content, dict):
            continue
        for part in content.get("parts", []):
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                chunks.append(part["text"])
    if chunks:
        return "".join(chunks)
    raise ProviderError("Google Gemini response did not include output text")


def _extract_anthropic_text(data: dict[str, Any]) -> str:
    chunks: list[str] = []
    for content in data.get("content", []):
        if isinstance(content, dict) and isinstance(content.get("text"), str):
            chunks.append(content["text"])
    if chunks:
        return "".join(chunks)
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
        req = request.Request(
            url,
            data=encoded,
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            last_error = ProviderError(f"{provider_name} API error {exc.code}: {detail}")
            if not _is_retryable_status(exc.code) or attempt == attempts:
                raise last_error from exc
            sleep_for = _retry_delay_from_headers(exc.headers, delay)
            if telemetry is not None:
                telemetry.record(str(exc.code), sleep_for)
        except error.URLError as exc:
            last_error = ProviderError(f"{provider_name} API request failed: {exc}")
            if attempt == attempts:
                raise last_error from exc
            if telemetry is not None:
                telemetry.record("url_error", sleep_for)

        time.sleep(sleep_for)
        delay *= 2

    raise last_error or ProviderError(f"{provider_name} API request failed")


def _provider_attempt_count() -> int:
    raw = os.environ.get("RWS_PROVIDER_MAX_ATTEMPTS", "3")
    try:
        return max(1, int(raw))
    except ValueError:
        return 3


def _provider_retry_delay() -> float:
    raw = os.environ.get("RWS_PROVIDER_RETRY_SECONDS", "1.0")
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 1.0


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
    value = headers.get(name)
    if value is not None:
        return str(value)
    lower_name = name.lower()
    if isinstance(headers, dict):
        for key, item in headers.items():
            if str(key).lower() == lower_name:
                return str(item)
    return None
