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
    if GOLD_BASELINE.exists():
        print(f"       GOLD MODE: comparing against {GOLD_BASELINE.name}")
        result = _run(
            [
                sys.executable, "-m", "ruwritingstyles.cli",
                "eval-regression",
                "--baseline", str(GOLD_BASELINE),
                "--provider", "mock",
                "--strict",
            ],
            cwd=REPO_ROOT / "src",
            check=False,
        )
        if "regressed: 0" not in result.stdout:
            print("       FAIL: Regressions detected vs gold baseline!")
            print(result.stdout[-2000:])
            sys.exit(1)
        print("       OK: zero regressions vs gold baseline")
    else:
        print("       SMOKE MODE: no gold baseline — promoting ci_mock and self-comparing")
        _run(
            [
                sys.executable, "-m", "ruwritingstyles.cli",
                "eval-promote", str(suite_result_path), "--tag", "ci_mock",
            ],
            cwd=REPO_ROOT / "src",
        )
        result = _run(
            [
                sys.executable, "-m", "ruwritingstyles.cli",
                "eval-regression",
                "--baseline", str(REPO_ROOT / "evals" / "baselines" / "ci_mock.json"),
                "--provider", "mock",
            ],
            cwd=REPO_ROOT / "src",
            check=False,
        )
        if "regressed: 0" not in result.stdout:
            print("       FAIL: Unexpected regression in smoke self-comparison!")
            print(result.stdout[-2000:])
            sys.exit(1)
        print("       OK: zero regressions (smoke mode)")
        print("       TIP: Run `rws eval-suite --provider google --execute` then")
        print("            `rws eval-promote <result> --tag gold` to activate GOLD MODE.")


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
    mode = "GOLD" if GOLD_BASELINE.exists() else "SMOKE"
    print(f"=== RuWritingStyles CI Gate [{mode} MODE] ===\n")

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
