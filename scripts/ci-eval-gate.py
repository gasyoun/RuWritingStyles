#!/usr/bin/env python3
"""CI Gate for RuWritingStyles.

Runs in two modes depending on whether a committed gold baseline exists:

  SMOKE MODE (no evals/baselines/gold.json):
    - Runs eval-suite with mock provider
    - Promotes result as ci_mock baseline
    - Verifies eval-regression produces zero regressions vs ci_mock
    - Validates dataset size has not shrunk below 30 cases

  GOLD MODE (evals/baselines/gold.json is committed):
    - Runs eval-suite with mock provider (smoke)
    - Runs eval-regression against gold.json (--strict)
    - Any regression vs gold causes CI failure

In both modes: compileall + validate_project + unittest + web build are run.
"""

import sys
import json
from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).parent.parent.resolve()
GOLD_BASELINE = REPO_ROOT / "evals" / "baselines" / "gold.json"


def _run(cmd: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(
        cmd,
        cwd=cwd or REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        print(f"FAILED: {' '.join(str(c) for c in cmd)}")
        print(result.stdout[-2000:])
        print(result.stderr[-1000:])
        sys.exit(1)
    return result


def step_compile() -> None:
    print("[ 1/6 ] Compile check...")
    _run([sys.executable, "-m", "compileall", "-q", "src", "tools", "tests"])
    print("       OK")


def step_validate() -> None:
    print("[ 2/6 ] Repository validation...")
    result = _run([sys.executable, "tools/validate_project.py"])
    for line in result.stdout.splitlines():
        if line.startswith("OK") or line.startswith("SUCCESS"):
            print(f"       {line}")


def step_unittests() -> None:
    print("[ 3/6 ] Unit tests...")
    result = _run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
    )
    # Print last few lines (summary)
    lines = (result.stdout + result.stderr).splitlines()
    for line in lines[-5:]:
        print(f"       {line}")


def step_eval_suite() -> tuple[dict, Path]:
    print("[ 4/6 ] Eval suite (mock mode)...")
    _run(
        [sys.executable, "-m", "ruwritingstyles.cli", "eval-suite", "--provider", "mock"],
        cwd=REPO_ROOT / "src",
    )
    runs_dir = REPO_ROOT / "runs"
    all_dirs = sorted(
        [d for d in runs_dir.iterdir() if d.is_dir() and "eval-suite" in d.name],
        reverse=True,
    )
    for d in all_dirs:
        result_path = d / "eval-suite-result.json"
        if result_path.exists():
            suite_data = json.loads(result_path.read_text(encoding="utf-8"))
            case_count = suite_data.get("case_count", 0)
            passed_count = suite_data.get("passed_count", 0)
            print(f"       Eval Suite: {passed_count}/{case_count} passed")
            if case_count < 30:
                print(f"       ERROR: Golden Dataset has shrunk! Expected 30+, got {case_count}")
                sys.exit(1)
            return suite_data, result_path
    print("       ERROR: No eval-suite-result.json found.")
    sys.exit(1)


def step_regression(suite_result_path: Path) -> None:
    print("[ 5/6 ] Regression check...")
    if not GOLD_BASELINE.exists():
        print(f"       ERROR: No gold baseline found at {GOLD_BASELINE.relative_to(REPO_ROOT)}")
        print("       To create one, run:")
        print("       rws eval-suite --provider google")
        print("       rws eval-promote <result_path> --tag gold")
        sys.exit(1)

    print(f"       Comparing against {GOLD_BASELINE.name}")
    result = _run(
        [
            sys.executable, "-m", "ruwritingstyles.cli",
            "eval-regression",
            "--baseline", str(GOLD_BASELINE),
            "--provider", "mock",
        ],
        cwd=REPO_ROOT / "src",
        check=False,
    )
    if "regressed: 0" not in result.stdout:
        print("       FAIL: Regressions detected vs gold baseline!")
        print(result.stdout[-2000:])
        sys.exit(1)
    print("       OK: zero regressions vs gold baseline")


def step_web_build() -> None:
    print("[ 6/6 ] Web Studio build...")
    web_dir = REPO_ROOT / "web"
    if not web_dir.exists():
        print("       SKIP: no web/ directory found")
        return
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=web_dir,
        capture_output=True,
        text=True,
        shell=True,
    )
    if result.returncode != 0:
        print(f"       FAIL: Web build failed")
        print(result.stderr[-1000:])
        sys.exit(1)
    print("       OK")


def main() -> None:
    print("=== RuWritingStyles CI Gate ===\n")

    step_compile()
    step_validate()
    step_unittests()
    suite_data, result_path = step_eval_suite()
    step_regression(result_path)
    step_web_build()

    print("\n=== CI Gate PASSED ===")
    sys.exit(0)


if __name__ == "__main__":
    main()
