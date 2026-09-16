#!/usr/bin/env python3
"""H5010 — same-judge candidate-order paired probe (position-bias isolation).

Companion of H4658's tools/judge_bias_probe.py. H4658's position-swap pass was
cross-judge (rater C glm-5.3-flash reversed vs rater B claude-fable-5 original),
so its 0/25 flip result cannot identify a position-only effect. This tool runs
the corrected design: the SAME judge scores the SAME 25 items under BOTH
candidate orders (original vs reversed+renumbered), with identity-blinded
presentation and randomized call order, and analyzes the paired outcomes.

Subcommands:
  prep      Generate 50 blinded judgement tasks (25 items x 2 orders) in a
            seeded shuffled call order + the hidden condition mapping.
  reveal    Map blinded responses back to (item, condition), compute paired
            discordance, flip-rate CI, directional first-position preference.
  selftest  Offline positive/negative controls (no model calls):
            - a synthetic known first-position selector MUST be detected;
            - an order-invariant (content-identity) selector MUST remain
              invariant after mapping candidate positions back.

Stdlib only. No network. Responses are produced by the human/model judge
outside this tool and fed back as JSON.

_Гасунс_
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

SEED = 5010
SHEET_DEFAULT = "evals/annotation/sheet-h073gov.json"


# ---------------------------------------------------------------- presentation

def _canon_type_set(run: dict) -> set:
    types = set(run.get("required_finding_types", []))
    for aliases in run.get("accepted_finding_aliases", {}).values():
        types.update(aliases)
    return types


def blinded_findings(run: dict, order: str) -> list[dict]:
    """Present findings in `order` ('original'|'reversed'), positions renumbered,
    identity fields (id/style_id/council_status) stripped."""
    findings = list(run["findings"])
    if order == "reversed":
        findings = findings[::-1]
    return [
        {
            "position": pos,
            "type": f["type"],
            "severity": f["severity"],
            "span_id": f.get("span_id"),
            "finding": f["finding"],
        }
        for pos, f in enumerate(findings, start=1)
    ]


def task_payload(run: dict, order: str) -> dict:
    """Everything the judge may see for one blinded task."""
    return {
        "run_label": run["run"],
        "purpose": run["purpose"],
        "required_finding_types": run.get("required_finding_types", []),
        "accepted_finding_aliases": run.get("accepted_finding_aliases", {}),
        "input_text": run["input_text"],
        "findings": blinded_findings(run, order),
    }


def build_tasks(sheet: dict, seed: int = SEED):
    """Return (tasks, mapping): 25 items x 2 orders, shuffled call order,
    opaque task ids; mapping kept separate for the reveal step."""
    entries = []
    for run in sheet["runs"]:
        for order in ("original", "reversed"):
            entries.append((run, order))
    rng = random.Random(seed)
    rng.shuffle(entries)
    tasks, mapping = [], []
    for task_no, (run, order) in enumerate(entries, start=1):
        tasks.append({"task": f"task-{task_no:03d}",
                      **task_payload(run, order)})
        mapping.append({
            "task": f"task-{task_no:03d}",
            "run": run["run"],
            "condition": order,
            "n_findings": len(run["findings"]),
        })
    return tasks, mapping


# ------------------------------------------------------------------- statistics

def wilson_ci(k: int, n: int, z: float = 1.959963985) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _first_canon_position(payload_findings: list[dict], canon_set: set):
    for f in payload_findings:
        if f["type"] in canon_set:
            return f["position"]
    return None


# -------------------------------------------------------------------- selectors
# Synthetic judges for the offline controls. Both consume the BLINDED payload
# (positions, not identities) and emit verdicts; the reveal step maps back.

def selector_first_position(task: dict, canon_set: set) -> dict:
    """Positive control: a judge that only credits whatever sits at position 1
    (classic strong primacy selector). Order-dependent by construction."""
    first = task["findings"][0]
    hit = first["type"] in canon_set
    fps = sum(1 for f in task["findings"][1:3] if f["type"] not in canon_set)
    return {"caught": "yes" if hit else "no",
            "type_correct": hit,
            "false_positives": fps,
            "notes": "synthetic first-position selector"}


def selector_content_identity(task: dict, canon_set: set) -> dict:
    """Negative control: a judge keyed to candidate CONTENT, not position.
    Identical verdicts for any permutation of the same findings."""
    types = [f["type"] for f in task["findings"]]
    hit = any(t in canon_set for t in types)
    seen, fps = set(), 0
    for t in types:
        if t in seen:
            fps += 1
        seen.add(t)
    return {"caught": "yes" if hit else "partial",
            "type_correct": hit,
            "false_positives": fps,
            "notes": "synthetic content-identity (order-invariant) selector"}


def synthetic_responses(tasks: list[dict], sheet: dict, selector) -> list[dict]:
    """Produce blinded responses for every task with a synthetic selector."""
    by_run = {r["run"]: r for r in sheet["runs"]}
    responses = []
    for task in tasks:
        canon = _canon_type_set(by_run[task["run_label"]])
        v = selector(task, canon)
        responses.append({"task": task["task"], **v})
    return responses


# ---------------------------------------------------------------------- reveal

def reveal(tasks: list[dict], mapping: list[dict], responses: list[dict],
           sheet: dict) -> dict:
    """Map responses back to (run, condition) and compute the paired analysis."""
    resp_by_id = {r["task"]: r for r in responses}
    task_by_id = {t["task"]: t for t in tasks}
    by_run = {r["run"]: r for r in sheet["runs"]}

    pairs: dict[str, dict[str, dict]] = {}
    invalid: list[dict] = []
    for m in mapping:
        task = task_by_id.get(m["task"])
        resp = resp_by_id.get(m["task"])
        if task is None or resp is None:
            invalid.append({"run": m["run"], "condition": m["condition"],
                            "reason": "missing_response"})
            continue
        # integrity: the task must still be the blinded payload for this
        # (run, condition) pair under the frozen sheet
        want = task_payload(by_run[m["run"]], m["condition"])
        if task["findings"] != want["findings"]:
            invalid.append({"run": m["run"], "condition": m["condition"],
                            "reason": "task_mapping_mismatch"})
            continue
        v = {"caught": resp.get("caught"),
             "type_correct": resp.get("type_correct"),
             "false_positives": resp.get("false_positives"),
             "notes": resp.get("notes", "")}
        if (v["caught"] not in ("yes", "partial", "no")
                or not isinstance(v["type_correct"], bool)
                or not isinstance(v["false_positives"], int)):
            invalid.append({"run": m["run"], "condition": m["condition"],
                            "reason": "malformed_verdict"})
            continue
        pairs.setdefault(m["run"], {})[m["condition"]] = v

    rows, discordant_runs = [], []
    presentations = []  # (target_pos, positive, run, condition)
    for run_id in sorted(pairs):
        cond = pairs[run_id]
        if "original" not in cond or "reversed" not in cond:
            invalid.append({"run": run_id, "reason": "missing_condition"})
            continue
        run = by_run[run_id]
        canon = _canon_type_set(run)
        a, b = cond["original"], cond["reversed"]
        row = {
            "run": run_id,
            "caught_A": a["caught"], "caught_B": b["caught"],
            "caught_flip": a["caught"] != b["caught"],
            "type_correct_A": a["type_correct"],
            "type_correct_B": b["type_correct"],
            "type_correct_flip": a["type_correct"] != b["type_correct"],
            "fp_A": a["false_positives"], "fp_B": b["false_positives"],
            "fp_flip": a["false_positives"] != b["false_positives"],
            "discordant": (a["caught"] != b["caught"]
                           or a["type_correct"] != b["type_correct"]
                           or a["false_positives"] != b["false_positives"]),
        }
        rows.append(row)
        if row["discordant"]:
            discordant_runs.append(run_id)
        for cond_name, v, order_key in (("original", a, "original"),
                                        ("reversed", b, "reversed")):
            tpos = _first_canon_position(
                task_payload(run, order_key)["findings"], canon)
            positive = (v["caught"] == "yes") or (v["type_correct"] is True)
            presentations.append((tpos, positive, run_id, cond_name))

    n = len(rows)
    k = len(discordant_runs)
    lo, hi = wilson_ci(k, n)

    pos_obs = [(positive, pos) for (pos, positive, _r, _c) in presentations
               if pos is not None]
    yes_pos = [pos for positive, pos in pos_obs if positive]
    no_pos = [pos for positive, pos in pos_obs if not positive]
    med_yes = sorted(yes_pos)[len(yes_pos) // 2] if yes_pos else None
    med_no = sorted(no_pos)[len(no_pos) // 2] if no_pos else None
    n_early_yes = sum(1 for positive, pos in pos_obs if positive and pos <= 2)
    n_late_yes = sum(1 for positive, pos in pos_obs if positive and pos > 2)
    n_early_no = sum(1 for positive, pos in pos_obs if not positive and pos <= 2)
    n_late_no = sum(1 for positive, pos in pos_obs if not positive and pos > 2)
    direction = {
        "positive_verdicts_target_pos_1_2": n_early_yes,
        "positive_verdicts_target_pos_3plus": n_late_yes,
        "negative_verdicts_target_pos_1_2": n_early_no,
        "negative_verdicts_target_pos_3plus": n_late_no,
        "median_target_pos_when_positive": med_yes,
        "median_target_pos_when_negative": med_no,
        "first_position_preference_detected": bool(
            med_yes is not None and med_no is not None
            and med_yes < med_no
            and n_early_yes / max(1, n_early_yes + n_late_yes)
            > n_early_no / max(1, n_early_no + n_late_no)),
    }

    return {
        "n_items": n,
        "n_invalid": len(invalid),
        "invalid": invalid,
        "discordant_pairs": k,
        "discordant_runs": sorted(discordant_runs),
        "flip_rate": (k / n) if n else 0.0,
        "flip_rate_wilson95": [lo, hi],
        "directional_first_position": direction,
        "material_order_sensitivity_flag": bool(
            n > 0 and n and (k / n) >= 0.20 and lo > 0.0),
        "rows": rows,
    }


def run_selector_analysis(sheet: dict, selector, seed: int = SEED) -> dict:
    """Full blinded pipeline (prep -> synthetic responses -> reveal -> metrics)
    for a synthetic selector. Same code path as the real analysis."""
    tasks, mapping = build_tasks(sheet, seed=seed)
    responses = synthetic_responses(tasks, sheet, selector)
    return reveal(tasks, mapping, responses, sheet)


# --------------------------------------------------------------------- selftest

def selftest() -> int:
    sheet = json.loads(Path(SHEET_DEFAULT).read_text(encoding="utf-8"))

    # Positive control: known first-position selector MUST be detected.
    # Exact expectation 16/25 on the frozen sheet: the 9 items whose canonical
    # findings sit at BOTH position 1 and position n are indistinguishable to a
    # pure first-position selector under reversal; the other 16 MUST discord.
    res_pos = run_selector_analysis(sheet, selector_first_position)
    assert res_pos["n_items"] == 25, res_pos["n_items"]
    assert res_pos["n_invalid"] == 0, res_pos["invalid"]
    assert res_pos["discordant_pairs"] == 16, res_pos["discordant_pairs"]
    assert res_pos["directional_first_position"]["first_position_preference_detected"], \
        res_pos["directional_first_position"]
    assert res_pos["material_order_sensitivity_flag"], "positive control must flag"

    # Negative control: order-invariant selector MUST remain invariant after
    # mapping positions back to candidate identities.
    res_neg = run_selector_analysis(sheet, selector_content_identity)
    assert res_neg["n_items"] == 25, res_neg["n_items"]
    assert res_neg["n_invalid"] == 0, res_neg["invalid"]
    assert res_neg["discordant_pairs"] == 0, res_neg["discordant_pairs"]
    assert not res_neg["material_order_sensitivity_flag"]
    assert not res_neg["directional_first_position"]["first_position_preference_detected"]

    # CI sanity: 0/25 must NOT collapse to [0,0] (zero flips != proof of absence)
    lo, hi = wilson_ci(0, 25)
    assert lo == 0.0 and 0.10 < hi < 0.20, (lo, hi)

    print("selftest PASS: first-position selector detected "
          f"({res_pos['discordant_pairs']}/25 discordant, flag=True); "
          f"order-invariant selector invariant (0/25, flag=False); "
          f"0/25 Wilson95 upper={hi:.3f}")
    return 0


# ------------------------------------------------------------------------ CLI

def cmd_prep(args) -> int:
    sheet = json.loads(Path(args.sheet).read_text(encoding="utf-8"))
    tasks, mapping = build_tasks(sheet, seed=SEED)
    tasks_path = Path(args.out_tasks)
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    tasks_path.write_text(json.dumps(
        {"seed": SEED, "sheet": args.sheet,
         "sheet_sha256": hashlib.sha256(Path(args.sheet).read_bytes()).hexdigest(),
         "n_tasks": len(tasks), "tasks": tasks},
        ensure_ascii=False, indent=1), encoding="utf-8")
    Path(args.out_mapping).write_text(json.dumps(mapping, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    print(f"prep: wrote {len(tasks)} blinded tasks -> {tasks_path}")
    return 0


def cmd_reveal(args) -> int:
    bundle = json.loads(Path(args.tasks).read_text(encoding="utf-8"))
    tasks = bundle["tasks"]
    mapping = json.loads(Path(args.mapping).read_text(encoding="utf-8"))
    responses = json.loads(Path(args.responses).read_text(encoding="utf-8"))
    if isinstance(responses, dict):
        responses = responses.get("responses", [])
    sheet = json.loads(Path(args.sheet).read_text(encoding="utf-8"))
    result = reveal(tasks, mapping, responses, sheet)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1),
                              encoding="utf-8")
    print(f"reveal: {result['n_items']} pairs, {result['discordant_pairs']} "
          f"discordant ({result['flip_rate']:.1%}), "
          f"wilson95=[{result['flip_rate_wilson95'][0]:.3f},"
          f"{result['flip_rate_wilson95'][1]:.3f}], "
          f"flag={result['material_order_sensitivity_flag']}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep")
    p.add_argument("--sheet", default=SHEET_DEFAULT)
    p.add_argument("--out-tasks", required=True)
    p.add_argument("--out-mapping", required=True)
    p.set_defaults(func=cmd_prep)
    p = sub.add_parser("reveal")
    p.add_argument("--tasks", required=True)
    p.add_argument("--mapping", required=True)
    p.add_argument("--responses", required=True)
    p.add_argument("--sheet", default=SHEET_DEFAULT)
    p.add_argument("--out", required=True)
    p.set_defaults(func=cmd_reveal)
    sub.add_parser("selftest").set_defaults(func=lambda a: selftest())
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
