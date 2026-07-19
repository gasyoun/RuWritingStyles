import os
from urllib import error
from unittest.mock import patch

import pytest

from ruwritingstyles.budget import (
    BudgetAccountingError,
    BudgetController,
    BudgetError,
    BudgetExhausted,
)
from ruwritingstyles.config import BudgetMode
from ruwritingstyles.providers import _post_json_with_retries


def _mode(
    *,
    name: str = "test",
    providers=(),
    attempts: int = 4,
    tokens: int = 100,
    wall: int = 60,
    explicit: bool = False,
) -> BudgetMode:
    return BudgetMode(name, tuple(providers), attempts, tokens, wall, explicit)


def test_smoke_rejects_paid_provider_before_a_call() -> None:
    with pytest.raises(BudgetError, match="not allowed"):
        BudgetController(
            _mode(name="smoke", providers=("mock", "local")),
            provider="openai",
        )


def test_retries_and_tool_turns_each_count_as_outbound_attempts() -> None:
    controller = BudgetController(_mode(), provider="local")
    prior_attempts = os.environ.get("RWS_PROVIDER_MAX_ATTEMPTS")
    prior_delay = os.environ.get("RWS_PROVIDER_RETRY_SECONDS")
    os.environ["RWS_PROVIDER_MAX_ATTEMPTS"] = "2"
    os.environ["RWS_PROVIDER_RETRY_SECONDS"] = "0"
    try:
        with controller.logical_call():
            with patch(
                "ruwritingstyles.providers._urlopen_json_with_deadline",
                side_effect=[error.URLError("retry"), {"ok": True}],
            ):
                _post_json_with_retries(
                    provider_name="Local",
                    url="http://localhost.invalid",
                    body={},
                    headers={},
                )
            with patch(
                "ruwritingstyles.providers._urlopen_json_with_deadline",
                return_value={"ok": True},
            ):
                _post_json_with_retries(
                    provider_name="Local",
                    url="http://localhost.invalid",
                    body={},
                    headers={},
                )
        assert controller.snapshot()["consumption"]["outbound_attempts"] == 3
    finally:
        if prior_attempts is None:
            os.environ.pop("RWS_PROVIDER_MAX_ATTEMPTS", None)
        else:
            os.environ["RWS_PROVIDER_MAX_ATTEMPTS"] = prior_attempts
        if prior_delay is None:
            os.environ.pop("RWS_PROVIDER_RETRY_SECONDS", None)
        else:
            os.environ["RWS_PROVIDER_RETRY_SECONDS"] = prior_delay


def test_token_exhaustion_stops_before_the_next_call() -> None:
    controller = BudgetController(_mode(tokens=10), provider="local")
    with controller.logical_call():
        pass
    controller.record_usage({"input_tokens": 6, "output_tokens": 4, "total_tokens": 10})
    with pytest.raises(BudgetExhausted, match="token limit"):
        with controller.logical_call():
            pass


def test_wall_time_exhaustion_is_checked_before_a_call() -> None:
    now = [0.0]
    controller = BudgetController(
        _mode(wall=5), provider="local", clock=lambda: now[0]
    )
    now[0] = 5.0
    with pytest.raises(BudgetExhausted, match="wall time"):
        with controller.logical_call():
            pass


def test_paid_provider_missing_usage_fails_closed() -> None:
    controller = BudgetController(_mode(), provider="openai")
    with pytest.raises(BudgetAccountingError, match="omitted token usage"):
        controller.record_usage({})


def test_expensive_mode_requires_explicit_selection() -> None:
    mode = _mode(name="expensive", explicit=True)
    with pytest.raises(BudgetError, match="explicit opt-in"):
        BudgetController(mode, provider="mock")
    BudgetController(mode, provider="mock", explicit_opt_in=True)


def test_impossible_plan_is_rejected_before_a_call() -> None:
    with pytest.raises(BudgetError, match="requires at least 5"):
        BudgetController(
            _mode(attempts=4), provider="mock", minimum_attempts=5
        )
