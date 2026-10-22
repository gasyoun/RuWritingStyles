"""H6845 — offline tests for tools/judge_bias_calibration.py (no model calls)."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "tools" / "judge_bias_calibration.py"


def run_tool(*args):
    return subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True, cwd=REPO)


def test_selftest_pass():
    r = run_tool("selftest")
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["selftest"] == "PASS"


def test_addendum_recompute_matches_committed_analysis():
    r = run_tool("recompute-addendum")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "parity=PASS" in r.stdout
    assert "discordant=0/25" in r.stdout
    assert "wilson=[0.0, 0.133192]" in r.stdout


def test_length_correlation_matches_h4658_axes():
    r = run_tool("length-correlation")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "parity=PASS (18 axes compared)" in r.stdout
    assert "'rho': 0.3821" in r.stdout


def test_self_preference_fails_closed_on_real_artifacts():
    r = run_tool("self-preference",
                 "--records", "evals/annotation/raterB-h073gov.json",
                 "--judge", "glm-5.3-flash", "--perms", "500")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "UNMEASURED" in r.stdout


def test_wilson_95_known_values():
    sys.path.insert(0, str(TOOL.parent))
    import judge_bias_calibration as jbc
    assert jbc.wilson95(0, 25) == [0.0, 0.133192]
    assert jbc.wilson95(3, 5)[0] > 0.2
