"""H1213 GOLD_DICTIONARY benchmark driver (register style-card eval).

Protocol (mirrors tools/paid_benchmark.py --h770 configuration):
  - 8 GOLD_DICTIONARY expert cases x N=5 on deepseek with production
    model_policy.yml routing (--routes): style_review/synthesis on
    deepseek-chat (= deepseek-v4-flash), council/verification on
    deepseek-v4-pro. N3 style commitments ON (default).
  - resumable per-case: a completed runs/h1213dict-<case>/eval-aggregate.json
    is reused, so a crashed batch continues where it stopped.

Writes scratch/h1213_dict_summary.json for docs/benchmark.md.
Run: PYTHONPATH=src python scratch/h1213_dict_benchmark.py
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dotenv import load_dotenv

load_dotenv(REPO_ROOT / ".env")

from ruwritingstyles.evals import run_eval_repeat  # noqa: E402

CASES = [
    "dict-circular-gloss",
    "dict-publicistic-register",
    "dict-zone-order",
    "dict-nonstandard-label",
    "dict-grammar-zone",
    "dict-synonym-heap",
    "dict-encyclopedic-gloss",
    "dict-pseudo-etymology-note",
]
REPEAT = 5
PREFIX = "h1213dict"


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _clean(agg_id: str) -> None:
    runs = REPO_ROOT / "runs"
    for path in runs.glob(f"{agg_id}*"):
        shutil.rmtree(path, ignore_errors=True)


def main() -> None:
    rows = []
    t0 = time.time()
    for case_id in CASES:
        agg_id = f"{PREFIX}-{case_id}"
        existing = REPO_ROOT / "runs" / agg_id / "eval-aggregate.json"
        if existing.exists():
            case = json.loads(existing.read_text(encoding="utf-8"))["cases"][0]
            rows.append(case)
            _log(f"{case_id} — already done, reusing aggregate")
            continue
        _log(f"{case_id} N={REPEAT} ...")
        t = time.time()
        result = None
        for attempt in (1, 2):
            _clean(agg_id)
            try:
                result = run_eval_repeat(
                    repo_root=REPO_ROOT,
                    case_id=case_id,
                    provider_name="deepseek",
                    model=None,
                    repeat=REPEAT,
                    aggregate_id=agg_id,
                    use_routes=True,
                )
                break
            except Exception as exc:  # noqa: BLE001
                _log(f"  attempt {attempt} crashed: {type(exc).__name__}: {exc}")
                if attempt == 2:
                    raise
        case = result.data["cases"][0]
        rows.append(case)
        _log(
            f"  done {case_id}: pass {case['pass_count']}/{REPEAT} "
            f"det {case['detection_count']}/{REPEAT} ({time.time()-t:.0f}s)"
        )

    total_pass = sum(c["pass_count"] for c in rows)
    total_det = sum(c["detection_count"] for c in rows)
    n = REPEAT * len(rows)
    summary = {
        "protocol": "H1213 GOLD_DICTIONARY x N=5, deepseek routed (--routes)",
        "prefix": PREFIX,
        "cases": rows,
        "totals": {
            "runs": n,
            "pass": total_pass,
            "pass_rate": round(total_pass / n, 3),
            "detection": total_det,
            "detection_rate": round(total_det / n, 3),
        },
    }
    out = REPO_ROOT / "scratch" / "h1213_dict_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _log(f"summary -> {out} (pass {total_pass}/{n}, det {total_det}/{n}, {time.time()-t0:.0f}s total)")


if __name__ == "__main__":
    main()
