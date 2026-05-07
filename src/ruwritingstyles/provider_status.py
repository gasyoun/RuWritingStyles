"""Provider readiness checks for real API execution."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping


@dataclass(frozen=True)
class ProviderStatus:
    """Configuration readiness for one provider."""

    provider: str
    ready: bool
    model: str
    api_key_env: tuple[str, ...]
    configured_env: str
    missing_env: tuple[str, ...]


def provider_statuses(env: Mapping[str, str] | None = None) -> tuple[ProviderStatus, ...]:
    """Return readiness for all supported providers without exposing secrets."""

    actual_env = env or os.environ
    return (
        _status(
            provider="mock",
            api_key_env=(),
            model=_env(actual_env, "RWS_MOCK_MODEL") or "mock",
            env=actual_env,
        ),
        _status(
            provider="openai",
            api_key_env=("OPENAI_API_KEY",),
            model=_env(actual_env, "RWS_OPENAI_MODEL") or "gpt-5.5",
            env=actual_env,
        ),
        _status(
            provider="google",
            api_key_env=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
            model=_env(actual_env, "RWS_GOOGLE_MODEL") or "gemini-3.1-pro-preview",
            env=actual_env,
        ),
        _status(
            provider="anthropic",
            api_key_env=("ANTHROPIC_API_KEY",),
            model=_env(actual_env, "RWS_ANTHROPIC_MODEL") or "claude-sonnet-4-6",
            env=actual_env,
        ),
    )


def render_provider_statuses(statuses: tuple[ProviderStatus, ...], provider: str | None = None) -> str:
    """Render provider readiness for CLI output."""

    selected = tuple(status for status in statuses if provider is None or status.provider == provider)
    if not selected:
        return "no provider matched"

    lines: list[str] = []
    for status in selected:
        configured = status.configured_env or "-"
        missing = ", ".join(status.missing_env) if status.missing_env else "-"
        ready = "yes" if status.ready else "no"
        lines.append(status.provider)
        lines.append(f"  ready: {ready}")
        lines.append(f"  model: {status.model}")
        lines.append(f"  configured_env: {configured}")
        lines.append(f"  missing_env: {missing}")
    return "\n".join(lines)


def _status(
    *,
    provider: str,
    api_key_env: tuple[str, ...],
    model: str,
    env: Mapping[str, str],
) -> ProviderStatus:
    configured = next((name for name in api_key_env if _env(env, name)), "")
    ready = provider == "mock" or bool(configured)
    missing = () if ready else api_key_env
    return ProviderStatus(
        provider=provider,
        ready=ready,
        model=model,
        api_key_env=api_key_env,
        configured_env=configured,
        missing_env=missing,
    )


def _env(env: Mapping[str, str], name: str) -> str:
    return str(env.get(name) or "").strip()
