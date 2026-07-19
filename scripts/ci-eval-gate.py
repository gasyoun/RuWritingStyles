#!/usr/bin/env python3
"""Run the committed mock eval regression gate.

Compilation, repository validation, unit tests, and frontend builds are separate
CI jobs.  This wrapper has one source of truth: the exit status of
``rws eval-regression`` against ``evals/baselines/gold.json``.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD_BASELINE = REPO_ROOT / "evals" / "baselines" / "gold.json"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    if not GOLD_BASELINE.exists():
        print(f"error: missing committed eval baseline: {GOLD_BASELINE}", file=sys.stderr)
        return 1

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruwritingstyles.cli",
            "eval-regression",
            "--baseline",
            str(GOLD_BASELINE),
            "--provider",
            "mock",
        ],
        cwd=REPO_ROOT,
        env=env,
        encoding="utf-8",
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
