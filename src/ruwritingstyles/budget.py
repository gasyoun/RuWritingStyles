"""Fail-closed provider attempt, token and wall-time budgets."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Any, Callable, Iterator

from .config import BudgetMode


PAID_PROVIDERS = frozenset({"openai", "google", "anthropic", "openrouter", "deepseek"})


class BudgetError(RuntimeError):
    """Base class for budget policy failures."""


class BudgetExhausted(BudgetError):
    """Raised before an outbound attempt that would exceed a limit."""


class BudgetAccountingError(BudgetError):
    """Raised when a paid provider omits token accounting."""


@dataclass
class _CallState:
    controller: "BudgetController"
    first_http_attempt: bool = True


_ACTIVE_CALL: ContextVar[_CallState | None] = ContextVar("rws_budget_call", default=None)


class BudgetController:
    def __init__(
        self,
        mode: BudgetMode,
        *,
        provider: str,
        explicit_opt_in: bool = False,
        minimum_attempts: int = 1,
        persist: Callable[[dict[str, Any]], None] | None = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.mode = mode
        self.provider = provider
        self._persist = persist
        self._clock = clock
        self._started = clock()
        self._attempts = 0
        self._input_tokens = 0
        self._output_tokens = 0
        self._total_tokens = 0
        # H5071: tokens attributed per actually-served route, not just the
        # requested provider — a fallback serves usage through another route.
        self._served_routes: dict[str, int] = {}
        self._exhaustion_reason: str | None = None
        self._lock = RLock()

        if mode.explicit_selection_required and not explicit_opt_in:
            raise BudgetError(
                f"budget mode {mode.name!r} requires explicit opt-in"
            )
        if mode.providers and provider not in mode.providers:
            raise BudgetError(
                f"provider {provider!r} is not allowed by budget mode {mode.name!r}"
            )
        if minimum_attempts > mode.max_outbound_attempts:
            raise BudgetError(
                f"step plan requires at least {minimum_attempts} provider attempts, "
                f"but budget mode {mode.name!r} allows {mode.max_outbound_attempts}"
            )
        self._save()

    @contextmanager
    def logical_call(self) -> Iterator[None]:
        self._before_attempt()
        token: Token[_CallState | None] = _ACTIVE_CALL.set(_CallState(self))
        try:
            yield
        finally:
            _ACTIVE_CALL.reset(token)

    def _before_attempt(self) -> None:
        with self._lock:
            elapsed = self._clock() - self._started
            reason = self._exhaustion_reason
            if reason is None and elapsed >= self.mode.max_wall_seconds:
                reason = f"wall time limit exhausted ({self.mode.max_wall_seconds}s)"
            if reason is None and self._attempts >= self.mode.max_outbound_attempts:
                reason = (
                    "outbound attempt limit exhausted "
                    f"({self.mode.max_outbound_attempts})"
                )
            if reason is None and self._total_tokens >= self.mode.max_tokens:
                reason = f"token limit exhausted ({self.mode.max_tokens})"
            if reason is not None:
                self._exhaustion_reason = reason
                self._save()
                raise BudgetExhausted(reason)
            self._attempts += 1
            self._save()

    def record_usage(self, usage: dict[str, Any], served_by: str | None = None) -> None:
        """Record token usage; ``served_by`` names the actually-served route
        ("provider/model", H5071) when known, so fallback-served usage shows up
        under its own route instead of the requested provider's name."""
        input_tokens = _nonnegative_int(usage.get("input_tokens"))
        output_tokens = _nonnegative_int(usage.get("output_tokens"))
        total_tokens = _nonnegative_int(usage.get("total_tokens"))
        if total_tokens == 0:
            total_tokens = input_tokens + output_tokens
        if self.provider in PAID_PROVIDERS and total_tokens <= 0:
            self._exhaustion_reason = (
                f"paid provider {self.provider!r} omitted token usage"
            )
            self._save()
            raise BudgetAccountingError(self._exhaustion_reason)
        with self._lock:
            self._input_tokens += input_tokens
            self._output_tokens += output_tokens
            self._total_tokens += total_tokens
            route = served_by or self.provider
            self._served_routes[route] = self._served_routes.get(route, 0) + total_tokens
            if self._total_tokens >= self.mode.max_tokens:
                self._exhaustion_reason = f"token limit exhausted ({self.mode.max_tokens})"
            self._save()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "mode": self.mode.name,
                "provider": self.provider,
                "limits": {
                    "outbound_attempts": self.mode.max_outbound_attempts,
                    "tokens": self.mode.max_tokens,
                    "wall_seconds": self.mode.max_wall_seconds,
                },
                "consumption": {
                    "outbound_attempts": self._attempts,
                    "input_tokens": self._input_tokens,
                    "output_tokens": self._output_tokens,
                    "total_tokens": self._total_tokens,
                    "wall_seconds": round(max(0.0, self._clock() - self._started), 3),
                    "served_routes": dict(sorted(self._served_routes.items())),
                },
                "exhaustion_reason": self._exhaustion_reason,
            }

    def _save(self) -> None:
        if self._persist is not None:
            self._persist(self.snapshot())


def before_http_attempt() -> None:
    """Count retries and additional tool-loop turns inside a logical call."""

    state = _ACTIVE_CALL.get()
    if state is None:
        return
    if state.first_http_attempt:
        state.first_http_attempt = False
        return
    state.controller._before_attempt()


def generate_with_budget(provider: Any, provider_request: Any) -> Any:
    """Execute one logical provider turn under its attached controller."""

    controller = provider.budget_controller()
    if controller is None:
        return provider.generate_json(provider_request)
    with controller.logical_call():
        result = provider.generate_json(provider_request)
    # H5071: attribute the usage to the actually-served route, so a
    # provider-level fallback (e.g. DeepSeek 402 → OpenRouter) is visible in
    # budget accounting rather than silently billed to the requested provider.
    served_by = None
    provenance = provider.last_call_provenance() if hasattr(provider, "last_call_provenance") else {}
    if provenance.get("actual_provider"):
        served_by = f"{provenance['actual_provider']}/{provenance.get('actual_model') or ''}"
    controller.record_usage(provider.last_usage(), served_by=served_by)
    return result


def _nonnegative_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    return 0
