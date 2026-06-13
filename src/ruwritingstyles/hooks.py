"""Hook points and sandbox boundaries for execution lifecycle."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import replace
from typing import Any

from .providers import ProviderRequest

logger = logging.getLogger(__name__)

# Patterns for known credential shapes — anchored to avoid false positives on
# legitimate Slavic/Russian text that may contain "sk-" as a morpheme prefix.
_CREDENTIAL_PATTERNS = [
    re.compile(r'sk-[A-Za-z0-9-]{20,}'),         # OpenAI / Anthropic / OpenRouter (sk-or-) / Nous (sk-nous-) keys
    re.compile(r'AKIA[A-Z0-9]{16}'),              # AWS Access Key IDs
    re.compile(r'AIza[0-9A-Za-z\\-_]{35}'),       # Google API keys
    re.compile(r'ghp_[A-Za-z0-9]{36}'),           # GitHub Personal Access Tokens
]

_PROMPT_MAX_CHARS = 200_000


def pre_provider_call(request: ProviderRequest) -> ProviderRequest:
    """Called before the provider API is invoked.

    Checks for security risks and applies prompt sanitisation.
    Raises RuntimeError if execution should be blocked.
    """
    if _stop_on_risk(request):
        raise RuntimeError(
            f"Execution blocked by risk guardrails for task '{request.task}'. "
            "Check logs for details."
        )

    # File path traversal guardrail
    if re.search(r'\.\.[/\\]', request.prompt):
        logger.warning("Guardrail: directory traversal sequence in prompt — sanitising.")
        request = replace(
            request,
            prompt=re.sub(r'\.\.[/\\]', '[[PATH_REDACTED]]', request.prompt)
        )

    return request


def post_provider_call(output: dict[str, Any], request: ProviderRequest) -> dict[str, Any]:
    """Called immediately after a successful provider response.

    Can be used for output normalisation or logging enrichment.
    Currently a pass-through; add task-specific transformations here.
    """
    return output


def post_schema_validate(output: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Called after output is validated against the JSON schema.

    NOTE: This hook intentionally does NOT prune null values, as `null` is a
    legitimate state in many schemas (e.g., `human_resolution: null` means
    "not yet resolved"). Only add repair logic here for specific, schema-level
    documented issues verified through the eval suite.
    """
    return output


def pre_write_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    """Called right before a JSON artifact is written to disk.

    Performs credential scanning and redaction on string-type leaf values only,
    to avoid corrupting structured data.
    """
    return _redact_credentials_in_tree(artifact)


def _stop_on_risk(request: ProviderRequest) -> bool:
    """Return True if the request poses a security or budget risk."""
    # Credential leak check — use anchored patterns to avoid morpheme false positives
    for pattern in _CREDENTIAL_PATTERNS:
        if pattern.search(request.prompt):
            logger.error(
                "Security hook: credential pattern '%s' detected in prompt for task '%s'.",
                pattern.pattern[:20],
                request.task,
            )
            return True

    # Budget guardrail
    if len(request.prompt) > _PROMPT_MAX_CHARS:
        logger.error(
            "Budget hook: prompt length %d exceeds safety limit %d for task '%s'.",
            len(request.prompt),
            _PROMPT_MAX_CHARS,
            request.task,
        )
        return True

    return False


def _redact_credentials_in_tree(obj: Any) -> Any:
    """Recursively redact credential strings in a JSON-like structure."""
    if isinstance(obj, dict):
        return {k: _redact_credentials_in_tree(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_credentials_in_tree(item) for item in obj]
    if isinstance(obj, str):
        redacted = obj
        for pattern in _CREDENTIAL_PATTERNS:
            if pattern.search(redacted):
                logger.warning("pre_write_artifact: redacting credential pattern in leaf value.")
                redacted = pattern.sub('[REDACTED]', redacted)
        return redacted
    return obj
