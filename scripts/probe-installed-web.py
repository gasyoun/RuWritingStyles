#!/usr/bin/env python3
"""Start an installed RWS Web Studio, probe it, and stop it cleanly."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen


sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    env = os.environ.copy()
    env["RWS_WORKSPACE"] = str(args.workspace.resolve())
    env.setdefault("RWS_OFFLINE", "1")
    process = subprocess.Popen(
        [sys.executable, "-m", "ruwritingstyles.cli", "web"],
        cwd=args.workspace,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    deadline = time.monotonic() + args.timeout
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise RuntimeError(
                    f"Web Studio exited with {process.returncode}\n{stdout}\n{stderr}"
                )
            try:
                with urlopen("http://127.0.0.1:8000/status", timeout=2) as response:
                    if response.status != 200:
                        raise RuntimeError(f"status endpoint returned {response.status}")
                with urlopen("http://127.0.0.1:8000/", timeout=2) as response:
                    body = response.read().decode("utf-8")
                    if response.status != 200 or '<div id="root">' not in body:
                        raise RuntimeError("bundled SPA probe failed")
                print("installed Web Studio: status and SPA probes passed")
                return 0
            except URLError:
                time.sleep(0.25)
        raise TimeoutError("installed Web Studio did not become ready")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
