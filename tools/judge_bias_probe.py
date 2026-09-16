#!/usr/bin/env python3
"""LLM-judge bias probes over the frozen gold annotation corpus (H4658, 14-09-2026).

Two probes over the SAME 25-run artifact set (evals/annotation/sheet-h073gov.json,
5 gold cases x 5 repeats, deepseek provider):

1. Length-bias probe (fully mechanical): correlates the judge's answer length
   (total findings text, chars and words) with every available score axis
   (rater A mechanical detection, scorer verification status, rater B caught /
   type_correct). If high scores systematically track long answers, the rubric
   needs revision; this tool reports the correlations and flags them.

2. Position-swap probe: a bounded re-judge pass (rater C) over the SAME corpus
   with the candidate findings list REVERSED (positions renumbered, scorer
   verdicts withheld), compared against rater B's original-order verdicts.
   Reports the verdict-flip rate; every flip is routed to human adjudication
   per evals/GOLD_PROTOCOL.md (the tool never adjudicates).

Design disclosure (carried into every report): the swap comparison is
C (glm-5.3-flash, swapped order) vs B (claude-fable-5, original order), so a
flip conflates judge identity with position. A zero flip rate therefore means
"no evidence of position bias robust even across judge change", not a
pure-position estimate; a HIGH flip rate would need a same-judge control
before any position-bias claim.

Usage:
    python tools/judge_bias_probe.py --sheet evals/annotation/sheet-h073gov.json \
        --raters evals/annotation/raterB-h073gov.json evals/annotation/raterC-h073gov-swap-2026-09-14.json \
        [--out evals/probes/judge-bias-h073gov-2026-09-14.json]
    python tools/judge_bias_probe.py --selftest
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


PASS_STATUSES = {"passed"}


def rank(xs: Sequence[float]) -> list[float]:
    """Average ranks (ties get the mean of their positions)."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    n = len(xs)
    if n < 2 or len(ys) != n:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None  # zero variance on at least one side: correlation undefined
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / (sxx * syy) ** 0.5


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    return pearson(rank(xs), rank(ys))


def degenerate(xs: Sequence[float], ys: Sequence[float]) -> str | None:
    """Human-readable reason when the correlation is undefined, else None."""
    if len(set(xs)) <= 1:
        return "zero variance in length"
    if len(set(ys)) <= 1:
        return "zero variance in score axis (degenerate: constant verdicts)"
    return None


def answer_length(run: dict[str, Any]) -> dict[str, int]:
    """Judge's answer = the run's findings output; length in chars and words."""
    text = " ".join(str(f.get("finding", "")) for f in run.get("findings", []))
    return {"chars": len(text), "words": len(text.split()), "n_findings": len(run.get("findings", []))}


def rater_a_detected(run: dict[str, Any]) -> bool:
    """Mechanical layer: canonical required type present, or a listed alias (GOLD_PROTOCOL label policy)."""
    req = run.get("required_finding_types", [])
    aliases = run.get("accepted_finding_aliases", {})
    canon = set(req) | {a for t in req for a in aliases.get(t, [])}
    return bool(canon & {f.get("type") for f in run.get("findings", [])})


def load_raters(paths: list[Path]) -> list[dict[str, Any]]:
    raters = []
    for p in paths:
        d = json.loads(p.read_text(encoding="utf-8"))
        raters.append({"name": Path(p).name, "meta": d, "map": {j["run"]: j for j in d["runs"]}})
    return raters


def length_bias(sheet: dict[str, Any], raters: list[dict[str, Any]]) -> dict[str, Any]:
    runs = sheet["runs"]
    lens = [answer_length(r) for r in runs]
    axes: dict[str, list[float]] = {
        "rater_a_detected": [1.0 if rater_a_detected(r) else 0.0 for r in runs],
        "scorer_passed": [1.0 if r.get("verification_status") in PASS_STATUSES else 0.0 for r in runs],
    }
    for rt in raters:
        axes[f"{rt['name']}_caught"] = [
            1.0 if rt["map"].get(r["run"], {}).get("caught") in ("yes", "partial") else 0.0 for r in runs
        ]
        axes[f"{rt['name']}_type_correct"] = [
            1.0 if rt["map"].get(r["run"], {}).get("type_correct") is True else 0.0 for r in runs
        ]
        axes[f"{rt['name']}_false_positives"] = [
            float(rt["map"].get(r["run"], {}).get("false_positives", 0)) for r in runs
        ]
    rows = {}
    for axis, ys in axes.items():
        for m in ("chars", "words", "n_findings"):
            xs = [l[m] for l in lens]
            rho = spearman(xs, ys)
            rows[f"{axis}~{m}"] = {
                "spearman_rho": None if rho is None else round(rho, 4),
                "undefined_reason": None if rho is not None else degenerate(xs, ys),
            }
        hi = [l for l, y in zip(lens, ys) if y > 0]
        lo = [l for l, y in zip(lens, ys) if y <= 0]
        rows[f"{axis}~group_means"] = {
            "positive_mean_chars": round(sum(x["chars"] for x in hi) / len(hi), 1) if hi else None,
            "nonpositive_mean_chars": round(sum(x["chars"] for x in lo) / len(lo), 1) if lo else None,
            "n_positive": len(hi),
        }
    flagged = sorted(
        k for k, v in rows.items()
        if k.endswith(("~chars", "~words")) and isinstance(v.get("spearman_rho"), (int, float))
        and abs(v["spearman_rho"]) >= 0.5 and "~false_positives" not in k
    )
    return {"axes": rows, "rubric_revision_flagged": flagged,
            "flag_rule": "|spearman_rho| >= 0.5 between answer length and a score axis (FP axes excluded)"}


def flip_table(sheet: dict[str, Any], rater_b: dict[str, Any], rater_c: dict[str, Any]) -> dict[str, Any]:
    flips, rows = [], []
    for r in sheet["runs"]:
        b = rater_b["map"].get(r["run"], {})
        c = rater_c["map"].get(r["run"], {})
        caught_flip = (b.get("caught") in ("yes", "partial")) != (c.get("caught") in ("yes", "partial"))
        type_flip = b.get("type_correct") is not c.get("type_correct")
        fp_flip = b.get("false_positives", 0) != c.get("false_positives", 0)
        row = {"run": r["run"], "b_caught": b.get("caught"), "c_caught": c.get("caught"),
               "b_type_correct": b.get("type_correct"), "c_type_correct": c.get("type_correct"),
               "b_fp": b.get("false_positives"), "c_fp": c.get("false_positives"),
               "flip": caught_flip or type_flip or fp_flip}
        rows.append(row)
        if row["flip"]:
            flips.append(row)
    n = len(rows)
    return {"n_runs": n,
            "caught_flips": sum(1 for x in rows if x["b_caught"] != x["c_caught"]),
            "type_correct_flips": sum(1 for x in rows if x["b_type_correct"] is not x["c_type_correct"]),
            "fp_localization_flips": sum(1 for x in rows if x["b_fp"] != x["c_fp"]),
            "any_flip_rate": round(len(flips) / max(1, n), 4),
            "flips": flips, "rows": rows}


def mechanical_layer(sheet: dict[str, Any]) -> dict[str, Any]:
    runs = sheet["runs"]
    det = [rater_a_detected(r) for r in runs]
    return {"n_runs": len(runs), "rater_a_detected": sum(det),
            "verification_status_distribution": {
                s: sum(1 for r in runs if r.get("verification_status") == s)
                for s in sorted({r.get("verification_status", "") for r in runs})}}


def run_probe(sheet_path: Path, rater_paths: list[Path]) -> dict[str, Any]:
    sheet = json.loads(sheet_path.read_text(encoding="utf-8"))
    raters = load_raters(rater_paths)
    if len(raters) != 2:
        raise SystemExit("expected exactly two rater files: original-order (B) and swapped (C)")
    result = {
        "probe": "H4658 LLM-judge bias probes (length + position-swap) on 20260703-h073gov",
        "sheet": str(sheet_path),
        "rater_original_order": raters[0]["name"],
        "rater_swapped_order": raters[1]["name"],
        "design_disclosure": ("swap comparison is cross-judge (C glm-5.3-flash swapped vs B claude-fable-5 "
                              "original); zero flips = no position-bias evidence robust across judge change, "
                              "not a pure-position estimate"),
        "mechanical_layer": mechanical_layer(sheet),
        "length_bias": length_bias(sheet, raters),
        "position_swap": flip_table(sheet, raters[0], raters[1]),
    }
    return result


def selftest() -> int:
    ok = True

    def check(name: str, cond: bool) -> None:
        nonlocal ok
        print(f"  {'PASS' if cond else 'FAIL'} {name}")
        ok = ok and cond

    # spearman sanity: perfect monotone, inverse, degenerate
    check("spearman perfect", spearman([1.0, 2.0, 3.0, 4.0], [10.0, 20.0, 30.0, 40.0]) == 1.0)
    check("spearman inverse", spearman([1.0, 2.0, 3.0, 4.0], [40.0, 30.0, 20.0, 10.0]) == -1.0)
    check("spearman ties", abs((spearman([1.0, 1.0, 2.0, 2.0], [1.0, 2.0, 3.0, 4.0]) or 0.0)
                               - 0.8944271910) < 1e-6)
    check("spearman degenerate is None", spearman([5.0, 5.0, 5.0], [1.0, 2.0, 3.0]) is None)

    # rater_a_detected honors aliases
    run = {"required_finding_types": ["t"], "accepted_finding_aliases": {"t": ["a"]},
           "findings": [{"type": "a"}]}
    check("alias detected", rater_a_detected(run) is True)
    run["findings"] = [{"type": "other"}]
    check("miss detected", rater_a_detected(run) is False)

    # flip table flags a genuine flip
    sheet = {"runs": [{"run": "x1", "findings": [{"type": "t"}], "required_finding_types": ["t"],
                       "accepted_finding_aliases": {}, "verification_status": "passed"}]}
    b = {"runs": [{"run": "x1", "caught": "yes", "type_correct": True, "false_positives": 0}]}
    c = {"runs": [{"run": "x1", "caught": "no", "type_correct": True, "false_positives": 0}]}
    bt, ct = load_raters([Path("b.json"), Path("c.json")]) if False else ({"name": "b", "map": {"x1": b["runs"][0]}},
                                                                          {"name": "c", "map": {"x1": c["runs"][0]}})
    ft = flip_table(sheet, bt, ct)
    check("flip detected", ft["type_correct_flips"] == 0 and ft["caught_flips"] == 1 and ft["any_flip_rate"] == 1.0)

    # length bias flags a planted monotone length-score coupling
    sheet2 = {"runs": [
        {"run": f"r{i}", "verification_status": "passed" if i >= 2 else "failed",
         "required_finding_types": ["t"], "accepted_finding_aliases": {},
         "findings": [{"type": "t", "finding": "x" * (100 * (i + 1))}]}
        for i in range(4)]}
    single = {"name": "b", "map": {f"r{i}": {"caught": "yes", "type_correct": True, "false_positives": 0}
                                   for i in range(4)}}
    lb = length_bias(sheet2, [single])
    check("length coupling flagged", "scorer_passed~chars" in lb["rubric_revision_flagged"])

    print("SELFTEST " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sheet", type=Path, help="annotation sheet (frozen corpus)")
    ap.add_argument("--raters", type=Path, nargs=2, metavar=("ORIGINAL", "SWAPPED"))
    ap.add_argument("--out", type=Path, help="write JSON results here (stdout otherwise)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.sheet or not args.raters:
        ap.error("--sheet and --raters are required unless --selftest")
    result = run_probe(args.sheet, args.raters)
    payload = json.dumps(result, ensure_ascii=False, indent=1)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
