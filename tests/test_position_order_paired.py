"""H5010 — offline tests for the same-judge order-paired probe tool.

No network, no model calls: exercises the synthetic-selector controls and the
reveal mapping invariants on the frozen h073gov sheet.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import position_order_paired as pop  # noqa: E402

SHEET = json.loads(
    (Path(__file__).resolve().parents[1] / pop.SHEET_DEFAULT).read_text(encoding="utf-8")
)


def test_selftest_controls_pass():
    """Positive first-position selector detected; order-invariant selector stays invariant."""
    assert pop.selftest() == 0


def test_wilson_ci_zero_of_25_not_zero_interval():
    """Zero flips must NOT collapse to a [0,0] interval (no proof of absence)."""
    lo, hi = pop.wilson_ci(0, 25)
    assert lo == 0.0
    assert 0.10 < hi < 0.20


def test_reveal_detects_planted_flip():
    """A response pair differing on one item must surface as discordant."""
    tasks, mapping = pop.build_tasks(SHEET, seed=pop.SEED)
    responses = pop.synthetic_responses(tasks, SHEET, pop.selector_content_identity)
    result = pop.reveal(tasks, mapping, responses, SHEET)
    assert result["discordant_pairs"] == 0
    # flip exactly one item's caught verdict in one condition
    victim = mapping[0]
    for r in responses:
        if r["task"] == victim["task"]:
            r["caught"] = "no" if r["caught"] != "no" else "yes"
            break
    result2 = pop.reveal(tasks, mapping, responses, SHEET)
    assert result2["discordant_pairs"] == 1
    assert result2["discordant_runs"] == [victim["run"]]


def test_reveal_flags_malformed_and_missing():
    """Malformed verdicts are counted as invalid, never silently scored."""
    tasks, mapping = pop.build_tasks(SHEET, seed=pop.SEED)
    responses = pop.synthetic_responses(tasks, SHEET, pop.selector_content_identity)
    responses[0]["caught"] = "maybe"  # not in rubric vocabulary
    result = pop.reveal(tasks, mapping, responses[:-1], SHEET)
    reasons = {i["reason"] for i in result["invalid"]}
    assert "malformed_verdict" in reasons
    assert "missing_response" in reasons
    # malformed run and response-less run each additionally surface as an
    # incomplete pair ("missing_condition"): 2 task-level + 2 pair-level
    assert result["n_invalid"] == 4


def test_prep_task_count_and_blinding():
    """25 items x 2 orders = 50 tasks; identity fields stripped from presentation."""
    tasks, mapping = pop.build_tasks(SHEET, seed=pop.SEED)
    assert len(tasks) == 50 and len(mapping) == 50
    identity_fields = {"id", "style_id", "council_status"}
    for t in tasks:
        for f in t["findings"]:
            assert not (identity_fields & set(f))
        assert [f["position"] for f in t["findings"]] == list(
            range(1, len(t["findings"]) + 1)
        )
