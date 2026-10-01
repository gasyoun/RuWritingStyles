"""H5010 offline controls for the position-pair analysis tool (no model calls).

Run: python -m pytest tests/test_position_bias_pair.py -q
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "position_bias_pair", REPO / "tools" / "position_bias_pair.py"
)
assert _spec is not None and _spec.loader is not None
pbp = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("position_bias_pair", pbp)
_spec.loader.exec_module(pbp)


def test_selftest_positive_and_negative_controls():
    """Positive: known first-position selector is detected. Negative: order-invariant judge stays invariant."""
    assert pbp.selftest() == 0


def test_wilson_zero_flips_bounds():
    """0/25 must give a bounded upper interval, not proof of absence."""
    p, lo, hi = pbp.wilson(0, 25)
    assert p == 0.0 and lo == 0.0
    assert 0.10 < hi < 0.15  # ~0.133 for n=25, z=1.96


def test_pair_stats_discordance_axes():
    a = {"caught": "yes", "type_correct": True, "false_positives": 1}
    b = {"caught": "no", "type_correct": False, "false_positives": 3}
    st = pbp.pair_stats(a, b)
    # yes -> no jumps two levels: any-flip True, adjacent-level flip False by definition
    assert st["caught_any_flip"] and not st["caught_adjacent_flip"] and st["type_correct_flip"]
    assert st["fp_delta"] == 2 and st["fp_flip"]
    part = {"caught": "partial", "type_correct": True, "false_positives": 1}
    adj = pbp.pair_stats(a, part)
    assert adj["caught_any_flip"] and adj["caught_adjacent_flip"] and not adj["type_correct_flip"]
    same = pbp.pair_stats(a, a)
    assert not any(same[k] for k in ("caught_any_flip", "caught_adjacent_flip", "type_correct_flip", "fp_flip"))
