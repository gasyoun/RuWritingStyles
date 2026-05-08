"""Hook points and sandbox boundaries for execution lifecycle."""

from __future__ import annotations

from typing import Any
import logging
import json

from .providers import ProviderRequest

logger = logging.getLogger(__name__)

class ExecutionHooks:
    """Extension points for telemetry, security, and schema manipulation."""

    @classmethod
    def pre_provider_call(cls, request: ProviderRequest) -> ProviderRequest:
        """Called before the provider API is invoked. Allows prompt modification or risk checks."""
        if cls.stop_on_risk(request):
            raise RuntimeError(f"Execution blocked by risk guardrails for task: {request.task}")
            
        # File path guardrails (prevent traversal outside workspace)
        if "../" in request.prompt or "..\\" in request.prompt:
            logger.warning("Guardrail: Potential directory traversal blocked in prompt.")
            request.prompt = request.prompt.replace("../", "[[REDACTED]]").replace("..\\", "[[REDACTED]]")
            
        return request

    @classmethod
    def post_provider_call(cls, output: dict[str, Any], request: ProviderRequest) -> dict[str, Any]:
        """Called immediately after a successful provider response."""
        return output

    @classmethod
    def post_schema_validate(cls, output: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
        """Called after output is validated against the JSON schema. Useful for repair."""
        # Simple schema repair hook: prune nulls or unknown keys if needed
        # In a real system, you would apply Pydantic/Instructor here.
        if isinstance(output, dict):
            return {k: v for k, v in output.items() if v is not None}
        return output

    @classmethod
    def pre_write_artifact(cls, artifact: dict[str, Any]) -> dict[str, Any]:
        """Called right before writing a final JSON artifact to disk."""
        # Secret redaction
        artifact_str = json.dumps(artifact)
        if "sk-" in artifact_str or "AKIA" in artifact_str:
            logger.error("Security hook: Redacting secrets from artifact before write.")
            # Simplistic redaction
            artifact_str = artifact_str.replace("sk-", "sk-[REDACTED]").replace("AKIA", "AKIA[REDACTED]")
            artifact = json.loads(artifact_str)
        return artifact

    @classmethod
    def stop_on_risk(cls, request: ProviderRequest) -> bool:
        """
        Evaluate if the request poses a security or budget risk.
        Returns True if execution should be stopped.
        """
        # Example sandbox boundary: Check if prompt contains credentials
        if "AWS_ACCESS_KEY_ID" in request.prompt or "sk-" in request.prompt:
            logger.error("Security hook: Potential credential leak detected in prompt.")
            return True
            
        # Example budget stop
        if len(request.prompt) > 200000:
            logger.error("Budget hook: Prompt length exceeds safety limit.")
            return True
            
        return False
