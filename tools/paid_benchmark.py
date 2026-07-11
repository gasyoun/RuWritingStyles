"""Paid DeepSeek benchmark driver (H072 Phase B1).

Protocol (author-approved 03-07-2026):
  - 5 GOLD_SANSKRIT non-deterministic cases x N=5 on deepseek-chat (-> v4-flash)
  - the same 5 cases x N=3 on deepseek-v4-pro (the genuinely heavier route;
    deepseek-reasoner is now aliased to v4-flash, so it is NOT a distinct model)
  - a temperature=0 reproducibility probe: 2 runs of one case, compare artifacts

Writes scratch/benchmark_summary.json for docs/benchmark.md.
Run in background: python scratch/paid_benchmark.py
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dotenv import load_dotenv

load_dotenv()

from ruwritingstyles.evals import run_eval_repeat  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLD = [
    "sanskrit-pseudo-etymology",
    "karaka-not-padezh",
    "vedic-classical-anachronism",
    "samasa-misclassification",
    "commentary-layer-mix",
]


def _clean(agg_id: str) -> None:
    runs = REPO_ROOT / "runs"
    for path in runs.glob(f"{agg_id}*"):
        shutil.rmtree(path, ignore_errors=True)


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run_group(label: str, model: str | None, repeat: int) -> list[dict]:
    cases = []
    for case_id in GOLD:
        agg_id = f"gold-{label}-{case_id}"
        existing = REPO_ROOT / "runs" / agg_id / "eval-aggregate.json"
        if existing.exists():
            # Resume: keep a completed aggregate from an interrupted batch.
            case = json.loads(existing.read_text(encoding="utf-8"))["cases"][0]
            cases.append(case)
            _log(f"{label} N={repeat} :: {case_id} — already done, reusing aggregate")
            continue
        _log(f"{label} N={repeat} :: {case_id} ...")
        t = time.time()
        result = None
        for attempt in (1, 2):  # one whole-case retry on an unexpected crash
            _clean(agg_id)
            try:
                result = run_eval_repeat(
                    repo_root=REPO_ROOT,
                    case_id=case_id,
                    provider_name="deepseek",
                    model=model,
                    repeat=repeat,
                    aggregate_id=agg_id,
                )
                break
            except Exception as exc:
                _log(f"  attempt {attempt} crashed: {type(exc).__name__}: {exc}")
                if attempt == 2:
                    raise
        case = result.data["cases"][0]
        cases.append(case)
        _log(
            f"  done {case_id}: pass {case['pass_count']}/{repeat} "
            f"det {case['detection_count']}/{repeat} "
            f"char {case['metrics']['char_delta_ratio']['mean']}+-{case['metrics']['char_delta_ratio']['stdev']} "
            f"({time.time()-t:.0f}s)"
        )
    return cases


def temp_probe() -> dict:
    case_id = "karaka-not-padezh"
    agg_id = "gold-tempprobe"
    existing = REPO_ROOT / "runs" / agg_id / "eval-aggregate.json"
    if existing.exists():
        _log("temperature=0 probe — already done, recomputing from existing runs")
        data = json.loads(existing.read_text(encoding="utf-8"))
        return _probe_from_runs(case_id, data["cases"][0]["runs"])
    _clean(agg_id)
    os.environ["RWS_DEEPSEEK_TEMPERATURE"] = "0"
    _log("temperature=0 probe (2 runs of karaka-not-padezh) ...")
    try:
        result = run_eval_repeat(
            repo_root=REPO_ROOT,
            case_id=case_id,
            provider_name="deepseek",
            model=None,
            repeat=2,
            aggregate_id=agg_id,
        )
    finally:
        os.environ.pop("RWS_DEEPSEEK_TEMPERATURE", None)
    return _probe_from_runs(case_id, result.data["cases"][0]["runs"])


def _probe_from_runs(case_id: str, runs: list[dict]) -> dict:
    r1 = REPO_ROOT / runs[0]["run_dir"]
    r2 = REPO_ROOT / runs[1]["run_dir"]

    def _read(p):
        f = p / "revised.md"
        return f.read_text(encoding="utf-8") if f.exists() else None

    def _ftypes(p):
        f = p / "eval-result.json"
        return sorted(json.loads(f.read_text(encoding="utf-8"))["finding_types"]) if f.exists() else None

    revised_identical = _read(r1) == _read(r2) and _read(r1) is not None
    findings_identical = _ftypes(r1) == _ftypes(r2)
    probe = {
        "case_id": case_id,
        "temperature": 0,
        "revised_md_identical": revised_identical,
        "finding_types_identical": findings_identical,
        "run1_finding_types": _ftypes(r1),
        "run2_finding_types": _ftypes(r2),
        "run1_char_delta": runs[0]["char_delta_ratio"],
        "run2_char_delta": runs[1]["char_delta_ratio"],
    }
    _log(f"  probe: revised_identical={revised_identical} findings_identical={findings_identical}")
    return probe


def main() -> None:
    summary: dict = {"started": time.strftime("%Y-%m-%d %H:%M:%S")}
    summary["temp_probe"] = temp_probe()
    summary["flash"] = {"model": "deepseek-chat", "resolves_to": "deepseek-v4-flash", "repeat": 5,
                        "cases": run_group("flash", None, 5)}
    # ONE comparison pass per the handoff's sanctioned matrix (case 1 already
    # completed at N=3 before the scope correction and is reused as-is).
    summary["pro"] = {"model": "deepseek-v4-pro", "repeat": 1,
                      "cases": run_group("pro", "deepseek-v4-pro", 1)}
    summary["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    out = REPO_ROOT / "scratch" / "benchmark_summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _log(f"WROTE {out}")


if __name__ == "__main__":
    main()
